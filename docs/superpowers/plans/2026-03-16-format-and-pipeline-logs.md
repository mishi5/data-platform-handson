# Format & Pipeline Logs Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Slackの通知フォーマットにarticle_idとコピー用URLを追加し、パイプライン実行ログをBigQueryに保存する。

**Architecture:** BigQueryに`pipeline_logs`テーブルを追加（Terraform管理）。`bq_client.py`に`insert_pipeline_log()`を追加し、`main.py`の`_run_pipeline()`が実行統計（件数・キーワード・エラー）をfinallyで確実に書き込む。通知フォーマットは`notifier.py`の`_format_message()`のみ修正。

**Tech Stack:** Python, BigQuery streaming insert, Terraform (google_bigquery_table), pytest with unittest.mock

---

## Chunk 1: Terraform + bq_client

### Task 1: `pipeline_logs` テーブルをTerraformに追加

**Files:**
- Modify: `news_pipeline/infra/bigquery.tf`

- [ ] **Step 1: `pipeline_logs` リソースを追加**

```hcl
resource "google_bigquery_table" "pipeline_logs" {
  dataset_id          = google_bigquery_dataset.tech_news.dataset_id
  table_id            = "pipeline_logs"
  deletion_protection = false

  schema = jsonencode([
    { name = "run_id",               type = "STRING",    mode = "REQUIRED" },
    { name = "triggered_by",         type = "STRING",    mode = "REQUIRED" },
    { name = "started_at",           type = "TIMESTAMP", mode = "REQUIRED" },
    { name = "finished_at",          type = "TIMESTAMP", mode = "NULLABLE" },
    { name = "articles_fetched",     type = "INT64",     mode = "NULLABLE" },
    { name = "new_articles",         type = "INT64",     mode = "NULLABLE" },
    { name = "summaries_generated",  type = "INT64",     mode = "NULLABLE" },
    { name = "notified_count",       type = "INT64",     mode = "NULLABLE" },
    { name = "error_count",          type = "INT64",     mode = "NULLABLE" },
    { name = "status",               type = "STRING",    mode = "REQUIRED" },
    { name = "error_message",        type = "STRING",    mode = "NULLABLE" },
    { name = "keywords",             type = "STRING",    mode = "REPEATED" },
  ])
}
```

- [ ] **Step 2: Terraform構文チェック**

```bash
cd news_pipeline/infra && terraform validate
```
Expected: `Success! The configuration is valid.`

- [ ] **Step 3: Commit**

```bash
git add news_pipeline/infra/bigquery.tf
git commit -m "feat: add pipeline_logs table to BigQuery (Terraform)"
```

---

### Task 2: `bq_client.py` に `insert_pipeline_log()` を追加

**Files:**
- Modify: `news_pipeline/collector/bq_client.py`
- Test: `news_pipeline/tests/test_bq_client.py`

- [ ] **Step 1: テストを書く**

`tests/test_bq_client.py` に追加：

```python
@patch("collector.bq_client.bigquery.Client")
def test_insert_pipeline_log_calls_insert_rows(mock_bq_class):
    mock_client = MagicMock()
    mock_bq_class.return_value = mock_client
    mock_client.insert_rows_json.return_value = []

    bq = BQClient(project="test-project")
    log = {
        "run_id": "run-1",
        "triggered_by": "scheduler",
        "started_at": "2026-03-16T10:00:00Z",
        "finished_at": "2026-03-16T10:01:00Z",
        "articles_fetched": 10,
        "new_articles": 5,
        "summaries_generated": 3,
        "notified_count": 3,
        "error_count": 0,
        "status": "success",
        "error_message": None,
        "keywords": ["dbt", "BigQuery"],
    }
    bq.insert_pipeline_log(log)

    mock_client.insert_rows_json.assert_called_once()
    call_args = mock_client.insert_rows_json.call_args
    assert "pipeline_logs" in call_args[0][0]
    assert call_args[0][1][0]["run_id"] == "run-1"
    assert call_args[0][1][0]["keywords"] == ["dbt", "BigQuery"]
```

- [ ] **Step 2: テストが失敗することを確認**

```bash
cd news_pipeline && python -m pytest tests/test_bq_client.py::test_insert_pipeline_log_calls_insert_rows -v
```
Expected: FAIL (AttributeError: 'BQClient' object has no attribute 'insert_pipeline_log')

- [ ] **Step 3: `insert_pipeline_log()` を実装**

`bq_client.py` の末尾に追加：

```python
def insert_pipeline_log(self, log: dict) -> None:
    """パイプライン実行ログを pipeline_logs テーブルに挿入する。"""
    table_id = f"{self.project}.{DATASET}.pipeline_logs"
    errors = self.client.insert_rows_json(table_id, [log])
    if errors:
        logger.error("[bq_client] insert_pipeline_log errors: %s", errors)
        raise RuntimeError(f"BigQuery pipeline_logs insert failed: {errors}")
```

- [ ] **Step 4: テストが通ることを確認**

```bash
cd news_pipeline && python -m pytest tests/test_bq_client.py -v
```
Expected: 全テスト PASS

- [ ] **Step 5: Commit**

```bash
git add news_pipeline/collector/bq_client.py news_pipeline/tests/test_bq_client.py
git commit -m "feat: add insert_pipeline_log() to BQClient"
```

---

## Chunk 2: main.py ログ収集 + notifier フォーマット

### Task 3: `_run_pipeline()` にログ収集ロジックを追加

**Files:**
- Modify: `news_pipeline/collector/main.py`

- [ ] **Step 1: `_run_pipeline()` を修正**

`main.py` の `_run_pipeline()` を以下のように書き換える：

```python
def _run_pipeline(triggered_by: str = "scheduler") -> int:
    """パイプライン実行。通知件数を返す。"""
    import uuid
    from datetime import datetime, timezone

    run_id = str(uuid.uuid4())
    started_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    log: dict = {
        "run_id": run_id,
        "triggered_by": triggered_by,
        "started_at": started_at,
        "finished_at": None,
        "articles_fetched": 0,
        "new_articles": 0,
        "summaries_generated": 0,
        "notified_count": 0,
        "error_count": 0,
        "status": "success",
        "error_message": None,
        "keywords": [],
    }

    config = load_config()
    feeds: dict[str, str] = config.get("feeds", {})
    keywords: list[str] = config.get("keywords", [])
    max_summarize: int = config.get("max_summarize", _DEFAULT_MAX_SUMMARIZE)
    log["keywords"] = keywords

    bq = BQClient(project=PROJECT_ID)

    try:
        # 1. RSS 取得
        articles = fetch_articles(feeds)
        log["articles_fetched"] = len(articles)
        logger.info("[pipeline] fetched %d articles from RSS", len(articles))

        # 2. dedup（raw_articlesベース）
        existing_urls = bq.get_existing_urls()
        new_articles = [a for a in articles if a["url"] not in existing_urls]
        log["new_articles"] = len(new_articles)
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
                        keywords=keywords,
                    )
                except Exception as e:
                    logger.warning("[pipeline] summarize failed for %s: %s", article["url"], e)
                    log["error_count"] += 1
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
            log["summaries_generated"] = len(relevant_summaries)
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

        log["notified_count"] = len(top)
        return len(top)

    except Exception as e:
        log["status"] = "error"
        log["error_message"] = str(e)
        logger.error("[pipeline] pipeline error: %s", e)
        raise

    finally:
        log["finished_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        try:
            bq.insert_pipeline_log(log)
            logger.info("[pipeline] saved pipeline log run_id=%s", run_id)
        except Exception as e:
            logger.error("[pipeline] failed to save pipeline log: %s", e)
```

- [ ] **Step 2: `/slack` エンドポイントに `triggered_by` を渡す**

`slack_command()` 内のスレッド起動部分を修正：

```python
threading.Thread(target=_run_pipeline, args=("slack_command",), daemon=True).start()
```

- [ ] **Step 3: 構文チェック**

```bash
cd news_pipeline && python -c "import collector.main"
```
Expected: エラーなし

- [ ] **Step 4: Commit**

```bash
git add news_pipeline/collector/main.py
git commit -m "feat: record pipeline execution log to BigQuery"
```

---

### Task 4: 通知フォーマットを改善

**Files:**
- Modify: `news_pipeline/collector/notifier.py`
- Test: `news_pipeline/tests/test_notifier.py`

- [ ] **Step 1: テストを追加**

`tests/test_notifier.py` の既存テストを更新し、新フォーマットのアサーションに合わせる：

```python
@patch("collector.notifier.requests.post")
def test_format_includes_article_id_and_url(mock_post):
    mock_post.return_value.status_code = 200

    articles = [
        {
            "article_id": "abc12345xyz",
            "title": "BigQuery update",
            "url": "https://cloud.google.com/blog/1",
            "source": "Google Cloud Blog",
            "summary": "- Feature A\n- Feature B",
        }
    ]
    send_slack_notification(articles, webhook_url="https://hooks.slack.com/test")

    call_json = mock_post.call_args.kwargs["json"]
    text = call_json["text"]
    assert "BigQuery update" in text
    assert "abc12345" in text          # article_id先頭8文字
    assert "https://cloud.google.com/blog/1" in text  # コピー用URL
```

- [ ] **Step 2: テストが失敗することを確認**

```bash
cd news_pipeline && python -m pytest tests/test_notifier.py::test_format_includes_article_id_and_url -v
```
Expected: FAIL

- [ ] **Step 3: `_format_message()` を修正**

```python
def _format_message(articles: list[dict]) -> str:
    """記事リストを Slack 投稿用のテキストにフォーマットする。"""
    lines = ["*本日のデータエンジニアリング技術ニュース*\n"]
    for i, a in enumerate(articles, 1):
        article_id_short = a.get("article_id", "")[:8]
        lines.append(f"*{i}. {a['title']}*")
        lines.append(a.get("summary", ""))
        lines.append(
            f"_出典: {a['source']}_ | ID: `{article_id_short}` | <{a['url']}|リンクを開く>"
        )
        lines.append(f"`{a['url']}`\n")
    return "\n".join(lines)
```

- [ ] **Step 4: 全テストが通ることを確認**

```bash
cd news_pipeline && python -m pytest tests/ -v
```
Expected: 全テスト PASS

- [ ] **Step 5: Commit**

```bash
git add news_pipeline/collector/notifier.py news_pipeline/tests/test_notifier.py
git commit -m "feat: improve Slack notification format (article_id, copyable URL)"
```
