# Data Platform Hands-on

AWS + BigQuery + dbt を使ったデータプラットフォーム構築の学習プロジェクト

## プロジェクト概要

サーバーレスアーキテクチャを用いた、ログ収集からデータ分析までの完全なデータパイプラインを構築します。

### アーキテクチャ全体図
```
[Phase 1: AWS データ収集]
ログファイル (S3 raw)
  ↓
Lambda (Docker) - ログ処理・Parquet変換
  ↓
S3 (processed) - Parquet形式で保存
  ↓
[Phase 2: BigQuery + dbt データ分析]
BigQuery - データウェアハウス
  ↓
dbt - データ変換・モデリング
  ↓
ドキュメント・テスト・可視化
```

---

## Phase 1: AWS データ収集パイプライン

### アーキテクチャ
```
S3 (raw logs)
  ↓ S3 Event Trigger
Lambda Function (Docker Container)
  ├─ Access Log Parser
  ├─ Application Log Parser
  └─ Parquet Converter
  ↓
S3 (processed)
  ├─ JSON (サマリー)
  └─ Parquet (詳細データ、パーティション分割)
```

### インフラ構成

**AWS リソース:**
- **S3 バケット**: 
  - `log-analysis-raw-*`: 生ログ保存
  - `log-analysis-processed-*`: 処理済みデータ（JSON + Parquet）
- **Lambda**: 
  - Docker イメージ (512MB, 60秒タイムアウト)
  - Python 3.11 + pyarrow + pandas
- **ECR**: Lambda用コンテナイメージ管理
- **IAM**: Lambda実行ロール

**Terraform モジュール:**
- `s3`: バケット管理
- `iam`: 権限管理
- `ecr`: コンテナレジストリ
- `lambda`: 関数定義

### データフロー

1. **ログアップロード**: S3 raw バケットに配置
2. **Lambda起動**: S3イベントトリガー
3. **ログ処理**: 
   - Access Log: Nginx形式パース
   - App Log: JSON形式パース
4. **データ出力**:
   - JSON: 集計サマリー
   - Parquet: 詳細レコード（パーティション: year/month/day）

### デプロイ方法
```bash
# インフラデプロイ
cd terraform
terraform init
terraform plan
terraform apply

# Lambda更新（コード変更時）
git push origin main  # GitHub Actions が自動デプロイ
```

### 月額コスト

- S3: $0.50
- Lambda: $0（無料枠内）
- ECR: $0
- 合計: **約$0.50/月**

---

## Phase 2: BigQuery + dbt データ分析

### アーキテクチャ
```
BigQuery (データウェアハウス)
  └── logs_database データセット
       ├── access (200,000行, 30日分パーティション)
       ├── app (200,000行, 30日分パーティション)
       ├── logs_database_staging
       │    ├── stg_access_logs (ビュー)
       │    └── stg_app_logs (ビュー)
       └── logs_database_marts
            ├── mart_url_performance (テーブル)
            └── mart_error_analysis (テーブル)
```

### dbtプロジェクト構成
```
dbt_logs_analysis/
├── dbt_project.yml          # プロジェクト設定
├── models/
│   ├── staging/             # データクレンジング層
│   │   ├── sources.yml      # ソース定義
│   │   ├── schema.yml       # テスト・ドキュメント
│   │   ├── stg_access_logs.sql
│   │   └── stg_app_logs.sql
│   └── marts/               # ビジネスロジック層
│       ├── schema.yml
│       ├── mart_url_performance.sql  # URL別パフォーマンス分析
│       └── mart_error_analysis.sql   # エラー分析
└── target/                  # 生成物（Git除外）
```

### データモデル

**Staging層（データクレンジング）:**
- `stg_access_logs`: Webアクセスログの標準化
  - タイムスタンプパース（TIMESTAMP型）
  - ステータスコード分類
  - URL正規化
- `stg_app_logs`: アプリケーションログの標準化
  - ログレベル統一
  - パフォーマンスメトリクス計算

**Marts層（ビジネスロジック）:**
- `mart_url_performance`: URL別パフォーマンス
  - リクエスト数、レスポンスタイム統計
  - エラー率、ユニークビジター数
  - 日別トレンド、ランキング
- `mart_error_analysis`: エラー分析
  - エラー種別集計
  - 時間別トレンド
  - 影響ユーザー数

### セットアップ手順

1. **GCPプロジェクト作成**
```bash
   gcloud init
   # プロジェクトID: data-platform-handson-1223
```

2. **課金アラート設定**
   - 上限: 2000円
   - しきい値: 50%, 90%, 100%

3. **BigQueryデータセット作成**
```bash
   bq mk --location=asia-northeast1 logs_database
```

4. **データロード（GCS経由）**
```bash
   # S3からローカルにダウンロード
   aws s3 sync s3://BUCKET/parquet/ bigquery-data/
   
   # GCSにアップロード
   gsutil -m cp -r bigquery-data/* gs://TEMP_BUCKET/
   
   # BigQueryにロード（TIMESTAMPパーティション）
   bq load --source_format=PARQUET \
     --hive_partitioning_mode=AUTO \
     logs_database.access \
     "gs://BUCKET/access/*"
```

5. **dbt-bigqueryインストール**
```bash
   uv pip install dbt-bigquery
```

6. **認証設定**
   - サービスアカウント作成: `dbt-bigquery@...`
   - ロール: BigQuery 管理者
   - キーファイル: `~/.dbt/bigquery-key.json`
   - profiles.yml: `~/.dbt/profiles.yml`

7. **dbt実行**
```bash
   cd dbt_logs_analysis
   dbt debug           # 接続確認
   dbt run             # モデル実行
   dbt test            # テスト実行 (16 tests)
   dbt docs generate   # ドキュメント生成
   dbt docs serve      # ドキュメント表示
```

### データ統計

- **ストレージ**: 約25MB
- **行数**: 400,000行（access: 200,000, app: 200,000）
- **パーティション**: 30日分（TIMESTAMP型、日次）
- **処理時間**: 
  - Staging: 5秒（ビュー作成）
  - Marts: 15-20秒（テーブル作成 + 集計）

### データ品質テスト

16個のテストを実装:
- `not_null`: NULL値チェック
- `accepted_values`: 値の範囲チェック
- すべてのテストが自動実行・検証

### コスト

**BigQuery（無料枠内）:**
- ストレージ: 25MB < 10GB無料枠 → **$0**
- クエリ: 数GB/月 < 1TB無料枠 → **$0**

**GCS一時バケット:**
- ストレージ: 25MB × $0.020/GB → **$0.0005/月**

**合計: 約$0.01/月**

---

## Phase 1 vs Phase 2 比較

### Athena（当初検討）からBigQueryへの移行理由

| 項目 | Athena | BigQuery |
|------|--------|----------|
| dbtサポート | △ 不安定 | ◎ 公式サポート |
| データ型 | △ 制限あり | ◎ 柔軟 |
| タイムスタンプ | △ ハック必要 | ◎ ネイティブ対応 |
| エラーメッセージ | △ 不明瞭 | ◎ 明確 |
| コスト | $1-2/月 | $0/月（無料枠内） |

### 主要な学習成果

**Phase 1 (AWS):**
- ✅ Terraform による IaC
- ✅ Lambda + Docker による処理
- ✅ S3 イベント駆動アーキテクチャ
- ✅ GitHub Actions による CI/CD
- ✅ Parquet フォーマット

**Phase 2 (BigQuery + dbt):**
- ✅ Athena → BigQuery 移行判断
- ✅ TIMESTAMPベースのパーティショニング
- ✅ dbtのレイヤー構造（staging → marts）
- ✅ データ品質テスト（not_null, accepted_values）
- ✅ 自動ドキュメント生成とLineage可視化
- ✅ BigQueryのクエリ最適化

---

## 技術スタック

### Phase 1
- **Infrastructure**: AWS (S3, Lambda, ECR, IAM)
- **IaC**: Terraform 1.9+
- **Runtime**: Python 3.11, Docker
- **Data Format**: Parquet (pyarrow, pandas)
- **CI/CD**: GitHub Actions, Terraform Cloud

### Phase 2
- **Data Warehouse**: Google BigQuery
- **Transformation**: dbt (dbt-bigquery 1.11.0)
- **Data Quality**: dbt tests
- **Documentation**: dbt docs
- **Storage**: Google Cloud Storage (GCS)

---

## ディレクトリ構造
```
data-platform-handson/
├── README.md
├── .gitignore
├── terraform/                    # Phase 1: AWS Infrastructure
│   ├── main.tf
│   ├── variables.tf
│   ├── outputs.tf
│   └── modules/
│       ├── s3/
│       ├── iam/
│       ├── ecr/
│       └── lambda/
├── docker/                       # Phase 1: Lambda Container
│   └── log-processor/
│       ├── Dockerfile
│       ├── app.py
│       └── requirements.txt
├── .github/
│   └── workflows/
│       └── deploy.yml           # Phase 1: CI/CD
├── dbt_logs_analysis/           # Phase 2: dbt Project
│   ├── dbt_project.yml
│   ├── models/
│   │   ├── staging/
│   │   │   ├── sources.yml
│   │   │   ├── schema.yml
│   │   │   ├── stg_access_logs.sql
│   │   │   └── stg_app_logs.sql
│   │   └── marts/
│   │       ├── schema.yml
│   │       ├── mart_url_performance.sql
│   │       └── mart_error_analysis.sql
│   └── target/                  # Git除外
└── scripts/                     # 補助スクリプト
    ├── generate_logs.py
    ├── recreate_tables.sql
    └── amplify_data.sql
```

---

## 環境変数

**AWS（Phase 1）:**
```bash
export AWS_PROFILE=default
export AWS_REGION=ap-northeast-1
```

**GCP（Phase 2）:**
```bash
export GOOGLE_APPLICATION_CREDENTIALS=~/.dbt/bigquery-key.json
```

---

## よくある問題と解決方法

### Phase 1

**問題**: Lambda関数が更新されない
- **原因**: ECRイメージのタグが `:latest` で変更検知されない
- **解決**: GitHub Actionsで自動デプロイ（CI/CD推奨）

**問題**: Terraform state の不整合
- **原因**: バックエンド移行時の state 未移行
- **解決**: `terraform import` で既存リソースをインポート

### Phase 2

**問題**: dbt test で型エラー
- **原因**: `accepted_values` で文字列と数値の型不一致
- **解決**: `quote: false` を追加

**問題**: BigQuery パーティションが作成されない
- **原因**: ローカルファイルパスではHiveパーティション不可
- **解決**: GCS経由でロード

---

## 今後の拡張案

- [ ] Looker / Metabase による可視化
- [ ] dbt Cloudへの移行
- [ ] Incremental モデルの実装
- [ ] Great Expectations による高度なテスト
- [ ] Airflow / Dagster によるオーケストレーション
- [ ] dbt docs の GitHub Pages 自動デプロイ

---

## ライセンス

MIT License

---

## 参考資料

- [dbt Documentation](https://docs.getdbt.com/)
- [BigQuery Documentation](https://cloud.google.com/bigquery/docs)
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)