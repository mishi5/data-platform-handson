import requests
import trafilatura


def fetch_content(url: str) -> str | None:
    """URL から記事本文を抽出して返す。失敗時は None。"""
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        text = trafilatura.extract(response.text)
        return text
    except Exception as e:
        print(f"[article_parser] failed to fetch {url}: {e}")
        return None
