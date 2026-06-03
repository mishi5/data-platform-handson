# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AWS + BigQuery + dbt ベースのデータ分析基盤ハンズオンプロジェクト。2フェーズ構成：
- **Phase 1 (AWS):** S3 → Lambda (Docker) → S3 (Parquet) のデータ収集パイプライン（Terraform管理）
- **Phase 2 (BigQuery + dbt):** `dbt_logs_analysis/` 配下でログデータの変換・分析

## Commands

### dbt (メインの開発対象)

```bash
cd dbt_logs_analysis

# 依存パッケージのインストール
dbt deps

# 全モデルのビルド
dbt build

# 特定モデルのみ実行
dbt run --select mart_url_performance
dbt run --select staging.*

# テスト実行
dbt test
dbt test --select stg_access_logs

# マクロのテスト（マクロ動作確認用のオペレーション）
dbt run-operation test_performance_stats
dbt run-operation test_percentile

# ドキュメント生成・閲覧
dbt docs generate
dbt docs serve
```

### SQL リント

```bash
cd dbt_logs_analysis

# 全SQLファイルのリント
sqlfluff lint models/

# 特定ファイルのフォーマット
sqlfluff fix models/marts/mart_url_performance.sql
```

### Terraform (Phase 1: AWS インフラ)

```bash
cd terraform
terraform init
terraform plan
terraform apply
```

## Architecture

### dbt プロジェクト構造

```
dbt_logs_analysis/
├── models/
│   ├── staging/    # BigQuery生テーブル → クリーニング（VIEW化）
│   └── marts/      # ビジネスロジック（TABLE化）
└── macros/         # 再利用可能なSQLマクロ
```

**データフロー:** `logs_database.access` / `logs_database.app` (BigQuery生テーブル) → staging views → marts tables

### マテリアライズ戦略
- `staging/`: `+materialized: view`, `+schema: staging`
- `marts/`: `+materialized: table`, `+schema: marts`
- 増分モデル (`mart_url_performance_incremental`): `materialized='incremental'`, `unique_key=['url_path', 'date']`

### マクロライブラリ

| ファイル | 主なマクロ | 用途 |
|---------|-----------|------|
| `macros/performance_metrics.sql` | `performance_stats()`, `percentile()` | レスポンスタイム集計 |
| `macros/error_detection.sql` | `is_http_error()`, `error_category()` | HTTPステータス分類 |
| `macros/date_filters.sql` | `recent_days()`, `date_between()` | 日付フィルタリング |
| `macros/test_macros.sql` | `test_performance_stats()` | マクロ動作確認 |

### BigQuery ソース定義
- プロジェクト: `data-platform-handson-1223`
- データセット: `logs_database`
- テーブル: `access`（Nginxアクセスログ 200K行）、`app`（アプリケーションログ 200K行）

### SQLfluff 規約
- dialect: BigQuery
- キーワード: 大文字 (`SELECT`, `FROM`, `WHERE`)
- リテラル: 小文字 (`true`, `false`, `null`)
- インデント: スペース4つ
- 除外ルール: L034, L036

### CI/CD
- `.github/workflows/deploy.yml`: Terraform + Docker イメージ (mainブランチプッシュ時)
- `.github/workflows/dbt-docs.yml`: dbt docs を GitHub Pages に自動デプロイ (`dbt_logs_analysis/**` 変更時)

## news_pipeline（ニュース自動収集）

Cloud Run Service + Slack通知によるデータエンジニアリングニュース収集システム。

```bash
# ローカル実行
cd news_pipeline/collector
python main.py

# テスト（BigQuery不要・モック完結）
cd news_pipeline && uv run pytest tests/ -v

# 本番デプロイ（Apple Silicon MacはPlatform指定必須）
docker build --platform linux/amd64 -f news_pipeline/collector/Dockerfile -t asia-northeast1-docker.pkg.dev/$GCP_PROJECT_ID/news-collector/news-collector:latest news_pipeline/
docker push asia-northeast1-docker.pkg.dev/$GCP_PROJECT_ID/news-collector/news-collector:latest

# Terraform（BigQuery + Cloud Run + Scheduler）
cd news_pipeline/infra
terraform apply -var="project_id=$GCP_PROJECT_ID"

# コード変更後の強制デプロイ（terraform applyではlatestタグ変更を検知しない）
gcloud run services update news-collector \
  --image=asia-northeast1-docker.pkg.dev/$GCP_PROJECT_ID/news-collector/news-collector:latest \
  --region=asia-northeast1 --project=$GCP_PROJECT_ID

# ログ確認
gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="news-collector"' \
  --limit=50 --project=$GCP_PROJECT_ID --format="value(timestamp,textPayload)" --freshness=1h
```

### news_pipeline 構造

```
news_pipeline/
├── collector/          # Cloud Run Service（Flask）
│   ├── main.py         # / (Scheduler) と /slack (Slash command) エンドポイント
│   ├── rss_fetcher.py  # RSS取得
│   ├── article_parser.py # 本文取得（requests + trafilatura）
│   ├── summarizer.py   # Claude API要約
│   ├── notifier.py     # Slack Incoming Webhook通知
│   └── bq_client.py    # BigQuery書き込み
└── infra/              # Terraform（Cloud Run・Scheduler・BigQuery）
```

### Gotchas
- **Apple Silicon Mac**: `docker build --platform linux/amd64` 必須（Cloud RunはX86_64）
- **Secret更新後**: `gcloud run services update` で再起動しないと新Secretを読まない
- **Cloud Run バックグラウンド処理**: `cpu_idle = false` を設定しないとリクエスト後にCPUが絞られデーモンスレッドが停止する
- **Terraform latestタグ**: イメージ内容が変わってもTerraformは検知しない。コード変更時は `gcloud run services update` を使う

### 環境変数（news_pipeline/.env）

| 変数 | 説明 |
|------|------|
| `GCP_PROJECT_ID` | GCPプロジェクトID |
| `ANTHROPIC_API_KEY` | Claude APIキー |
| `SLACK_WEBHOOK_URL` | Slack Incoming Webhook URL |
| `SLACK_SIGNING_SECRET` | Slash command署名検証（空でも可） |
| `MAX_ARTICLES` | 処理記事数上限（ローカル推奨: 5、本番: 20） |

### Google Sheets 設定（news-pipeline-config）

通知の分類・件数上限・表示名は Google Sheets で動的に管理する（コード変更不要）。

- **feeds シート**: `URL | source | category` の3列。`category` 列でニュースの分類を指定（任意の文字列）。空欄は `other` 扱い。
- **settings シート**: `group | key | value` の3列（namespace 方式）。`group` の出現順が通知順になる。
  - `general / max_summarize`: 1実行で要約する最大件数
  - `<category> / max_notify`: そのカテゴリの通知件数上限（未設定は5）
  - `<category> / label`: Slack 通知のヘッダー表示名（未設定はカテゴリ名、`other` は `📰 その他`）

通知は feeds の `category` ごとに独立した Slack メッセージとして送られる。カテゴリの追加・削除・件数変更は feeds/settings シートの編集だけで完結する。