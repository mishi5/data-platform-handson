"""TypeSafe Jev による採点の PoC 評価スクリプト。

Claude（summarizer.score_article）の採点を Jev の型付き判断で置き換えられるかを測る。

  1. 一致率: Claude が採点した記事を判定区分ごとに層化サンプルし、
     Jev のスコアが Claude の通過／関連度落ち／重要度落ちをどれだけ再現するか（AUC）。
  2. 正解セット: eval_scoring.LABELS（keep/drop）とお気に入り（keep）で Claude と Jev の正解率。
     Jev の閾値は 1 の層化サンプルで決め、正解セットには当てはめるだけにする（過適合防止）。

Claude の relevance は summaries_claude_relevance_v3（backfill_jev_relevance.py が
Jev に切り替える前に退避したもの）から読む。summaries.relevance_score は既に Jev の値。

variant で「質問文の言語（en/ja）」「本文の長さ」を振る。en2_2000 が本番（relevance.py）
と同じ質問。Jev の応答は JEV_CACHE（既定 scripts/.jev_cache.json）にキャッシュし、
再実行で課金しない。

使い方:
    cd news_pipeline
    uv run python scripts/eval_jev.py --per-stratum 50
    uv run python scripts/eval_jev.py --claude-gold   # 正解セットを Claude でも採点
"""

import argparse
import asyncio
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "collector"))
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

from google.cloud import bigquery  # noqa: E402
from typesafe_sdk import AsyncTypeSafeClient, Noul, Score  # noqa: E402

from eval_scoring import LABELS  # noqa: E402
from relevance import MODEL as RELEVANCE_MODEL  # noqa: E402
from relevance import QUESTION as PROD_QUESTION  # noqa: E402
from summarizer import _DOMAIN_DEFINITION  # noqa: E402

PROJECT_ID = os.environ["GCP_PROJECT_ID"]
DATASET = "tech_news"
MODEL = RELEVANCE_MODEL
IMPORTANCE_THRESHOLD = 0.65
RELEVANCE_THRESHOLD = 0.55
# Jev の単価（入力のみ課金）: $0.042 / 100万トークン
USD_PER_MTOK = 0.042

CACHE_PATH = os.environ.get(
    "JEV_CACHE", os.path.join(os.path.dirname(__file__), ".jev_cache.json")
)

# ---------------------------------------------------------------------------
# 質問定義
# ---------------------------------------------------------------------------

_DOMAIN_EN = {
    "domain": "data engineering / data platforms",
    "in_scope": [
        "data warehouses and lakehouses (BigQuery, Snowflake, Databricks, Redshift, Iceberg, Delta Lake)",
        "ETL/ELT, data pipelines and workflow orchestration (dbt, Dataform, Airflow, Dagster, Fivetran, Spark)",
        "streaming and CDC (Kafka, Flink, Debezium)",
        "data quality, data governance, data catalogs, metadata, lineage",
        "BI, visualization, semantic layers, metric definitions (Looker, Tableau, Omni)",
        "AI/LLM applied on top of a data platform (data foundations for RAG, vector search, "
        "semantic models, AI applied to building or operating the data platform itself)",
        "the data side of MLOps (feature stores, training-data pipelines)",
    ],
    "out_of_scope": [
        "general cloud operations, IAM, permissions, security, authentication",
        "network operations, server operations, general infrastructure operations",
        "developer environment and local tooling tips (SSH, shell, editors, package managers, credential storage)",
        "software development process, AI coding practices or organization theory not tied to a data platform",
        "general web / app / game development",
    ],
    "principle": (
        "Judge by what the technique is applied to, not by whether AI, Terraform/IaC or cloud "
        "appears. The same technique applied to a different target flips the answer."
    ),
    "contrast_examples": {
        "yes": [
            "Developing a Snowflake + dbt project with Claude Code (AI applied to a data platform)",
            "Managing dbt models with Terraform",
        ],
        "no": [
            "How much specification to write in AI-driven software development (general development)",
            "Automating coding-guideline reviews with GitHub Copilot (general development)",
            "Why spec gaps go unnoticed when AI modernizes a legacy system (general development)",
            "IAM Policy Autopilot supports Terraform plan files (permission management)",
            "SSoT and IaC for network configuration in a NOC server team (network operations)",
            "Using the 1Password SSH agent from WSL2 (developer environment tip)",
        ],
    },
}


def _questions(lang: str) -> dict:
    if lang == "en2":
        # 本番（relevance.py）の質問。en の定義に「業界でのデータ活用論は対象外」を足した版
        return {**_questions("en"), "data_platform": PROD_QUESTION}
    if lang == "en":
        return {
            "data_platform": Noul(
                instructions={
                    "question": (
                        "Is the main subject of this article something the technique is applied to "
                        "within data engineering / data platforms, as defined below?"
                    ),
                    "definition": _DOMAIN_EN,
                },
                criteria={
                    "true": "The article's techniques are applied to data, data pipelines or a data platform (in_scope).",
                    "false": "The article is about an out_of_scope target, even if it mentions AI, IaC or cloud.",
                },
            ),
            "depth": Score(
                instructions=(
                    "How much practical or technical value does this article offer to a working data engineer?"
                ),
                criteria=[
                    "Announcement, link list, or brief news with almost no technical detail",
                    "General introduction or basic tutorial of well-known features; correct but shallow",
                    "Concrete practical know-how: design decisions, configuration, operations or troubleshooting with specifics",
                    "In-depth technical analysis or a production case study with real-world lessons, trade-offs or scale",
                ],
            ),
            "promo": Noul(
                instructions=(
                    "Is this article primarily marketing or product promotion rather than sharing technical knowledge?"
                ),
            ),
        }
    return {
        "data_platform": Noul(
            instructions={
                "question": "この記事の技法の適用対象は、下の定義でいうデータ／データ基盤か？",
                "definition": _DOMAIN_DEFINITION,
            },
            criteria={
                "true": "記事の技法がデータ・データパイプライン・データ基盤に適用されている（対象）",
                "false": "AI・IaC・クラウドが登場していても、適用対象が対象外の領域である",
            },
        ),
        "depth": Score(
            instructions="この記事は現場のデータエンジニアにとって、実務的・技術的にどれだけ読む価値があるか？",
            criteria=[
                "告知・リンク集・短いニュースで、技術的な中身がほぼ無い",
                "よく知られた機能の一般的な紹介や基本チュートリアルで、正しいが浅い",
                "設計判断・設定・運用・トラブル対応などの具体的な実務ノウハウがある",
                "仕組みの深い技術分析、またはスケールやトレードオフの教訓を含む本番事例",
            ],
        ),
        "promo": Noul(
            instructions="この記事は技術知見の共有ではなく、主にマーケティングや製品の宣伝か？",
        ),
    }


VARIANTS = {
    "en_8000": ("en", 8000),
    "ja_8000": ("ja", 8000),
    "en_2000": ("en", 2000),
    "en2_2000": ("en2", 2000),
}


def composite_importance(ans: dict) -> float:
    """depth（0〜3）を 0〜1 に正規化し、宣伝色で減点する。重みはコード側で持つ。"""
    return max(0.0, ans["depth"] / 3 - 0.3 * ans["promo"])


# ---------------------------------------------------------------------------
# データ取得
# ---------------------------------------------------------------------------

_ARTICLE_COLS = """
    s.article_id,
    ANY_VALUE(s.title) AS title,
    ANY_VALUE(s.importance_score) AS claude_imp,
    ANY_VALUE(b.relevance_score) AS claude_rel,
    ANY_VALUE(r.content) AS content
"""


def fetch_stratified(client: bigquery.Client, per_stratum: int) -> list[dict]:
    query = f"""
        WITH a AS (
            SELECT {_ARTICLE_COLS}
            FROM `{PROJECT_ID}.{DATASET}.summaries` s
            JOIN `{PROJECT_ID}.{DATASET}.raw_articles` r USING (article_id)
            JOIN `{PROJECT_ID}.{DATASET}.summaries_claude_relevance_v3` b USING (article_id)
            WHERE r.content IS NOT NULL AND LENGTH(r.content) > 200
            GROUP BY s.article_id
        )
        SELECT *, CASE
            WHEN claude_rel < {RELEVANCE_THRESHOLD} THEN 'rel_drop'
            WHEN claude_imp < {IMPORTANCE_THRESHOLD} THEN 'imp_drop'
            ELSE 'pass' END AS stratum
        FROM a
        QUALIFY ROW_NUMBER() OVER (
            PARTITION BY stratum ORDER BY FARM_FINGERPRINT(article_id)
        ) <= {per_stratum}
    """
    return [dict(r) for r in client.query(query).result()]


def fetch_gold(client: bigquery.Client) -> list[dict]:
    """LABELS（タイトル部分一致）とお気に入り（keep）。"""
    patterns = [p for p, _ in LABELS]
    like = " OR ".join(f"s.title LIKE @p{i}" for i in range(len(patterns)))
    params = [
        bigquery.ScalarQueryParameter(f"p{i}", "STRING", f"%{p}%")
        for i, p in enumerate(patterns)
    ]
    query = f"""
        SELECT {_ARTICLE_COLS}
        FROM `{PROJECT_ID}.{DATASET}.summaries` s
        LEFT JOIN `{PROJECT_ID}.{DATASET}.raw_articles` r USING (article_id)
        LEFT JOIN `{PROJECT_ID}.{DATASET}.summaries_claude_relevance_v3` b USING (article_id)
        WHERE {like}
        GROUP BY s.article_id
    """
    rows = [
        dict(r)
        for r in client.query(
            query, job_config=bigquery.QueryJobConfig(query_parameters=params)
        ).result()
    ]
    gold: dict[str, dict] = {}
    for pattern, expected in LABELS:
        match = next((r for r in rows if pattern in r["title"]), None)
        if match is None:
            print(f"[warn] not found: {pattern}")
            continue
        gold[match["article_id"]] = {**match, "expected": expected, "src": "labels"}

    fav_query = f"""
        SELECT {_ARTICLE_COLS}
        FROM `{PROJECT_ID}.{DATASET}.favorites` f
        JOIN `{PROJECT_ID}.{DATASET}.summaries` s USING (article_id)
        LEFT JOIN `{PROJECT_ID}.{DATASET}.raw_articles` r USING (article_id)
        LEFT JOIN `{PROJECT_ID}.{DATASET}.summaries_claude_relevance_v3` b USING (article_id)
        GROUP BY s.article_id
    """
    for r in client.query(fav_query).result():
        r = dict(r)
        # LABELS でユーザーが drop と明示した記事はそちらを優先する
        gold.setdefault(r["article_id"], {**r, "expected": "keep", "src": "favorite"})
    return list(gold.values())


# ---------------------------------------------------------------------------
# Jev 呼び出し
# ---------------------------------------------------------------------------


def _load_cache() -> dict:
    try:
        with open(CACHE_PATH) as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def _save_cache(cache: dict) -> None:
    with open(CACHE_PATH, "w") as f:
        json.dump(cache, f, ensure_ascii=False)


async def _ask(client, sem, variant: str, article: dict) -> dict:
    lang, max_chars = VARIANTS[variant]
    state = {
        "title": article["title"],
        "body": (article.get("content") or "")[:max_chars],
    }
    async with sem:
        t0 = time.perf_counter()
        res = await client.system_one(state, _questions(lang))
        elapsed = time.perf_counter() - t0
    a = res.answers
    return {
        "data_platform": a["data_platform"].noul,
        "depth": a["depth"].score,
        "depth_conf": a["depth"].confidence,
        "promo": a["promo"].noul,
        "input_tokens": res.usage.input_tokens,
        "latency": elapsed,
    }


async def run_jev(articles: list[dict], variants: list[str], concurrency: int) -> dict:
    cache = _load_cache()
    sem = asyncio.Semaphore(concurrency)
    todo = [
        (v, a)
        for v in variants
        for a in articles
        if f"{v}:{a['article_id']}" not in cache
    ]
    print(
        f"Jev calls: {len(todo)} (cached {len(articles) * len(variants) - len(todo)})"
    )
    async with AsyncTypeSafeClient(model=MODEL) as client:

        async def one(v, a):
            try:
                cache[f"{v}:{a['article_id']}"] = await _ask(client, sem, v, a)
            except Exception as e:  # noqa: BLE001
                print(f"[error] {v} {a['title'][:40]}: {e}")

        await asyncio.gather(*(one(v, a) for v, a in todo))
    _save_cache(cache)
    return cache


# ---------------------------------------------------------------------------
# 指標
# ---------------------------------------------------------------------------


def auc(pos: list[float], neg: list[float]) -> float:
    """Mann-Whitney の U から AUC（pos が neg より高い確率）。"""
    if not pos or not neg:
        return float("nan")
    wins = sum((p > n) + 0.5 * (p == n) for p in pos for n in neg)
    return wins / (len(pos) * len(neg))


def best_threshold(scores: list[float], labels: list[bool]) -> tuple[float, float]:
    """一致率が最大になる閾値（score >= t を True とする）。"""
    best = (0.5, 0.0)
    for t in sorted(set(scores)) + [1.01]:
        acc = sum((s >= t) == y for s, y in zip(scores, labels)) / len(scores)
        if acc > best[1]:
            best = (t, acc)
    return best


def spearman(x: list[float], y: list[float]) -> float:
    def ranks(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
                j += 1
            for k in range(i, j + 1):
                r[order[k]] = (i + j) / 2
            i = j + 1
        return r

    rx, ry = ranks(x), ranks(y)
    n = len(x)
    mx, my = sum(rx) / n, sum(ry) / n
    cov = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    vx = sum((a - mx) ** 2 for a in rx) ** 0.5
    vy = sum((b - my) ** 2 for b in ry) ** 0.5
    return cov / (vx * vy) if vx and vy else float("nan")


def report_agreement(variant: str, sample: list[dict], cache: dict) -> dict:
    rows = [
        (a, cache[f"{variant}:{a['article_id']}"])
        for a in sample
        if f"{variant}:{a['article_id']}" in cache
    ]
    rel_label = [a["claude_rel"] >= RELEVANCE_THRESHOLD for a, _ in rows]
    rel_score = [j["data_platform"] for _, j in rows]
    t_rel, acc_rel = best_threshold(rel_score, rel_label)

    # 重要度は関連度で通った記事の中で比べる（Claude の imp は関連度に引きずられるため）
    rel_ok = [(a, j) for a, j in rows if a["claude_rel"] >= RELEVANCE_THRESHOLD]
    imp_label = [a["claude_imp"] >= IMPORTANCE_THRESHOLD for a, _ in rel_ok]
    imp_score = [composite_importance(j) for _, j in rel_ok]
    t_imp, acc_imp = best_threshold(imp_score, imp_label)

    tokens = [j["input_tokens"] for _, j in rows]
    lat = sorted(j["latency"] for _, j in rows)
    print(f"\n=== {variant}  (n={len(rows)}) ===")
    print(
        f"関連度: AUC={auc([s for s, y in zip(rel_score, rel_label) if y], [s for s, y in zip(rel_score, rel_label) if not y]):.3f}"
        f"  Spearman(Claude rel)={spearman(rel_score, [a['claude_rel'] for a, _ in rows]):.3f}"
        f"  最良閾値={t_rel:.3f} 一致率={acc_rel:.1%}"
    )
    print(
        f"重要度: AUC={auc([s for s, y in zip(imp_score, imp_label) if y], [s for s, y in zip(imp_score, imp_label) if not y]):.3f}"
        f"  Spearman(Claude imp)={spearman(imp_score, [a['claude_imp'] for a, _ in rel_ok]):.3f}"
        f"  最良閾値={t_imp:.3f} 一致率={acc_imp:.1%}  (n={len(rel_ok)})"
    )
    print(
        f"入力トークン: 平均 {sum(tokens) / len(tokens):,.0f}"
        f"  → ${sum(tokens) / len(tokens) * USD_PER_MTOK / 1e6:.5f}/記事"
        f"  レイテンシ p50={lat[len(lat) // 2]:.2f}s p90={lat[int(len(lat) * 0.9)]:.2f}s"
    )
    return {"t_rel": t_rel, "t_imp": t_imp}


def report_gold(
    variant: str, gold: list[dict], cache: dict, th: dict, claude: dict
) -> None:
    print(
        f"\n--- 正解セット {variant}（閾値 rel>={th['t_rel']:.3f}, imp>={th['t_imp']:.3f}）---"
    )
    print(
        f"{'dp':>5} {'dep':>5} {'pro':>5} {'c_rel':>5} {'c_imp':>5}  expect jev    claude  title"
    )
    jev_ok = claude_ok = n = 0
    for a in gold:
        j = cache.get(f"{variant}:{a['article_id']}")
        if j is None:
            continue
        jev = (
            "keep"
            if j["data_platform"] >= th["t_rel"]
            and composite_importance(j) >= th["t_imp"]
            else "drop"
        )
        c = claude.get(a["article_id"])
        cj = "-"
        if c is not None:
            rel = c.get("relevance_score")
            cj = (
                "keep"
                if c["importance_score"] >= IMPORTANCE_THRESHOLD
                and (rel is None or rel >= RELEVANCE_THRESHOLD)
                else "drop"
            )
            claude_ok += cj == a["expected"]
        n += 1
        jev_ok += jev == a["expected"]
        mark = " " if jev == a["expected"] else "*"
        cmark = " " if cj in ("-", a["expected"]) else "*"
        c_rel = (
            c["relevance_score"]
            if c and c.get("relevance_score") is not None
            else float("nan")
        )
        c_imp = c["importance_score"] if c else float("nan")
        print(
            f"{j['data_platform']:>5.2f} {j['depth']:>5.2f} {j['promo']:>5.2f} {c_rel:>5.2f} {c_imp:>5.2f}"
            f"  {a['expected']:<6} {jev:<5}{mark} {cj:<5}{cmark} {a['title'][:50]}"
        )
    print(f"正解: Jev {jev_ok}/{n}" + (f"  Claude {claude_ok}/{n}" if claude else ""))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--per-stratum", type=int, default=50)
    parser.add_argument("--variants", default=",".join(VARIANTS))
    parser.add_argument("--concurrency", type=int, default=8)
    parser.add_argument(
        "--claude-gold", action="store_true", help="正解セットを Claude でも採点する"
    )
    args = parser.parse_args()
    variants = args.variants.split(",")

    bq = bigquery.Client(project=PROJECT_ID)
    gold = fetch_gold(bq)
    gold_ids = {a["article_id"] for a in gold}
    sample = [
        a
        for a in fetch_stratified(bq, args.per_stratum)
        if a["article_id"] not in gold_ids
    ]
    print(f"層化サンプル {len(sample)} 件 / 正解セット {len(gold)} 件")

    cache = asyncio.run(run_jev(sample + gold, variants, args.concurrency))

    claude: dict = {}
    if args.claude_gold:
        from bq_client import BQClient
        from summarizer import score_article

        favorite_tags = BQClient(project=PROJECT_ID).get_favorite_tag_counts(5)
        for a in gold:
            s = score_article(
                title=a["title"],
                content=a.get("content") or "",
                api_key=os.environ["ANTHROPIC_API_KEY"],
                keywords=[],
                favorite_tags=favorite_tags,
            )
            if s is not None:
                claude[a["article_id"]] = s

    for v in variants:
        th = report_agreement(v, sample, cache)
        report_gold(v, gold, cache, th, claude)


if __name__ == "__main__":
    main()
