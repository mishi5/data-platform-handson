# News Pipeline

データエンジニアリング技術ニュースの自動収集・要約・通知システム。

## アーキテクチャ

```
Cloud Scheduler（平日9時 JST）
      │
      ▼
Cloud Run Job (news-collector)
      │
      ▼
RSS Fetch → 本文抽出 → BigQuery (raw_articles)
      │
      ▼
フィルタリング → Claude 要約 → BigQuery (summaries)
      │
      ▼
Slack 通知（最大5件）
```

## セットアップ

```bash
cp .env.example .env
# .env を編集して各値を設定

pip install -r requirements-dev.txt
```

## ローカル実行

```bash
cd collector
export $(cat ../.env | xargs)
python main.py
# 別ターミナルで
curl -X POST http://localhost:8080/
```

## テスト

```bash
python -m pytest tests/ -v
```

## デプロイ

### 1. BigQuery テーブル作成

```bash
cd infra
terraform init
terraform apply -var="project_id=$GCP_PROJECT_ID"
```

### 2. Secret Manager に秘密情報を登録

```bash
echo -n "$ANTHROPIC_API_KEY" | gcloud secrets create anthropic-api-key --data-file=-
echo -n "$SLACK_WEBHOOK_URL" | gcloud secrets create slack-webhook-url --data-file=-
```

### 3. Docker イメージをビルド & プッシュ

```bash
docker build -t gcr.io/$GCP_PROJECT_ID/news-collector:latest collector/
docker push gcr.io/$GCP_PROJECT_ID/news-collector:latest
```

### 4. Cloud Run + Scheduler をデプロイ

```bash
cd infra
terraform apply -var="project_id=$GCP_PROJECT_ID"
```

## データ構造

| テーブル | 用途 |
|---------|------|
| `tech_news.raw_articles` | 収集した記事の原文 |
| `tech_news.summaries` | Claude 生成サマリー |
| `tech_news.article_chunks` | 将来の RAG 検索用（現在は空） |

## 環境変数

| 変数名 | 説明 |
|--------|------|
| `GCP_PROJECT_ID` | GCP プロジェクト ID |
| `ANTHROPIC_API_KEY` | Claude API キー（Secret Manager 経由） |
| `SLACK_WEBHOOK_URL` | Slack Incoming Webhook URL（Secret Manager 経由） |
