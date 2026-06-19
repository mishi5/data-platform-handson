# Slack通知に発行日/取得日を表示 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Slack のニュース通知で各記事に発行日（無ければ取得日）を JST・絶対日付＋種別ラベルで表示する。

**Architecture:** `notifier.py` に純粋関数 `format_date_label` を追加し、各記事セクションの「出典」行に併記。日付は `summaries` に無いため、`bq_client.get_unnotified_summaries` で `raw_articles` を LEFT JOIN して `published_at` / `collected_at` を取得する。

**Tech Stack:** Python 3.13 / FastAPI / Slack Block Kit / pytest（モック完結）/ zoneinfo（標準ライブラリ）

---

## File Structure

- **Modify** `news_pipeline/collector/notifier.py` — `format_date_label` 追加、`_format_blocks` で出典行に併記。
- **Modify** `news_pipeline/tests/test_notifier.py` — `format_date_label` のテスト追加。
- **Modify** `news_pipeline/collector/bq_client.py` — `get_unnotified_summaries` に raw_articles JOIN。

テストは `cd news_pipeline && uv run pytest` で実行（CLAUDE.md準拠）。import は `collector.` 始まり。

---

### Task 1: `format_date_label` 純粋関数

**Files:**
- Modify: `news_pipeline/collector/notifier.py`
- Test: `news_pipeline/tests/test_notifier.py`

- [ ] **Step 1: Write the failing test**

`news_pipeline/tests/test_notifier.py` の import 行を更新:

```python
from collector.notifier import (
    format_date_label,
    send_no_news_notification,
    send_slack_notification,
)
```

ファイル末尾に追記:

```python
def test_format_date_label_uses_published():
    # JST: 2026-06-18T09:00Z -> 18:00 JST 同日
    assert format_date_label("2026-06-18T09:00:00+00:00", "2026-06-19T00:00:00+00:00") == "🗓 発行: 2026-06-18"


def test_format_date_label_falls_back_to_collected():
    assert format_date_label(None, "2026-06-18T09:00:00+00:00") == "🗓 取得: 2026-06-18"
    assert format_date_label("", "2026-06-18T09:00:00+00:00") == "🗓 取得: 2026-06-18"


def test_format_date_label_both_missing_returns_empty():
    assert format_date_label(None, None) == ""
    assert format_date_label("", "") == ""


def test_format_date_label_utc_to_jst_rolls_over():
    # UTC 2026-06-18T20:00Z -> JST 2026-06-19T05:00
    assert format_date_label("2026-06-18T20:00:00+00:00", None) == "🗓 発行: 2026-06-19"


def test_format_date_label_accepts_datetime():
    from datetime import datetime, timezone

    dt = datetime(2026, 6, 18, 20, 0, 0, tzinfo=timezone.utc)
    assert format_date_label(dt, None) == "🗓 発行: 2026-06-19"


def test_format_date_label_unparseable_published_falls_back():
    assert format_date_label("not-a-date", "2026-06-18T09:00:00+00:00") == "🗓 取得: 2026-06-18"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd news_pipeline && uv run pytest tests/test_notifier.py -v`
Expected: FAIL（`ImportError: cannot import name 'format_date_label'`）

- [ ] **Step 3: Write minimal implementation**

`news_pipeline/collector/notifier.py` の import 群に追加:

```python
from datetime import datetime
from zoneinfo import ZoneInfo
```

`_format_blocks` の定義より前（`logger = ...` の直後）に追加:

```python
_JST = ZoneInfo("Asia/Tokyo")


def _to_jst_date(value) -> str | None:
    """datetime / ISO文字列を JST の YYYY-MM-DD に変換する。無効なら None。"""
    if not value:
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        try:
            dt = datetime.fromisoformat(str(value))
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo("UTC"))
    return dt.astimezone(_JST).strftime("%Y-%m-%d")


def format_date_label(published_at, collected_at) -> str:
    """発行日優先・無ければ取得日を「🗓 発行: YYYY-MM-DD」形式で返す。両方無効なら空文字。"""
    pub = _to_jst_date(published_at)
    if pub:
        return f"🗓 発行: {pub}"
    col = _to_jst_date(collected_at)
    if col:
        return f"🗓 取得: {col}"
    return ""
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd news_pipeline && uv run pytest tests/test_notifier.py -v`
Expected: PASS（既存 + 新規6件）

- [ ] **Step 5: Commit**

```bash
git add news_pipeline/collector/notifier.py news_pipeline/tests/test_notifier.py
git commit -m "feat(notifier): 発行日/取得日をJSTで整形する format_date_label を追加

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: `_format_blocks` の出典行に日付を併記

**Files:**
- Modify: `news_pipeline/collector/notifier.py:17-27`
- Test: `news_pipeline/tests/test_notifier.py`

- [ ] **Step 1: Write the failing test**

`news_pipeline/tests/test_notifier.py` の末尾に追記:

```python
@patch("collector.notifier.requests.post")
def test_notification_includes_published_date(mock_post):
    mock_post.return_value.status_code = 200
    articles = [
        {
            "title": "BigQuery update",
            "url": "https://cloud.google.com/blog/1",
            "source": "Google Cloud Blog",
            "summary": "- Feature A",
            "published_at": "2026-06-18T09:00:00+00:00",
        }
    ]
    send_slack_notification(articles, webhook_url="https://hooks.slack.com/test")
    blocks_str = str(mock_post.call_args.kwargs["json"]["blocks"])
    assert "🗓 発行: 2026-06-18" in blocks_str


@patch("collector.notifier.requests.post")
def test_notification_without_date_has_no_date_label(mock_post):
    mock_post.return_value.status_code = 200
    articles = [
        {
            "title": "No date article",
            "url": "https://example.com/1",
            "source": "Example",
            "summary": "- x",
        }
    ]
    send_slack_notification(articles, webhook_url="https://hooks.slack.com/test")
    blocks_str = str(mock_post.call_args.kwargs["json"]["blocks"])
    assert "🗓" not in blocks_str
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd news_pipeline && uv run pytest tests/test_notifier.py::test_notification_includes_published_date -v`
Expected: FAIL（`🗓 発行: 2026-06-18` が blocks に含まれない）

- [ ] **Step 3: Write minimal implementation**

`news_pipeline/collector/notifier.py` の `_format_blocks` 内、記事セクションを生成する箇所を変更する。

既存:

```python
    for i, a in enumerate(articles, 1):
        article_id = a.get("article_id", "")
        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{i}. {a['title']}*\n{a.get('summary', '')}\n_出典: {a['source']}_",
                },
            }
        )
```

変更後:

```python
    for i, a in enumerate(articles, 1):
        article_id = a.get("article_id", "")
        date_label = format_date_label(a.get("published_at"), a.get("collected_at"))
        source_line = f"_出典: {a['source']}"
        if date_label:
            source_line += f" ・ {date_label}"
        source_line += "_"
        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{i}. {a['title']}*\n{a.get('summary', '')}\n{source_line}",
                },
            }
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd news_pipeline && uv run pytest tests/test_notifier.py -v`
Expected: PASS（全件）

- [ ] **Step 5: Commit**

```bash
git add news_pipeline/collector/notifier.py news_pipeline/tests/test_notifier.py
git commit -m "feat(notifier): 通知メッセージの出典行に発行日/取得日を併記

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: `get_unnotified_summaries` に raw_articles を JOIN

**Files:**
- Modify: `news_pipeline/collector/bq_client.py:29-43`

- [ ] **Step 1: Update the query**

`news_pipeline/collector/bq_client.py` の `get_unnotified_summaries` の query を変更し、raw_articles を LEFT JOIN して published_at / collected_at を加える。

既存:

```python
        query = (
            f"SELECT s.* FROM ("
            f"  SELECT *, ROW_NUMBER() OVER (PARTITION BY article_id ORDER BY importance_score DESC) AS _rn"
            f"  FROM `{self.project}.{DATASET}.summaries`"
            f") s"
            f" LEFT JOIN `{self.project}.{DATASET}.notification_log` n"
            f" ON s.article_id = n.article_id"
            f" WHERE n.article_id IS NULL AND s._rn = 1"
            f" ORDER BY s.importance_score DESC"
        )
```

変更後:

```python
        query = (
            f"SELECT s.*, r.published_at, r.collected_at FROM ("
            f"  SELECT *, ROW_NUMBER() OVER (PARTITION BY article_id ORDER BY importance_score DESC) AS _rn"
            f"  FROM `{self.project}.{DATASET}.summaries`"
            f") s"
            f" LEFT JOIN `{self.project}.{DATASET}.notification_log` n"
            f" ON s.article_id = n.article_id"
            f" LEFT JOIN `{self.project}.{DATASET}.raw_articles` r"
            f" ON s.article_id = r.article_id"
            f" WHERE n.article_id IS NULL AND s._rn = 1"
            f" ORDER BY s.importance_score DESC"
        )
```

返却 dict から `_rn` を除外する処理（既存の dict 内包表記）はそのまま。

- [ ] **Step 2: Verify no test regressions**

Run: `cd news_pipeline && uv run pytest -v`
Expected: PASS（全テスト。bq_client は BigQuery 接続が無いと実行されない純クエリ変更なので既存テストに影響なし）

- [ ] **Step 3: Syntax check**

Run: `cd news_pipeline && uv run python -m py_compile collector/bq_client.py && echo OK`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add news_pipeline/collector/bq_client.py
git commit -m "feat(bq_client): get_unnotified_summaries に発行日/取得日をJOINで付与

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: 最終確認

- [ ] **Step 1: Run full test suite**

Run: `cd news_pipeline && uv run pytest -q`
Expected: 全テスト PASS。

- [ ] **Step 2: 表示の手動確認**

```bash
cd news_pipeline && uv run python -c "
from collector.notifier import format_date_label
print(format_date_label('2026-06-18T20:00:00+00:00', None))  # 🗓 発行: 2026-06-19
print(format_date_label(None, '2026-06-18T01:00:00+00:00'))  # 🗓 取得: 2026-06-18
print(repr(format_date_label(None, None)))                   # ''
"
```

Expected: `🗓 発行: 2026-06-19` / `🗓 取得: 2026-06-18` / `''`
