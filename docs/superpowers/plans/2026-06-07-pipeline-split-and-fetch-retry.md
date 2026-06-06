# パイプライン分割・本文取得リトライ・閾値変更 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** news_pipeline を収集（`/collect`）と通知（`/notify`）の2エンドポイント+2スケジューラに分割し、本文取得の次回繰り越しリトライを追加し、importance_threshold を settings シートの 0.65 に移行する。

**Architecture:** リトライの状態遷移は純粋関数 `fetch_retry.py` に切り出して単体テストする。`article_parser.fetch_content` は UA を付け `(text, ok)` を返す。`bq_client` に pending 取得（SELECT）と本文更新（DML UPDATE・buffer エラーは握りつぶし）を追加。raw_articles に `content_status`/`retry_count` 列を足す。`main.py` の `_run_pipeline` を `_run_collect`/`_run_notify` に分割し、閾値・リトライ上限を settings から読む。Cloud Scheduler を collect/notify の2本にする。

**Tech Stack:** Python 3.12 / FastAPI / BigQuery（google-cloud-bigquery）/ Terraform / pytest（`uv run pytest`）

---

## File Structure

- **Create** `news_pipeline/collector/fetch_retry.py` — 本文取得結果→次状態の純粋関数（重い依存なし）
- **Create** `news_pipeline/tests/test_fetch_retry.py` — fetch_retry の単体テスト
- **Modify** `news_pipeline/collector/article_parser.py` — UA 付与・`(text, ok)` 返却
- **Modify** `news_pipeline/tests/test_article_parser.py` — 戻り値 tuple 化に追従
- **Modify** `news_pipeline/collector/bq_client.py` — `get_pending_articles` / `update_article_content` 追加
- **Modify** `news_pipeline/tests/test_bq_client.py` — 新メソッドのテスト追加
- **Modify** `news_pipeline/infra/bigquery.tf` — raw_articles に `content_status`/`retry_count` 列追加
- **Modify** `news_pipeline/collector/main.py` — `_run_pipeline` を `_run_collect`/`_run_notify` に分割・エンドポイント再編・settings 由来の閾値/リトライ上限
- **Modify** `news_pipeline/infra/main.tf` — collect スケジューラ張り替え + notify スケジューラ追加
- **Modify** `CLAUDE.md` / **Modify** `news_pipeline/README.md` — 構成・設定の追従

テストは `cd news_pipeline && uv run pytest ...`（uv 必須）。

---

## Task 1: fetch_retry 純粋関数

**Files:**
- Create: `news_pipeline/collector/fetch_retry.py`
- Test: `news_pipeline/tests/test_fetch_retry.py`

- [ ] **Step 1: Write the failing test**

`news_pipeline/tests/test_fetch_retry.py` を新規作成:

```python
from collector.fetch_retry import next_fetch_state


def test_success_keeps_retry_count_and_sets_ok():
    assert next_fetch_state(ok=True, retry_count=0, max_retries=3) == ("ok", 0)


def test_success_on_pending_article_sets_ok():
    assert next_fetch_state(ok=True, retry_count=2, max_retries=3) == ("ok", 2)


def test_first_failure_becomes_pending():
    assert next_fetch_state(ok=False, retry_count=0, max_retries=3) == ("pending", 1)


def test_failure_below_max_stays_pending():
    assert next_fetch_state(ok=False, retry_count=1, max_retries=3) == ("pending", 2)


def test_failure_reaching_max_becomes_failed():
    assert next_fetch_state(ok=False, retry_count=2, max_retries=3) == ("failed", 3)


def test_failure_at_max_one_becomes_failed_immediately():
    assert next_fetch_state(ok=False, retry_count=0, max_retries=1) == ("failed", 1)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd news_pipeline && uv run pytest tests/test_fetch_retry.py -v`
Expected: FAIL（`ModuleNotFoundError: collector.fetch_retry`）

- [ ] **Step 3: Implement**

`news_pipeline/collector/fetch_retry.py` を新規作成:

```python
"""本文取得の結果から次の (content_status, retry_count) を決める純粋関数。

重い依存を持たず単体テストしやすい。content_status は "ok" / "pending" / "failed"。
"""


def next_fetch_state(ok: bool, retry_count: int, max_retries: int) -> tuple[str, int]:
    """本文取得結果から次状態を決める。

    ok=True  … 取得成功 → ("ok", retry_count)（カウント据え置き、本文の有無は問わない）
    ok=False … 失敗 → カウント +1。max 以上なら ("failed", n+1)、未満なら ("pending", n+1)
    """
    if ok:
        return "ok", retry_count
    new_count = retry_count + 1
    if new_count >= max_retries:
        return "failed", new_count
    return "pending", new_count
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd news_pipeline && uv run pytest tests/test_fetch_retry.py -v`
Expected: PASS（6テスト）

- [ ] **Step 5: Commit**

```bash
git add news_pipeline/collector/fetch_retry.py news_pipeline/tests/test_fetch_retry.py
git commit -m "feat(fetch_retry): 本文取得結果から次状態を決める純粋関数を追加

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: article_parser に UA 付与・(text, ok) 返却

**Files:**
- Modify: `news_pipeline/collector/article_parser.py`（全面置き換え）
- Test: `news_pipeline/tests/test_article_parser.py`（全面置き換え）

- [ ] **Step 1: Write the failing test**

`news_pipeline/tests/test_article_parser.py` を以下で全面置き換え:

```python
from collector.article_parser import fetch_content


def test_fetch_content_returns_text_and_ok(mocker):
    mock_resp = mocker.MagicMock()
    mock_resp.text = "<html><body><p>BigQuery is great.</p></body></html>"
    mock_resp.raise_for_status.return_value = None
    mocker.patch("collector.article_parser.requests.get", return_value=mock_resp)
    mocker.patch(
        "collector.article_parser.trafilatura.extract",
        return_value="BigQuery is great.",
    )

    text, ok = fetch_content("https://example.com/article")
    assert text == "BigQuery is great."
    assert ok is True


def test_fetch_content_http_error_returns_none_false(mocker):
    mock_resp = mocker.MagicMock()
    mock_resp.raise_for_status.side_effect = Exception("403 Forbidden")
    mocker.patch("collector.article_parser.requests.get", return_value=mock_resp)

    text, ok = fetch_content("https://example.com/article")
    assert text is None
    assert ok is False


def test_fetch_content_extract_none_is_ok(mocker):
    mock_resp = mocker.MagicMock()
    mock_resp.text = "<html></html>"
    mock_resp.raise_for_status.return_value = None
    mocker.patch("collector.article_parser.requests.get", return_value=mock_resp)
    mocker.patch("collector.article_parser.trafilatura.extract", return_value=None)

    text, ok = fetch_content("https://example.com/article")
    assert text is None
    assert ok is True


def test_fetch_content_sends_user_agent(mocker):
    mock_resp = mocker.MagicMock()
    mock_resp.text = "<html></html>"
    mock_resp.raise_for_status.return_value = None
    mock_get = mocker.patch("collector.article_parser.requests.get", return_value=mock_resp)
    mocker.patch("collector.article_parser.trafilatura.extract", return_value="x")

    fetch_content("https://example.com/article")
    headers = mock_get.call_args.kwargs["headers"]
    assert "User-Agent" in headers
    assert "Mozilla" in headers["User-Agent"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd news_pipeline && uv run pytest tests/test_article_parser.py -v`
Expected: FAIL（現 `fetch_content` は単一値を返すため tuple アンパックや UA 検証で失敗）

- [ ] **Step 3: Implement**

`news_pipeline/collector/article_parser.py` を以下で全面置き換え:

```python
"""記事URLから本文テキストを取得するモジュール。requests + trafilatura を使用。"""
import requests
import trafilatura  # type: ignore[import-untyped]

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}


def fetch_content(url: str) -> tuple[str | None, bool]:
    """URL から記事本文を抽出する。

    戻り値 (text, ok):
      ok=True  … HTTP取得に成功（text は本文。抽出できなければ None だがリトライ不要）
      ok=False … HTTP/通信エラー（リトライ対象）
    """
    try:
        response = requests.get(url, headers=_HEADERS, timeout=30)
        response.raise_for_status()
    except Exception as e:
        print(f"[article_parser] failed to fetch {url}: {e}")
        return None, False
    text = trafilatura.extract(response.text)  # type: ignore[attr-defined]
    return text, True
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd news_pipeline && uv run pytest tests/test_article_parser.py -v`
Expected: PASS（4テスト）

- [ ] **Step 5: Commit**

```bash
git add news_pipeline/collector/article_parser.py news_pipeline/tests/test_article_parser.py
git commit -m "feat(article_parser): UA付与と (text, ok) 返却でリトライ判定を可能に

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: bq_client に pending 取得・本文更新を追加

**Files:**
- Modify: `news_pipeline/collector/bq_client.py`（`insert_raw_articles` 直後にメソッド追加）
- Test: `news_pipeline/tests/test_bq_client.py`（末尾にテスト追加）

- [ ] **Step 1: Write the failing test**

`news_pipeline/tests/test_bq_client.py` の末尾に追加:

```python
@patch("collector.bq_client.bigquery.Client")
def test_get_pending_articles_filters_pending_and_retry(mock_bq_class):
    mock_client = MagicMock()
    mock_bq_class.return_value = mock_client

    _data = {
        "article_id": "p1", "url": "https://example.com/p1",
        "title": "Pending", "source": "Src", "retry_count": 1,
    }
    mock_row = MagicMock()
    mock_row.keys.return_value = list(_data.keys())
    mock_row.__getitem__ = lambda self, key: _data[key]
    mock_client.query.return_value.result.return_value = [mock_row]

    bq = BQClient(project="test-project")
    result = bq.get_pending_articles(max_retries=3)

    assert isinstance(result, list)
    assert result[0]["article_id"] == "p1"
    query_arg = mock_client.query.call_args[0][0]
    assert "raw_articles" in query_arg
    assert "content_status" in query_arg
    assert "pending" in query_arg
    assert "retry_count" in query_arg


@patch("collector.bq_client.bigquery.Client")
def test_update_article_content_runs_update_dml(mock_bq_class):
    mock_client = MagicMock()
    mock_bq_class.return_value = mock_client

    bq = BQClient(project="test-project")
    bq.update_article_content("p1", "body text", "ok", 1)

    query_arg = mock_client.query.call_args[0][0]
    assert "UPDATE" in query_arg
    assert "raw_articles" in query_arg
    assert "content_status" in query_arg


@patch("collector.bq_client.bigquery.Client")
def test_update_article_content_swallows_streaming_buffer_error(mock_bq_class):
    mock_client = MagicMock()
    mock_bq_class.return_value = mock_client
    mock_client.query.return_value.result.side_effect = Exception(
        "UPDATE or DELETE statement over table would affect rows in the streaming buffer"
    )

    bq = BQClient(project="test-project")
    # 例外を送出せず黙って握りつぶす（pending のまま次回に回す）
    bq.update_article_content("p1", "body text", "ok", 1)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd news_pipeline && uv run pytest tests/test_bq_client.py -k "pending or update_article_content" -v`
Expected: FAIL（`AttributeError: 'BQClient' object has no attribute 'get_pending_articles'`）

- [ ] **Step 3: Implement**

`news_pipeline/collector/bq_client.py` の `insert_raw_articles`（現 line 57-63）の直後に2メソッドを追加:

```python
    def get_pending_articles(self, max_retries: int) -> list[dict]:
        """本文未取得（content_status='pending'）かつリトライ上限未満の記事を返す。"""
        query = (
            f"SELECT article_id, url, title, source, retry_count"
            f" FROM `{self.project}.{DATASET}.raw_articles`"
            f" WHERE content_status = 'pending' AND retry_count < @max_retries"
        )
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("max_retries", "INT64", max_retries)
            ]
        )
        rows = self.client.query(query, job_config=job_config).result()
        return [dict(row) for row in rows]

    def update_article_content(
        self, article_id: str, content: str | None, content_status: str, retry_count: int
    ) -> None:
        """pending 記事の本文・ステータス・retry_count を DML UPDATE で更新する。

        streaming buffer 制約等で UPDATE が失敗しても送出せずログのみ。
        その記事は pending のまま残り、次回実行（buffer flush 後）で再試行される。
        """
        query = (
            f"UPDATE `{self.project}.{DATASET}.raw_articles`"
            f" SET content = @content, content_status = @status, retry_count = @retry"
            f" WHERE article_id = @aid"
        )
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("content", "STRING", content),
                bigquery.ScalarQueryParameter("status", "STRING", content_status),
                bigquery.ScalarQueryParameter("retry", "INT64", retry_count),
                bigquery.ScalarQueryParameter("aid", "STRING", article_id),
            ]
        )
        try:
            self.client.query(query, job_config=job_config).result()
        except Exception as e:
            logger.warning(
                "[bq_client] update_article_content skipped for %s: %s", article_id, e
            )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd news_pipeline && uv run pytest tests/test_bq_client.py -v`
Expected: PASS（既存 + 新規3テスト）

- [ ] **Step 5: Commit**

```bash
git add news_pipeline/collector/bq_client.py news_pipeline/tests/test_bq_client.py
git commit -m "feat(bq_client): pending 記事取得と本文 UPDATE（buffer エラー握りつぶし）を追加

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 4: raw_articles スキーマに列追加（Terraform）

**Files:**
- Modify: `news_pipeline/infra/bigquery.tf:11-19`（raw_articles の schema）

このタスクは単体テスト対象外（インフラ定義）。検証は `terraform validate`。

- [ ] **Step 1: schema に列を追加**

`news_pipeline/infra/bigquery.tf` の raw_articles の `schema = jsonencode([...])` を以下に変更（`content` 行の後に2行追加）:

```hcl
  schema = jsonencode([
    { name = "article_id",     type = "STRING",    mode = "REQUIRED" },
    { name = "title",          type = "STRING",    mode = "REQUIRED" },
    { name = "url",            type = "STRING",    mode = "REQUIRED" },
    { name = "source",         type = "STRING",    mode = "REQUIRED" },
    { name = "published_at",   type = "TIMESTAMP", mode = "NULLABLE" },
    { name = "collected_at",   type = "TIMESTAMP", mode = "REQUIRED" },
    { name = "content",        type = "STRING",    mode = "NULLABLE" },
    { name = "content_status", type = "STRING",    mode = "NULLABLE" },
    { name = "retry_count",    type = "INT64",     mode = "NULLABLE" },
  ])
```

- [ ] **Step 2: terraform validate で構文確認**

Run: `cd news_pipeline/infra && terraform validate`
Expected: `Success! The configuration is valid.`
（`terraform init` 未実行で validate が失敗する場合は `terraform init -backend=false` を先に実行）

- [ ] **Step 3: Commit**

```bash
git add news_pipeline/infra/bigquery.tf
git commit -m "feat(infra): raw_articles に content_status / retry_count 列を追加

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

> 補足（実行者向け・適用は後続の運用ステップ）: NULLABLE 列追加は BigQuery の非破壊スキーマ更新。`terraform apply` 時にテーブル再作成は発生しない。既存行の2列は NULL のままで問題ない。

---

## Task 5: main.py を collect/notify に分割

**Files:**
- Modify: `news_pipeline/collector/main.py`（import・定数・`_run_pipeline` 分割・エンドポイント）

**重要:** `main.py` はモジュールレベルで環境変数を要求し import 不可のため単体テストは追加しない。検証は「構文チェック + ダミー環境変数での import + 全テスト緑」。リトライ状態遷移と分類は Task 1/前PRの categorizer で単体テスト済み。

着手前に `news_pipeline/collector/main.py` 全体を Read すること。以下は現状の主要位置（前PRで変動しうるため Read で確認）:
- import 群（`from article_parser import fetch_content` ほか）
- 定数（`IMPORTANCE_THRESHOLD`、`_DEFAULT_MAX_SUMMARIZE`）
- `_run_pipeline(triggered_by)`（収集〜通知の全処理）
- エンドポイント `@app.post("/")`（`run_pipeline`）、`@app.post("/slack")`（`slack_command`）

依存シグネチャ（本PRで実装済み）:
- `article_parser.fetch_content(url) -> tuple[str|None, bool]`
- `fetch_retry.next_fetch_state(ok, retry_count, max_retries) -> tuple[str, int]`
- `bq_client.get_pending_articles(max_retries) -> list[dict]`（article_id, url, title, source, retry_count）
- `bq_client.update_article_content(article_id, content, content_status, retry_count) -> None`
- `bq_client.insert_raw_articles(articles)`（各 dict に content_status / retry_count を含めてよい）
- categorizer の `group_by_category` / `order_categories` / `category_limit` / `category_label`（実装済み）

- [ ] **Step 1: import を追加**

`from article_parser import fetch_content` の近くに追加:

```python
from fetch_retry import next_fetch_state
```

- [ ] **Step 2: 定数を差し替え**

`IMPORTANCE_THRESHOLD = float(os.environ.get("IMPORTANCE_THRESHOLD", 0.5))`（コメント含む2行）を削除し、`_DEFAULT_MAX_SUMMARIZE = 10` の近くに以下を追加:

```python
# settings シートの general から取得するデフォルト値
_DEFAULT_IMPORTANCE_THRESHOLD = 0.65
_DEFAULT_MAX_CONTENT_RETRIES = 3
```

- [ ] **Step 3: `_run_pipeline` を `_run_collect` と `_run_notify` に置き換え**

現在の `def _run_pipeline(triggered_by: str = "scheduler") -> int:` 関数全体（`finally` の pipeline_logs 保存まで）を、以下の2関数で置き換える:

```python
def _run_collect(triggered_by: str = "scheduler") -> int:
    """収集パイプライン。RSS取得〜要約〜summaries保存。新着要約件数を返す。"""
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
    settings: dict = config.get("settings", {})
    general: dict = settings.get("general", {})
    max_summarize: int = int(general.get("max_summarize", _DEFAULT_MAX_SUMMARIZE))
    importance_threshold: float = float(
        general.get("importance_threshold", _DEFAULT_IMPORTANCE_THRESHOLD)
    )
    max_content_retries: int = int(
        general.get("max_content_retries", _DEFAULT_MAX_CONTENT_RETRIES)
    )
    log["keywords"] = keywords

    bq = BQClient(project=PROJECT_ID)

    try:
        # 1. RSS 取得
        articles = fetch_articles(feeds)
        log["articles_fetched"] = len(articles)
        logger.info("[collect] fetched %d articles from RSS", len(articles))

        # 2. dedup（raw_articles ベース）→ 要約上限で絞る
        existing_urls = bq.get_existing_urls()
        new_articles = [a for a in articles if a["url"] not in existing_urls]
        log["new_articles"] = len(new_articles)
        new_articles = new_articles[:max_summarize]
        logger.info(
            "[collect] %d new articles (limited to %d)", log["new_articles"], len(new_articles)
        )

        # to_summarize: この実行で本文取得に成功した記事（新着 + pending→ok）
        to_summarize: list[dict] = []

        # 3. 新着の本文取得（UA付き・1回）
        for article in new_articles:
            text, ok = fetch_content(article["url"])
            status, retry = next_fetch_state(ok, 0, max_content_retries)
            article["content"] = text
            article["content_status"] = status
            article["retry_count"] = retry
            if status == "ok" and text:
                to_summarize.append(article)

        # 4. raw_articles 保存（content_status / retry_count 込み）
        if new_articles:
            bq.insert_raw_articles(new_articles)
            logger.info("[collect] saved %d to raw_articles", len(new_articles))

        # 5. pending 記事の再取得（次回繰り越し分）
        pending = bq.get_pending_articles(max_content_retries)
        logger.info("[collect] %d pending articles to retry", len(pending))
        for p in pending:
            text, ok = fetch_content(p["url"])
            status, retry = next_fetch_state(ok, int(p.get("retry_count", 0)), max_content_retries)
            bq.update_article_content(p["article_id"], text, status, retry)
            if status == "ok" and text:
                to_summarize.append(
                    {
                        "article_id": p["article_id"],
                        "title": p["title"],
                        "url": p["url"],
                        "source": p["source"],
                        "content": text,
                    }
                )

        # 6. 要約生成（本文取得に成功した記事のみ）
        summaries = []
        for article in to_summarize:
            try:
                result = summarize_article(
                    title=article["title"],
                    content=article["content"] or "",
                    api_key=ANTHROPIC_API_KEY,
                    keywords=keywords,
                )
            except Exception as e:
                logger.warning("[collect] summarize failed for %s: %s", article["url"], e)
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

        # 7. importance_threshold フィルタ
        relevant_summaries = [
            s for s in summaries if s.get("importance_score", 0) >= importance_threshold
        ]
        log["summaries_generated"] = len(relevant_summaries)
        logger.info(
            "[collect] %d relevant summaries (importance_score >= %.2f)",
            len(relevant_summaries),
            importance_threshold,
        )

        # 8. summaries 保存（article_id 重複を排除）
        if relevant_summaries:
            existing_summary_ids = bq.get_existing_summary_ids()
            relevant_summaries = [
                s for s in relevant_summaries if s["article_id"] not in existing_summary_ids
            ]
        if relevant_summaries:
            bq.insert_summaries(relevant_summaries)
            logger.info("[collect] saved %d summaries", len(relevant_summaries))

        return log["summaries_generated"]

    except Exception as e:
        log["status"] = "error"
        log["error_message"] = str(e)
        logger.error("[collect] pipeline error: %s", e)
        raise

    finally:
        log["finished_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        try:
            bq.insert_pipeline_log(log)
            logger.info("[collect] saved pipeline log run_id=%s", run_id)
        except Exception as e:
            logger.error("[collect] failed to save pipeline log: %s", e)


def _run_notify(triggered_by: str = "scheduler") -> int:
    """通知パイプライン。未通知サマリーをカテゴリ別に Slack 通知。通知件数を返す。"""
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
    settings: dict = config.get("settings", {})
    feed_categories: dict[str, str] = config.get("feed_categories", {})

    bq = BQClient(project=PROJECT_ID)

    try:
        # 9. 未通知サマリーを取得
        unnotified = bq.get_unnotified_summaries()
        logger.info("[notify] %d unnotified summaries in BQ", len(unnotified))

        if not unnotified:
            send_no_news_notification(SLACK_WEBHOOK_URL, "新着記事はありませんでした。")
            return 0

        # 10. カテゴリ別にグルーピングし、カテゴリごとに通知
        groups = group_by_category(unnotified, feed_categories)
        notified_ids: list[str] = []
        for category in order_categories(list(groups.keys()), settings):
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
                "[notify] notified %d articles in category '%s'", len(top), category
            )

        if not notified_ids:
            send_no_news_notification(SLACK_WEBHOOK_URL, "新着記事はありませんでした。")
            return 0

        # 11. 通知済みマーク（全カテゴリの和集合）
        bq.mark_summaries_notified(notified_ids)
        logger.info("[notify] marked %d summaries as notified", len(notified_ids))

        log["notified_count"] = len(notified_ids)
        return len(notified_ids)

    except Exception as e:
        log["status"] = "error"
        log["error_message"] = str(e)
        logger.error("[notify] pipeline error: %s", e)
        raise

    finally:
        log["finished_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        try:
            bq.insert_pipeline_log(log)
            logger.info("[notify] saved pipeline log run_id=%s", run_id)
        except Exception as e:
            logger.error("[notify] failed to save pipeline log: %s", e)
```

- [ ] **Step 4: エンドポイントを再編**

現在の `@app.post("/", response_model=PipelineResponse)` の `run_pipeline` 関数を削除し、以下2エンドポイントに置き換える:

```python
@app.post("/collect", response_model=PipelineResponse)
async def collect():
    """Cloud Scheduler からの収集トリガー。収集〜要約を同期実行する。"""
    summarized = await asyncio.to_thread(_run_collect)
    return PipelineResponse(status="ok", notified=summarized)


@app.post("/notify", response_model=PipelineResponse)
async def notify():
    """Cloud Scheduler からの通知トリガー。未通知サマリーを通知する。"""
    notified = await asyncio.to_thread(_run_notify)
    return PipelineResponse(status="ok", notified=notified)
```

`@app.post("/slack", ...)` の `slack_command` 内のバックグラウンドタスクを通知のみに変更:

```python
    background_tasks.add_task(_run_notify, "slack_command")
```

（`slack_command` の即時応答テキストは「通知中」に合わせて変更してよい。例:
`text=":hourglass: 未通知ニュースを送信中です..."`）

- [ ] **Step 5: 構文・import・全テストで検証**

Run: `cd news_pipeline && uv run python -c "import ast; ast.parse(open('collector/main.py').read()); print('syntax ok')"`
Expected: `syntax ok`

Run: `cd news_pipeline/collector && GCP_PROJECT_ID=x ANTHROPIC_API_KEY=x SLACK_WEBHOOK_URL=x uv run python -c "import main; print('import ok')"`
Expected: `import ok`

Run: `cd news_pipeline && uv run pytest tests/ -q`
Expected: 全テスト PASS

Run: `cd news_pipeline && grep -n "IMPORTANCE_THRESHOLD\|_run_pipeline\|\"/\"" collector/main.py`
Expected: `IMPORTANCE_THRESHOLD` と `_run_pipeline` は0件（残存なし）

- [ ] **Step 6: Commit**

```bash
git add news_pipeline/collector/main.py
git commit -m "feat(main): 収集(/collect)と通知(/notify)を分割しリトライ・settings閾値を導入

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 6: Cloud Scheduler を collect/notify の2本に

**Files:**
- Modify: `news_pipeline/infra/main.tf:85-100`（既存 scheduler の張り替え + notify 追加）

単体テスト対象外。検証は `terraform validate`。

- [ ] **Step 1: 既存 collect スケジューラを毎日6:00 JST・/collect に変更**

`news_pipeline/infra/main.tf` の `resource "google_cloud_scheduler_job" "news_pipeline_trigger"` ブロックを以下に変更:

```hcl
# Cloud Scheduler（収集: 毎日 6:00 JST = 21:00 UTC 前日）
resource "google_cloud_scheduler_job" "news_pipeline_collect" {
  name      = "news-pipeline-collect"
  schedule  = "0 21 * * *"
  time_zone = "UTC"
  region    = var.region

  http_target {
    http_method = "POST"
    uri         = "${google_cloud_run_v2_service.news_collector.uri}/collect"

    oidc_token {
      service_account_email = google_service_account.scheduler.email
    }
  }
}

# Cloud Scheduler（通知: 毎日 6:30 JST = 21:30 UTC 前日）
resource "google_cloud_scheduler_job" "news_pipeline_notify" {
  name      = "news-pipeline-notify"
  schedule  = "30 21 * * *"
  time_zone = "UTC"
  region    = var.region

  http_target {
    http_method = "POST"
    uri         = "${google_cloud_run_v2_service.news_collector.uri}/notify"

    oidc_token {
      service_account_email = google_service_account.scheduler.email
    }
  }
}
```

> 注: リソース名を `news_pipeline_trigger` → `news_pipeline_collect` に変更している。`terraform apply` 時は旧ジョブ `news-pipeline-daily` が destroy され、`news-pipeline-collect` が create される（ジョブ名も変わる）。意図通り。

- [ ] **Step 2: terraform validate**

Run: `cd news_pipeline/infra && terraform validate`
Expected: `Success! The configuration is valid.`
（必要なら `terraform init -backend=false` を先に）

- [ ] **Step 3: Commit**

```bash
git add news_pipeline/infra/main.tf
git commit -m "feat(infra): Cloud Scheduler を collect(6:00)/notify(6:30) の2本に分割

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 7: ドキュメント更新（CLAUDE.md / README）

**Files:**
- Modify: `CLAUDE.md`
- Modify: `news_pipeline/README.md`

- [ ] **Step 1: CLAUDE.md のエンドポイント記述を更新**

`CLAUDE.md` の news_pipeline 構造説明にある `main.py` の行を確認し、エンドポイント記述を以下の趣旨に更新する。`collector/` の説明テーブル/箇条書きの該当行を:

```
│   ├── main.py         # /collect(収集) /notify(通知) と /slack(Slash command) エンドポイント
```

に変更。さらに「Google Sheets 設定」セクションの settings 説明に以下2行を追記:

```markdown
  - `general / importance_threshold`: summaries に残す importance_score の下限（未設定は 0.65）
  - `general / max_content_retries`: 本文取得の最大リトライ回数（未設定は 3）
```

- [ ] **Step 2: CLAUDE.md に収集/通知分割の Gotcha を追記**

`### Gotchas` の箇条書きに以下を追加:

```markdown
- **収集/通知の分離**: `/collect`（毎日6:00 JST・RSS取得〜要約）と `/notify`（毎日6:30 JST・Slack通知）は別エンドポイント・別 Cloud Scheduler。Slack の `/news-update` は `/notify` を呼ぶ（軽量・即応答）
- **本文取得リトライ**: 取得失敗は raw_articles に `content_status='pending'` + `retry_count` で保存し次回 `/collect` で再取得。`max_content_retries` 到達で `failed`（要約せずスキップ）
```

- [ ] **Step 3: README のフロー図・エンドポイント・設定表を更新**

`news_pipeline/README.md` を編集:

(a) アーキテクチャ/フロー図の Cloud Run エンドポイント記述（`POST /` 等）を以下に更新:

```
      │  POST /collect   ← スケジューラ（毎日6:00 JST）: RSS取得〜要約〜summaries保存
      │  POST /notify    ← スケジューラ（毎日6:30 JST）: 未通知サマリーをカテゴリ別に通知
      │  POST /slack     ← Slack スラッシュコマンド（/news-update）: 通知のみ
```

(b) 本文取得の行（フロー図中）に次回繰り越しリトライを反映:

```
RSS Fetch → dedup（raw_articles） → 本文取得（失敗は pending で次回再取得）→ raw_articles 保存
```

(c) 「Google Sheets で管理する設定」表の `settings` 行を以下に更新:

```
| `settings` | `general/max_summarize`（要約件数上限・既定10）、`general/importance_threshold`（残す下限・既定0.65）、`general/max_content_retries`（本文リトライ上限・既定3）、`<category>/max_notify`、`<category>/label` | 次回実行時（デプロイ不要） |
```

(d) 環境変数表に `IMPORTANCE_THRESHOLD` の行が残っていれば削除する。

Run（確認）: `grep -n "IMPORTANCE_THRESHOLD" news_pipeline/README.md CLAUDE.md`
Expected: 該当なし

- [ ] **Step 4: Commit**

```bash
git add CLAUDE.md news_pipeline/README.md
git commit -m "docs: 収集/通知分割・本文リトライ・settings閾値を CLAUDE.md/README に反映

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Self-Review メモ（実装者向け）

- **Spec coverage:**
  - 収集/通知分割（Task5 関数分割・エンドポイント、Task6 スケジューラ）✓
  - Slack /news-update = notify（Task5 Step4）✓
  - `/` 廃止（Task5 Step4・Step5 grep 確認）✓
  - 本文取得 UA + (text, ok)（Task2）✓
  - リトライ状態遷移・次回繰り越し（Task1 純粋関数 + Task5 collect 手順3/5）✓
  - 上限到達で failed・要約スキップ（Task1 + Task5 手順6 は ok のみ対象）✓
  - raw_articles 列追加（Task4）+ pending 取得/更新（Task3）✓
  - streaming buffer エラー握りつぶし（Task3 update_article_content + テスト）✓
  - importance_threshold=0.65 を settings へ（Task5 定数・読み出し）✓
  - max_content_retries=3 settings（Task5）✓
  - ドキュメント（Task7）✓
- **型整合:** `next_fetch_state(ok, retry_count, max_retries) -> (str, int)`（Task1 定義 = Task5 呼び出し）、`fetch_content(url) -> (str|None, bool)`（Task2 = Task5）、`get_pending_articles(max_retries)` / `update_article_content(article_id, content, content_status, retry_count)`（Task3 = Task5）一致。
- **注意:** settings 値は config_loader が int 変換可能なら int 化するため、`importance_threshold`（"0.65"）は文字列で来る → `float()` 必須（Task5 で対応済み）。`max_summarize`/`max_content_retries` は int で来るが `int()` で再ラップ。
