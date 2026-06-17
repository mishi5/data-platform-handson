# 特定ユーザー（著者）ブロック機能 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** feeds シートに `block_users`・`user_location` 列を追加し、指定ユーザーの記事を収集・通知の両段階で除外する。

**Architecture:** URLからユーザー識別子を抽出する純粋関数（`blocklist.py`）を新設し、デフォルトはパス第1セグメント、例外サイトは feeds シートの `user_location` 列で抽出位置を指定する。設定は `config_loader._load_feed_blocks` が `{source: {users, location}}` として読み込み、`main.py` の収集時（RSS取得直後）と通知時（unnotified取得直後）でフィルタする。

**Tech Stack:** Python 3.13 / FastAPI / pytest（モック完結・BigQuery不要）/ uv / Google Sheets (gspread)

---

## File Structure

- **Create** `news_pipeline/collector/blocklist.py` — URL→ユーザー抽出とブロック判定の純粋関数（`extract_user`, `is_blocked`）。
- **Create** `news_pipeline/tests/test_blocklist.py` — 上記の単体テスト。
- **Modify** `news_pipeline/collector/config_loader.py` — `_load_feed_blocks` 追加、`load_config` に `feed_blocks` キー追加。
- **Modify** `news_pipeline/tests/test_config_loader.py` — `_load_feed_blocks` のテスト追加。
- **Modify** `news_pipeline/collector/main.py` — `_run_collect`・`_run_notify` にフィルタ適用。
- **Modify** `CLAUDE.md` — Google Sheets 設定の feeds 説明に列追記。

テストは `cd news_pipeline && uv run pytest` で実行する（CLAUDE.md準拠）。`collector.` 始まりの import を使う（既存 test と同様）。

---

### Task 1: `blocklist.py` — `extract_user`

**Files:**
- Create: `news_pipeline/collector/blocklist.py`
- Test: `news_pipeline/tests/test_blocklist.py`

- [ ] **Step 1: Write the failing test**

`news_pipeline/tests/test_blocklist.py`:

```python
from collector.blocklist import extract_user, is_blocked


def test_extract_user_path1_default_empty_location():
    url = "https://zenn.dev/web_benriya/articles/abc"
    assert extract_user(url, "") == "web_benriya"


def test_extract_user_path1_explicit():
    url = "https://zenn.dev/web_benriya/articles/abc"
    assert extract_user(url, "path1") == "web_benriya"


def test_extract_user_subdomain():
    url = "https://taro.hatenablog.com/entry/2026/06/18/foo"
    assert extract_user(url, "subdomain") == "taro"


def test_extract_user_path2():
    url = "https://example.com/tech/author_x/posts/1"
    assert extract_user(url, "path2") == "author_x"


def test_extract_user_missing_segment_returns_none():
    assert extract_user("https://zenn.dev/", "path1") is None
    assert extract_user("https://zenn.dev/onlyone", "path2") is None


def test_extract_user_unknown_location_returns_none():
    assert extract_user("https://zenn.dev/web_benriya/x", "bogus") is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd news_pipeline && uv run pytest tests/test_blocklist.py -v`
Expected: FAIL（`ModuleNotFoundError: No module named 'collector.blocklist'`）

- [ ] **Step 3: Write minimal implementation**

`news_pipeline/collector/blocklist.py`:

```python
"""記事URLからユーザー識別子を抽出し、ブロック対象か判定するモジュール。"""

from urllib.parse import urlparse


def extract_user(url: str, location: str) -> str | None:
    """URL からユーザー識別子を抽出する。抽出できなければ None。

    location:
      "" / "path1"     -> パス第1セグメント（Zenn / Qiita / note）
      "subdomain"      -> ホスト名の先頭ラベル（はてなブログ等）
      "path2","path3".. -> パスの N 番目セグメント（1始まり）
    """
    parsed = urlparse(url)
    loc = (location or "path1").strip().lower()

    if loc == "subdomain":
        host = parsed.hostname or ""
        label = host.split(".")[0]
        return label or None

    if loc.startswith("path"):
        suffix = loc[len("path"):]
        index = int(suffix) if suffix.isdigit() else 1
        segments = [s for s in parsed.path.split("/") if s]
        if 1 <= index <= len(segments):
            return segments[index - 1]
        return None

    return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd news_pipeline && uv run pytest tests/test_blocklist.py -v`
Expected: PASS（6 tests）

- [ ] **Step 5: Commit**

```bash
git add news_pipeline/collector/blocklist.py news_pipeline/tests/test_blocklist.py
git commit -m "feat(blocklist): URLからユーザー識別子を抽出する extract_user を追加

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: `blocklist.py` — `is_blocked`

**Files:**
- Modify: `news_pipeline/collector/blocklist.py`
- Test: `news_pipeline/tests/test_blocklist.py`

- [ ] **Step 1: Write the failing test**

`news_pipeline/tests/test_blocklist.py` に追記:

```python
def test_is_blocked_exact_match():
    url = "https://zenn.dev/web_benriya/articles/abc"
    assert is_blocked(url, {"web_benriya"}, "path1") is True


def test_is_blocked_no_partial_match():
    # web_benriya2 は別ユーザー: 部分一致で誤ブロックしない
    url = "https://zenn.dev/web_benriya2/articles/abc"
    assert is_blocked(url, {"web_benriya"}, "path1") is False


def test_is_blocked_empty_users():
    url = "https://zenn.dev/web_benriya/articles/abc"
    assert is_blocked(url, set(), "path1") is False


def test_is_blocked_extract_none():
    assert is_blocked("https://zenn.dev/", {"web_benriya"}, "path1") is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd news_pipeline && uv run pytest tests/test_blocklist.py -v`
Expected: FAIL（`is_blocked` 内で抽出結果を判定していない／未実装の挙動でFAIL。少なくとも import は通る）

- [ ] **Step 3: Write minimal implementation**

`news_pipeline/collector/blocklist.py` の末尾に追記:

```python
def is_blocked(url: str, users: set[str], location: str) -> bool:
    """URL から抽出したユーザーが users に完全一致で含まれれば True。"""
    if not users:
        return False
    user = extract_user(url, location)
    return user is not None and user in users
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd news_pipeline && uv run pytest tests/test_blocklist.py -v`
Expected: PASS（10 tests）

- [ ] **Step 5: Commit**

```bash
git add news_pipeline/collector/blocklist.py news_pipeline/tests/test_blocklist.py
git commit -m "feat(blocklist): 完全一致でブロック判定する is_blocked を追加

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: `config_loader._load_feed_blocks`

**Files:**
- Modify: `news_pipeline/collector/config_loader.py`
- Modify: `news_pipeline/tests/test_config_loader.py`

- [ ] **Step 1: Write the failing test**

`news_pipeline/tests/test_config_loader.py` の import 行を更新し、テストを追記する。

import 行を以下に変更:

```python
from collector.config_loader import (
    _load_feed_blocks,
    _load_feed_categories,
    _load_settings,
)
```

末尾に追記:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd news_pipeline && uv run pytest tests/test_config_loader.py -v`
Expected: FAIL（`ImportError: cannot import name '_load_feed_blocks'`）

- [ ] **Step 3: Write minimal implementation**

`news_pipeline/collector/config_loader.py` に `_load_feed_blocks` を追加する（`_load_feed_categories` の直後あたり）:

```python
def _load_feed_blocks(spreadsheet) -> dict[str, dict]:
    """feeds シートを {source: {"users": set, "location": str}} で返す。

    4列目 block_users（カンマ区切り）、5列目 user_location（空欄は path1）。
    block_users が空の行は登録しない。
    """
    try:
        ws = spreadsheet.worksheet("feeds")
        rows = ws.get_all_values()[1:]  # 1行目はヘッダー
        result: dict[str, dict] = {}
        for row in rows:
            if len(row) < 4 or not row[1]:
                continue
            source = row[1]
            users = {u.strip() for u in row[3].split(",") if u.strip()}
            if not users:
                continue
            location = row[4].strip() if len(row) >= 5 and row[4].strip() else "path1"
            result[source] = {"users": users, "location": location}
        return result
    except Exception as e:
        logger.warning("[config_loader] failed to load feed blocks: %s", e)
        return {}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd news_pipeline && uv run pytest tests/test_config_loader.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add news_pipeline/collector/config_loader.py news_pipeline/tests/test_config_loader.py
git commit -m "feat(config_loader): feeds の block_users/user_location を読む _load_feed_blocks を追加

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: `load_config` に `feed_blocks` を組み込む

**Files:**
- Modify: `news_pipeline/collector/config_loader.py:27-42`

- [ ] **Step 1: Write the implementation**

`load_config()` 内で `feed_categories` を読む行の直後に追加し、返り値 dict に `"feed_blocks"` を加える。

`_load_feed_categories` 呼び出しの直後:

```python
        feed_categories = _load_feed_categories(spreadsheet)
        feed_blocks = _load_feed_blocks(spreadsheet)
        settings = _load_settings(spreadsheet)
```

返り値 dict を以下に変更:

```python
        return {
            "feeds": feeds,
            "keywords": keywords,
            "feed_categories": feed_categories,
            "feed_blocks": feed_blocks,
            "settings": settings,
        }
```

- [ ] **Step 2: Run tests to verify nothing breaks**

Run: `cd news_pipeline && uv run pytest -v`
Expected: PASS（全テスト）

- [ ] **Step 3: Commit**

```bash
git add news_pipeline/collector/config_loader.py
git commit -m "feat(config_loader): load_config の返り値に feed_blocks を追加

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: 収集時フィルタ（`_run_collect`）

**Files:**
- Modify: `news_pipeline/collector/main.py:23-43`（import）
- Modify: `news_pipeline/collector/main.py:133-164`（collect本体）

- [ ] **Step 1: Add import**

`main.py` の import 群に追加（`from bq_client import BQClient` の付近）:

```python
from blocklist import is_blocked
```

- [ ] **Step 2: Read feed_blocks in `_run_collect`**

`_run_collect` 内、`feed_categories` は読んでいないので `config` から取得する。`feeds` を取得している付近（`feeds: dict[str, str] = config.get("feeds", {})` の下）に追加:

```python
    feed_blocks: dict = config.get("feed_blocks", {})
```

- [ ] **Step 3: Apply filter right after fetch**

`# 1. RSS 取得` ブロックの直後、`# 2. dedup` の前にフィルタを挿入する。

既存:

```python
        # 1. RSS 取得
        articles = fetch_articles(feeds)
        log["articles_fetched"] = len(articles)
        logger.info("[collect] fetched %d articles from RSS", len(articles))

        # 2. dedup（raw_articles ベース）→ 要約上限で絞る
```

変更後:

```python
        # 1. RSS 取得
        articles = fetch_articles(feeds)
        log["articles_fetched"] = len(articles)
        logger.info("[collect] fetched %d articles from RSS", len(articles))

        # 1.5. ブロックユーザーの記事を除外
        before_block = len(articles)
        articles = [
            a
            for a in articles
            if not is_blocked(
                a["url"],
                feed_blocks.get(a["source"], {}).get("users", set()),
                feed_blocks.get(a["source"], {}).get("location", "path1"),
            )
        ]
        if before_block != len(articles):
            logger.info(
                "[collect] blocked %d articles by feed block list",
                before_block - len(articles),
            )

        # 2. dedup（raw_articles ベース）→ 要約上限で絞る
```

- [ ] **Step 4: Run full test suite**

Run: `cd news_pipeline && uv run pytest -v`
Expected: PASS（既存テストが壊れていないこと）

- [ ] **Step 5: Commit**

```bash
git add news_pipeline/collector/main.py
git commit -m "feat(collect): RSS取得直後にブロックユーザーの記事を除外

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: 通知時フィルタ（`_run_notify`）

**Files:**
- Modify: `news_pipeline/collector/main.py:294-303`（notify本体）

- [ ] **Step 1: Read feed_blocks in `_run_notify`**

`_run_notify` 内、`feed_categories` を読む行の付近に追加:

```python
    feed_blocks: dict = config.get("feed_blocks", {})
```

- [ ] **Step 2: Apply filter after fetching unnotified**

`# 9. 未通知サマリーを取得` のブロック、`unnotified = bq.get_unnotified_summaries()` の直後にフィルタを挿入する。

既存:

```python
        # 9. 未通知サマリーを取得
        unnotified = bq.get_unnotified_summaries()
        logger.info("[notify] %d unnotified summaries in BQ", len(unnotified))

        if not unnotified:
```

変更後:

```python
        # 9. 未通知サマリーを取得
        unnotified = bq.get_unnotified_summaries()
        logger.info("[notify] %d unnotified summaries in BQ", len(unnotified))

        # 9.5. ブロックユーザーの記事を除外（保存済み記事も通知しない）
        before_block = len(unnotified)
        unnotified = [
            s
            for s in unnotified
            if not is_blocked(
                s["url"],
                feed_blocks.get(s["source"], {}).get("users", set()),
                feed_blocks.get(s["source"], {}).get("location", "path1"),
            )
        ]
        if before_block != len(unnotified):
            logger.info(
                "[notify] blocked %d summaries by feed block list",
                before_block - len(unnotified),
            )

        if not unnotified:
```

- [ ] **Step 3: Run full test suite**

Run: `cd news_pipeline && uv run pytest -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add news_pipeline/collector/main.py
git commit -m "feat(notify): 通知時にもブロックユーザーの記事を除外

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 7: ドキュメント更新（CLAUDE.md）

**Files:**
- Modify: `CLAUDE.md`（「Google Sheets 設定（news-pipeline-config）」セクションの feeds 説明）

- [ ] **Step 1: Update feeds description**

`CLAUDE.md` の以下の行:

```markdown
- **feeds シート**: `URL | source | category` の3列。`category` 列でニュースの分類を指定（任意の文字列）。空欄は `other` 扱い。
```

を次に置き換える:

```markdown
- **feeds シート**: `URL | source | category | block_users | user_location` の5列。
  - `category`: ニュースの分類（任意の文字列）。空欄は `other` 扱い。
  - `block_users`: ブロックする著者の識別子（カンマ区切り、**完全一致**）。空欄ならブロックなし。
  - `user_location`: `block_users` を記事URLのどこと照合するか。空欄は `path1`（パス第1セグメント）。

  **ブロックの仕組みと対応サイト**（記事URLから抽出した識別子と `block_users` を完全一致で照合）:

  | user_location | 抽出位置 | 対応サイト例 | block_users に書く値 |
  |---|---|---|---|
  | （空欄）/ `path1` | パス第1セグメント | Zenn `zenn.dev/<user>/...`、Qiita、note | ユーザー名（例: `web_benriya`） |
  | `subdomain` | ホスト名の先頭ラベル | はてなブログ `<user>.hatenablog.com` | サブドメイン名 |
  | `path2` / `path3` … | パスの N 番目セグメント | 第1がカテゴリ等で第2が著者のサイト | 著者slug |

  - 部分一致はしないため `web_benriya` 指定で `web_benriya2` は誤ブロックされない。
  - 著者slugがURLに無いサイト（一般メディア等）はブロック不可。`block_users` を書いても一致しなければ無視されるだけで無害。
  - Zenn の organization 記事（`zenn.dev/<org>/...`）は第1セグメントが org slug なので org 単位のブロックになる。
```

- [ ] **Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: feeds シートの block_users/user_location 列を説明に追記

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 8: 最終確認

- [ ] **Step 1: Run full test suite**

Run: `cd news_pipeline && uv run pytest -v`
Expected: 全テスト PASS（新規10件 + config 2件 + 既存）

- [ ] **Step 2: 動作の手動確認（任意）**

```bash
cd news_pipeline && uv run python -c "
from collector.blocklist import is_blocked
print(is_blocked('https://zenn.dev/web_benriya/articles/x', {'web_benriya'}, 'path1'))  # True
print(is_blocked('https://zenn.dev/web_benriya2/articles/x', {'web_benriya'}, 'path1')) # False
"
```

Expected: `True` と `False`
