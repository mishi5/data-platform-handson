from unittest.mock import MagicMock
from collector.rss_fetcher import fetch_articles

_DUMMY_FEEDS = {"https://example.com/rss": "Example Source"}


def _mock_response(mocker, content: bytes = b"<rss/>"):
    resp = MagicMock()
    resp.content = content
    resp.raise_for_status.return_value = None
    return mocker.patch("collector.rss_fetcher.requests.get", return_value=resp)


def test_fetch_articles_returns_list(mocker):
    mock_get = _mock_response(mocker)
    mock_feed = MagicMock()
    mock_feed.entries = [
        MagicMock(
            title="BigQuery update",
            link="https://cloud.google.com/blog/1",
            published="Sat, 08 Mar 2026 09:00:00 GMT",
        )
    ]
    mocker.patch("collector.rss_fetcher.feedparser.parse", return_value=mock_feed)

    articles = fetch_articles(_DUMMY_FEEDS)

    assert len(articles) == 1
    assert articles[0]["title"] == "BigQuery update"
    assert articles[0]["url"] == "https://cloud.google.com/blog/1"
    assert articles[0]["source"] == "Example Source"
    # フィード取得はタイムアウト付きの requests 経由で行う（ハング防止）
    assert mock_get.call_args.kwargs.get("timeout") is not None


def test_fetch_articles_returns_empty_when_feeds_empty():
    articles = fetch_articles({})
    assert articles == []


def test_fetch_articles_skips_entries_without_link(mocker):
    _mock_response(mocker)
    mock_feed = MagicMock()
    mock_feed.entries = [MagicMock(spec=[])]  # link 属性なし
    mocker.patch("collector.rss_fetcher.feedparser.parse", return_value=mock_feed)

    articles = fetch_articles(_DUMMY_FEEDS)
    assert articles == []


def test_fetch_articles_handles_feed_error(mocker):
    mocker.patch(
        "collector.rss_fetcher.requests.get", side_effect=Exception("network error")
    )

    articles = fetch_articles(_DUMMY_FEEDS)
    assert articles == []


def test_fetch_articles_handles_http_error(mocker):
    resp = MagicMock()
    resp.raise_for_status.side_effect = Exception("404 Not Found")
    mocker.patch("collector.rss_fetcher.requests.get", return_value=resp)

    articles = fetch_articles(_DUMMY_FEEDS)
    assert articles == []
