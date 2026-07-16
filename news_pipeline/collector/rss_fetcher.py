"""RSS フィードから記事メタデータを取得するモジュール。

feedparser にURLを直接渡すとタイムアウト指定ができず、応答しないフィードが
1つあると収集全体がハングする。requests でタイムアウト付き取得してから
feedparser にパースさせる2段構成にしている。
"""

import hashlib
import logging
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import feedparser
import requests

logger = logging.getLogger(__name__)

# dedup を妨げるトラッキング用クエリパラメータ（utm_* はプレフィックスで判定）
_TRACKING_PARAMS = {"fbclid", "gclid", "yclid", "mc_cid", "mc_eid"}

_FEED_TIMEOUT_SECONDS = 30

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}


def _parse_published(entry) -> str | None:
    """RSS エントリの published フィールドを ISO 8601 文字列に変換する。パース失敗時は None。"""
    if hasattr(entry, "published"):
        try:
            dt = parsedate_to_datetime(entry.published)
            return dt.isoformat()
        except Exception:
            pass
    return None


def _normalize_url(url: str) -> str:
    """トラッキング用クエリパラメータ（utm_* 等）と fragment を除去する。

    同じ記事が utm 付きで再配信されると URL 完全一致の dedup をすり抜けて
    重複収集・重複通知されるため、記事ID計算・保存の前に正規化する。
    """
    parts = urlsplit(url)
    query = [
        (k, v)
        for k, v in parse_qsl(parts.query, keep_blank_values=True)
        if not k.lower().startswith("utm_") and k.lower() not in _TRACKING_PARAMS
    ]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), ""))


def _make_article_id(url: str) -> str:
    """URL の SHA-256 ハッシュ先頭16文字を記事 ID として返す。"""
    return hashlib.sha256(url.encode()).hexdigest()[:16]


def fetch_articles(feeds: dict[str, str]) -> list[dict]:
    """RSSフィードから記事リストを返す。feeds が空の場合は空リストを返す。"""
    if not feeds:
        logger.warning("[rss_fetcher] feeds is empty")
        return []

    results = []
    for feed_url, source_name in feeds.items():
        try:
            response = requests.get(
                feed_url, headers=_HEADERS, timeout=_FEED_TIMEOUT_SECONDS
            )
            response.raise_for_status()
            feed = feedparser.parse(response.content)
            for entry in feed.entries:
                if not hasattr(entry, "link"):
                    continue
                url = _normalize_url(str(entry.link))
                results.append(
                    {
                        "article_id": _make_article_id(url),
                        "title": getattr(entry, "title", ""),
                        "url": url,
                        "source": source_name,
                        "published_at": _parse_published(entry),
                        "collected_at": datetime.now(timezone.utc).isoformat(),
                        # description は1次フィルタ用の一時情報。raw_articles 保存前に除去する。
                        "description": getattr(entry, "summary", ""),
                    }
                )
        except Exception as e:
            logger.warning("[rss_fetcher] feed error %s: %s", feed_url, e)

    return results
