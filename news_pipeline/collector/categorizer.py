"""ニュースのカテゴリ分類・表示名・件数上限・通知順を決める純粋関数群。

Google Sheets 由来の設定だけで動作し、重い依存（BigQuery等）を持たないため
単体テストしやすい。
  - feed_categories: {source名: category}  （config_loader が feeds シートから生成）
  - settings:        {group名: {key: value}}（config_loader が settings シートから生成）
"""

DEFAULT_CATEGORY = "other"
DEFAULT_MAX_NOTIFY = 5
DEFAULT_OTHER_LABEL = "📰 その他"


def categorize(source: str, feed_categories: dict[str, str]) -> str:
    """source 名からカテゴリを決める。未知・空欄は DEFAULT_CATEGORY。"""
    return (feed_categories.get(source) or "").strip() or DEFAULT_CATEGORY


def group_by_category(
    summaries: list[dict], feed_categories: dict[str, str]
) -> dict[str, list[dict]]:
    """サマリーをカテゴリ別の dict にグルーピングする。"""
    groups: dict[str, list[dict]] = {}
    for s in summaries:
        cat = categorize(s.get("source", ""), feed_categories)
        groups.setdefault(cat, []).append(s)
    return groups


def category_label(category: str, settings: dict[str, dict]) -> str:
    """カテゴリの Slack ヘッダー表示名。settings の label 優先、無ければカテゴリ名。"""
    label = settings.get(category, {}).get("label")
    if label:
        return str(label)
    if category == DEFAULT_CATEGORY:
        return DEFAULT_OTHER_LABEL
    return category


def category_limit(category: str, settings: dict[str, dict]) -> int:
    """カテゴリの通知件数上限。settings の max_notify、無ければ DEFAULT_MAX_NOTIFY。"""
    val = settings.get(category, {}).get("max_notify", DEFAULT_MAX_NOTIFY)
    try:
        return int(val)
    except (TypeError, ValueError):
        return DEFAULT_MAX_NOTIFY


def order_categories(present: list[str], settings: dict[str, dict]) -> list[str]:
    """通知順を決める。settings の group 出現順を優先し、未定義カテゴリは後ろにアルファベット順。"""
    present_set = set(present)
    ordered = [g for g in settings.keys() if g in present_set]
    rest = sorted(present_set - set(ordered))
    return ordered + rest
