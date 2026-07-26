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
│   ├── main.py         # /collect (収集) /notify (通知) /recalculate (再採点) /resummarize (要約漏れ復旧) と /slack (Slash command, 通知) エンドポイント
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
- **収集/通知の分離**: `/collect`（毎日6:00 JST）がRSS取得〜要約〜summaries保存、`/notify`（毎日6:30 JST）が未通知サマリーをSlack通知。それぞれ独立したCloud Schedulerで呼び出す。Slack `/news-update` は `/notify` を呼ぶ軽量即応答。
- **本文取得リトライ**: 本文取得に失敗した記事は `raw_articles` に `content_status='pending'` と `retry_count` で保存し、次回 `/collect` 実行時に再取得。`max_content_retries`（settings: `general/max_content_retries`、既定3）到達後は `failed` となり要約をスキップ。
- **収集の繰り越し（取りこぼし防止）**: `/collect` は新着を**全件 `raw_articles` に保存**する（切り捨てない）。`max_summarize` は「1実行の要約バジェット＝繰り越し（pending）＋新着の合算上限」。バジェットは古い順に pending を優先消化し、残り枠で新着を即時要約。超過した新着は `content_status='pending'`・`retry_count=0` で繰り越し、次回以降に処理される（本文取得失敗の pending と同じキューを再利用）。
- **Speaker Deck（スライド）**: feeds に `https://speakerdeck.com/<user>.rss`（ユーザー/組織単位のRSS）を追加すると収集対象になる。本文はスライド画像のため trafilatura では取れない。`article_parser.fetch_content` が Speaker Deck URL を判定し、`speakerdeck.fetch_slide_text` に委譲＝記事ページから PDF を取得し Claude のビジョン入力（`document` ブロック・Haiku 4.5）でプレーンテキストに**書き起こして** content として返す。以降（要約・再採点・deepdive・繰り越し/リトライ）は通常記事と同じ。PDF未発見やAPI 400（ページ超過等）はリトライ不要のスキップ、通信エラーは pending で繰り越す。pypdf 等のテキスト抽出は日本語スライドで文字化けするため不可。
  - **1次フィルタ（コスト最適化）**: PDF取得の前に RSS の `title`+`description` だけで関連度を Haiku で見積もり（`summarizer.score_slide_relevance`）、`general/slide_prefilter_threshold`（既定0.3）未満なら PDFビジョン書き起こし(~$0.05)をスキップする。弾いた記事は `raw_articles` に `content_status='filtered'` で記録され再取得されない。description は空の item が多いため title 中心の判定で、判定不能(None)・閾値以上は通す（取りこぼし防止）。Speaker Deck 以外には適用しない。`description` は1次フィルタ専用の一時情報で raw_articles には保存しない。
- **スコア再計算**: importance_score のロジック（`summarizer._build_scoring_criteria`）を変えたら `summarizer.SCORING_VERSION` を +1 してデプロイし、`POST /recalculate` を古い版が無くなるまで数回叩く。`summaries.scoring_version` で差分管理（既存行は NULL=旧版）。1回 `recalculate_limit`（既定50）件ずつ処理し、スコア更新のみで行は削除しない。
- **閾値未満の終端化**: `/collect` で要約したが `importance_threshold` 未満だった記事は `content_status='summarized'`（終端）で保存され、orphan にならない（新着は streaming buffer 制約を避けるため raw_articles 保存前に status を確定、繰り越し由来は DML でマーク）。
- **通知失敗の再送**: Slack 送信に失敗したカテゴリは通知済みマークをスキップし、次回 `/notify` で再送される。パイプライン例外時は Slack にエラーアラートが飛ぶ。設定ロード失敗（feeds/config 空）は「成功・0件」ではなくエラーになる。
- **dedup**: 既存URLとの照合は**全件スキャン**（url 列のみ・数MB規模でコスト無視できる）。過去に直近90日窓にしたところ、RSSに90日超の記事を残すフィードで窓落ち記事が再収集され重複通知が発生したため窓は使わない。同一実行内の重複（同じURLが複数フィードに載る）も排除する。収集URLは `utm_*`・`fbclid` 等のトラッキングパラメータと fragment を除去して正規化してから article_id を計算する。通知クエリ（`get_unnotified_summaries`）は summaries・raw_articles の両側を article_id ごとに1行へ絞り、raw 重複行による通知の増幅を防ぐ。
- **スコアリングのパーソナライズ**: `/collect` `/recalculate` `/resummarize` は開始時に favorites × summaries からタグ頻度上位N個（`general/personalize_top_tags`、既定5・0で無効）を取得し、採点基準の加点ヒントとして追記する（`bq_client.get_favorite_tag_counts`）。出現2回以上のタグのみ対象（偶発タグへの過適合防止）。タグは英語・小文字・スペース区切りで生成・保存する（プロンプト指示＋`summarizer._normalize_tag` による保存前の機械正規化）。既存データは 2026-07-21 に `scripts/backfill_english_tags.py` で英語統一済み。集計クエリ側にも同じ正規化を安全網として残している。keywords シート同様「ヒント入力」の変化なので `SCORING_VERSION` は上げない。タグ取得失敗時は空リストで続行（パーソナライズなしにフォールバック）。
- **要約漏れの復旧（/resummarize）**: 本文取得は成功したが要約に失敗した記事（クレジット枯渇・API障害など）は `content_status='ok'`・`content` ありで残るが `summaries` が無く、pending でもないため自動リトライされない。`POST /resummarize` はこの orphan（`ok`＋本文あり＋summaries無し）を古い順に再要約する手動バッチ。閾値超えは `summaries` に保存し通常の未通知フローで通知、閾値未満は `content_status='summarized'`（終端）にマークして以降の対象外にする（冪等）。1回 `resummarize_limit`（既定50）件・直近 `resummarize_days`（既定7）日を対象。`recovered=0` かつ orphan 枯渇まで数回叩く。

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

- **feeds シート**: `URL | source | category | block_users | user_location` の5列。
  - `category`: ニュースの分類（任意の文字列）。空欄は `other` 扱い。
  - `block_users`: ブロックする著者の識別子（カンマ区切り、**完全一致**）。空欄ならブロックなし。
  - `user_location`: `block_users` を記事URLのどこと照合するか。空欄は `path1`（パス第1セグメント）。

  **ブロックの仕組みと対応サイト**（記事URLから抽出した識別子と `block_users` を完全一致で照合）:

  | user_location | 抽出位置 | 対応サイト例 | block_users に書く値 |
  |---|---|---|---|
  | （空欄）/ `path1` | パス第1セグメント | Zenn `zenn.dev/<user>/...`、Qiita、note | ユーザー名（例: `web_benriya`） |
  | `subdomain` | ホスト名の先頭ラベル | はてなブログ `<user>.hatenablog.com` | サブドメイン名 |
  | `path2` / `path3` … | パスの N 番目セグメント | 第1がカテゴリ等で第2が著者のサイト | 著者slug |

  - 部分一致はしないため `web_benriya` 指定で `web_benriya2` は誤ブロックされない。
  - 著者slugがURLに無いサイト（一般メディア等）はブロック不可。`block_users` を書いても一致しなければ無視されるだけで無害。
  - Zenn の organization 記事（`zenn.dev/<org>/...`）は第1セグメントが org slug なので org 単位のブロックになる。
  - ブロックは収集時（RSS取得直後）と通知時（保存済みサマリーの通知前）の両方で適用される。
- **settings シート**: `group | key | value` の3列（namespace 方式）。`group` の出現順が通知順になる。
  - `general / max_summarize`: 1実行で要約する最大件数（繰り越し pending ＋ 新着の合算バジェット）
  - `general / importance_threshold`: summaries に残す importance_score の下限（未設定は 0.65）
  - `general / max_content_retries`: 本文取得の最大リトライ回数（未設定は 3）
  - `general / slide_prefilter_threshold`: Speaker Deck の PDF を取得する前の関連度フィルタ下限（未設定は 0.3）。低いほど通しやすい
  - `general / personalize_top_tags`: お気に入り記事のタグ頻度上位N個を採点の加点ヒントに使う（未設定は 5、`0` で無効）
  - `general / recalculate_limit`: 1回の /recalculate で再採点する最大件数（未設定は 50）
  - `general / resummarize_limit`: 1回の /resummarize で再要約する最大件数（未設定は 50）
  - `general / resummarize_days`: /resummarize が対象とする収集日ウィンドウ（未設定は 7）
  - `<category> / max_notify`: そのカテゴリの通知件数上限（未設定は5）
  - `<category> / label`: Slack 通知のヘッダー表示名（未設定はカテゴリ名、`other` は `📰 その他`）

通知は feeds の `category` ごとに独立した Slack メッセージとして送られる。カテゴリの追加・削除・件数変更は feeds/settings シートの編集だけで完結する。