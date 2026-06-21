"""Speaker Deck のスライドPDFをテキストに書き起こすモジュール。

Speaker Deck はユーザー単位の RSS（`https://speakerdeck.com/<user>.rss`）を持つが、
本文はスライド画像のため trafilatura では取得できない。本モジュールは記事ページから
PDF を取得し、Claude のビジョン入力（document ブロック）でプレーンテキストへ書き起こす。
書き起こした本文は通常記事と同じ content として下流（要約・再採点・deepdive）に流れる。
"""

import base64
import logging
import re

import anthropic
import requests
from anthropic.types import TextBlock

logger = logging.getLogger(__name__)

# 書き起こしに使うモデル。summarizer と統一（Haiku 4.5・PDF/ビジョン対応・低コスト）。
_MODEL = "claude-haiku-4-5-20251001"

# Claude の PDF 入力上限（リクエスト 32MB）。超える PDF はスキップする。
_MAX_PDF_BYTES = 32 * 1024 * 1024

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

# 記事ページHTML内のダウンロードPDFリンク。
# 例: https://files.speakerdeck.com/presentations/<id>/<name>.pdf
_PDF_URL_RE = re.compile(r'https://files\.speakerdeck\.com/presentations/[^"\s]+?\.pdf')

_TRANSCRIBE_PROMPT = (
    "以下は Speaker Deck のプレゼンテーションスライド（PDF）です。"
    "後段の要約処理が読めるよう、各スライドの内容を日本語のプレーンテキストに"
    "書き起こしてください。技術的な要点（設計・構成・コード片・数値・結論）を"
    "漏らさず箇条書き中心で拾ってください。スライド番号や前置き・説明は不要で、"
    "書き起こした本文のみを返してください。"
)


def is_speakerdeck_url(url: str) -> bool:
    """Speaker Deck の記事URLかどうかを判定する。"""
    return "speakerdeck.com/" in url and "/presentations/" not in url


def _extract_pdf_url(html: str) -> str | None:
    """記事ページHTMLからスライドPDFのURLを抽出する。なければ None。"""
    match = _PDF_URL_RE.search(html)
    return match.group(0) if match else None


def fetch_slide_text(url: str, api_key: str) -> tuple[str | None, bool]:
    """Speaker Deck の記事URLからスライド本文（書き起こし）を返す。

    戻り値 (text, ok):
      ok=True  … 処理完了（text は書き起こし本文。PDF未発見やページ超過は None だが
                 リトライ不要のスキップ扱い）
      ok=False … HTTP/通信エラーなどリトライ対象
    """
    # 1. 記事ページHTMLを取得して PDF URL を抽出
    try:
        page = requests.get(url, headers=_HEADERS, timeout=30)
        page.raise_for_status()
    except Exception as e:
        logger.warning("[speakerdeck] failed to fetch page %s: %s", url, e)
        return None, False

    pdf_url = _extract_pdf_url(page.text)
    if not pdf_url:
        # PDF が無い（埋め込み制限・削除など）。再取得しても無駄なのでスキップ。
        logger.info("[speakerdeck] no PDF link found for %s", url)
        return None, True

    # 2. PDF をダウンロード
    try:
        pdf_resp = requests.get(pdf_url, headers=_HEADERS, timeout=60)
        pdf_resp.raise_for_status()
    except Exception as e:
        logger.warning("[speakerdeck] failed to download PDF %s: %s", pdf_url, e)
        return None, False

    pdf_bytes = pdf_resp.content
    if len(pdf_bytes) > _MAX_PDF_BYTES:
        logger.info(
            "[speakerdeck] PDF too large (%d bytes), skipping %s",
            len(pdf_bytes),
            url,
        )
        return None, True

    # 3. Claude のビジョン入力でテキスト書き起こし
    pdf_b64 = base64.standard_b64encode(pdf_bytes).decode("ascii")
    try:
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model=_MODEL,
            max_tokens=4096,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "document",
                            "source": {
                                "type": "base64",
                                "media_type": "application/pdf",
                                "data": pdf_b64,
                            },
                        },
                        {"type": "text", "text": _TRANSCRIBE_PROMPT},
                    ],
                }
            ],
        )
    except anthropic.APIStatusError as e:
        # 400（ページ超過・PDF不正など）はリトライ不要、それ以外はリトライ対象。
        if 400 <= e.status_code < 500:
            logger.info("[speakerdeck] API rejected PDF for %s: %s", url, e)
            return None, True
        logger.warning("[speakerdeck] API error for %s: %s", url, e)
        return None, False
    except Exception as e:
        logger.warning("[speakerdeck] transcription failed for %s: %s", url, e)
        return None, False

    if not message.content or not isinstance(message.content[0], TextBlock):
        return None, True
    text = message.content[0].text.strip()
    return (text or None), True
