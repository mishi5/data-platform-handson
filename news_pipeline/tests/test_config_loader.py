from unittest.mock import MagicMock

from collector.config_loader import (
    _load_feed_blocks,
    _load_feed_categories,
    _load_settings,
)


def _spreadsheet_with(sheet_name, values):
    """worksheet(sheet_name).get_all_values() が values を返す擬似 spreadsheet。

    想定外のシート名で呼ばれた場合は KeyError を投げ、対象関数が
    正しいシートを参照していることをテストで担保する。
    """
    ws = MagicMock()
    ws.get_all_values.return_value = values

    def _worksheet(name):
        if name != sheet_name:
            raise KeyError(name)
        return ws

    ss = MagicMock()
    ss.worksheet.side_effect = _worksheet
    return ss


def test_load_feed_categories_maps_source_to_category():
    ss = _spreadsheet_with(
        "feeds",
        [
            ["url", "source", "category"],
            ["https://a", "Google Cloud Blog", "official"],
            ["https://b", "個人ブログ", "personal"],
        ],
    )
    assert _load_feed_categories(ss) == {
        "Google Cloud Blog": "official",
        "個人ブログ": "personal",
    }


def test_load_feed_categories_missing_third_column_is_empty():
    ss = _spreadsheet_with(
        "feeds",
        [
            ["url", "source", "category"],
            ["https://a", "No Category Feed"],
        ],
    )
    assert _load_feed_categories(ss) == {"No Category Feed": ""}


def test_load_settings_nests_by_group_and_int_converts():
    ss = _spreadsheet_with(
        "settings",
        [
            ["group", "key", "value"],
            ["general", "max_summarize", "10"],
            ["official", "label", "📢 公式ブログ"],
            ["official", "max_notify", "5"],
        ],
    )
    assert _load_settings(ss) == {
        "general": {"max_summarize": 10},
        "official": {"label": "📢 公式ブログ", "max_notify": 5},
    }


def test_load_settings_skips_malformed_rows():
    ss = _spreadsheet_with(
        "settings",
        [
            ["group", "key", "value"],
            ["official", "max_notify", "5"],
            ["", "orphan", "1"],  # group 欠落 → skip
            ["vendor", "", "3"],  # key 欠落 → skip
            ["partial", "key"],  # value 欠落（2列）→ skip
        ],
    )
    assert _load_settings(ss) == {"official": {"max_notify": 5}}


def test_load_settings_preserves_group_order():
    ss = _spreadsheet_with(
        "settings",
        [
            ["group", "key", "value"],
            ["general", "max_summarize", "10"],
            ["vendor", "max_notify", "3"],
            ["official", "max_notify", "5"],
        ],
    )
    assert list(_load_settings(ss).keys()) == ["general", "vendor", "official"]


def test_load_feed_blocks_parses_users_and_location():
    ss = _spreadsheet_with(
        "feeds",
        [
            ["url", "source", "category", "block_users", "user_location"],
            ["https://a", "Zenn", "bigquery", "web_benriya, spammer", ""],
            ["https://b", "Hatena", "personal", "taro", "subdomain"],
        ],
    )
    assert _load_feed_blocks(ss) == {
        "Zenn": {"users": {"web_benriya", "spammer"}, "location": "path1"},
        "Hatena": {"users": {"taro"}, "location": "subdomain"},
    }


def test_load_feed_blocks_skips_rows_without_users():
    ss = _spreadsheet_with(
        "feeds",
        [
            ["url", "source", "category", "block_users", "user_location"],
            ["https://a", "Zenn", "bigquery", "", ""],
            ["https://b", "Qiita", "personal"],  # 列不足
        ],
    )
    assert _load_feed_blocks(ss) == {}


# --- 一時障害へのリトライ ----------------------------------------------------

from unittest.mock import patch

import pytest


def _api_error(code: int):
    """gspread の APIError（.code を持つ）を組み立てる。"""
    from gspread.exceptions import APIError

    response = MagicMock()
    response.json.return_value = {"error": {"code": code, "message": "boom"}}
    return APIError(response)


@patch("collector.config_loader.time.sleep")
@patch("collector.config_loader._load_config_once")
@patch("collector.config_loader.SHEET_ID", "sheet-1")
def test_load_config_retries_transient_error(mock_once, mock_sleep):
    """Sheets の 503（一時障害）は再試行する。

    実際に JST 6:30 の /notify が 503 で丸ごと落ち、通知がスキップされた。
    """
    from collector.config_loader import load_config

    mock_once.side_effect = [_api_error(503), {"feeds": {"u": "s"}}]

    config = load_config()

    assert config == {"feeds": {"u": "s"}}
    assert mock_once.call_count == 2
    mock_sleep.assert_called_once()


@patch("collector.config_loader.time.sleep")
@patch("collector.config_loader._load_config_once")
@patch("collector.config_loader.SHEET_ID", "sheet-1")
def test_load_config_gives_up_after_max_attempts(mock_once, mock_sleep):
    """一時障害が続いたら諦めて空 dict（呼び出し側が設定ガードで落とす）。"""
    from collector.config_loader import load_config

    mock_once.side_effect = _api_error(503)

    assert load_config() == {}
    assert mock_once.call_count == 3
    # 最終試行のあとは待たない
    assert mock_sleep.call_count == 2


@patch("collector.config_loader.time.sleep")
@patch("collector.config_loader._load_config_once")
@patch("collector.config_loader.SHEET_ID", "sheet-1")
def test_load_config_does_not_retry_permanent_error(mock_once, mock_sleep):
    """403（権限エラー）など恒久的な失敗はリトライしない（待つだけ無駄）。"""
    from collector.config_loader import load_config

    mock_once.side_effect = _api_error(403)

    assert load_config() == {}
    assert mock_once.call_count == 1
    mock_sleep.assert_not_called()


@patch("collector.config_loader.time.sleep")
@patch("collector.config_loader._load_config_once")
@patch("collector.config_loader.SHEET_ID", "sheet-1")
def test_load_config_backoff_is_exponential(mock_once, mock_sleep):
    from collector.config_loader import load_config

    mock_once.side_effect = _api_error(503)
    load_config()

    assert [c.args[0] for c in mock_sleep.call_args_list] == [1.0, 2.0]


@pytest.mark.parametrize("exc", [ConnectionError("net"), TimeoutError("slow")])
@patch("collector.config_loader.time.sleep")
@patch("collector.config_loader._load_config_once")
@patch("collector.config_loader.SHEET_ID", "sheet-1")
def test_load_config_retries_network_errors(mock_once, mock_sleep, exc):
    """接続エラー・タイムアウトも一時障害として再試行する。"""
    from collector.config_loader import load_config

    mock_once.side_effect = [exc, {"feeds": {}}]

    assert load_config() == {"feeds": {}}
    assert mock_once.call_count == 2
