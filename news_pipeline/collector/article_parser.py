"""記事URLから本文テキストを取得するモジュール。requests + trafilatura を使用。"""

import requests
import trafilatura  # type: ignore[import-untyped]

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}


def fetch_content(url: str) -> tuple[str | None, bool]:
    """URL から記事本文を抽出する。

    戻り値 (text, ok):
      ok=True  … HTTP取得に成功（text は本文。抽出できなければ None だがリトライ不要）
      ok=False … HTTP/通信エラー（リトライ対象）
    """
    try:
        response = requests.get(url, headers=_HEADERS, timeout=30)
        response.raise_for_status()
    except Exception as e:
        print(f"[article_parser] failed to fetch {url}: {e}")
        return None, False
    text = trafilatura.extract(response.text)  # type: ignore[attr-defined]
    return text, True
