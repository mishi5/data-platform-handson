# ニュース通知のカテゴリ別分割（N分割・動的カテゴリ）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** news_pipeline の Slack 通知を feeds の category 列に基づきカテゴリ別の独立メッセージに分割し、カテゴリ・件数上限・表示名を Google Sheets だけで動的に管理できるようにする。

**Architecture:** 分類の純粋ロジックを新規 `collector/categorizer.py` に切り出して単体テスト可能にする。`config_loader.py` が feeds の category 列（`{source: category}`）と settings シートの namespace 3列（`{group: {key: value}}`）を読み込み、`main.py` の通知ステップがカテゴリ別にグルーピングして `notifier.send_slack_notification(header=...)` をカテゴリ数だけ呼ぶ。BQ スキーマ・`fetch_articles`・`bq_client` は変更しない。

**Tech Stack:** Python 3.12 / FastAPI / gspread / BigQuery / pytest（`uv run pytest`）

---

## File Structure

- **Create** `news_pipeline/collector/categorizer.py` — 分類・ラベル・上限・順序の純粋関数群（重い import なし）
- **Create** `news_pipeline/tests/test_categorizer.py` — categorizer の単体テスト
- **Create** `news_pipeline/tests/test_config_loader.py` — `_load_feed_categories` / `_load_settings` の単体テスト
- **Modify** `news_pipeline/collector/notifier.py` — `_format_blocks` / `send_slack_notification` に `header` 引数追加
- **Modify** `news_pipeline/tests/test_notifier.py` — header 引数のテスト追加
- **Modify** `news_pipeline/collector/config_loader.py` — `_load_feed_categories` 追加、`_load_settings` をネスト化、`load_config` 戻り値変更
- **Modify** `news_pipeline/collector/main.py` — 定数整理・`max_summarize` 読み出し変更・通知ステップの N分割化
- **Modify** `CLAUDE.md` — settings 3列化・feeds category 列・`MAX_NOTIFY` 廃止を反映

すべて `news_pipeline/` 配下で `uv run pytest` を実行する（CLAUDE.md 記載のコマンド）。

---

## Task 1: notifier に header 引数を追加

**Files:**
- Modify: `news_pipeline/collector/notifier.py:8-53`（`_format_blocks`）, `:118-133`（`send_slack_notification`）
- Test: `news_pipeline/tests/test_notifier.py`

- [ ] **Step 1: Write the failing test**

`news_pipeline/tests/test_notifier.py` の末尾に追加:

```python
@patch("collector.notifier.requests.post")
def test_send_notification_uses_custom_header(mock_post):
    mock_post.return_value.status_code = 200

    articles = [
        {
            "article_id": "id1",
            "title": "Some article",
            "url": "https://example.com/1",
            "source": "Example Blog",
            "summary": "- point",
        }
    ]
    send_slack_notification(
        articles, webhook_url="https://hooks.slack.com/test", header="📢 公式ブログ"
    )

    call_json = mock_post.call_args.kwargs["json"]
    assert call_json["text"] == "📢 公式ブログ"
    # ヘッダーブロックにラベルが入っている
    header_block = call_json["blocks"][0]
    assert header_block["type"] == "header"
    assert header_block["text"]["text"] == "📢 公式ブログ"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd news_pipeline && uv run pytest tests/test_notifier.py::test_send_notification_uses_custom_header -v`
Expected: FAIL（`send_slack_notification` に `header` 引数が無く `TypeError`）

- [ ] **Step 3: Implement — `_format_blocks` と `send_slack_notification` を変更**

`news_pipeline/collector/notifier.py` の `_format_blocks` シグネチャとヘッダー行を変更:

```python
def _format_blocks(articles: list[dict], header_text: str) -> list:
    """記事リストを Slack Block Kit 形式に変換する。"""
    blocks: list[dict] = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": header_text},
        }
    ]
```

（`for i, a in enumerate(...)` 以降は変更しない）

`send_slack_notification` を変更:

```python
def send_slack_notification(
    articles: list[dict],
    webhook_url: str,
    header: str = "本日のデータエンジニアリング技術ニュース",
) -> None:
    """summaries リストを Slack に通知する。header はメッセージ見出し。"""
    if not articles:
        logger.info("[notifier] no articles to notify")
        return

    blocks = _format_blocks(articles, header)
    payload = {"text": header, "blocks": blocks}
    try:
        resp = requests.post(webhook_url, json=payload, timeout=10)
        if resp.status_code != 200:
            logger.error("[notifier] slack error: %s %s", resp.status_code, resp.text)
        else:
            logger.info("[notifier] sent %d articles to slack (%s)", len(articles), header)
    except Exception as e:
        logger.error("[notifier] failed to post to slack: %s", e)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd news_pipeline && uv run pytest tests/test_notifier.py -v`
Expected: PASS（新規テスト + 既存4テストすべて。既存テストは `header` 未指定でデフォルト値を使うため影響なし）

- [ ] **Step 5: Commit**

```bash
git add news_pipeline/collector/notifier.py news_pipeline/tests/test_notifier.py
git commit -m "feat(notifier): send_slack_notification に header 引数を追加"
```

---

## Task 2: categorizer モジュール（純粋ロジック）

**Files:**
- Create: `news_pipeline/collector/categorizer.py`
- Test: `news_pipeline/tests/test_categorizer.py`

- [ ] **Step 1: Write the failing test**

`news_pipeline/tests/test_categorizer.py` を新規作成:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd news_pipeline && uv run pytest tests/test_categorizer.py -v`
Expected: FAIL（`ModuleNotFoundError: collector.categorizer`）

- [ ] **Step 3: Implement — categorizer.py**

`news_pipeline/collector/categorizer.py` を新規作成:

```python
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


def order_categories(present, settings: dict[str, dict]) -> list[str]:
    """通知順を決める。settings の group 出現順を優先し、未定義カテゴリは後ろにアルファベット順。"""
    present_set = set(present)
    ordered = [g for g in settings.keys() if g in present_set]
    rest = sorted(present_set - set(ordered))
    return ordered + rest
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd news_pipeline && uv run pytest tests/test_categorizer.py -v`
Expected: PASS（13テスト）

- [ ] **Step 5: Commit**

```bash
git add news_pipeline/collector/categorizer.py news_pipeline/tests/test_categorizer.py
git commit -m "feat(categorizer): カテゴリ分類・ラベル・上限・通知順の純粋関数を追加"
```

---

## Task 3: config_loader に feed_categories と settings ネスト化

**Files:**
- Modify: `news_pipeline/collector/config_loader.py:14-38`（`load_config`）, `:41-49`（`_load_feeds` の直後に新関数追加）, `:63-79`（`_load_settings`）
- Test: `news_pipeline/tests/test_config_loader.py`（新規）

- [ ] **Step 1: Write the failing test**

`news_pipeline/tests/test_config_loader.py` を新規作成:

```python
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
            ["", "orphan", "1"],      # group 欠落 → skip
            ["vendor", "", "3"],       # key 欠落 → skip
            ["partial", "key"],        # value 欠落（2列）→ skip
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd news_pipeline && uv run pytest tests/test_config_loader.py -v`
Expected: FAIL（`ImportError: cannot import name '_load_feed_categories'` と、`_load_settings` の戻りがフラットで不一致）

- [ ] **Step 3: Implement — config_loader.py を変更**

(a) `_load_feeds` の直後（`news_pipeline/collector/config_loader.py:49` の後）に新関数を追加:

```python
def _load_feed_categories(spreadsheet) -> dict[str, str]:
    """feeds シートを {Source Name: category} の dict で返す。category 列が無ければ空文字。"""
    try:
        ws = spreadsheet.worksheet("feeds")
        rows = ws.get_all_values()[1:]  # 1行目はヘッダー
        result: dict[str, str] = {}
        for row in rows:
            if len(row) >= 2 and row[1]:
                source = row[1]
                category = row[2] if len(row) >= 3 else ""
                result[source] = category
        return result
    except Exception as e:
        logger.warning("[config_loader] failed to load feed categories: %s", e)
        return {}
```

(b) `_load_settings` を namespace 3列・ネスト dict 版に置き換え:

```python
def _load_settings(spreadsheet) -> dict:
    """settings シートを {group: {key: value}} のネスト dict で返す。

    シートは group | key | value の3列。value は int 変換可能なら int 化する。
    group の出現順を保持する（通知順の決定に使う）。
    """
    try:
        ws = spreadsheet.worksheet("settings")
        rows = ws.get_all_values()[1:]  # 1行目はヘッダー
        result: dict = {}
        for row in rows:
            if len(row) >= 3 and row[0] and row[1]:
                group, key, val = row[0], row[1], row[2]
                try:
                    typed = int(val)
                except ValueError:
                    typed = val
                result.setdefault(group, {})[key] = typed
        return result
    except Exception as e:
        logger.warning("[config_loader] failed to load settings sheet: %s", e)
        return {}
```

(c) `load_config` の本体（feeds/keywords/settings を読む箇所、現 `:26-35`）を変更:

```python
        feeds = _load_feeds(spreadsheet)
        keywords = _load_keywords(spreadsheet)
        feed_categories = _load_feed_categories(spreadsheet)
        settings = _load_settings(spreadsheet)
        logger.info(
            "[config_loader] loaded %d feeds, %d keywords, %d setting groups from Sheets",
            len(feeds),
            len(keywords),
            len(settings),
        )
        return {
            "feeds": feeds,
            "keywords": keywords,
            "feed_categories": feed_categories,
            "settings": settings,
        }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd news_pipeline && uv run pytest tests/test_config_loader.py -v`
Expected: PASS（5テスト）

- [ ] **Step 5: Commit**

```bash
git add news_pipeline/collector/config_loader.py news_pipeline/tests/test_config_loader.py
git commit -m "feat(config_loader): feed category 読み込みと settings の namespace ネスト化"
```

---

## Task 4: main.py の通知ステップを N分割化

**Files:**
- Modify: `news_pipeline/collector/main.py:27`（import）, `:43-46`（定数）, `:119-122`（max_summarize 読み出し）, `:200-221`（通知ステップ）

このタスクは `main.py` がモジュールレベルで環境変数を要求し import 不可のため単体テストを追加しない。Task 1〜3 の単体テストで分類・通知ロジックは担保済み。検証は「全テスト緑 + import 構文確認」で行う。

- [ ] **Step 1: import を追加**

`news_pipeline/collector/main.py:27`（`from notifier import ...` の行付近）に追加:

```python
from categorizer import (
    category_label,
    category_limit,
    group_by_category,
    order_categories,
)
```

（既存の `from notifier import format_favorites_blocks, send_no_news_notification, send_slack_notification` はそのまま）

- [ ] **Step 2: 定数を整理**

`news_pipeline/collector/main.py:43-44` の `MAX_NOTIFY` 定義を削除する:

```python
# 削除する2行:
# MAX_NOTIFY: importance_scoreフィルタ後に実際に通知する件数の上限（未設定 = 5件）
# MAX_NOTIFY = int(os.environ.get("MAX_NOTIFY", 5))
```

`IMPORTANCE_THRESHOLD`（`:45-46`）と `_DEFAULT_MAX_SUMMARIZE`（`:49`）はそのまま残す。

- [ ] **Step 3: max_summarize の読み出しを settings ネストに合わせる**

`news_pipeline/collector/main.py:122` を変更:

```python
    # 変更前:
    # max_summarize: int = config.get("max_summarize", _DEFAULT_MAX_SUMMARIZE)
    # 変更後:
    settings: dict = config.get("settings", {})
    feed_categories: dict[str, str] = config.get("feed_categories", {})
    max_summarize: int = settings.get("general", {}).get(
        "max_summarize", _DEFAULT_MAX_SUMMARIZE
    )
```

（`feeds` / `keywords` を読む既存行はそのまま。`settings` と `feed_categories` をこの位置で取得しておき、後段の通知で使う）

- [ ] **Step 4: 通知ステップ（ステップ10〜11）を N分割化**

`news_pipeline/collector/main.py:208-221`（`# 10. importance_score 降順 ...` から `return len(top)` まで）を以下に置き換える:

```python
        # 10. カテゴリ別にグルーピングし、カテゴリごとに通知
        groups = group_by_category(unnotified, feed_categories)
        notified_ids: list[str] = []
        for category in order_categories(groups.keys(), settings):
            items = sorted(
                groups[category],
                key=lambda x: x.get("importance_score", 0),
                reverse=True,
            )
            top = items[: category_limit(category, settings)]
            if not top:
                continue
            send_slack_notification(
                top, SLACK_WEBHOOK_URL, header=category_label(category, settings)
            )
            notified_ids.extend(a["article_id"] for a in top)
            logger.info(
                "[pipeline] notified %d articles in category '%s'", len(top), category
            )

        if not notified_ids:
            send_no_news_notification(SLACK_WEBHOOK_URL, "新着記事はありませんでした。")
            return 0

        # 11. 通知済みマーク（全カテゴリの和集合）
        bq.mark_summaries_notified(notified_ids)
        logger.info("[pipeline] marked %d summaries as notified", len(notified_ids))

        log["notified_count"] = len(notified_ids)
        return len(notified_ids)
```

（直前の `# 9.` ブロック＝`unnotified = bq.get_unnotified_summaries()` と `if not unnotified: send_no_news_notification(...) return 0` はそのまま残す）

- [ ] **Step 5: import 構文と全テストを検証**

Run: `cd news_pipeline && uv run python -c "import ast; ast.parse(open('collector/main.py').read()); print('syntax ok')"`
Expected: `syntax ok`

Run: `cd news_pipeline && uv run pytest tests/ -v`
Expected: 全テスト PASS（既存 + 新規 test_categorizer / test_config_loader / test_notifier 追加分）

- [ ] **Step 6: sqlfluff 相当のフォーマット確認は不要（Python のみ）。コミット**

```bash
git add news_pipeline/collector/main.py
git commit -m "feat(main): 通知をカテゴリ別の独立メッセージに分割（N分割・動的カテゴリ）"
```

---

## Task 5: ドキュメント更新（CLAUDE.md）

**Files:**
- Modify: `CLAUDE.md`（news_pipeline の環境変数表とセクション）

- [ ] **Step 1: 環境変数表から MAX_NOTIFY 系の記述を整理**

`CLAUDE.md` の news_pipeline 環境変数表（`| 変数 | 説明 |` のテーブル）を確認し、`MAX_ARTICLES` の行はそのまま残しつつ、件数上限が Google Sheets の settings シートに移ったことを反映する。テーブル直後に以下の注記を追加:

```markdown
### Google Sheets 設定（news-pipeline-config）

- **feeds シート**: `URL | source | category` の3列。`category` 列でニュースの分類を指定（任意の文字列）。空欄は `other` 扱い。
- **settings シート**: `group | key | value` の3列（namespace 方式）。
  - `general / max_summarize`: 1実行で要約する最大件数
  - `<category> / max_notify`: そのカテゴリの通知件数上限（未設定は5）
  - `<category> / label`: Slack 通知のヘッダー表示名（未設定はカテゴリ名、`other` は `📰 その他`）
  - カテゴリの追加・削除・件数変更は settings/feeds シートの編集だけで完結（コード変更不要）
- 通知はカテゴリごとに独立した Slack メッセージとして送られる。通知順は settings シートの group 出現順。
```

- [ ] **Step 2: 環境変数の記述から MAX_NOTIFY の言及があれば削除**

`CLAUDE.md` 内を `MAX_NOTIFY` で検索し、もし記載があれば削除する（現状の表には無いが念のため確認）。

Run: `grep -n "MAX_NOTIFY" CLAUDE.md`
Expected: 該当なし、または削除後に該当なし

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: news_pipeline のカテゴリ別通知と Sheets 設定（feeds/settings 3列化）を追記"
```

---

## Self-Review メモ（実装者向け確認事項）

- **Spec coverage:** feeds category 列（Task3）、settings namespace 3列（Task3）、N分割通知（Task4）、グループ別上限（Task2/4）、通知順=group 出現順（Task2/4）、label フォールバック（Task2）、空欄→other（Task2）、全カテゴリ空→no_news（Task4）、MAX_NOTIFY 廃止（Task4/5）、ドキュメント（Task5）— すべてタスクに対応済み。
- **型整合:** `categorize` / `group_by_category` / `category_label` / `category_limit` / `order_categories` の関数名・引数は Task2 の定義と Task4 の呼び出しで一致。`send_slack_notification(articles, webhook_url, header)` は Task1 定義と Task4 呼び出しで一致。
- **カテゴリ照合は大文字小文字を区別する完全一致**（feeds の category 値と settings の group 名を一致させること）。
- BQ スキーマ・`fetch_articles`・`bq_client` は無変更。
```
