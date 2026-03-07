import hashlib
import feedparser
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

FEEDS = [
    "https://cloudblog.withgoogle.com/rss/",
    "https://cloud.google.com/feeds/bigquery-release-notes.xml",
    "https://www.getdbt.com/blog/rss.xml",
    "https://www.databricks.com/feed",
    "https://www.snowflake.com/blog/feed/",
    "https://www.infoq.com/data-engineering/rss/",
    "https://zenn.dev/topics/bigquery/feed",
]


def _parse_published(entry) -> str | None:
    if hasattr(entry, "published"):
        try:
            dt = parsedate_to_datetime(entry.published)
            return dt.isoformat()
        except Exception:
            pass
    return None


def _make_article_id(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()[:16]


def fetch_articles(feeds: list[str] = None) -> list[dict]:
    """RSSフィードから記事リストを返す。"""
    if feeds is None:
        feeds = FEEDS

    results = []
    for feed_url in feeds:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries:
                if not hasattr(entry, "link"):
                    continue
                results.append({
                    "article_id": _make_article_id(entry.link),
                    "title": getattr(entry, "title", ""),
                    "url": entry.link,
                    "source": feed_url,
                    "published_at": _parse_published(entry),
                    "collected_at": datetime.now(timezone.utc).isoformat(),
                })
        except Exception as e:
            print(f"[rss_fetcher] feed error {feed_url}: {e}")

    return results
