"""採点プロンプトのオフライン評価スクリプト。

ユニットテストは Anthropic クライアントをモックするためプロンプトの品質を測れない。
本番デプロイ前に、実際に Claude を叩いて正解セットに対する判定を確認する。

使い方:
    cd news_pipeline
    uv run python scripts/eval_scoring.py            # 正解セット（keep/drop）を評価
    uv run python scripts/eval_scoring.py --sample 50  # 通過帯からサンプルして目視用に出力

正解セットは LABELS で定義する。タイトルの部分一致で BigQuery から本文を引く。
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "collector"))

from dotenv import load_dotenv  # noqa: E402
from google.cloud import bigquery  # noqa: E402

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

from bq_client import BQClient  # noqa: E402
from summarizer import score_article  # noqa: E402

PROJECT_ID = os.environ["GCP_PROJECT_ID"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
DATASET = "tech_news"

IMPORTANCE_THRESHOLD = 0.65
RELEVANCE_THRESHOLD = 0.55

# 正解セット: (タイトルの部分一致, 期待する判定)
# "keep" = 通知されるべき / "drop" = 落とされるべき
LABELS: list[tuple[str, str]] = [
    # --- ユーザーが対象外と指定した記事 ---
    ("IAM Policy Autopilot", "drop"),
    ("AI駆動開発で仕様はどこまで書くべきか", "drop"),
    ("WSL2 から 1Password の SSH エージェント", "drop"),
    ("JANOG58 NOCサーバーチーム", "drop"),
    # お気に入り済みだが本文は一般的なシステム移行論。ユーザー判断で drop 側。
    ("AIに任せたレガシーシステムのモダナイズ", "drop"),
    # Google Cloud の ADC を 1Password に保存する話も開発環境 Tips
    ("ADC ファイルを 1Password に保存", "drop"),
    # --- お気に入り済み（データ基盤系）＝残すべき ---
    ("AI.DETECT_ANOMALIES", "keep"),
    ("Dataformのincremental", "keep"),
    ("Query Tags", "keep"),
    ("Icebergで紐解くSnowflake", "keep"),
    ("Snowflake Cortex Analyst", "keep"),
    ("クラウド版 Dataform のワークフローを JSON", "keep"),
    ("Claude Codeで Snowflake + dbtプロジェクト", "keep"),
    ("Omni公式のClaude Code Plugin", "keep"),
    ("メルカリが全社で導入したNotion Architecture", "keep"),
    ("Fivetran and dbt are one company", "keep"),
]


def _fetch_articles(client: bigquery.Client, patterns: list[str]) -> list[dict]:
    """タイトルの部分一致で summaries + raw_articles.content を引く。"""
    like = " OR ".join(f"s.title LIKE @p{i}" for i in range(len(patterns)))
    query = f"""
        SELECT s.article_id, s.title, s.importance_score AS old_score,
               ANY_VALUE(r.content) AS content
        FROM `{PROJECT_ID}.{DATASET}.summaries` s
        LEFT JOIN `{PROJECT_ID}.{DATASET}.raw_articles` r USING (article_id)
        WHERE {like}
        GROUP BY s.article_id, s.title, s.importance_score
    """
    params = [
        bigquery.ScalarQueryParameter(f"p{i}", "STRING", f"%{p}%")
        for i, p in enumerate(patterns)
    ]
    job_config = bigquery.QueryJobConfig(query_parameters=params)
    return [dict(row) for row in client.query(query, job_config=job_config).result()]


def _fetch_sample(client: bigquery.Client, n: int) -> list[dict]:
    """通過帯（importance >= 0.65）からサンプルを引く。目視ラベル用。"""
    query = f"""
        SELECT s.article_id, s.title, s.importance_score AS old_score,
               ANY_VALUE(r.content) AS content
        FROM `{PROJECT_ID}.{DATASET}.summaries` s
        LEFT JOIN `{PROJECT_ID}.{DATASET}.raw_articles` r USING (article_id)
        WHERE s.importance_score >= {IMPORTANCE_THRESHOLD}
        GROUP BY s.article_id, s.title, s.importance_score
        ORDER BY FARM_FINGERPRINT(s.article_id)
        LIMIT {n}
    """
    return [dict(row) for row in client.query(query).result()]


def _score(article: dict, keywords: list[str], favorite_tags: list[str]) -> dict | None:
    return score_article(
        title=article["title"],
        content=article.get("content") or "",
        api_key=ANTHROPIC_API_KEY,
        keywords=keywords,
        favorite_tags=favorite_tags,
    )


def _passes(scores: dict) -> bool:
    if scores["importance_score"] < IMPORTANCE_THRESHOLD:
        return False
    rel = scores.get("relevance_score")
    return not (rel is not None and rel < RELEVANCE_THRESHOLD)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", type=int, default=0)
    args = parser.parse_args()

    client = bigquery.Client(project=PROJECT_ID)
    bq = BQClient(project=PROJECT_ID)
    favorite_tags = bq.get_favorite_tag_counts(5)
    keywords: list[str] = []
    print(f"favorite_tags: {favorite_tags}\n")

    if args.sample:
        rows = _fetch_sample(client, args.sample)
        print(f"{'imp':>5} {'rel':>5} {'old':>5}  judge  title")
        for r in rows:
            s = _score(r, keywords, favorite_tags)
            if s is None:
                print(f"{'ERR':>5} {'':>5} {r['old_score']:>5.2f}  -      {r['title']}")
                continue
            rel = s.get("relevance_score")
            judge = "KEEP" if _passes(s) else "DROP"
            print(
                f"{s['importance_score']:>5.2f} "
                f"{(rel if rel is not None else float('nan')):>5.2f} "
                f"{r['old_score']:>5.2f}  {judge}   {r['title']}"
            )
        return

    patterns = [p for p, _ in LABELS]
    rows = _fetch_articles(client, patterns)
    by_pattern: dict[str, dict] = {}
    for pattern, _ in LABELS:
        match = next((r for r in rows if pattern in r["title"]), None)
        if match is None:
            print(f"[warn] not found in BigQuery: {pattern}")
            continue
        by_pattern[pattern] = match

    correct = 0
    total = 0
    failures: list[str] = []
    print(f"{'imp':>5} {'rel':>5} {'old':>5}  expect judge  title")
    for pattern, expected in LABELS:
        article = by_pattern.get(pattern)
        if article is None:
            continue
        scores = _score(article, keywords, favorite_tags)
        if scores is None:
            print(f"[error] scoring failed: {pattern}")
            continue
        judge = "keep" if _passes(scores) else "drop"
        total += 1
        ok = judge == expected
        correct += ok
        rel = scores.get("relevance_score")
        rel_str = f"{rel:.2f}" if rel is not None else " n/a"
        mark = " " if ok else "*"
        print(
            f"{scores['importance_score']:>5.2f} {rel_str:>5} "
            f"{article['old_score']:>5.2f}  {expected:<6} {judge:<5}{mark} "
            f"{article['title']}"
        )
        if not ok:
            failures.append(f"{expected}→{judge}: {article['title']}")

    print(f"\n正解 {correct}/{total}")
    if failures:
        print("\n誤判定:")
        for f in failures:
            print(f"  - {f}")


if __name__ == "__main__":
    main()
