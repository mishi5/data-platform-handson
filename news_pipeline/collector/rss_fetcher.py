import hashlib
import feedparser
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

FEEDS = {
    "https://cloud.google.com/feeds/bigquery-release-notes.xml": "Google Cloud BigQuery",
    "https://www.getdbt.com/blog/rss.xml": "dbt Blog",
    "https://www.databricks.com/feed": "Databricks Blog",
    "https://www.snowflake.com/blog/feed/": "Snowflake Blog",
    "https://www.infoq.com/data-engineering/rss/": "InfoQ Data Engineering",
    "https://zenn.dev/topics/bigquery/feed": "Zenn BigQuery",
}


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


def fetch_articles(feeds: dict[str, str] = None) -> list[dict]:
    """RSSフィードから記事リストを返す。"""
    if feeds is None:
        feeds = FEEDS

    results = []
    for feed_url, source_name in feeds.items():
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries:
                if not hasattr(entry, "link"):
                    continue
                results.append({
                    "article_id": _make_article_id(entry.link),
                    "title": getattr(entry, "title", ""),
                    "url": entry.link,
                    "source": source_name,
                    "published_at": _parse_published(entry),
                    "collected_at": datetime.now(timezone.utc).isoformat(),
                })
        except Exception as e:
            print(f"[rss_fetcher] feed error {feed_url}: {e}")

    return results
