from unittest.mock import MagicMock

from collector.config_loader import _load_feed_categories, _load_settings


def _spreadsheet_with(sheet_name, values):
    """worksheet(sheet_name).get_all_values() が values を返す擬似 spreadsheet。"""
    ws = MagicMock()
    ws.get_all_values.return_value = values
    ss = MagicMock()
    ss.worksheet.return_value = ws
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
