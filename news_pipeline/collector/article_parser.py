import trafilatura


def fetch_content(url: str) -> str | None:
    """URL から記事本文を抽出して返す。失敗時は None。"""
    try:
        downloaded = trafilatura.fetch_url(url)
        if downloaded is None:
            return None
        text = trafilatura.extract(downloaded)
        return text
    except Exception as e:
        print(f"[article_parser] failed to fetch {url}: {e}")
        return None
