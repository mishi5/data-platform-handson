"""週次/月次ダイジェスト用に BigQuery から記事を取り出す。

2つのモードを持つ。選定と深掘りで必要なデータ量が違うため。

  一覧モード（選定用・本文なし）:
      uv run python scripts/digest/fetch_articles.py --period week
  本文モード（深掘り用）:
      uv run python scripts/digest/fetch_articles.py --ids a1,a2,a3

ゲート条件は本番の通知経路（bq_client.get_unnotified_summaries）と同じ規則にする。
relevance_score が NULL の旧データは落とさない。

対象期間は「昨日まで」の N 日間（JST）。当日を含めると翌週の窓と1日重なり、
同じ記事が2回のダイジェストに載る。
"""

import argparse
import json
import os
import sys
from datetime import date, datetime, timedelta, timezone

from dotenv import load_dotenv
from google.cloud import bigquery

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

DATASET = "tech_news"
TIMEZONE = "Asia/Tokyo"
_JST = timezone(timedelta(hours=9))
_PERIOD_DAYS = {"week": 7, "month": 30}
_DEFAULT_MIN_IMPORTANCE = 0.65
_DEFAULT_MIN_RELEVANCE = 0.55

# summaries には同一 article_id の行が複数ある（再要約など）。ANY_VALUE は列ごとに
# 独立して行を選ぶため、title と summary が別々の行から来て混ざりうる。本番の
# get_unnotified_summaries と同じく ROW_NUMBER で1行に畳む。同点は scoring_version
# の新しい方 → summary の辞書順で決め、実行ごとにぶれないようにする。
_SUMMARY_PICK = """(
          SELECT * EXCEPT (_rn) FROM (
            SELECT *, ROW_NUMBER() OVER (
              PARTITION BY article_id
              ORDER BY importance_score DESC, IFNULL(scoring_version, 0) DESC, summary
            ) AS _rn
            FROM `{project}.{dataset}.summaries`
          ) WHERE _rn = 1
        )"""

# raw_articles 側も1行に畳む。窓の判定は初回収集日（collected_at 最古）で行う。
# 再収集で新しい行が増えたときに、既に載せた記事が翌週の窓へ再浮上しないため。
_RAW_FIRST = """(
          SELECT * EXCEPT (_rn) FROM (
            SELECT article_id, collected_at, content, ROW_NUMBER() OVER (
              PARTITION BY article_id ORDER BY collected_at ASC
            ) AS _rn
            FROM `{project}.{dataset}.raw_articles`
          ) WHERE _rn = 1
        )"""

# 本文モードは「本文がある行」を優先する。本文取得リトライで content が NULL の
# 行が同じ article_id に混ざっていても、本文を取りこぼさない。指定 id で先に絞って
# から畳む（絞らないと content 列を全件スキャンする）。
_RAW_WITH_CONTENT = """(
          SELECT * EXCEPT (_rn) FROM (
            SELECT article_id, collected_at, content, ROW_NUMBER() OVER (
              PARTITION BY article_id
              ORDER BY IFNULL(LENGTH(content), 0) DESC, collected_at ASC
            ) AS _rn
            FROM `{project}.{dataset}.raw_articles`
            WHERE article_id IN UNNEST(@ids)
          ) WHERE _rn = 1
        )"""

_COLUMNS = """
          s.article_id,
          s.title,
          s.url,
          s.source,
          s.summary,
          s.tags,
          s.importance_score,
          s.relevance_score,
          r.collected_at"""


def resolve_days(period: str, days: int | None) -> int:
    """対象期間を日数に解決する。--days は --period より優先する。"""
    if days is None:
        return _PERIOD_DAYS[period]
    days = int(days)
    if days < 1:
        raise ValueError(f"--days must be >= 1 (got {days})")
    return days


def window_dates(days: int, today: date | None = None) -> tuple[date, date]:
    """対象期間を (開始日, 終了日) で返す。両端とも含む JST の日付。

    終了日は「昨日」。当日は収集途中（毎朝6:00 JST）なので含めない。含めると
    次回の窓と1日重なり、同じ記事が2回のダイジェストに載る。
    """
    if today is None:
        today = datetime.now(_JST).date()
    end = today - timedelta(days=1)
    start = today - timedelta(days=int(days))
    return start, end


def build_list_query(
    project: str, days: int, min_importance: float, min_relevance: float
) -> str:
    """選定用の一覧クエリ。本文は含めない（件数が多く巨大になるため）。"""
    imp = float(min_importance)
    rel = float(min_relevance)
    n = int(days)
    summaries = _SUMMARY_PICK.format(project=project, dataset=DATASET)
    raws = _RAW_FIRST.format(project=project, dataset=DATASET)
    return f"""
        SELECT{_COLUMNS}
        FROM {summaries} s
        JOIN {raws} r USING (article_id)
        WHERE DATE(r.collected_at, '{TIMEZONE}')
                >= DATE_SUB(CURRENT_DATE('{TIMEZONE}'), INTERVAL {n} DAY)
          AND DATE(r.collected_at, '{TIMEZONE}') < CURRENT_DATE('{TIMEZONE}')
          AND s.importance_score >= {imp}
          AND (s.relevance_score IS NULL OR s.relevance_score >= {rel})
        ORDER BY s.importance_score * IFNULL(s.relevance_score, 1.0) DESC
    """


def build_content_query(
    project: str, article_ids: list[str]
) -> tuple[str, list[bigquery.ArrayQueryParameter]]:
    """深掘り用。指定記事の本文を含めて返す。"""
    if not article_ids:
        raise ValueError("article_ids is empty")
    summaries = _SUMMARY_PICK.format(project=project, dataset=DATASET)
    raws = _RAW_WITH_CONTENT.format(project=project, dataset=DATASET)
    query = f"""
        SELECT{_COLUMNS},
          r.content
        FROM {summaries} s
        JOIN {raws} r USING (article_id)
        WHERE s.article_id IN UNNEST(@ids)
    """
    params = [bigquery.ArrayQueryParameter("ids", "STRING", article_ids)]
    return query, params


def missing_ids(requested: list[str], rows: list[dict]) -> list[str]:
    """指定したのに取れなかった article_id を返す。黙って件数を減らさないため。"""
    found = {row.get("article_id") for row in rows}
    return [i for i in requested if i not in found]


def run_query(project: str, query: str, params: list | None) -> list[dict]:
    client = bigquery.Client(project=project)
    job_config = bigquery.QueryJobConfig(query_parameters=params) if params else None
    rows = client.query(query, job_config=job_config).result()
    return [dict(row) for row in rows]


def _json_default(value):
    """TIMESTAMP など JSON に落ちない型を文字列にする。"""
    return value.isoformat() if hasattr(value, "isoformat") else str(value)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--period", choices=["week", "month"], default="week")
    parser.add_argument("--days", type=int, default=None, help="期間を直接指定")
    parser.add_argument(
        "--ids", default=None, help="本文モード。カンマ区切りの article_id"
    )
    parser.add_argument("--min-importance", type=float, default=_DEFAULT_MIN_IMPORTANCE)
    parser.add_argument("--min-relevance", type=float, default=_DEFAULT_MIN_RELEVANCE)
    parser.add_argument("--out", default=None, help="出力先ファイル（既定は標準出力）")
    args = parser.parse_args()

    project = os.environ.get("GCP_PROJECT_ID")
    if not project:
        print("GCP_PROJECT_ID is not set", file=sys.stderr)
        return 1

    ids: list[str] = []
    header = ""
    if args.ids is not None:
        ids = [i.strip() for i in args.ids.split(",") if i.strip()]
        if not ids:
            print("--ids に有効な article_id がありません", file=sys.stderr)
            return 1
        query, params = build_content_query(project, ids)
    else:
        try:
            days = resolve_days(args.period, args.days)
        except ValueError as e:
            print(str(e), file=sys.stderr)
            return 1
        start, end = window_dates(days)
        header = f"対象期間 {start.isoformat()} 〜 {end.isoformat()}（JST・{days}日間）"
        query = build_list_query(project, days, args.min_importance, args.min_relevance)
        params = None

    rows = run_query(project, query, params)

    if ids:
        lost = missing_ids(ids, rows)
        if lost:
            print(
                f"指定した article_id のうち {len(lost)} 件が見つかりません: "
                f"{', '.join(lost)}",
                file=sys.stderr,
            )
    if not rows:
        print("対象記事が0件です。期間や閾値を見直してください。", file=sys.stderr)
        return 2

    if header:
        print(header, file=sys.stderr)
    payload = json.dumps(rows, ensure_ascii=False, indent=2, default=_json_default)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(payload)
        print(f"{len(rows)} 件を {args.out} に出力しました", file=sys.stderr)
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
