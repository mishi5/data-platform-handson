# Deep-dive & Q&A Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `/news-deepdive <article_id>` Slackコマンドで記事をClaude Sonnetで深堀り分析し、結果をキャッシュして返す。

**Architecture:** `deepdiver.py`（新規）がSonnet呼び出しを担当し、`deepdives` BigQueryテーブルをキャッシュとして使う。`main.py`に`/slack/deepdive`エンドポイントを追加し、3秒制限対策としてバックグラウンドスレッドで処理して`response_url`に遅延応答する。article_idは先頭8文字のプレフィックスで検索。

**Tech Stack:** Python, Flask, anthropic SDK (claude-sonnet-4-6), BigQuery, Terraform

---

## Chunk 1: Terraform + deepdiver.py + bq_client拡張

### Task 1: `deepdives` テーブルをTerraformに追加

**Files:**
- Modify: `news_pipeline/infra/bigquery.tf`

- [ ] **Step 1: `deepdives` リソースを追加**

`bigquery.tf` の末尾（`article_chunks` の後）に追加：

```hcl
resource "google_bigquery_table" "deepdives" {
  dataset_id          = google_bigquery_dataset.tech_news.dataset_id
  table_id            = "deepdives"
  deletion_protection = false

  schema = jsonencode([
    { name = "article_id",    type = "STRING",    mode = "REQUIRED" },
    { name = "deepdive_text", type = "STRING",    mode = "REQUIRED" },
    { name = "created_at",    type = "TIMESTAMP", mode = "REQUIRED" },
  ])
}
```

- [ ] **Step 2: Terraform構文チェック**

```bash
cd news_pipeline/infra && terraform validate
```
Expected: `Success! The configuration is valid.`

- [ ] **Step 3: Terraform apply**

```bash
cd news_pipeline/infra && terraform apply -var="project_id=data-platform-handson-1223" -auto-approve
```
Expected: `1 added, 0 changed, 0 destroyed.`

- [ ] **Step 4: Commit**

```bash
git add news_pipeline/infra/bigquery.tf
git commit -m "feat: add deepdives table to BigQuery (Terraform)"
```

---

### Task 2: `deepdiver.py` を新規作成（TDD）

**Files:**
- Create: `news_pipeline/collector/deepdiver.py`
- Create: `news_pipeline/tests/test_deepdiver.py`

- [ ] **Step 1: テストを書く**

`news_pipeline/tests/test_deepdiver.py` を新規作成：

```python
from unittest.mock import MagicMock, patch

from collector.deepdiver import deepdive_article


@patch("collector.deepdiver.anthropic.Anthropic")
def test_deepdive_article_returns_markdown(mock_anthropic_class):
    mock_client = MagicMock()
    mock_anthropic_class.return_value = mock_client

    mock_block = MagicMock()
    mock_block.text = "📌 背景・概要\nBigQueryの新機能が発表された。\n\n🔍 技術的なポイント\n• 高速化"
    mock_client.messages.create.return_value.content = [mock_block]

    result = deepdive_article(
        title="BigQuery update",
        content="BigQuery announced new features...",
        api_key="test-key",
    )

    assert result is not None
    assert isinstance(result, str)
    assert len(result) > 0
    call_kwargs = mock_client.messages.create.call_args.kwargs
    assert call_kwargs["model"] == "claude-sonnet-4-6"
    assert call_kwargs["max_tokens"] == 1024


@patch("collector.deepdiver.anthropic.Anthropic")
def test_deepdive_article_returns_none_on_error(mock_anthropic_class):
    mock_client = MagicMock()
    mock_anthropic_class.return_value = mock_client
    mock_client.messages.create.side_effect = Exception("API error")

    result = deepdive_article(title="title", content="body", api_key="test-key")

    assert result is None


@patch("collector.deepdiver.anthropic.Anthropic")
def test_deepdive_article_truncates_long_content(mock_anthropic_class):
    mock_client = MagicMock()
    mock_anthropic_class.return_value = mock_client

    mock_block = MagicMock()
    mock_block.text = "深堀り結果"
    mock_client.messages.create.return_value.content = [mock_block]

    long_content = "x" * 10000
    deepdive_article(title="title", content=long_content, api_key="test-key")

    call_kwargs = mock_client.messages.create.call_args.kwargs
    user_msg = call_kwargs["messages"][0]["content"]
    assert len(user_msg) < 10000 + 200  # 本文が切り詰められていること
```

- [ ] **Step 2: テストが失敗することを確認**

```bash
cd news_pipeline && python -m pytest tests/test_deepdiver.py -v
```
Expected: FAIL (ModuleNotFoundError: No module named 'collector.deepdiver')

- [ ] **Step 3: `deepdiver.py` を実装**

`news_pipeline/collector/deepdiver.py` を新規作成：

```python
"""Claude Sonnet を使って記事を深堀り分析するモジュール。"""
import logging

import anthropic
from anthropic.types import TextBlock

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """あなたはデータエンジニアリングの技術記事を深く分析するエキスパートです。
記事を読んで、以下の構成でMarkdown形式の詳細分析を日本語で行ってください。

📌 背景・概要
（この技術/発表の背景と概要を2〜3文で）

🔍 技術的なポイント（詳細）
（重要な技術的詳細を箇条書きで4〜6項目）

💡 実践への示唆
（実際の現場でどう活かせるか、注意点など2〜3文で）

Markdownのみを返してください。説明文や前置きは不要です。"""


def deepdive_article(title: str, content: str, api_key: str) -> str | None:
    """Claude Sonnet を使って記事を深堀り分析する。Markdown文字列を返す。失敗時は None。"""
    try:
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=_SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": f"タイトル: {title}\n\n本文:\n{content[:5000]}",
                }
            ],
        )
        block = message.content[0]
        if not isinstance(block, TextBlock):
            return None
        return block.text.strip()
    except Exception as e:
        logger.error("[deepdiver] failed: %s", e)
        return None
```

- [ ] **Step 4: テストが通ることを確認**

```bash
cd news_pipeline && python -m pytest tests/test_deepdiver.py -v
```
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add news_pipeline/collector/deepdiver.py news_pipeline/tests/test_deepdiver.py
git commit -m "feat: add deepdiver.py with Claude Sonnet deep-dive analysis"
```

---

### Task 3: `bq_client.py` に深堀り用メソッドを追加（TDD）

**Files:**
- Modify: `news_pipeline/collector/bq_client.py`
- Modify: `news_pipeline/tests/test_bq_client.py`

- [ ] **Step 1: テストを追加**

`test_bq_client.py` の末尾に追加：

```python
@patch("collector.bq_client.bigquery.Client")
def test_get_deepdive_returns_text_when_found(mock_bq_class):
    mock_client = MagicMock()
    mock_bq_class.return_value = mock_client

    mock_row = MagicMock()
    mock_row.deepdive_text = "📌 背景...\n🔍 技術的なポイント..."
    mock_client.query.return_value.result.return_value = [mock_row]

    bq = BQClient(project="test-project")
    result = bq.get_deepdive("abc12345")

    assert result == "📌 背景...\n🔍 技術的なポイント..."
    query_arg = mock_client.query.call_args[0][0]
    assert "deepdives" in query_arg
    assert "abc12345" in query_arg


@patch("collector.bq_client.bigquery.Client")
def test_get_deepdive_returns_none_when_not_found(mock_bq_class):
    mock_client = MagicMock()
    mock_bq_class.return_value = mock_client
    mock_client.query.return_value.result.return_value = []

    bq = BQClient(project="test-project")
    result = bq.get_deepdive("notfound")

    assert result is None


@patch("collector.bq_client.bigquery.Client")
def test_insert_deepdive_calls_insert_rows(mock_bq_class):
    mock_client = MagicMock()
    mock_bq_class.return_value = mock_client
    mock_client.insert_rows_json.return_value = []

    bq = BQClient(project="test-project")
    bq.insert_deepdive("abc123full", "深堀りテキスト")

    mock_client.insert_rows_json.assert_called_once()
    call_args = mock_client.insert_rows_json.call_args
    assert "deepdives" in call_args[0][0]
    row = call_args[0][1][0]
    assert row["article_id"] == "abc123full"
    assert row["deepdive_text"] == "深堀りテキスト"
    assert "created_at" in row


@patch("collector.bq_client.bigquery.Client")
def test_get_article_by_id_returns_dict_when_found(mock_bq_class):
    mock_client = MagicMock()
    mock_bq_class.return_value = mock_client

    mock_row = MagicMock()
    _data = {
        "article_id": "abc12345xyz",
        "title": "BigQuery update",
        "url": "https://example.com",
        "content": "article body",
    }
    mock_row.keys.return_value = list(_data.keys())
    mock_row.__getitem__ = lambda self, key: _data[key]
    mock_client.query.return_value.result.return_value = [mock_row]

    bq = BQClient(project="test-project")
    result = bq.get_article_by_id("abc12345")

    assert result is not None
    assert result["article_id"] == "abc12345xyz"
    query_arg = mock_client.query.call_args[0][0]
    assert "abc12345" in query_arg
    assert "raw_articles" in query_arg
    assert "summaries" in query_arg


@patch("collector.bq_client.bigquery.Client")
def test_get_article_by_id_returns_none_when_not_found(mock_bq_class):
    mock_client = MagicMock()
    mock_bq_class.return_value = mock_client
    mock_client.query.return_value.result.return_value = []

    bq = BQClient(project="test-project")
    result = bq.get_article_by_id("notfound")

    assert result is None


@patch("collector.bq_client.bigquery.Client")
def test_get_top_undived_article_returns_dict(mock_bq_class):
    mock_client = MagicMock()
    mock_bq_class.return_value = mock_client

    mock_row = MagicMock()
    _data = {
        "article_id": "top123",
        "title": "Top article",
        "url": "https://example.com/top",
        "content": "top content",
    }
    mock_row.keys.return_value = list(_data.keys())
    mock_row.__getitem__ = lambda self, key: _data[key]
    mock_client.query.return_value.result.return_value = [mock_row]

    bq = BQClient(project="test-project")
    result = bq.get_top_undived_article()

    assert result is not None
    assert result["article_id"] == "top123"
    query_arg = mock_client.query.call_args[0][0]
    assert "deepdives" in query_arg
    assert "importance_score" in query_arg


@patch("collector.bq_client.bigquery.Client")
def test_get_top_undived_article_returns_none_when_all_dived(mock_bq_class):
    mock_client = MagicMock()
    mock_bq_class.return_value = mock_client
    mock_client.query.return_value.result.return_value = []

    bq = BQClient(project="test-project")
    result = bq.get_top_undived_article()

    assert result is None
```

- [ ] **Step 2: テストが失敗することを確認**

```bash
cd news_pipeline && python -m pytest tests/test_bq_client.py -k "deepdive or undived or article_by_id" -v
```
Expected: 全て FAIL

- [ ] **Step 3: `bq_client.py` にメソッドを追加**

`bq_client.py` の `insert_pipeline_log` の後に追加：

```python
    def get_deepdive(self, article_id: str) -> str | None:
        """既存の深堀り結果を取得。なければ None。"""
        query = (
            f"SELECT deepdive_text FROM `{self.project}.{DATASET}.deepdives`"
            f" WHERE article_id = '{article_id}'"
            f" LIMIT 1"
        )
        rows = list(self.client.query(query).result())
        if not rows:
            return None
        return rows[0].deepdive_text

    def insert_deepdive(self, article_id: str, text: str) -> None:
        """深堀り結果を deepdives テーブルに保存する。"""
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        table_id = f"{self.project}.{DATASET}.deepdives"
        errors = self.client.insert_rows_json(
            table_id, [{"article_id": article_id, "deepdive_text": text, "created_at": now}]
        )
        if errors:
            logger.error("[bq_client] insert_deepdive errors: %s", errors)
            raise RuntimeError(f"BigQuery deepdives insert failed: {errors}")

    def get_article_by_id(self, article_id_prefix: str) -> dict | None:
        """先頭8文字のIDプレフィックスで記事を取得。summaries + raw_articles を JOIN。"""
        query = (
            f"SELECT s.article_id, s.title, s.url, r.content"
            f" FROM `{self.project}.{DATASET}.summaries` s"
            f" JOIN `{self.project}.{DATASET}.raw_articles` r ON s.article_id = r.article_id"
            f" WHERE s.article_id LIKE '{article_id_prefix}%'"
            f" LIMIT 1"
        )
        rows = list(self.client.query(query).result())
        if not rows:
            return None
        return dict(rows[0])

    def get_top_undived_article(self) -> dict | None:
        """深堀り未実施の記事の中でimportance_score最上位のものを返す。"""
        query = (
            f"SELECT s.article_id, s.title, s.url, r.content"
            f" FROM `{self.project}.{DATASET}.summaries` s"
            f" JOIN `{self.project}.{DATASET}.raw_articles` r ON s.article_id = r.article_id"
            f" LEFT JOIN `{self.project}.{DATASET}.deepdives` d ON s.article_id = d.article_id"
            f" WHERE d.article_id IS NULL"
            f" ORDER BY s.importance_score DESC"
            f" LIMIT 1"
        )
        rows = list(self.client.query(query).result())
        if not rows:
            return None
        return dict(rows[0])
```

- [ ] **Step 4: テストが通ることを確認**

```bash
cd news_pipeline && python -m pytest tests/test_bq_client.py -v
```
Expected: 全テスト PASS

- [ ] **Step 5: Commit**

```bash
git add news_pipeline/collector/bq_client.py news_pipeline/tests/test_bq_client.py
git commit -m "feat: add deepdive methods to BQClient"
```

---

## Chunk 2: main.py エンドポイント追加

### Task 4: `/slack/deepdive` エンドポイントを `main.py` に追加

**Files:**
- Modify: `news_pipeline/collector/main.py`

- [ ] **Step 1: import に `deepdiver` を追加**

`main.py` の既存 import 群に追加：

```python
from deepdiver import deepdive_article
```

- [ ] **Step 2: `_post_to_response_url` ヘルパーを追加**

`_verify_slack_signature` の直後に追加：

```python
def _post_to_response_url(response_url: str, text: str) -> None:
    """Slack の response_url に遅延応答を POST する。"""
    import requests as _requests
    try:
        _requests.post(
            response_url,
            json={"response_type": "in_channel", "text": text},
            timeout=10,
        )
    except Exception as e:
        logger.error("[deepdive] failed to post to response_url: %s", e)
```

- [ ] **Step 3: `_run_deepdive` 処理関数を追加**

`_run_pipeline` の直後に追加：

```python
def _run_deepdive(article_id_prefix: str, response_url: str) -> None:
    """深堀り処理。完了後に response_url へ結果を POST する。"""
    bq = BQClient(project=PROJECT_ID)

    # 1. 対象記事を取得
    if article_id_prefix:
        article = bq.get_article_by_id(article_id_prefix)
        if not article:
            _post_to_response_url(response_url, f"ID `{article_id_prefix}` の記事が見つかりませんでした。")
            return
    else:
        article = bq.get_top_undived_article()
        if not article:
            _post_to_response_url(response_url, "深堀り対象の記事がありません。")
            return

    title = article["title"]
    url = article["url"]
    article_id = article["article_id"]

    # 2. キャッシュ確認
    cached = bq.get_deepdive(article_id)
    if cached:
        logger.info("[deepdive] cache hit for %s", article_id)
        _post_to_response_url(response_url, f"*[深堀り] {title}*\n\n{cached}\n\n🔗 <{url}|元記事を読む>")
        return

    # 3. 深堀り生成
    logger.info("[deepdive] generating for %s", article_id)
    text = deepdive_article(
        title=title,
        content=article.get("content") or "",
        api_key=ANTHROPIC_API_KEY,
    )
    if not text:
        _post_to_response_url(response_url, "深堀り生成に失敗しました。しばらく経ってから再試行してください。")
        return

    # 4. キャッシュ保存
    try:
        bq.insert_deepdive(article_id, text)
    except Exception as e:
        logger.error("[deepdive] failed to cache deepdive: %s", e)

    # 5. 結果を送信
    _post_to_response_url(response_url, f"*[深堀り] {title}*\n\n{text}\n\n🔗 <{url}|元記事を読む>")
    logger.info("[deepdive] completed for %s", article_id)
```

- [ ] **Step 4: `/slack/deepdive` エンドポイントを追加**

`slack_command` の直後（`if __name__ == "__main__":` の前）に追加：

```python
@app.route("/slack/deepdive", methods=["POST"])
def slack_deepdive():
    """Slack スラッシュコマンド（/news-deepdive）のエンドポイント。"""
    if SLACK_SIGNING_SECRET and not _verify_slack_signature(request):
        logger.warning("[slack] invalid signature")
        return jsonify({"error": "invalid signature"}), 403

    article_id_prefix = request.form.get("text", "").strip()
    response_url = request.form.get("response_url", "")

    # Slack は 3 秒以内のレスポンスを要求するため、バックグラウンドで実行
    threading.Thread(
        target=_run_deepdive,
        args=(article_id_prefix, response_url),
        daemon=True,
    ).start()

    msg = f"ID `{article_id_prefix}` の記事を深堀り中です..." if article_id_prefix else "最新記事を深堀り中です..."
    return jsonify({"response_type": "in_channel", "text": f":mag: {msg}"})
```

- [ ] **Step 5: docstring を更新**

`main.py` 冒頭の docstring を更新：

```python
"""
news_pipeline メインモジュール。

Flask サーバーとして起動し、以下の3エンドポイントを提供する:
  POST /              - Cloud Scheduler からの定期実行トリガー
  POST /slack         - Slack スラッシュコマンド（/news-update）からの手動実行トリガー
  POST /slack/deepdive - Slack スラッシュコマンド（/news-deepdive）からの深堀りトリガー

パイプライン処理は _run_pipeline() に集約されており、
Slack エンドポイントではタイムアウト対策としてバックグラウンドスレッドで実行する。
"""
```

- [ ] **Step 6: 全テストが通ることを確認**

```bash
cd news_pipeline && python -m pytest tests/ -v
```
Expected: 全テスト PASS

- [ ] **Step 7: Commit**

```bash
git add news_pipeline/collector/main.py
git commit -m "feat: add /slack/deepdive endpoint for article deep-dive"
```

---

### Task 5: Dockerビルド & デプロイ

**Files:** なし（デプロイ作業）

- [ ] **Step 1: Dockerイメージをビルド**

```bash
cd /path/to/repo && docker build --platform linux/amd64 \
  -t asia-northeast1-docker.pkg.dev/data-platform-handson-1223/news-collector/news-collector:latest \
  news_pipeline/collector/
```
Expected: Successfully built

- [ ] **Step 2: イメージをプッシュ**

```bash
docker push asia-northeast1-docker.pkg.dev/data-platform-handson-1223/news-collector/news-collector:latest
```

- [ ] **Step 3: Cloud Run を更新**

```bash
gcloud run services update news-collector \
  --image=asia-northeast1-docker.pkg.dev/data-platform-handson-1223/news-collector/news-collector:latest \
  --region=asia-northeast1 --project=data-platform-handson-1223
```
Expected: `Service [news-collector] revision [...] has been deployed and is serving 100 percent of traffic.`

- [ ] **Step 4: Slack App に `/news-deepdive` コマンドを追加（手動）**

Slack App管理画面 → Slash Commands → Create New Command:
- Command: `/news-deepdive`
- Request URL: `https://news-collector-416464944882.asia-northeast1.run.app/slack/deepdive`
- Short Description: `記事を深堀り分析する`
- Usage Hint: `[article_id]`
