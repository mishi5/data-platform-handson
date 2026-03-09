"""Claude API を使って記事を要約するモジュール。JSON 形式（summary/tags/importance_score）で返す。"""
import json
import logging
import anthropic
from anthropic.types import TextBlock

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """あなたはデータエンジニアリングの技術ニュースを要約するアシスタントです。
記事を読んで以下の JSON 形式で回答してください。

{
  "summary": "箇条書きで3〜5項目の技術ポイント（日本語・文字列・改行区切り）",
  "tags": ["タグ1", "タグ2"],
  "importance_score": 0.0〜1.0 (BigQuery/GCP関連なら高め)
}

JSON のみを返してください。説明文は不要です。"""


def summarize_article(title: str, content: str, api_key: str) -> dict | None:
    """Claude で記事を要約する。失敗時は None。"""
    try:
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=512,
            system=SYSTEM_PROMPT,
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
        text = block.text.strip()
        # マークダウンコードブロックを除去（```json ... ``` や ``` ... ```）
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()
        result = json.loads(text)
        # summary がリストで返された場合は文字列に変換（BQ の STRING 型に合わせる）
        if isinstance(result.get("summary"), list):
            result["summary"] = "\n".join(result["summary"])
        return result
    except Exception as e:
        logger.error("[summarizer] failed: %s", e)
        return None
