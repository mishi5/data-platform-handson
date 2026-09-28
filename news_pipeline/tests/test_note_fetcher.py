import os
import sys
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest
import requests

# note_fetcher は兄弟モジュール（rss_fetcher）を bare import するため collector を path に追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "collector"))

from collector.note_fetcher import fetch_articles, source_name
from collector.rss_fetcher import _make_article_id, _normalize_url

_JST = timezone(timedelta(hours=9))


def _hours_ago(hours: float) -> str:
    return (datetime.now(_JST) - timedelta(hours=hours)).isoformat()


def _note(
    key: str,
    *,
    hours_ago: float = 1,
    price: int = 0,
    type_: str = "TextNote",
    urlname: str = "writer",
    name: str | None = None,
    body: str = "冒頭",
) -> dict:
    """/api/v3/hashtags/{tag}/notes の notes[] 要素を縮めたもの（実レスポンスの形に合わせる）。"""
    return {
        "key": key,
        "name": name or f"title {key}",
        "body": body,
        "price": price,
        "type": type_,
        "publish_at": _hours_ago(hours_ago),
        "like_count": 0,
        "user": {"urlname": urlname, "nickname": "N"},
    }


def _page(notes: list[dict], is_last_page: bool = False) -> MagicMock:
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.json.return_value = {
        "data": {
            "notes": notes,
            "count": 999,
            "next_page": None,
            "is_last_page": is_last_page,
        }
    }
    return resp


@pytest.fixture(autouse=True)
def no_sleep(mocker):
    return mocker.patch("collector.note_fetcher.time.sleep")


def test_source_name_prefixes_note_hash():
    assert source_name("dbt") == "note #dbt"


def test_converts_note_to_rss_shaped_article(mocker):
    mocker.patch(
        "collector.note_fetcher.requests.get",
        return_value=_page(
            [_note("nabc", urlname="guchey", name="分析エージェント", body="本文冒頭")],
            is_last_page=True,
        ),
    )

    articles = fetch_articles(["データ基盤"], lookback_days=2, max_pages=3)

    assert len(articles) == 1
    a = articles[0]
    url = _normalize_url("https://note.com/guchey/n/nabc")
    assert a["url"] == url
    # RSS 経由の同じ記事と dedup で一致させるため article_id は rss_fetcher と同じ計算
    assert a["article_id"] == _make_article_id(url)
    assert a["title"] == "分析エージェント"
    assert a["source"] == "note #データ基盤"
    assert a["description"] == "本文冒頭"
    assert a["origin"] == "note_tag"
    assert a["published_at"] is not None
    assert a["collected_at"] is not None


def test_requests_new_order_with_timeout(mocker):
    mock_get = mocker.patch(
        "collector.note_fetcher.requests.get", return_value=_page([], is_last_page=True)
    )

    fetch_articles(["dbt"], lookback_days=2, max_pages=3)

    args, kwargs = mock_get.call_args
    assert "/api/v3/hashtags/dbt/notes" in args[0]
    assert kwargs["params"] == {"order": "new", "page": 1}
    assert kwargs.get("timeout") is not None


def test_skips_paid_and_non_text_notes(mocker):
    mocker.patch(
        "collector.note_fetcher.requests.get",
        return_value=_page(
            [
                _note("nfree"),
                _note("npaid", price=300),
                _note("nimage", type_="ImageNote"),
            ],
            is_last_page=True,
        ),
    )

    articles = fetch_articles(["dbt"], lookback_days=2, max_pages=3)

    assert [a["url"].rsplit("/", 1)[1] for a in articles] == ["nfree"]


def test_stops_at_notes_older_than_lookback(mocker):
    mock_get = mocker.patch(
        "collector.note_fetcher.requests.get",
        return_value=_page(
            [_note("nnew", hours_ago=10), _note("nold", hours_ago=24 * 3)]
        ),
    )

    articles = fetch_articles(["dbt"], lookback_days=2, max_pages=3)

    assert [a["url"].rsplit("/", 1)[1] for a in articles] == ["nnew"]
    # 窓外に到達したので次ページは取りに行かない
    assert mock_get.call_count == 1


def test_stops_at_last_page(mocker):
    mock_get = mocker.patch(
        "collector.note_fetcher.requests.get",
        side_effect=[_page([_note("n1")]), _page([_note("n2")], is_last_page=True)],
    )

    articles = fetch_articles(["dbt"], lookback_days=2, max_pages=5)

    assert len(articles) == 2
    assert mock_get.call_count == 2
    assert mock_get.call_args_list[1].kwargs["params"]["page"] == 2


def test_stops_at_max_pages(mocker):
    mock_get = mocker.patch(
        "collector.note_fetcher.requests.get",
        side_effect=lambda *a, **k: _page([_note(f"n{k['params']['page']}")]),
    )

    articles = fetch_articles(["dbt"], lookback_days=2, max_pages=2)

    assert len(articles) == 2
    assert mock_get.call_count == 2


def test_stops_on_empty_page(mocker):
    mock_get = mocker.patch(
        "collector.note_fetcher.requests.get", return_value=_page([])
    )

    assert fetch_articles(["dbt"], lookback_days=2, max_pages=3) == []
    assert mock_get.call_count == 1


@pytest.mark.parametrize(
    "failure",
    [requests.HTTPError("503"), requests.Timeout("timeout"), KeyError("data")],
)
def test_failed_tag_does_not_stop_other_tags(mocker, failure):
    def _get(url, **kwargs):
        if "/hashtags/broken/" in url:
            raise failure
        return _page([_note("nok")], is_last_page=True)

    mocker.patch("collector.note_fetcher.requests.get", side_effect=_get)

    articles = fetch_articles(["broken", "dbt"], lookback_days=2, max_pages=3)

    assert [a["source"] for a in articles] == ["note #dbt"]


def test_keeps_pages_fetched_before_failure(mocker):
    mocker.patch(
        "collector.note_fetcher.requests.get",
        side_effect=[_page([_note("n1")]), requests.HTTPError("500")],
    )

    articles = fetch_articles(["dbt"], lookback_days=2, max_pages=3)

    assert len(articles) == 1


def test_empty_tags_makes_no_request(mocker):
    mock_get = mocker.patch("collector.note_fetcher.requests.get")

    assert fetch_articles([], lookback_days=2, max_pages=3) == []
    mock_get.assert_not_called()


def test_sleeps_between_requests(mocker, no_sleep):
    mocker.patch(
        "collector.note_fetcher.requests.get",
        side_effect=[
            _page([_note("n1")]),
            _page([_note("n2")], is_last_page=True),
            _page([_note("n3")], is_last_page=True),
        ],
    )

    fetch_articles(["dbt", "BigQuery"], lookback_days=2, max_pages=3)

    # 3リクエストの間に2回待つ（最初のリクエスト前は待たない）
    assert no_sleep.call_count == 2
    assert all(c.args[0] >= 1 for c in no_sleep.call_args_list)


def test_url_encodes_japanese_tag(mocker):
    mock_get = mocker.patch(
        "collector.note_fetcher.requests.get", return_value=_page([], is_last_page=True)
    )

    fetch_articles(["データ基盤"], lookback_days=2, max_pages=3)

    assert (
        "/api/v3/hashtags/%E3%83%87%E3%83%BC%E3%82%BF%E5%9F%BA%E7%9B%A4/notes"
        in mock_get.call_args.args[0]
    )
