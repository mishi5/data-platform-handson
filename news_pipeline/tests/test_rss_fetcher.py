import os
import sys
from unittest.mock import MagicMock

# rss_fetcher は release_notes を bare import するため collector を path に追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "collector"))

from collector.rss_fetcher import _normalize_url, fetch_articles

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


def test_normalize_url_strips_tracking_params():
    assert (
        _normalize_url(
            "https://example.com/post?utm_source=rss&utm_medium=feed&id=1&fbclid=xyz"
        )
        == "https://example.com/post?id=1"
    )


def test_normalize_url_strips_fragment():
    assert _normalize_url("https://example.com/post#section-2") == (
        "https://example.com/post"
    )


def test_normalize_url_keeps_clean_url_unchanged():
    assert (
        _normalize_url("https://example.com/post?page=2")
        == "https://example.com/post?page=2"
    )


def test_fetch_articles_normalizes_entry_url(mocker):
    _mock_response(mocker)
    mock_feed = MagicMock()
    mock_feed.entries = [
        MagicMock(
            title="T",
            link="https://example.com/post?utm_source=rss",
            published="Sat, 08 Mar 2026 09:00:00 GMT",
        )
    ]
    mocker.patch("collector.rss_fetcher.feedparser.parse", return_value=mock_feed)

    articles = fetch_articles(_DUMMY_FEEDS)
    assert articles[0]["url"] == "https://example.com/post"


_RELEASE_NOTE_URL = (
    "https://docs.cloud.google.com/bigquery/docs/release-notes#September_24_2026"
)


def test_normalize_url_keeps_release_notes_fragment():
    # リリースノートは1ページ内のアンカーが日付ごとの記事。fragment を落とすと
    # 全エントリが同じ URL になり、2件目以降が dedup で捨てられる
    assert _normalize_url(_RELEASE_NOTE_URL) == _RELEASE_NOTE_URL


def test_normalize_url_release_notes_still_strips_tracking_params():
    assert _normalize_url(
        "https://docs.cloud.google.com/bigquery/docs/release-notes"
        "?utm_source=rss#September_24_2026"
    ) == _RELEASE_NOTE_URL


def test_fetch_articles_release_notes_title_has_feed_title(mocker):
    # エントリのタイトルは日付だけなので、何の更新か分かるようフィード名を前に付ける
    _mock_response(mocker)
    mock_feed = MagicMock()
    mock_feed.feed = {"title": "BigQuery - Release notes"}
    mock_feed.entries = [
        MagicMock(
            title="September 24, 2026",
            link=_RELEASE_NOTE_URL,
            published="Thu, 24 Sep 2026 07:00:00 GMT",
        ),
        MagicMock(
            title="September 22, 2026",
            link=_RELEASE_NOTE_URL.replace("24", "22"),
            published="Tue, 22 Sep 2026 07:00:00 GMT",
        ),
    ]
    mocker.patch("collector.rss_fetcher.feedparser.parse", return_value=mock_feed)

    articles = fetch_articles(_DUMMY_FEEDS)

    assert articles[0]["title"] == "BigQuery - Release notes: September 24, 2026"
    assert articles[0]["url"] == _RELEASE_NOTE_URL
    # 日付ごとに別の記事として扱われる
    assert articles[0]["article_id"] != articles[1]["article_id"]


def test_fetch_articles_other_titles_unchanged(mocker):
    _mock_response(mocker)
    mock_feed = MagicMock()
    mock_feed.feed = {"title": "Some Blog"}
    mock_feed.entries = [
        MagicMock(
            title="Post",
            link="https://example.com/post",
            published="Sat, 08 Mar 2026 09:00:00 GMT",
        )
    ]
    mocker.patch("collector.rss_fetcher.feedparser.parse", return_value=mock_feed)

    assert fetch_articles(_DUMMY_FEEDS)[0]["title"] == "Post"
