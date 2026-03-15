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
RSS Fetch → dedup（raw_articles） → 本文取得 → raw_articles 保存
      │
      ▼
Claude 要約（全新着記事）→ importance_score フィルタ → summaries 保存
      │
      ▼
未通知サマリー取得（notification_log で管理）
      │
      ├─ 1件以上 → Slack 通知（最大 MAX_NOTIFY 件）→ notification_log に記録
      └─ 0件     → ネタ切れ通知
```

設定（feeds / keywords / max_summarize）は **Google Sheets** で管理。デプロイ不要で変更可能。

## 前提条件

- [gcloud CLI](https://cloud.google.com/sdk/docs/install) インストール済み
- [Terraform](https://developer.hashicorp.com/terraform/install) インストール済み
- [Docker](https://docs.docker.com/get-docker/) インストール済み
- [Make](https://www.gnu.org/software/make/) インストール済み
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
  sheets.googleapis.com \
  --project=$GCP_PROJECT_ID
```

### 1. Artifact Registry リポジトリ作成

```bash
gcloud artifacts repositories create news-collector \
  --repository-format=docker \
  --location=asia-northeast1 \
  --project=$GCP_PROJECT_ID
```

### 2. Google Sheets の設定

1. Google スプレッドシートを新規作成し、以下のシートを追加:

   | シート名 | 列構成 | 内容 |
   |---------|-------|------|
   | `feeds` | A: URL, B: ソース名 | RSS フィード一覧 |
   | `keywords` | A: キーワード | importance_score 判定の基準語 |
   | `settings` | A: キー, B: 値 | `max_summarize` などのパラメータ |

2. URL から Spreadsheet ID を取得（`/d/<SHEET_ID>/` の部分）
3. Cloud Run のデフォルト SA（`<PROJECT_NUMBER>-compute@developer.gserviceaccount.com`）に「閲覧者」として共有

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
- BigQuery Dataset / Tables（`raw_articles`, `summaries`, `notification_log`, `article_chunks`）
- Google Sheets API 有効化
- IAM: Compute Engine デフォルト SA に `secretmanager.secretAccessor` 付与

### 5. イメージをビルド＆デプロイ

> **Apple Silicon Mac の場合は `--platform linux/amd64` が必須。**
> Cloud Run は x86_64 で動作するため、arm64 イメージはそのまま使えない。

```bash
gcloud auth configure-docker asia-northeast1-docker.pkg.dev

# news_pipeline/ ディレクトリで実行
make deploy   # build + push + gcloud run services update を一括実行
```

個別に実行したい場合:

```bash
make build    # docker build のみ
make push     # docker push のみ
make update   # gcloud run services update のみ（設定変更後の再起動など）
```

> `terraform apply` では `latest` タグの中身が変わっても新リビジョンを作成しないため、
> コード変更時は `make deploy` または `make update` を使う。

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
2. アプリをクリックしてアプリ詳細画面を開く
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
| `tech_news.raw_articles` | 収集した記事の原文（dedup の基準） |
| `tech_news.summaries` | Claude 生成サマリー（importance_score 閾値以上のみ） |
| `tech_news.notification_log` | Slack 通知済み article_id の記録 |
| `tech_news.article_chunks` | 将来の RAG 検索用（現在は空） |

## 環境変数

| 変数名 | 説明 | ローカル | 本番 |
|--------|------|---------|------|
| `GCP_PROJECT_ID` | GCP プロジェクト ID | `.env` | Terraform で設定 |
| `ANTHROPIC_API_KEY` | Claude API キー | `.env` | Secret Manager |
| `SLACK_WEBHOOK_URL` | Slack Incoming Webhook URL | `.env` | Secret Manager |
| `SLACK_SIGNING_SECRET` | Slack App の署名シークレット | `.env`（空でも可） | Secret Manager |
| `SHEET_ID` | 設定スプレッドシートの ID | `.env` | Terraform で設定 |
| `MAX_NOTIFY` | フィルタ後に通知する件数の上限 | `.env`（デフォルト: 5） | Terraform で設定 |
| `IMPORTANCE_THRESHOLD` | 通知対象とする importance_score の閾値 | `.env`（デフォルト: 0.5） | Terraform で設定 |

## Google Sheets で管理する設定

| シート | 内容 | 変更反映 |
|--------|------|---------|
| `feeds` | RSS フィード URL とソース名 | 次回実行時（デプロイ不要） |
| `keywords` | importance_score 判定の基準キーワード | 次回実行時（デプロイ不要） |
| `settings` | `max_summarize`（要約件数上限、デフォルト 10） | 次回実行時（デプロイ不要） |
