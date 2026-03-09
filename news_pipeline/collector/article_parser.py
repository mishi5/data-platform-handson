"""記事URLから本文テキストを取得するモジュール。requests + trafilatura を使用。"""
import requests
import trafilatura  # type: ignore[import-untyped]


def fetch_content(url: str) -> str | None:
    """URL から記事本文を抽出して返す。失敗時は None。"""
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        text = trafilatura.extract(response.text)  # type: ignore[attr-defined]
        return text
    except Exception as e:
        print(f"[article_parser] failed to fetch {url}: {e}")
        return None
