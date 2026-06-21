"""記事URLから本文テキストを取得するモジュール。requests + trafilatura を使用。

Speaker Deck の記事はスライド画像のため trafilatura では取得できない。
URL を判定して speakerdeck モジュール（PDF→Claudeビジョン書き起こし）へ委譲する。
"""

import requests
import trafilatura  # type: ignore[import-untyped]

import speakerdeck

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}


def fetch_content(url: str, api_key: str | None = None) -> tuple[str | None, bool]:
    """URL から記事本文を抽出する。

    Speaker Deck の記事はスライドPDFを Claude で書き起こす（api_key が必要）。
    それ以外は requests + trafilatura でHTML本文を抽出する。

    戻り値 (text, ok):
      ok=True  … 取得に成功（text は本文。抽出できなければ None だがリトライ不要）
      ok=False … HTTP/通信エラー（リトライ対象）
    """
    if speakerdeck.is_speakerdeck_url(url):
        if not api_key:
            # api_key 無しでは書き起こせない。リトライ不要のスキップ。
            return None, True
        return speakerdeck.fetch_slide_text(url, api_key)
    try:
        response = requests.get(url, headers=_HEADERS, timeout=30)
        response.raise_for_status()
    except Exception as e:
        print(f"[article_parser] failed to fetch {url}: {e}")
        return None, False
    text = trafilatura.extract(response.text)  # type: ignore[attr-defined]
    return text, True
