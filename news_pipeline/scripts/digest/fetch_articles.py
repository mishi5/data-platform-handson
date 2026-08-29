"""週次/月次ダイジェスト用に BigQuery から記事を取り出す。

2つのモードを持つ。選定と深掘りで必要なデータ量が違うため。

  一覧モード（選定用・本文なし）:
      uv run python scripts/digest/fetch_articles.py --period week
  本文モード（深掘り用）:
      uv run python scripts/digest/fetch_articles.py --ids a1,a2,a3

ゲート条件は本番の通知経路（bq_client.get_unnotified_summaries）と同じ規則にする。
relevance_score が NULL の旧データは落とさない。
"""

import argparse
import json
import os
import sys

from dotenv import load_dotenv
from google.cloud import bigquery

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

DATASET = "tech_news"
_PERIOD_DAYS = {"week": 7, "month": 30}
_DEFAULT_MIN_IMPORTANCE = 0.65
_DEFAULT_MIN_RELEVANCE = 0.55


def resolve_days(period: str, days: int | None) -> int:
    """対象期間を日数に解決する。--days は --period より優先する。"""
    if days is not None:
        return int(days)
    return _PERIOD_DAYS[period]


def build_list_query(
    project: str, days: int, min_importance: float, min_relevance: float
) -> str:
    """選定用の一覧クエリ。本文は含めない（件数が多く巨大になるため）。

    summaries・raw_articles とも article_id ごとに1行へ畳む。畳まないと
    重複行を持つ記事が JOIN で増幅する。
    """
    imp = float(min_importance)
    rel = float(min_relevance)
    return f"""
        SELECT
          s.article_id,
          ANY_VALUE(s.title) AS title,
          ANY_VALUE(s.url) AS url,
          ANY_VALUE(s.source) AS source,
          ANY_VALUE(s.summary) AS summary,
          ANY_VALUE(s.tags) AS tags,
          ANY_VALUE(s.importance_score) AS importance_score,
          ANY_VALUE(s.relevance_score) AS relevance_score,
          MIN(r.collected_at) AS collected_at
        FROM `{project}.{DATASET}.summaries` s
        JOIN `{project}.{DATASET}.raw_articles` r USING (article_id)
        WHERE DATE(r.collected_at) >= DATE_SUB(CURRENT_DATE(), INTERVAL {days} DAY)
          AND s.importance_score >= {imp}
          AND (s.relevance_score IS NULL OR s.relevance_score >= {rel})
        GROUP BY s.article_id
        ORDER BY
          ANY_VALUE(s.importance_score) * IFNULL(ANY_VALUE(s.relevance_score), 1.0) DESC
    """


def build_content_query(
    project: str, article_ids: list[str]
) -> tuple[str, list[bigquery.ArrayQueryParameter]]:
    """深掘り用。指定記事の本文を含めて返す。"""
    if not article_ids:
        raise ValueError("article_ids is empty")
    query = f"""
        SELECT
          s.article_id,
          ANY_VALUE(s.title) AS title,
          ANY_VALUE(s.url) AS url,
          ANY_VALUE(s.source) AS source,
          ANY_VALUE(s.summary) AS summary,
          ANY_VALUE(s.tags) AS tags,
          ANY_VALUE(s.importance_score) AS importance_score,
          ANY_VALUE(s.relevance_score) AS relevance_score,
          MIN(r.collected_at) AS collected_at,
          ANY_VALUE(r.content) AS content
        FROM `{project}.{DATASET}.summaries` s
        JOIN `{project}.{DATASET}.raw_articles` r USING (article_id)
        WHERE s.article_id IN UNNEST(@ids)
        GROUP BY s.article_id
    """
    params = [bigquery.ArrayQueryParameter("ids", "STRING", article_ids)]
    return query, params


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

    if args.ids:
        ids = [i.strip() for i in args.ids.split(",") if i.strip()]
        query, params = build_content_query(project, ids)
    else:
        days = resolve_days(args.period, args.days)
        query = build_list_query(project, days, args.min_importance, args.min_relevance)
        params = None

    rows = run_query(project, query, params)
    if not rows:
        print("対象記事が0件です。期間や閾値を見直してください。", file=sys.stderr)
        return 2

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
