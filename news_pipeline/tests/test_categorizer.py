from collector.categorizer import (
    DEFAULT_CATEGORY,
    DEFAULT_OTHER_LABEL,
    categorize,
    category_label,
    category_limit,
    group_by_category,
    order_categories,
)


def test_categorize_known_source():
    fc = {"Google Cloud Blog": "official"}
    assert categorize("Google Cloud Blog", fc) == "official"


def test_categorize_blank_category_falls_back_to_default():
    fc = {"Some Feed": ""}
    assert categorize("Some Feed", fc) == DEFAULT_CATEGORY


def test_categorize_unknown_source_falls_back_to_default():
    assert categorize("Unknown", {}) == DEFAULT_CATEGORY


def test_categorize_strips_whitespace():
    fc = {"Feed": "  official  "}
    assert categorize("Feed", fc) == "official"


def test_category_label_from_settings():
    settings = {"official": {"label": "📢 公式ブログ", "max_notify": 5}}
    assert category_label("official", settings) == "📢 公式ブログ"


def test_category_label_fallback_to_category_name():
    assert category_label("vendor", {}) == "vendor"


def test_category_label_other_uses_default_label():
    assert category_label(DEFAULT_CATEGORY, {}) == DEFAULT_OTHER_LABEL


def test_category_limit_from_settings():
    settings = {"official": {"max_notify": 3}}
    assert category_limit("official", settings) == 3


def test_category_limit_missing_uses_default():
    assert category_limit("official", {}) == 5


def test_category_limit_non_int_uses_default():
    settings = {"official": {"max_notify": "abc"}}
    assert category_limit("official", settings) == 5


def test_group_by_category():
    summaries = [
        {"article_id": "1", "source": "A"},
        {"article_id": "2", "source": "B"},
        {"article_id": "3", "source": "A"},
    ]
    fc = {"A": "official", "B": "vendor"}
    groups = group_by_category(summaries, fc)
    assert {g: [s["article_id"] for s in items] for g, items in groups.items()} == {
        "official": ["1", "3"],
        "vendor": ["2"],
    }


def test_order_categories_honors_settings_order():
    settings = {"general": {}, "official": {}, "vendor": {}}
    present = ["vendor", "official"]
    assert order_categories(present, settings) == ["official", "vendor"]


def test_order_categories_appends_unknown_alphabetically():
    settings = {"official": {}}
    present = ["zeta", "official", "alpha"]
    assert order_categories(present, settings) == ["official", "alpha", "zeta"]
