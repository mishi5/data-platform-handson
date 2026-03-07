from unittest.mock import patch, MagicMock
from collector.rss_fetcher import fetch_articles, FEEDS


def test_feeds_list_not_empty():
    assert len(FEEDS) > 0


def test_fetch_articles_returns_list(mocker):
    mock_feed = MagicMock()
    mock_feed.entries = [
        MagicMock(
            title="BigQuery update",
            link="https://cloud.google.com/blog/1",
            published="Sat, 08 Mar 2026 09:00:00 GMT",
        )
    ]
    mocker.patch("collector.rss_fetcher.feedparser.parse", return_value=mock_feed)

    articles = fetch_articles(["https://example.com/rss"])

    assert len(articles) == 1
    assert articles[0]["title"] == "BigQuery update"
    assert articles[0]["url"] == "https://cloud.google.com/blog/1"
    assert articles[0]["source"] == "https://example.com/rss"


def test_fetch_articles_skips_entries_without_link(mocker):
    mock_feed = MagicMock()
    mock_feed.entries = [MagicMock(spec=[])]  # link 属性なし
    mocker.patch("collector.rss_fetcher.feedparser.parse", return_value=mock_feed)

    articles = fetch_articles(["https://example.com/rss"])
    assert articles == []


def test_fetch_articles_handles_feed_error(mocker):
    mocker.patch("collector.rss_fetcher.feedparser.parse", side_effect=Exception("network error"))

    articles = fetch_articles(["https://example.com/rss"])
    assert articles == []
