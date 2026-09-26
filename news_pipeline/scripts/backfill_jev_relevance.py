"""summaries.relevance_score を Jev の判定で付け直す一回性メンテナンススクリプト。

SCORING_VERSION 4 で relevance_score の尺度を Claude の 0〜1 スコアから Jev の確率
（collector/relevance.py）に変えた。importance の採点は版 3 と同じなので、Claude を
呼ぶ /recalculate は使わず、版 3 の行の relevance だけを Jev で付け直して版 4 にする
（Claude なら約 $20、Jev なら約 $0.2）。

1. scoring_version = 3 の summaries を本文付きで取得（本文が無ければ要約文で判定）
2. 本番と同じ質問（relevance.QUESTION / build_state）で Jev に並列で問い合わせ
3. 更新前の Claude の relevance_score を BACKUP_TABLE に退避（初回のみ作成）。
   切り戻しと、scripts/eval_jev.py の比較対象（Claude の判定）に使う
4. 結果を一時テーブルに load し、1回の UPDATE で relevance_score と scoring_version を更新
5. 前後の分布を表示

Jev の呼び出しに失敗した行は版 3 のまま残る。0 件になるまで再実行する。
streaming buffer 制約があるため、/collect 直後（JST 6:00〜7:30）は実行しないこと。

実行:
    cd news_pipeline
    uv run python scripts/backfill_jev_relevance.py --dry-run   # 判定と分布の確認のみ
    uv run python scripts/backfill_jev_relevance.py             # 実行
"""

import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "collector"))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

from google.cloud import bigquery  # noqa: E402
from typesafe_sdk import AsyncTypeSafeClient  # noqa: E402

from relevance import MODEL, QUESTION, build_state  # noqa: E402
from summarizer import SCORING_VERSION  # noqa: E402

PROJECT_ID = os.environ["GCP_PROJECT_ID"]
TYPESAFE_API_KEY = os.environ["TYPESAFE_API_KEY"]
DATASET = "tech_news"
FROM_VERSION = 3
TMP_TABLE = f"{PROJECT_ID}.{DATASET}._jev_relevance_backfill"
BACKUP_TABLE = f"{PROJECT_ID}.{DATASET}.summaries_claude_relevance_v3"
CONCURRENCY = 8

assert SCORING_VERSION == FROM_VERSION + 1, "版 3→4 の移行専用スクリプト"


def fetch_targets(client: bigquery.Client) -> list[dict]:
    query = f"""
        SELECT s.article_id,
               ANY_VALUE(s.title) AS title,
               ANY_VALUE(s.summary) AS summary,
               ANY_VALUE(s.relevance_score) AS old_relevance,
               ANY_VALUE(r.content) AS content
        FROM `{PROJECT_ID}.{DATASET}.summaries` s
        LEFT JOIN `{PROJECT_ID}.{DATASET}.raw_articles` r USING (article_id)
        WHERE s.scoring_version = {FROM_VERSION}
        GROUP BY s.article_id
    """
    return [dict(row) for row in client.query(query).result()]


async def judge_all(rows: list[dict]) -> dict[str, float]:
    sem = asyncio.Semaphore(CONCURRENCY)
    results: dict[str, float] = {}
    failed = 0

    async with AsyncTypeSafeClient(api_key=TYPESAFE_API_KEY, model=MODEL) as client:

        async def one(row: dict) -> None:
            nonlocal failed
            body = row["content"] or row["summary"] or ""
            try:
                async with sem:
                    res = await client.system_one(
                        build_state(row["title"], body), {"data_platform": QUESTION}
                    )
                results[row["article_id"]] = float(res.answers["data_platform"].noul)
            except Exception as e:  # noqa: BLE001
                failed += 1
                print(f"  [error] {row['title'][:50]}: {e}")
            done = len(results) + failed
            if done % 200 == 0:
                print(f"  judged {done}/{len(rows)}")

        await asyncio.gather(*(one(r) for r in rows))
    print(f"judged {len(results)} / failed {failed}")
    return results


def show_distribution(rows: list[dict], results: dict[str, float]) -> None:
    buckets = [0, 0.1, 0.2, 0.3, 0.5, 0.8, 1.01]
    print("\nJev relevance の分布:")
    for lo, hi in zip(buckets, buckets[1:]):
        n = sum(lo <= v < hi for v in results.values())
        print(f"  [{lo:.1f}, {hi:.1f})  {n}")
    old_pass = {r["article_id"] for r in rows if (r["old_relevance"] or 0) >= 0.55}
    new_pass = {k for k, v in results.items() if v >= 0.2}
    print(
        f"\n関連度ゲート通過: Claude(>=0.55) {len(old_pass & results.keys())}"
        f" → Jev(>=0.2) {len(new_pass)}"
        f"  （Claude のみ通過 {len((old_pass & results.keys()) - new_pass)}"
        f" / Jev のみ通過 {len(new_pass - old_pass)}）"
    )


def backup(client: bigquery.Client) -> None:
    """版 3 の Claude の relevance を退避する。再実行時は最初の退避を残す。"""
    client.query(
        f"""
        CREATE TABLE IF NOT EXISTS `{BACKUP_TABLE}` AS
        SELECT article_id, ANY_VALUE(relevance_score) AS relevance_score
        FROM `{PROJECT_ID}.{DATASET}.summaries`
        WHERE scoring_version = {FROM_VERSION}
        GROUP BY article_id
        """
    ).result()


def apply(client: bigquery.Client, results: dict[str, float]) -> int:
    rows = [{"article_id": k, "relevance": v} for k, v in results.items()]
    job_config = bigquery.LoadJobConfig(
        schema=[
            bigquery.SchemaField("article_id", "STRING"),
            bigquery.SchemaField("relevance", "FLOAT64"),
        ],
        write_disposition="WRITE_TRUNCATE",
    )
    client.load_table_from_json(rows, TMP_TABLE, job_config=job_config).result()
    try:
        job = client.query(
            f"""
            UPDATE `{PROJECT_ID}.{DATASET}.summaries` s
            SET relevance_score = b.relevance, scoring_version = {SCORING_VERSION}
            FROM `{TMP_TABLE}` b
            WHERE s.article_id = b.article_id AND s.scoring_version = {FROM_VERSION}
            """
        )
        job.result()
        return job.num_dml_affected_rows or 0
    finally:
        client.delete_table(TMP_TABLE, not_found_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    client = bigquery.Client(project=PROJECT_ID)
    rows = fetch_targets(client)
    print(f"targets (scoring_version={FROM_VERSION}): {len(rows)}")
    if not rows:
        return

    results = asyncio.run(judge_all(rows))
    show_distribution(rows, results)
    if args.dry_run:
        print("\n--dry-run のため更新しない")
        return

    backup(client)
    updated = apply(client, results)
    print(f"\nupdated {updated} rows → scoring_version={SCORING_VERSION}")
    remaining = len(rows) - len(results)
    if remaining:
        print(f"{remaining} 件は失敗したため版 {FROM_VERSION} のまま。再実行する。")


if __name__ == "__main__":
    main()
