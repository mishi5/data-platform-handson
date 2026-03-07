# News Pipeline Phase 1 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** RSS フィードから技術記事を収集し、Claude で要約して Slack に通知する Cloud Run ジョブを構築する。

**Architecture:** Cloud Scheduler が平日1回 Cloud Run を起動 → RSS 取得・本文抽出・BigQuery 保存（`raw_articles`）→ Claude で要約 → `summaries` 保存 → Slack 通知（最大5件）。BigQuery テーブルは Terraform で管理する。

**Tech Stack:** Python 3.11, feedparser, trafilatura, google-cloud-bigquery, anthropic SDK, pytest, Docker, Terraform, Cloud Run, Cloud Scheduler

---

## ディレクトリ構成（完成形）

```
news_pipeline/
├── collector/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py              # HTTP エントリポイント（Cloud Run）
│   ├── rss_fetcher.py       # RSS フィード取得・URL 抽出
│   ├── article_parser.py    # 記事本文取得（trafilatura）
│   ├── bq_client.py         # BigQuery 操作（dedup・insert）
│   ├── summarizer.py        # Claude API 要約生成
│   └── notifier.py          # Slack Webhook 通知
├── infra/
│   ├── main.tf
│   ├── variables.tf
│   └── bigquery.tf          # raw_articles / summaries / article_chunks
└── tests/
    ├── conftest.py
    ├── test_rss_fetcher.py
    ├── test_article_parser.py
    ├── test_bq_client.py
    ├── test_summarizer.py
    └── test_notifier.py
```

---

## Task 1: プロジェクト骨格の作成

**Files:**
- Create: `news_pipeline/collector/requirements.txt`
- Create: `news_pipeline/collector/Dockerfile`
- Create: `news_pipeline/tests/conftest.py`

**Step 1: ディレクトリ作成**

```bash
mkdir -p news_pipeline/collector news_pipeline/infra news_pipeline/tests
touch news_pipeline/tests/__init__.py news_pipeline/collector/__init__.py
```

**Step 2: `requirements.txt` 作成**

```
feedparser==6.0.11
trafilatura==1.12.2
google-cloud-bigquery==3.27.0
anthropic==0.43.0
requests==2.32.3
Flask==3.1.0
pytest==8.3.4
pytest-mock==3.14.0
```

**Step 3: `Dockerfile` 作成**

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "main.py"]
```

**Step 4: `tests/conftest.py` 作成**

```python
import pytest

@pytest.fixture
def sample_article():
    return {
        "article_id": "abc123",
        "title": "BigQuery new features 2026",
        "url": "https://cloud.google.com/blog/bigquery-2026",
        "source": "Google Cloud Blog",
        "published_at": "2026-03-08T09:00:00Z",
        "collected_at": "2026-03-08T10:00:00Z",
        "content": "BigQuery announced new features including...",
    }
```

**Step 5: Commit**

```bash
git add news_pipeline/
git commit -m "feat: add news_pipeline project skeleton"
```

---

## Task 2: BigQuery テーブル定義（Terraform）

**Files:**
- Create: `news_pipeline/infra/main.tf`
- Create: `news_pipeline/infra/variables.tf`
- Create: `news_pipeline/infra/bigquery.tf`

**Step 1: `variables.tf` 作成**

```hcl
variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP Region"
  type        = string
  default     = "asia-northeast1"
}
```

**Step 2: `main.tf` 作成**

```hcl
terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}
```

**Step 3: `bigquery.tf` 作成（3テーブル）**

```hcl
resource "google_bigquery_dataset" "tech_news" {
  dataset_id = "tech_news"
  location   = var.region
}

resource "google_bigquery_table" "raw_articles" {
  dataset_id          = google_bigquery_dataset.tech_news.dataset_id
  table_id            = "raw_articles"
  deletion_protection = false

  schema = jsonencode([
    { name = "article_id",   type = "STRING",    mode = "REQUIRED" },
    { name = "title",        type = "STRING",    mode = "REQUIRED" },
    { name = "url",          type = "STRING",    mode = "REQUIRED" },
    { name = "source",       type = "STRING",    mode = "REQUIRED" },
    { name = "published_at", type = "TIMESTAMP", mode = "NULLABLE" },
    { name = "collected_at", type = "TIMESTAMP", mode = "REQUIRED" },
    { name = "content",      type = "STRING",    mode = "NULLABLE" },
  ])
}

resource "google_bigquery_table" "summaries" {
  dataset_id          = google_bigquery_dataset.tech_news.dataset_id
  table_id            = "summaries"
  deletion_protection = false

  schema = jsonencode([
    { name = "article_id",       type = "STRING",  mode = "REQUIRED" },
    { name = "title",            type = "STRING",  mode = "REQUIRED" },
    { name = "url",              type = "STRING",  mode = "REQUIRED" },
    { name = "source",           type = "STRING",  mode = "REQUIRED" },
    { name = "summary",          type = "STRING",  mode = "NULLABLE" },
    { name = "tags",             type = "STRING",  mode = "REPEATED" },
    { name = "importance_score", type = "FLOAT64", mode = "NULLABLE" },
  ])
}

resource "google_bigquery_table" "article_chunks" {
  dataset_id          = google_bigquery_dataset.tech_news.dataset_id
  table_id            = "article_chunks"
  deletion_protection = false

  schema = jsonencode([
    { name = "chunk_id",   type = "STRING", mode = "REQUIRED" },
    { name = "article_id", type = "STRING", mode = "REQUIRED" },
    { name = "chunk_text", type = "STRING", mode = "NULLABLE" },
    {
      name   = "embedding"
      type   = "FLOAT64"
      mode   = "REPEATED"
    },
  ])
}
```

**Step 4: Terraform の動作確認**

```bash
cd news_pipeline/infra
terraform init
terraform validate
```

Expected: `Success! The configuration is valid.`

**Step 5: Commit**

```bash
cd ../..
git add news_pipeline/infra/
git commit -m "feat: add BigQuery table definitions for news pipeline"
```

---

## Task 3: RSS Fetcher

**Files:**
- Create: `news_pipeline/collector/rss_fetcher.py`
- Create: `news_pipeline/tests/test_rss_fetcher.py`

**Step 1: テスト作成**

`news_pipeline/tests/test_rss_fetcher.py`:

```python
from unittest.mock import patch, MagicMock
from collector.rss_fetcher import fetch_articles, FEEDS


def test_feeds_list_not_empty():
    assert len(FEEDS) > 0


def test_fetch_articles_returns_list(mocker):
    mock_feed = MagicMock()
    mock_feed.entries = [
        MagicMock(
            title="BigQuery update",
            link="https://cloud.google.com/blog/1",
            published="Sat, 08 Mar 2026 09:00:00 GMT",
        )
    ]
    mocker.patch("collector.rss_fetcher.feedparser.parse", return_value=mock_feed)

    articles = fetch_articles(["https://example.com/rss"])

    assert len(articles) == 1
    assert articles[0]["title"] == "BigQuery update"
    assert articles[0]["url"] == "https://cloud.google.com/blog/1"
    assert articles[0]["source"] == "https://example.com/rss"


def test_fetch_articles_skips_entries_without_link(mocker):
    mock_feed = MagicMock()
    mock_feed.entries = [MagicMock(spec=[])]  # link 属性なし
    mocker.patch("collector.rss_fetcher.feedparser.parse", return_value=mock_feed)

    articles = fetch_articles(["https://example.com/rss"])
    assert articles == []


def test_fetch_articles_handles_feed_error(mocker):
    mocker.patch("collector.rss_fetcher.feedparser.parse", side_effect=Exception("network error"))

    articles = fetch_articles(["https://example.com/rss"])
    assert articles == []
```

**Step 2: テスト実行（失敗確認）**

```bash
cd news_pipeline
python -m pytest tests/test_rss_fetcher.py -v
```

Expected: `ImportError` または `ModuleNotFoundError`

**Step 3: `rss_fetcher.py` 実装**

```python
import hashlib
import feedparser
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

FEEDS = [
    "https://cloudblog.withgoogle.com/rss/",
    "https://cloud.google.com/feeds/bigquery-release-notes.xml",
    "https://www.getdbt.com/blog/rss.xml",
    "https://www.databricks.com/feed",
    "https://www.snowflake.com/blog/feed/",
    "https://www.infoq.com/data-engineering/rss/",
    "https://zenn.dev/topics/bigquery/feed",
]


def _parse_published(entry) -> str | None:
    if hasattr(entry, "published"):
        try:
            dt = parsedate_to_datetime(entry.published)
            return dt.isoformat()
        except Exception:
            pass
    return None


def _make_article_id(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()[:16]


def fetch_articles(feeds: list[str] = None) -> list[dict]:
    """RSSフィードから記事リストを返す。"""
    if feeds is None:
        feeds = FEEDS

    results = []
    for feed_url in feeds:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries:
                if not hasattr(entry, "link"):
                    continue
                results.append({
                    "article_id": _make_article_id(entry.link),
                    "title": getattr(entry, "title", ""),
                    "url": entry.link,
                    "source": feed_url,
                    "published_at": _parse_published(entry),
                    "collected_at": datetime.now(timezone.utc).isoformat(),
                })
        except Exception as e:
            print(f"[rss_fetcher] feed error {feed_url}: {e}")

    return results
```

**Step 4: テスト実行（成功確認）**

```bash
python -m pytest tests/test_rss_fetcher.py -v
```

Expected: `4 passed`

**Step 5: Commit**

```bash
cd ..
git add news_pipeline/collector/rss_fetcher.py news_pipeline/tests/test_rss_fetcher.py
git commit -m "feat: add RSS fetcher with feed list and article ID generation"
```

---

## Task 4: Article Parser（本文抽出）

**Files:**
- Create: `news_pipeline/collector/article_parser.py`
- Create: `news_pipeline/tests/test_article_parser.py`

**Step 1: テスト作成**

`news_pipeline/tests/test_article_parser.py`:

```python
from unittest.mock import patch
from collector.article_parser import fetch_content


def test_fetch_content_returns_text(mocker):
    mocker.patch(
        "collector.article_parser.trafilatura.fetch_url",
        return_value="<html><body><p>BigQuery is great.</p></body></html>",
    )
    mocker.patch(
        "collector.article_parser.trafilatura.extract",
        return_value="BigQuery is great.",
    )

    result = fetch_content("https://example.com/article")
    assert result == "BigQuery is great."


def test_fetch_content_returns_none_on_failure(mocker):
    mocker.patch(
        "collector.article_parser.trafilatura.fetch_url",
        return_value=None,
    )

    result = fetch_content("https://example.com/article")
    assert result is None


def test_fetch_content_handles_exception(mocker):
    mocker.patch(
        "collector.article_parser.trafilatura.fetch_url",
        side_effect=Exception("timeout"),
    )

    result = fetch_content("https://example.com/article")
    assert result is None
```

**Step 2: テスト実行（失敗確認）**

```bash
cd news_pipeline
python -m pytest tests/test_article_parser.py -v
```

Expected: `ImportError`

**Step 3: `article_parser.py` 実装**

```python
import trafilatura


def fetch_content(url: str) -> str | None:
    """URL から記事本文を抽出して返す。失敗時は None。"""
    try:
        downloaded = trafilatura.fetch_url(url)
        if downloaded is None:
            return None
        text = trafilatura.extract(downloaded)
        return text
    except Exception as e:
        print(f"[article_parser] failed to fetch {url}: {e}")
        return None
```

**Step 4: テスト実行（成功確認）**

```bash
python -m pytest tests/test_article_parser.py -v
```

Expected: `3 passed`

**Step 5: Commit**

```bash
cd ..
git add news_pipeline/collector/article_parser.py news_pipeline/tests/test_article_parser.py
git commit -m "feat: add article content extractor using trafilatura"
```

---

## Task 5: BigQuery クライアント（dedup + insert）

**Files:**
- Create: `news_pipeline/collector/bq_client.py`
- Create: `news_pipeline/tests/test_bq_client.py`

**Step 1: テスト作成**

`news_pipeline/tests/test_bq_client.py`:

```python
from unittest.mock import MagicMock, patch
from collector.bq_client import BQClient


@patch("collector.bq_client.bigquery.Client")
def test_get_existing_urls_returns_set(mock_bq_class):
    mock_client = MagicMock()
    mock_bq_class.return_value = mock_client

    mock_row1 = MagicMock()
    mock_row1.url = "https://example.com/1"
    mock_row2 = MagicMock()
    mock_row2.url = "https://example.com/2"
    mock_client.query.return_value.result.return_value = [mock_row1, mock_row2]

    bq = BQClient(project="test-project")
    urls = bq.get_existing_urls()

    assert urls == {"https://example.com/1", "https://example.com/2"}


@patch("collector.bq_client.bigquery.Client")
def test_insert_raw_articles_calls_insert_rows(mock_bq_class):
    mock_client = MagicMock()
    mock_bq_class.return_value = mock_client
    mock_client.insert_rows_json.return_value = []  # エラーなし

    bq = BQClient(project="test-project")
    articles = [{"article_id": "abc", "title": "T", "url": "https://x.com", "source": "s",
                 "published_at": None, "collected_at": "2026-03-08T10:00:00Z", "content": "body"}]
    bq.insert_raw_articles(articles)

    mock_client.insert_rows_json.assert_called_once()


@patch("collector.bq_client.bigquery.Client")
def test_insert_summaries_calls_insert_rows(mock_bq_class):
    mock_client = MagicMock()
    mock_bq_class.return_value = mock_client
    mock_client.insert_rows_json.return_value = []

    bq = BQClient(project="test-project")
    summaries = [{"article_id": "abc", "title": "T", "url": "u", "source": "s",
                  "summary": "sum", "tags": ["bigquery"], "importance_score": 0.9}]
    bq.insert_summaries(summaries)

    mock_client.insert_rows_json.assert_called_once()
```

**Step 2: テスト実行（失敗確認）**

```bash
cd news_pipeline
python -m pytest tests/test_bq_client.py -v
```

Expected: `ImportError`

**Step 3: `bq_client.py` 実装**

```python
from google.cloud import bigquery

DATASET = "tech_news"


class BQClient:
    def __init__(self, project: str):
        self.client = bigquery.Client(project=project)
        self.project = project

    def get_existing_urls(self) -> set[str]:
        """raw_articles に保存済みの URL セットを返す（dedup 用）。"""
        query = f"SELECT url FROM `{self.project}.{DATASET}.raw_articles`"
        rows = self.client.query(query).result()
        return {row.url for row in rows}

    def insert_raw_articles(self, articles: list[dict]) -> None:
        table_id = f"{self.project}.{DATASET}.raw_articles"
        errors = self.client.insert_rows_json(table_id, articles)
        if errors:
            print(f"[bq_client] insert_raw_articles errors: {errors}")

    def insert_summaries(self, summaries: list[dict]) -> None:
        table_id = f"{self.project}.{DATASET}.summaries"
        errors = self.client.insert_rows_json(table_id, summaries)
        if errors:
            print(f"[bq_client] insert_summaries errors: {errors}")
```

**Step 4: テスト実行（成功確認）**

```bash
python -m pytest tests/test_bq_client.py -v
```

Expected: `3 passed`

**Step 5: Commit**

```bash
cd ..
git add news_pipeline/collector/bq_client.py news_pipeline/tests/test_bq_client.py
git commit -m "feat: add BigQuery client with dedup check and insert operations"
```

---

## Task 6: LLM Summarizer（Claude API）

**Files:**
- Create: `news_pipeline/collector/summarizer.py`
- Create: `news_pipeline/tests/test_summarizer.py`

**Step 1: テスト作成**

`news_pipeline/tests/test_summarizer.py`:

```python
import json
from unittest.mock import MagicMock, patch
from collector.summarizer import summarize_article


@patch("collector.summarizer.anthropic.Anthropic")
def test_summarize_article_returns_dict(mock_anthropic_class):
    mock_client = MagicMock()
    mock_anthropic_class.return_value = mock_client

    response_text = json.dumps({
        "summary": "- BigQuery added new feature\n- Improves performance",
        "tags": ["bigquery", "performance"],
        "importance_score": 0.85,
    })
    mock_client.messages.create.return_value.content = [MagicMock(text=response_text)]

    result = summarize_article(
        title="BigQuery update",
        content="BigQuery announced...",
        api_key="test-key",
    )

    assert result["summary"] == "- BigQuery added new feature\n- Improves performance"
    assert "bigquery" in result["tags"]
    assert result["importance_score"] == 0.85


@patch("collector.summarizer.anthropic.Anthropic")
def test_summarize_article_returns_none_on_api_error(mock_anthropic_class):
    mock_client = MagicMock()
    mock_anthropic_class.return_value = mock_client
    mock_client.messages.create.side_effect = Exception("API error")

    result = summarize_article(title="T", content="C", api_key="key")
    assert result is None
```

**Step 2: テスト実行（失敗確認）**

```bash
cd news_pipeline
python -m pytest tests/test_summarizer.py -v
```

Expected: `ImportError`

**Step 3: `summarizer.py` 実装**

```python
import json
import anthropic

SYSTEM_PROMPT = """あなたはデータエンジニアリングの技術ニュースを要約するアシスタントです。
記事を読んで以下の JSON 形式で回答してください。

{
  "summary": "箇条書きで3〜5項目の技術ポイント（日本語）",
  "tags": ["タグ1", "タグ2"],
  "importance_score": 0.0〜1.0 (BigQuery/GCP関連なら高め)
}

JSON のみを返してください。説明文は不要です。"""


def summarize_article(title: str, content: str, api_key: str) -> dict | None:
    """Claude で記事を要約する。失敗時は None。"""
    try:
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=512,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": f"タイトル: {title}\n\n本文:\n{content[:3000]}",
                }
            ],
        )
        return json.loads(message.content[0].text)
    except Exception as e:
        print(f"[summarizer] failed: {e}")
        return None
```

**Step 4: テスト実行（成功確認）**

```bash
python -m pytest tests/test_summarizer.py -v
```

Expected: `2 passed`

**Step 5: Commit**

```bash
cd ..
git add news_pipeline/collector/summarizer.py news_pipeline/tests/test_summarizer.py
git commit -m "feat: add Claude-based article summarizer with JSON output"
```

---

## Task 7: Slack Notifier

**Files:**
- Create: `news_pipeline/collector/notifier.py`
- Create: `news_pipeline/tests/test_notifier.py`

**Step 1: テスト作成**

`news_pipeline/tests/test_notifier.py`:

```python
from unittest.mock import MagicMock, patch
from collector.notifier import send_slack_notification


@patch("collector.notifier.requests.post")
def test_send_notification_posts_to_webhook(mock_post):
    mock_post.return_value.status_code = 200

    articles = [
        {
            "title": "BigQuery update",
            "url": "https://cloud.google.com/blog/1",
            "source": "Google Cloud Blog",
            "summary": "- Feature A\n- Feature B",
        }
    ]
    send_slack_notification(articles, webhook_url="https://hooks.slack.com/test")

    mock_post.assert_called_once()
    call_json = mock_post.call_args.kwargs["json"]
    assert "BigQuery update" in call_json["text"]


@patch("collector.notifier.requests.post")
def test_send_notification_limits_to_5(mock_post):
    mock_post.return_value.status_code = 200

    articles = [{"title": f"Article {i}", "url": f"https://x.com/{i}",
                 "source": "s", "summary": "s"} for i in range(10)]
    send_slack_notification(articles, webhook_url="https://hooks.slack.com/test")

    posted_text = mock_post.call_args.kwargs["json"]["text"]
    assert posted_text.count("https://x.com/") == 5


@patch("collector.notifier.requests.post")
def test_send_notification_no_articles_skips_post(mock_post):
    send_slack_notification([], webhook_url="https://hooks.slack.com/test")
    mock_post.assert_not_called()
```

**Step 2: テスト実行（失敗確認）**

```bash
cd news_pipeline
python -m pytest tests/test_notifier.py -v
```

Expected: `ImportError`

**Step 3: `notifier.py` 実装**

```python
import requests

MAX_ARTICLES = 5


def _format_message(articles: list[dict]) -> str:
    lines = ["*本日のデータエンジニアリング技術ニュース*\n"]
    for i, a in enumerate(articles[:MAX_ARTICLES], 1):
        lines.append(f"*{i}. {a['title']}*")
        lines.append(f"出典: {a['source']}")
        lines.append(a.get("summary", ""))
        lines.append(f"<{a['url']}|記事を読む>\n")
    return "\n".join(lines)


def send_slack_notification(articles: list[dict], webhook_url: str) -> None:
    """summaries リストを Slack に通知する。"""
    if not articles:
        print("[notifier] no articles to notify")
        return

    text = _format_message(articles)
    resp = requests.post(webhook_url, json={"text": text})
    if resp.status_code != 200:
        print(f"[notifier] slack error: {resp.status_code} {resp.text}")
```

**Step 4: テスト実行（成功確認）**

```bash
python -m pytest tests/test_notifier.py -v
```

Expected: `3 passed`

**Step 5: Commit**

```bash
cd ..
git add news_pipeline/collector/notifier.py news_pipeline/tests/test_notifier.py
git commit -m "feat: add Slack notifier with 5-article limit"
```

---

## Task 8: メインオーケストレーター

**Files:**
- Create: `news_pipeline/collector/main.py`

**Step 1: `main.py` 実装**

`news_pipeline/collector/main.py`:

```python
import os
from flask import Flask, jsonify

from rss_fetcher import fetch_articles
from article_parser import fetch_content
from bq_client import BQClient
from summarizer import summarize_article
from notifier import send_slack_notification

app = Flask(__name__)

# 環境変数
PROJECT_ID = os.environ["GCP_PROJECT_ID"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
SLACK_WEBHOOK_URL = os.environ["SLACK_WEBHOOK_URL"]

# キーワードフィルタ（高優先度）
HIGH_PRIORITY_KEYWORDS = [
    "bigquery", "dataform", "data catalog", "data lineage",
    "data governance", "google cloud", "data modeling",
]


def _is_relevant(title: str, content: str) -> bool:
    text = (title + " " + (content or "")).lower()
    return any(kw in text for kw in HIGH_PRIORITY_KEYWORDS)


@app.route("/", methods=["POST"])
def run_pipeline():
    bq = BQClient(project=PROJECT_ID)

    # 1. RSS 取得
    articles = fetch_articles()
    print(f"[pipeline] fetched {len(articles)} articles from RSS")

    # 2. dedup
    existing_urls = bq.get_existing_urls()
    new_articles = [a for a in articles if a["url"] not in existing_urls]
    print(f"[pipeline] {len(new_articles)} new articles after dedup")

    if not new_articles:
        return jsonify({"status": "ok", "message": "no new articles"})

    # 3. 本文取得
    for article in new_articles:
        article["content"] = fetch_content(article["url"])

    # 4. raw_articles 保存
    bq.insert_raw_articles(new_articles)
    print(f"[pipeline] saved {len(new_articles)} to raw_articles")

    # 5. フィルタリング
    relevant = [a for a in new_articles if _is_relevant(a["title"], a["content"])]
    print(f"[pipeline] {len(relevant)} relevant articles after filtering")

    # 6. 要約生成
    summaries = []
    for article in relevant:
        result = summarize_article(
            title=article["title"],
            content=article["content"] or "",
            api_key=ANTHROPIC_API_KEY,
        )
        if result:
            summaries.append({
                "article_id": article["article_id"],
                "title": article["title"],
                "url": article["url"],
                "source": article["source"],
                **result,
            })

    # 7. summaries 保存
    if summaries:
        bq.insert_summaries(summaries)
        print(f"[pipeline] saved {len(summaries)} summaries")

    # 8. 通知（importance_score 降順で最大5件）
    top_articles = sorted(summaries, key=lambda x: x.get("importance_score", 0), reverse=True)
    send_slack_notification(top_articles, webhook_url=SLACK_WEBHOOK_URL)

    return jsonify({"status": "ok", "notified": len(top_articles[:5])})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
```

**Step 2: ローカル動作確認（モック環境）**

```bash
cd news_pipeline/collector
GCP_PROJECT_ID=test ANTHROPIC_API_KEY=test SLACK_WEBHOOK_URL=https://x.com python -c "import main; print('import ok')"
```

Expected: `import ok`

**Step 3: 全テスト実行**

```bash
cd news_pipeline
python -m pytest tests/ -v
```

Expected: `12 passed`

**Step 4: Commit**

```bash
cd ..
git add news_pipeline/collector/main.py
git commit -m "feat: add main pipeline orchestrator with Flask endpoint"
```

---

## Task 9: Cloud Run + Cloud Scheduler（Terraform）

**Files:**
- Modify: `news_pipeline/infra/main.tf`（Cloud Run / Scheduler 追加）

**Step 1: `main.tf` に Cloud Run と Scheduler を追加**

```hcl
# Cloud Run Job
resource "google_cloud_run_v2_job" "news_collector" {
  name     = "news-collector"
  location = var.region

  template {
    template {
      containers {
        image = "gcr.io/${var.project_id}/news-collector:latest"

        env {
          name  = "GCP_PROJECT_ID"
          value = var.project_id
        }
        env {
          name = "ANTHROPIC_API_KEY"
          value_source {
            secret_key_ref {
              secret  = "anthropic-api-key"
              version = "latest"
            }
          }
        }
        env {
          name = "SLACK_WEBHOOK_URL"
          value_source {
            secret_key_ref {
              secret  = "slack-webhook-url"
              version = "latest"
            }
          }
        }
      }
    }
  }
}

# Cloud Scheduler（平日9時 JST = 0時 UTC）
resource "google_cloud_scheduler_job" "news_pipeline_trigger" {
  name      = "news-pipeline-daily"
  schedule  = "0 0 * * 1-5"
  time_zone = "UTC"
  region    = var.region

  http_target {
    http_method = "POST"
    uri         = "https://${var.region}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${var.project_id}/jobs/news-collector:run"

    oauth_token {
      service_account_email = google_service_account.scheduler.email
    }
  }
}

resource "google_service_account" "scheduler" {
  account_id   = "news-pipeline-scheduler"
  display_name = "News Pipeline Scheduler"
}

resource "google_project_iam_member" "scheduler_run_invoker" {
  project = var.project_id
  role    = "roles/run.invoker"
  member  = "serviceAccount:${google_service_account.scheduler.email}"
}
```

**Step 2: Terraform validate**

```bash
cd news_pipeline/infra
terraform validate
```

Expected: `Success! The configuration is valid.`

**Step 3: Commit**

```bash
cd ../..
git add news_pipeline/infra/main.tf
git commit -m "feat: add Cloud Run job and Cloud Scheduler Terraform config"
```

---

## Task 10: README と .env.example

**Files:**
- Create: `news_pipeline/README.md`
- Create: `news_pipeline/.env.example`

**Step 1: `.env.example` 作成**

```bash
GCP_PROJECT_ID=your-project-id
ANTHROPIC_API_KEY=sk-ant-...
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
```

**Step 2: `README.md` 作成**

```markdown
# News Pipeline

データエンジニアリング技術ニュースの自動収集・要約・通知システム。

## セットアップ

```bash
cp .env.example .env
# .env を編集して各値を設定

pip install -r collector/requirements.txt
```

## ローカル実行

```bash
cd collector
source ../.env
python main.py
# 別ターミナルで
curl -X POST http://localhost:8080/
```

## テスト

```bash
pip install pytest pytest-mock
python -m pytest tests/ -v
```

## デプロイ

```bash
# BigQuery テーブル作成
cd infra
terraform init
terraform apply -var="project_id=$GCP_PROJECT_ID"

# Docker ビルド & プッシュ
docker build -t gcr.io/$GCP_PROJECT_ID/news-collector:latest collector/
docker push gcr.io/$GCP_PROJECT_ID/news-collector:latest
```
```

**Step 3: Commit**

```bash
git add news_pipeline/README.md news_pipeline/.env.example
git commit -m "docs: add news pipeline README and env example"
```

---

## 完了チェックリスト

- [ ] `python -m pytest news_pipeline/tests/ -v` → 12 passed
- [ ] `terraform validate` → `Success!`
- [ ] ローカルで `curl -X POST http://localhost:8080/` が 200 を返す
- [ ] BigQuery に `tech_news.raw_articles` / `summaries` / `article_chunks` テーブルが存在する
- [ ] Slack に通知が届く

---

## 環境変数（Secret Manager に登録）

| 変数名 | 説明 |
|--------|------|
| `GCP_PROJECT_ID` | GCP プロジェクト ID |
| `ANTHROPIC_API_KEY` | Claude API キー |
| `SLACK_WEBHOOK_URL` | Slack Incoming Webhook URL |
