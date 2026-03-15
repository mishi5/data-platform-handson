"""RSS フィードから記事メタデータを取得するモジュール。"""
import hashlib
import feedparser
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime


def _parse_published(entry) -> str | None:
    """RSS エントリの published フィールドを ISO 8601 文字列に変換する。パース失敗時は None。"""
    if hasattr(entry, "published"):
        try:
            dt = parsedate_to_datetime(entry.published)
            return dt.isoformat()
        except Exception:
            pass
    return None


def _make_article_id(url: str) -> str:
    """URL の SHA-256 ハッシュ先頭16文字を記事 ID として返す。"""
    return hashlib.sha256(url.encode()).hexdigest()[:16]


def fetch_articles(feeds: dict[str, str]) -> list[dict]:
    """RSSフィードから記事リストを返す。feeds が空の場合は空リストを返す。"""
    if not feeds:
        print("[rss_fetcher] feeds is empty")
        return []

    results = []
    for feed_url, source_name in feeds.items():
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries:
                if not hasattr(entry, "link"):
                    continue
                url = str(entry.link)
                results.append({
                    "article_id": _make_article_id(url),
                    "title": getattr(entry, "title", ""),
                    "url": url,
                    "source": source_name,
                    "published_at": _parse_published(entry),
                    "collected_at": datetime.now(timezone.utc).isoformat(),
                })
        except Exception as e:
            print(f"[rss_fetcher] feed error {feed_url}: {e}")

    return results
