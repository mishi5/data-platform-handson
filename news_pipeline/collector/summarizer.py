"""Claude API を使って記事を要約・採点するモジュール。

- summarize_article: 要約(summary)+タグ(tags)+重要度(importance_score) を1回で生成
- score_article: 重要度スコアのみを再計算（/recalculate 用）
スコア判定基準は _build_scoring_criteria に集約し両者で共用する。
スコアロジックを変えたら SCORING_VERSION を +1 すること。
"""

import json
import logging
import anthropic
from anthropic.types import TextBlock

logger = logging.getLogger(__name__)

# スコアロジックの版。_build_scoring_criteria を変えたら +1 する。
SCORING_VERSION = 1

_MODEL = "claude-haiku-4-5-20251001"

_SUMMARY_PROMPT_TEMPLATE = """あなたはデータエンジニアリングの技術ニュースを要約するアシスタントです。
記事を読んで以下の JSON 形式で回答してください。

{{
  "summary": "箇条書きで3〜5項目の技術ポイント（日本語・文字列・改行区切り）",
  "tags": ["タグ1", "タグ2"],
  "importance_score": 0.0〜1.0
}}

{scoring_criteria}

JSON のみを返してください。説明文は不要です。"""

_SCORE_PROMPT_TEMPLATE = """あなたはデータエンジニアリングの技術ニュースの重要度を評価するアシスタントです。
記事を読んで以下の JSON 形式で重要度スコアのみを回答してください。

{{
  "importance_score": 0.0〜1.0
}}

{scoring_criteria}

JSON のみを返してください。説明文は不要です。"""


def _build_scoring_criteria(keywords: list[str]) -> str:
    """importance_score の判定基準を組み立てる。summarize / score_article で共用。"""
    if keywords:
        items = "\n".join(f"  - {kw}" for kw in keywords)
    else:
        items = "  （キーワード未設定のため、データエンジニアリング全般を対象とする）"
    return (
        "importance_score の判定基準：\n"
        "- 以下のキーワードに関連する内容であるほど高いスコアを付ける\n"
        f"{items}\n"
        "- 複数のキーワードに関連するほど高くする\n"
        "- 全く関連しない場合は 0.1 以下にする"
    )


def _build_system_prompt(keywords: list[str]) -> str:
    """要約+タグ+スコア用のシステムプロンプト。"""
    return _SUMMARY_PROMPT_TEMPLATE.format(
        scoring_criteria=_build_scoring_criteria(keywords)
    )


def _build_score_only_prompt(keywords: list[str]) -> str:
    """スコアのみ用のシステムプロンプト。"""
    return _SCORE_PROMPT_TEMPLATE.format(
        scoring_criteria=_build_scoring_criteria(keywords)
    )


def _strip_code_fence(text: str) -> str:
    """```json ... ``` や ``` ... ``` のコードフェンスを除去する。"""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    return text


def summarize_article(
    title: str, content: str, api_key: str, keywords: list[str] | None = None
) -> dict | None:
    """Claude で記事を要約する。失敗時は None。keywords に基づいて importance_score を判定する。"""
    system_prompt = _build_system_prompt(keywords or [])
    try:
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model=_MODEL,
            max_tokens=512,
            system=system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": f"タイトル: {title}\n\n本文:\n{content[:3000]}",
                }
            ],
        )
        block = message.content[0]
        if not isinstance(block, TextBlock):
            return None
        result = json.loads(_strip_code_fence(block.text))
        if isinstance(result.get("summary"), list):
            result["summary"] = "\n".join(result["summary"])
        return result
    except Exception as e:
        logger.error("[summarizer] failed: %s", e)
        return None


def score_article(
    title: str, content: str, api_key: str, keywords: list[str] | None = None
) -> float | None:
    """記事の importance_score のみを再計算する。失敗時は None。"""
    system_prompt = _build_score_only_prompt(keywords or [])
    try:
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model=_MODEL,
            max_tokens=64,
            system=system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": f"タイトル: {title}\n\n本文:\n{content[:3000]}",
                }
            ],
        )
        block = message.content[0]
        if not isinstance(block, TextBlock):
            return None
        result = json.loads(_strip_code_fence(block.text))
        score = result.get("importance_score")
        if score is None:
            return None
        return float(score)
    except Exception as e:
        logger.error("[summarizer] score failed: %s", e)
        return None
