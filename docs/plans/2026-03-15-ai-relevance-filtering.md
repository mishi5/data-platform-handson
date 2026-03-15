# AI-based Relevance Filtering Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** キーワードマッチによる事前フィルタを廃止し、全記事を要約した上で `importance_score` による関連性フィルタに置き換える。

**Architecture:**
- dedup判定を `summaries` から `raw_articles` に切り替えることでキーワードフィルタ廃止後もデータの整合性を維持する。
- 全記事を Claude で要約し、`importance_score >= IMPORTANCE_THRESHOLD` を満たした記事のみ `summaries` テーブルへ保存する。
- `summaries` テーブルに `notified_at` カラムを追加し、通知済み管理を行う。新着記事がなくても **未通知サマリーが存在すれば通知判定に進む**。
- **変数の意味を明確化:**
  - `max_summarize`: 1回の実行で要約する記事の最大件数（Google Sheetsで管理）
  - `MAX_NOTIFY`: importance_scoreフィルタ後に実際に通知する件数の上限（env var）

**Tech Stack:** Python, anthropic SDK (claude-haiku-4-5), BigQuery, pytest, pytest-mock

---

## 変更ファイル一覧

| ファイル | 変更内容 |
|---------|---------|
| `news_pipeline/infra/main.tf` | `summaries` テーブルに `notified_at TIMESTAMP` カラム追加 |
| `news_pipeline/collector/bq_client.py` | `get_existing_urls()` を `raw_articles` に変更、`get_unnotified_summaries()`・`mark_summaries_notified()` 追加 |
| `news_pipeline/collector/main.py` | `_is_relevant` 削除、`max_summarize` 変数化、`IMPORTANCE_THRESHOLD` 追加、未通知サマリー対応、通知後マーク処理追加 |
| `news_pipeline/tests/test_bq_client.py` | `get_existing_urls` のテスト更新、新メソッドのテスト追加 |
| `news_pipeline/.env.example` | `IMPORTANCE_THRESHOLD` 変数を追加 |

---

## Chunk 0: summaries テーブルに notified_at を追加 & BQ クライアント拡張

### Task 0-1: Terraform スキーマ変更

**Files:**
- Modify: `news_pipeline/infra/main.tf`

- [ ] **Step 1: `summaries` テーブルの schema に `notified_at` を追加**

`main.tf` の `google_bigquery_table` リソース（summaries テーブル）の schema に以下を追記する：

```json
{
  "name": "notified_at",
  "type": "TIMESTAMP",
  "mode": "NULLABLE",
  "description": "Slack通知を送った日時。NULLの場合は未通知。"
}
```

- [ ] **Step 2: `terraform apply` で BigQuery テーブルを更新**

```bash
cd news_pipeline/infra
terraform apply -var="project_id=$GCP_PROJECT_ID"
```

期待: `google_bigquery_table.summaries` が updated in-place（既存データは保持）

---

### Task 0-2: `bq_client.py` に未通知サマリー取得・通知済みマーク処理を追加

**Files:**
- Modify: `news_pipeline/collector/bq_client.py`
- Test: `news_pipeline/tests/test_bq_client.py`

- [ ] **Step 1: テストを先に追加（TDD）**

`news_pipeline/tests/test_bq_client.py` に以下を追加：

```python
@patch("collector.bq_client.bigquery.Client")
def test_get_unnotified_summaries_returns_list(mock_bq_class):
    mock_client = MagicMock()
    mock_bq_class.return_value = mock_client

    mock_row = MagicMock()
    mock_row.__iter__ = MagicMock(return_value=iter([]))
    # dict(row) を模倣するため keys() と __getitem__ を設定
    mock_row.keys.return_value = ["article_id", "title", "url", "source", "summary", "importance_score", "notified_at"]
    mock_row.__getitem__ = lambda self, key: {
        "article_id": "abc123",
        "title": "Test",
        "url": "https://example.com",
        "source": "Test Source",
        "summary": "summary text",
        "importance_score": 0.8,
        "notified_at": None,
    }[key]
    mock_client.query.return_value.result.return_value = [mock_row]

    bq = BQClient(project="test-project")
    result = bq.get_unnotified_summaries()

    assert isinstance(result, list)
    query_arg = mock_client.query.call_args[0][0]
    assert "notified_at IS NULL" in query_arg
    assert "summaries" in query_arg


@patch("collector.bq_client.bigquery.Client")
def test_mark_summaries_notified_runs_update(mock_bq_class):
    mock_client = MagicMock()
    mock_bq_class.return_value = mock_client
    mock_client.query.return_value.result.return_value = []

    bq = BQClient(project="test-project")
    bq.mark_summaries_notified(["id1", "id2"])

    query_arg = mock_client.query.call_args[0][0]
    assert "UPDATE" in query_arg
    assert "notified_at" in query_arg
    assert "id1" in query_arg
```

- [ ] **Step 2: テストが失敗することを確認**

```bash
cd news_pipeline
python -m pytest tests/test_bq_client.py::test_get_unnotified_summaries_returns_list \
  tests/test_bq_client.py::test_mark_summaries_notified_runs_update -v
```

期待: `FAILED` — メソッドが存在しないため

- [ ] **Step 3: `bq_client.py` に新メソッドを実装**

```python
def get_unnotified_summaries(self) -> list[dict]:
    """notified_at IS NULL のサマリーを返す（未通知分）。"""
    query = (
        f"SELECT * FROM `{self.project}.{DATASET}.summaries`"
        " WHERE notified_at IS NULL"
        " ORDER BY importance_score DESC"
    )
    rows = self.client.query(query).result()
    return [dict(row) for row in rows]

def mark_summaries_notified(self, article_ids: list[str]) -> None:
    """指定した article_id の notified_at を現在時刻に更新する。"""
    if not article_ids:
        return
    ids_str = ", ".join(f"'{aid}'" for aid in article_ids)
    query = (
        f"UPDATE `{self.project}.{DATASET}.summaries`"
        f" SET notified_at = CURRENT_TIMESTAMP()"
        f" WHERE article_id IN ({ids_str})"
    )
    self.client.query(query).result()
```

- [ ] **Step 4: テストが通ることを確認**

```bash
cd news_pipeline
python -m pytest tests/test_bq_client.py -v
```

期待: 全テスト PASSED

- [ ] **Step 5: コミット**

```bash
git add news_pipeline/infra/main.tf news_pipeline/collector/bq_client.py news_pipeline/tests/test_bq_client.py
git commit -m "feat: summariesにnotified_atカラム追加、未通知サマリー取得・更新メソッドを追加"
```

---

## Chunk 1: dedup クエリを raw_articles に変更

### Task 1: `get_existing_urls` のクエリ変更

**Files:**
- Modify: `news_pipeline/collector/bq_client.py:16-23`
- Test: `news_pipeline/tests/test_bq_client.py`

- [ ] **Step 1: テストを更新（クエリ対象が `raw_articles` であることを検証）**

`news_pipeline/tests/test_bq_client.py` の `test_get_existing_urls_returns_set` を以下に差し替える：

```python
@patch("collector.bq_client.bigquery.Client")
def test_get_existing_urls_queries_raw_articles(mock_bq_class):
    mock_client = MagicMock()
    mock_bq_class.return_value = mock_client

    mock_row1 = MagicMock()
    mock_row1.url = "https://example.com/1"
    mock_client.query.return_value.result.return_value = [mock_row1]

    bq = BQClient(project="test-project")
    urls = bq.get_existing_urls()

    assert urls == {"https://example.com/1"}
    query_arg = mock_client.query.call_args[0][0]
    assert "raw_articles" in query_arg
    assert "summaries" not in query_arg
```

- [ ] **Step 2: テストが失敗することを確認**

```bash
cd news_pipeline
python -m pytest tests/test_bq_client.py::test_get_existing_urls_queries_raw_articles -v
```

期待: `FAILED` — `assert "summaries" not in query_arg` で失敗

- [ ] **Step 3: `bq_client.py` の実装を変更**

`news_pipeline/collector/bq_client.py` の `get_existing_urls` を以下に変更：

```python
def get_existing_urls(self) -> set[str]:
    """raw_articles に保存済みの URL セットを返す（dedup 用）。"""
    query = f"SELECT url FROM `{self.project}.{DATASET}.raw_articles`"
    rows = self.client.query(query).result()
    return {row.url for row in rows}
```

- [ ] **Step 4: テストが通ることを確認**

```bash
cd news_pipeline
python -m pytest tests/test_bq_client.py -v
```

期待: 全テスト PASSED

- [ ] **Step 5: コミット**

```bash
git add news_pipeline/collector/bq_client.py news_pipeline/tests/test_bq_client.py
git commit -m "fix: dedup判定をsummariesからraw_articlesに変更"
```

---

## Chunk 2: キーワードフィルタ廃止・importance_score フィルタへ置き換え

### Task 2: `main.py` のパイプライン変更

**Files:**
- Modify: `news_pipeline/collector/main.py`
- Modify: `news_pipeline/.env.example`

#### 変数名の整理

| 変数 | 管理場所 | 意味 |
|------|---------|------|
| `max_summarize` | Google Sheets（settings シート） | 1実行で要約する記事の最大件数 |
| `MAX_NOTIFY` | 環境変数（Terraform） | フィルタ後に実際に通知する件数の上限 |
| `IMPORTANCE_THRESHOLD` | 環境変数（Terraform） | importance_score フィルタの閾値 |

#### 変更後のパイプライン全体像

現在（キーワードフィルタあり）：
```
全記事 → dedup → _is_relevant → relevant[] → 要約 → summaries保存 → 通知
```

変更後（importance_score フィルタ + 未通知サマリー対応）：
```
全記事 → dedup →（新着あり）→ 要約(max_summarize件) → importance_score >= THRESHOLD → summaries保存 → 未通知サマリー取得 → 通知(MAX_NOTIFY件) → mark notified
                ↓（新着なし）
          未通知サマリー取得 → (あれば) → 通知(MAX_NOTIFY件) → mark notified
                            → (なければ) → no-news通知
```

- [ ] **Step 1: `IMPORTANCE_THRESHOLD` 環境変数・変数名変更の追加**

`news_pipeline/collector/main.py` の環境変数読み込みブロックに以下を適用：

```python
# max_summarize: Google Sheetsのsettingsシートから取得（load_config経由）
_DEFAULT_MAX_SUMMARIZE = 10

# importance_score フィルタ閾値（未設定 = 0.5）
IMPORTANCE_THRESHOLD = float(os.environ.get("IMPORTANCE_THRESHOLD", 0.5))

# MAX_NOTIFY: importance_scoreフィルタ後に通知する件数の上限
MAX_NOTIFY = int(os.environ.get("MAX_NOTIFY", 5))
```

`news_pipeline/.env.example` に以下を追加：
```
IMPORTANCE_THRESHOLD=0.5
```

- [ ] **Step 2: `_is_relevant` 関数とフィルタステップを削除し、`_run_pipeline` を全面変更**

`main.py` から `_is_relevant` 関数を削除する。

`_run_pipeline` を以下に置き換える：

```python
def _run_pipeline() -> int:
    """パイプライン実行。通知件数を返す。"""
    config = load_config()
    feeds: dict[str, str] = config.get("feeds", {})
    max_summarize: int = config.get("max_summarize", _DEFAULT_MAX_SUMMARIZE)

    bq = BQClient(project=PROJECT_ID)

    # 1. RSS 取得
    articles = fetch_articles(feeds)
    logger.info("[pipeline] fetched %d articles from RSS", len(articles))

    # 2. dedup
    existing_urls = bq.get_existing_urls()
    new_articles = [a for a in articles if a["url"] not in existing_urls]
    logger.info("[pipeline] %d new articles after dedup", len(new_articles))

    if new_articles:
        # 3. 要約する件数を上限に絞る
        new_articles = new_articles[:max_summarize]
        logger.info("[pipeline] limited to %d articles (max_summarize)", max_summarize)

        # 4. 本文取得
        for article in new_articles:
            article["content"] = fetch_content(article["url"])

        # 5. raw_articles 保存
        bq.insert_raw_articles(new_articles)
        logger.info("[pipeline] saved %d to raw_articles", len(new_articles))

        # 6. 要約生成（全新着記事）
        summaries = []
        for article in new_articles:
            try:
                result = summarize_article(
                    title=article["title"],
                    content=article["content"] or "",
                    api_key=ANTHROPIC_API_KEY,
                )
            except Exception as e:
                logger.warning("[pipeline] summarize failed for %s: %s", article["url"], e)
                continue
            if result:
                summaries.append(
                    {
                        "article_id": article["article_id"],
                        "title": article["title"],
                        "url": article["url"],
                        "source": article["source"],
                        **result,
                    }
                )

        # 7. importance_score によるフィルタリング
        relevant_summaries = [
            s for s in summaries if s.get("importance_score", 0) >= IMPORTANCE_THRESHOLD
        ]
        logger.info(
            "[pipeline] %d relevant summaries (importance_score >= %.1f)",
            len(relevant_summaries),
            IMPORTANCE_THRESHOLD,
        )

        # 8. summaries 保存（関連あり記事のみ）
        if relevant_summaries:
            bq.insert_summaries(relevant_summaries)
            logger.info("[pipeline] saved %d summaries", len(relevant_summaries))
    else:
        logger.info("[pipeline] no new articles, checking unnotified summaries")

    # 9. 未通知サマリーを取得して通知（新着ありなしに関わらず実施）
    unnotified = bq.get_unnotified_summaries()
    logger.info("[pipeline] %d unnotified summaries in BQ", len(unnotified))

    if not unnotified:
        send_no_news_notification(SLACK_WEBHOOK_URL, "新着記事はありませんでした。")
        return 0

    # 10. importance_score 降順で最大 MAX_NOTIFY 件を通知
    top = sorted(unnotified, key=lambda x: x.get("importance_score", 0), reverse=True)[
        :MAX_NOTIFY
    ]
    send_slack_notification(top, webhook_url=SLACK_WEBHOOK_URL)
    logger.info("[pipeline] notified %d articles", len(top))

    # 11. 通知済みマーク
    notified_ids = [a["article_id"] for a in top]
    bq.mark_summaries_notified(notified_ids)
    logger.info("[pipeline] marked %d summaries as notified", len(notified_ids))

    return len(top)
```

- [ ] **Step 3: テストを実行して既存テストが壊れていないことを確認**

```bash
cd news_pipeline
python -m pytest tests/ -v
```

期待: 全テスト PASSED

- [ ] **Step 4: コミット**

```bash
git add news_pipeline/collector/main.py news_pipeline/.env.example
git commit -m "feat: キーワードフィルタをimportance_scoreフィルタに置き換え・未通知サマリー対応"
```

---

## 動作確認チェックリスト

ローカル実行で以下を確認：

```bash
cd news_pipeline/collector
python main.py
```

- [ ] `[pipeline] fetched N articles from RSS` のログが出る
- [ ] `[pipeline] N new articles after dedup` のログが出る（`raw_articles` ベースでdedup）
- [ ] （新着あり時）`[pipeline] N relevant summaries (importance_score >= 0.5)` のログが出る
- [ ] `[pipeline] N unnotified summaries in BQ` のログが出る
- [ ] Slack に通知が届く（またはno-news通知が届く）
- [ ] 通知後、BQ の `summaries` テーブルで `notified_at` が更新されていること
- [ ] 再実行時、通知済み記事が重複通知されないこと
