# News Pipeline

データエンジニアリング技術ニュースの自動収集・要約・通知システム。

## アーキテクチャ

```
Cloud Scheduler（平日7:30 JST）
      │
      ▼
Cloud Run Service (news-collector)
      │  POST /          ← スケジューラからの定期実行
      │  POST /slack     ← Slack スラッシュコマンドからの手動実行
      ▼
RSS Fetch → 本文取得 → BigQuery (raw_articles)
      │
      ▼
フィルタリング → Claude 要約 → BigQuery (summaries)
      │
      ▼
Slack 通知（最大5件）
```

## 前提条件

- [gcloud CLI](https://cloud.google.com/sdk/docs/install) インストール済み
- [Terraform](https://developer.hashicorp.com/terraform/install) インストール済み
- [Docker](https://docs.docker.com/get-docker/) インストール済み
- GCP プロジェクト作成済み（BigQuery・Cloud Run・Cloud Scheduler が使えること）
- [Anthropic API キー](https://console.anthropic.com/) 取得済み
- Slack Incoming Webhook URL 取得済み
- Slack App 作成済み（Signing Secret 取得用）

## ローカル実行

### 1. 環境変数の設定

```bash
cp .env.example .env
# .env を編集して各変数を設定
```

### 2. Python 依存インストール

```bash
uv pip install -r requirements-dev.txt
```

### 3. GCP 認証

```bash
gcloud auth application-default login
```

### 4. BigQuery テーブル作成

```bash
cd infra
terraform init
terraform apply -var="project_id=$GCP_PROJECT_ID"
cd ..
```

### 5. サーバー起動

`.env` が自動的に読み込まれます（export 不要）。

```bash
cd collector
python main.py
```

### 6. 動作確認

別ターミナルで:

```bash
curl -X POST http://localhost:8080/
```

## テスト

（GCP 認証・BigQuery 不要。モックで完結する。）

```bash
python -m pytest tests/ -v
```

## 本番デプロイ

### 0. 必要な API を有効化

```bash
gcloud services enable \
  run.googleapis.com \
  cloudscheduler.googleapis.com \
  secretmanager.googleapis.com \
  artifactregistry.googleapis.com \
  --project=$GCP_PROJECT_ID
```

### 1. Artifact Registry リポジトリ作成

```bash
gcloud artifacts repositories create news-collector \
  --repository-format=docker \
  --location=asia-northeast1 \
  --project=$GCP_PROJECT_ID
```

### 2. イメージをビルド＆プッシュ

> **Apple Silicon Mac の場合は `--platform linux/amd64` が必須。**
> Cloud Run は x86_64 で動作するため、arm64 イメージはそのまま使えない。

```bash
gcloud auth configure-docker asia-northeast1-docker.pkg.dev

docker build --platform linux/amd64 \
  -t asia-northeast1-docker.pkg.dev/$GCP_PROJECT_ID/news-collector/news-collector:latest \
  collector/

docker push asia-northeast1-docker.pkg.dev/$GCP_PROJECT_ID/news-collector/news-collector:latest
```

### 3. Secret Manager に秘密情報を登録

```bash
echo -n "$ANTHROPIC_API_KEY" | gcloud secrets create anthropic-api-key \
  --data-file=- --project=$GCP_PROJECT_ID

echo -n "$SLACK_WEBHOOK_URL" | gcloud secrets create slack-webhook-url \
  --data-file=- --project=$GCP_PROJECT_ID

echo -n "$SLACK_SIGNING_SECRET" | gcloud secrets create slack-signing-secret \
  --data-file=- --project=$GCP_PROJECT_ID
```

既存シークレットを更新する場合:

```bash
echo -n "$ANTHROPIC_API_KEY" | gcloud secrets versions add anthropic-api-key \
  --data-file=- --project=$GCP_PROJECT_ID
```

### 4. Cloud Run Service + Scheduler をデプロイ

```bash
cd infra
terraform init
terraform apply -var="project_id=$GCP_PROJECT_ID"
```

Terraform が作成・管理するリソース:
- Cloud Run Service（`/` と `/slack` エンドポイント）
- Cloud Scheduler（平日7:30 JST に `POST /` を呼び出し）
- BigQuery Dataset / Tables
- IAM: Compute Engine デフォルト SA に `secretmanager.secretAccessor` 付与

### 5. イメージ更新時の再デプロイ

コードを変更した場合は、イメージを再ビルド・プッシュした後に以下を実行:

```bash
gcloud run services update news-collector \
  --image=asia-northeast1-docker.pkg.dev/$GCP_PROJECT_ID/news-collector/news-collector:latest \
  --region=asia-northeast1 \
  --project=$GCP_PROJECT_ID
```

> `terraform apply` では `latest` タグの中身が変わっても新リビジョンを作成しないため、
> イメージ更新時は `gcloud run services update` を使う。

### 6. Slack スラッシュコマンドの設定

**Cloud Run の URL を確認:**

```bash
gcloud run services describe news-collector \
  --region=asia-northeast1 \
  --project=$GCP_PROJECT_ID \
  --format="value(status.url)"
```

**Slack App の設定:**

1. [api.slack.com/apps](https://api.slack.com/apps) にアクセス
2. アプリ名（例: `news_pipline`）をクリックしてアプリ詳細画面を開く
3. 左メニュー「Slash Commands」→「Create New Command」
   - Command: `/news-update`（任意）
   - Request URL: `https://<Cloud Run URL>/slack`
   - Short Description: データエンジニアリングニュースを手動収集
4. 「Save」をクリック
5. 左メニュー「Install App」→「Install to Workspace」→「許可する」

インストール後、Slack の通知先チャンネルで `/news-update` と入力して動作確認。

### 7. ログの確認

**Cloud Run ログ（本番）:**

```bash
gcloud logging read \
  'resource.type="cloud_run_revision" AND resource.labels.service_name="news-collector"' \
  --limit=50 \
  --project=$GCP_PROJECT_ID \
  --format="value(timestamp,textPayload)" \
  --freshness=1h
```

または GCP コンソール:
`Cloud Run` → `news-collector` → 「ログ」タブ

## データ構造

| テーブル | 用途 |
|---------|------|
| `tech_news.raw_articles` | 収集した記事の原文 |
| `tech_news.summaries` | Claude 生成サマリー |
| `tech_news.article_chunks` | 将来の RAG 検索用（現在は空） |

## 環境変数

| 変数名 | 説明 | ローカル | 本番 |
|--------|------|---------|------|
| `GCP_PROJECT_ID` | GCP プロジェクト ID | `.env` | Terraform で設定 |
| `ANTHROPIC_API_KEY` | Claude API キー | `.env` | Secret Manager |
| `SLACK_WEBHOOK_URL` | Slack Incoming Webhook URL | `.env` | Secret Manager |
| `SLACK_SIGNING_SECRET` | Slack App の署名シークレット | `.env`（空でも可） | Secret Manager |
| `MAX_ARTICLES` | 処理する記事数の上限 | `.env`（推奨: 5） | Terraform で `20` に設定 |
