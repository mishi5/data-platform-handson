"""データ基盤との関連度（relevance_score）を TypeSafe Jev で判定するモジュール。

Jev は文章を生成せず、型付きの判断と確率だけを返すモデル。関連度は
「この記事の技法の適用対象はデータ／データ基盤か」という Yes/No（Noul）の
確率として受け取り、そのまま relevance_score にする。

Claude の 0〜1 スコアは 0.5 のような丸い値に寄りやすく、閾値を 0.55 に逃がして
いた。Noul は確率なので境界がなだらかで、単価も Haiku の約1/50で済む
（評価は scripts/eval_jev.py）。/collect・/resummarize・/recalculate・スライドの
1次フィルタの全経路でこの判定を使い、summaries.relevance_score の尺度を揃える。

判定に失敗した場合は None を返す。呼び出し側は「判定不能＝ゲートを通す」として
扱う（取りこぼし防止。main.passes_thresholds）。
"""

import functools
import logging

from typesafe_sdk import Noul, TypeSafeClient

logger = logging.getLogger(__name__)

# 版を固定する。jev-latest は更新で確率の出方（＝最適な閾値）が変わりうるため、
# 上げるときは scripts/eval_jev.py で閾値を確かめてから変える。
MODEL = "jev-1.13.0"

# 本文はタイトル＋冒頭だけで判定できる。長く渡すと無関係な文脈で判定がぶれ、
# 評価でも 8000 字より 2000 字の方が Claude との一致が高かった。
_MAX_BODY_CHARS = 2000
_TIMEOUT_SEC = 30.0

# Jev は英語が主言語のため定義は英語で書く（評価では日本語の質問文よりわずかに良かった）。
# 判定原理は summarizer._DOMAIN_DEFINITION と同じ「技法の適用対象がデータ基盤か」。
DOMAIN_DEFINITION = {
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
        # 業界でのデータ活用論（ベンダーブログに多い）を Jev はデータ基盤と取り違えやすい
        "business or industry commentary about using data and analytics (healthcare, pharma, finance, "
        "media, marketing) that does not explain how data systems are built or operated",
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
            "Pharma launch analytics: how to win the first 90 days (industry commentary, no data-system engineering)",
            "Media finance teams need to understand their audience (business commentary)",
        ],
    },
}

QUESTION = Noul(
    instructions={
        "question": (
            "Is the main subject of this article something the technique is applied to "
            "within data engineering / data platforms, as defined below?"
        ),
        "definition": DOMAIN_DEFINITION,
    },
    criteria={
        "true": "The article's techniques are applied to data, data pipelines or a data platform (in_scope).",
        "false": "The article is about an out_of_scope target, even if it mentions AI, IaC or cloud.",
    },
)


@functools.lru_cache(maxsize=1)
def _client(api_key: str) -> TypeSafeClient:
    return TypeSafeClient(api_key=api_key, model=MODEL, timeout=_TIMEOUT_SEC)


def build_state(title: str, body: str) -> dict:
    """Jev に渡す state。本文が無ければタイトルだけで判定させる（スライドの1次フィルタ）。"""
    state = {"title": title}
    if body:
        state["body"] = body[:_MAX_BODY_CHARS]
    return state


def judge_relevance(title: str, body: str, api_key: str) -> float | None:
    """記事がデータ基盤を対象としている確率（0〜1）を返す。失敗時は None。"""
    try:
        res = _client(api_key).system_one(
            build_state(title, body), {"data_platform": QUESTION}
        )
        return float(res.answers["data_platform"].noul)
    except Exception as e:
        logger.error("[relevance] judge failed for %r: %s", title[:60], e)
        return None
