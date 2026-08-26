"""Claude Sonnet を使って記事を深堀り分析するモジュール。

Sonnet 5 は adaptive thinking が既定で走るため、レスポンスの先頭ブロックが
thinking になりうる。content[0] を決め打ちせず TextBlock を探すこと。
"""
import logging

import anthropic
from anthropic.types import TextBlock

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """あなたはデータエンジニアリングの技術記事を深く分析するエキスパートです。
記事を読んで、以下の構成でMarkdown形式の詳細分析を日本語で行ってください。

📌 背景・概要
（この技術/発表の背景と概要を2〜3文で）

🔍 技術的なポイント（詳細）
（重要な技術的詳細を箇条書きで4〜6項目）

💡 実践への示唆
（実際の現場でどう活かせるか、注意点など2〜3文で）

Markdownのみを返してください。説明文や前置きは不要です。"""


def deepdive_article(title: str, content: str, api_key: str) -> str | None:
    """Claude Sonnet を使って記事を深堀り分析する。Markdown文字列を返す。失敗時は None。"""
    try:
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-sonnet-5",
            # thinking + 本文の合算上限。1024 では thinking だけで使い切る
            max_tokens=4096,
            thinking={"type": "adaptive"},
            system=_SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": f"タイトル: {title}\n\n本文:\n{content[:5000]}",
                }
            ],
        )
        block = next(
            (b for b in message.content if isinstance(b, TextBlock)),
            None,
        )
        if block is None:
            return None
        return block.text.strip()
    except Exception as e:
        logger.error("[deepdiver] failed: %s", e)
        return None
