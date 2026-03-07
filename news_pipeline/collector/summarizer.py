import json
import logging
import anthropic

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """あなたはデータエンジニアリングの技術ニュースを要約するアシスタントです。
記事を読んで以下の JSON 形式で回答してください。

{
  "summary": "箇条書きで3〜5項目の技術ポイント（日本語）",
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
        return json.loads(message.content[0].text)
    except Exception as e:
        logger.error("[summarizer] failed: %s", e)
        return None
