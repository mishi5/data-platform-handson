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
│   ├── relevance.py    # データ基盤との関連度判定（TypeSafe Jev）
│   ├── note_fetcher.py # note のハッシュタグに付いた記事一覧の取得（非公式 API）
│   ├── notifier.py     # Slack Incoming Webhook通知
│   └── bq_client.py    # BigQuery書き込み
└── infra/              # Terraform（Cloud Run・Scheduler・BigQuery）
```

### Gotchas
- **Claude SDK / モデル**: `anthropic` は **1.x**（`pyproject.toml` で固定）。使用モデルは要約・採点・スライド書き起こしが `claude-haiku-4-5`（`summarizer._MODEL` / `speakerdeck._MODEL`）、深堀りが `claude-sonnet-5`（`deepdiver`）。**モデルIDに日付サフィックスを付けない**（`claude-haiku-4-5-20251001` のような形は使わない）。
  - **`temperature` は `extra_body` で渡す**: SDK 1.x で `messages.create()` の引数から削除された。Haiku 4.5 は値自体は受け付けるので、採点の一貫性のために `extra_body={"temperature": 0}` として送っている。引数で渡すと `TypeError` で落ちる。
  - **Sonnet 5 は adaptive thinking が既定で走る**: レスポンスの先頭ブロックが `thinking` になりうるため `content[0]` を決め打ちしてはいけない（`deepdiver` は TextBlock を探索する）。`max_tokens` は thinking と本文の合算上限なので余裕が要る（1024 では thinking だけで使い切る。実測で 4096 が妥当）。
  - **モックテストは SDK の破壊的変更を検出できない**: Anthropic クライアントを丸ごとモックしているため、0.43.0 → 1.0.0 で `temperature` が削除されてもテストは全て通ったまま本番だけが落ちる状態だった。`tests/sdk_signature.py` の `assert_matches_sdk_signature` が、モックの記録した kwargs を実 SDK のシグネチャに `bind_partial` して齟齬を落とす。API 呼び出しの kwargs を検証するテストではこれを併用する。
- **関連度判定（TypeSafe Jev）**: `relevance_score` だけは Claude ではなく TypeSafe の Jev（`relevance.py`、`typesafe-sdk` を `pyproject.toml` で固定、モデルは `jev-1.13.0` に固定）で判定する。Jev は文章を生成せず型付きの判断と確率だけを返すモデルで、「この記事の技法の適用対象はデータ／データ基盤か」の Yes/No 確率（Noul）をそのまま relevance_score にする。単価は Haiku の約1/50（入力 $0.042/100万トークン・出力無料）、1件約0.2秒。APIキーは Secret `typesafe-api-key` → 環境変数 `TYPESAFE_API_KEY`。
  - **全経路で Jev に統一**: `/collect`・`/resummarize`・`/recalculate` は Claude の結果の relevance_score を `main._with_jev_relevance` で Jev の値に置き換えてから保存・ゲートする。スライドの1次フィルタも Jev。Claude のプロンプトには引き続き relevance を出させている（importance の判断材料として。保存には使わない）。尺度の違う値が summaries に混ざると閾値を1つに決められなくなるため、一部の経路だけ Claude に戻すことはしない。
  - **本文は冒頭2000字だけ渡す**: 長く渡すと無関係な文脈で判定がぶれる（評価で 8000 字より 2000 字の方が一致が高かった）。定義は英語で書く（Jev は英語が主言語。日本語の記事本文はそのまま渡してよい）。
  - **苦手**: 業界でのデータ活用論（製薬・医療・メディア財務などのベンダーブログ）をデータ基盤と取り違えやすく、対象外に明記して抑えている。社内ナレッジ基盤（Notion 等）のような境界の記事は低く出る。重要度（importance）は PoC で Claude との一致が弱かった（AUC 約0.7）ため Claude のまま。
  - **モデルの版を上げるとき**: 確率の出方（＝最適な閾値）が変わりうるので、`relevance.MODEL` を変える前に `scripts/eval_jev.py` で閾値を確かめる。
- **Apple Silicon Mac**: `docker build --platform linux/amd64` 必須（Cloud RunはX86_64）
- **Secret更新後**: `gcloud run services update` で再起動しないと新Secretを読まない
- **Cloud Run バックグラウンド処理**: `cpu_idle = false` を設定しないとリクエスト後にCPUが絞られデーモンスレッドが停止する
- **Terraform latestタグ**: イメージ内容が変わってもTerraformは検知しない。コード変更時は `gcloud run services update` を使う
- **BigQuery 列追加時のデプロイ順序**: summaries/raw_articles に列を足す変更は**必ず `terraform apply` → `gcloud run services update` の順**。`insert_rows_json` はスキーマに無いフィールドを含む行をエラーにするため、逆順だと `/collect` がサマリー保存で落ちてパイプライン全体が例外になる。`tests/test_main.py` の `test_summaries_payload_fits_bigquery_schema` が insert ペイロードと `infra/bigquery.tf` の齟齬をローカルで捕捉する
- **収集/通知の分離**: `/collect`（毎日6:00 JST）がRSS取得〜要約〜summaries保存、`/notify`（毎日6:30 JST）が未通知サマリーをSlack通知。それぞれ独立したCloud Schedulerで呼び出す。Slack `/news-update` は `/notify` を呼ぶ軽量即応答。
- **本文取得リトライ**: 本文取得に失敗した記事は `raw_articles` に `content_status='pending'` と `retry_count` で保存し、次回 `/collect` 実行時に再取得。`max_content_retries`（settings: `general/max_content_retries`、既定3）到達後は `failed` となり要約をスキップ。
- **収集の繰り越し（取りこぼし防止）**: `/collect` は新着を**全件 `raw_articles` に保存**する（切り捨てない）。`max_summarize` は「1実行の要約バジェット＝繰り越し（pending）＋新着の合算上限」。バジェットは古い順に pending を優先消化し、残り枠で新着を即時要約。超過した新着は `content_status='pending'`・`retry_count=0` で繰り越し、次回以降に処理される（本文取得失敗の pending と同じキューを再利用）。
- **Speaker Deck（スライド）**: feeds に `https://speakerdeck.com/<user>.rss`（ユーザー/組織単位のRSS）を追加すると収集対象になる。本文はスライド画像のため trafilatura では取れない。`article_parser.fetch_content` が Speaker Deck URL を判定し、`speakerdeck.fetch_slide_text` に委譲＝記事ページから PDF を取得し Claude のビジョン入力（`document` ブロック・Haiku 4.5）でプレーンテキストに**書き起こして** content として返す。以降（要約・再採点・deepdive・繰り越し/リトライ）は通常記事と同じ。PDF未発見やAPI 400（ページ超過等）はリトライ不要のスキップ、通信エラーは pending で繰り越す。pypdf 等のテキスト抽出は日本語スライドで文字化けするため不可。
  - **1次フィルタ（コスト最適化）**: PDF取得の前に RSS の `title`+`description` だけで関連度を Jev で見積もり（`relevance.judge_relevance`）、`general/slide_prefilter_threshold`（既定0.1）未満なら PDFビジョン書き起こし(~$0.05)をスキップする。弾いた記事は `raw_articles` に `content_status='filtered'` で記録され再取得されない。description は空の item が多いため title 中心の判定で、判定不能(None)・閾値以上は通す（取りこぼし防止）。Speaker Deck 以外には適用しない。`description` は1次フィルタ専用の一時情報で raw_articles には保存しない。
- **note のハッシュタグ経路（note_fetcher）**: `note_tags` シートに書いたタグの新着を、非公式 API `GET https://note.com/api/v3/hashtags/{tag}/notes?order=new&page=N`（ログイン不要・1ページ50件）で取得する。note のハッシュタグ RSS は最新25件しか返さず、1日1回の収集では取りこぼすため API を使う。`publish_at` が `note_lookback_days` 日より前の記事・`is_last_page`・`note_max_pages` のいずれかでページ送りを止める。source 名は `note #<tag>`（`note_fetcher.source_name`）。URL は `https://note.com/<urlname>/n/<key>` に組み立て、`rss_fetcher` と同じ正規化・article_id 計算を通すので、著者 RSS 経由の同じ記事とも dedup で一致する。設計は `docs/superpowers/specs/2026-09-29-note-tag-collector-design.md`。
  - **非公式 API への依存は一覧だけ**: 本文は記事ページから通常どおり trafilatura で取る。認証が必要なエンドポイントは使わず、リクエスト間に1秒待つ。一覧 API にハッシュタグは含まれない（個別記事 API にはあるが1件1リクエストになる）。仕様変更で失敗してもタグ単位で warning を出して続行し、RSS の収集は止めない。有料記事（`price > 0`、無料部分しか取れない）と `TextNote` 以外は取り込まない。
  - **1次フィルタ**: タグ経路は著者を選んでいない流入なので、本文取得の前に一覧 API の `body`（本文冒頭240字）と title を Jev で判定し、`general/note_prefilter_threshold`（既定0.1）未満は `content_status='filtered'`（終端）で保存する。記事 dict の一時情報 `origin="note_tag"` で見分けるため、feeds に登録した note の著者 RSS の記事には適用しない。実測では `#データエンジニアリング` の新着50件中30件が 0.5 以上、競艇予想などの対象外は 0.01〜0.10 に分かれた。
  - **タグの選び方**: 流量の多いタグ（`#データ分析` 約3,000件/日、`#ClaudeCode` 約400件/日）は入れていない。1日のリクエストが数十回に増えるうえ、命中は新着50件中0〜1件だった。`order=popular` / `order=hot` は note の読者層での人気順で技術的な関連度とは無関係なので使わない。タグの総件数と関連タグは `GET https://note.com/api/v2/hashtags/{tag}` の `count` / `relatedHashtags` で調べられる。`#DBT` は弁証法的行動療法と衝突する（Jev で落ちる）。
- **要約のリテラル `\n` 対策**: tool use 出力でモデルが改行を二重エスケープすることがあり、そのままだと Slack に「\n」が表示される。`summarizer._unescape_literal_newlines` が保存前に summary のリテラル `\n` を実改行へ置換する（対象は summary のみ）。ただし記事が改行文字自体を扱うケース（`'\n'`・`「\n」`・`(\n)` などクォート/カッコ囲み）は正規表現の lookbehind/lookahead で除外して保持する。既存37件は 2026-08-10 に BigQuery の `REPLACE(summary, '\n\\n', '\n\n')` で backfill 済み（BigQuery の REGEXP_REPLACE は RE2 で lookaround 不可のため単純置換）。
- **対象領域ゲート（relevance_score）**: 採点は「読む価値（importance_score）」と「データ基盤との関連度（relevance_score）」の2軸。良質でも対象領域外（AWS の IAM/セキュリティ、ネットワーク運用、開発環境Tips、データ基盤に紐づかない AI コーディング論など）の記事を落とすための軸で、これが無いと importance だけでは 0.7〜0.8 に大量のノイズが混ざる。判定原理は「AI・IaC・クラウドという技法が登場するか」ではなく**その技法の適用対象がデータ／データ基盤か**の一点で、`relevance.DOMAIN_DEFINITION`（Jev 用・英語）に対象/対象外と対比例を置く。Claude の importance 判断用に同じ原理の日本語版 `summarizer._DOMAIN_DEFINITION` もあり、定義を変えるときは両方を揃える。
  - **キャップではなくゲート**: relevance で importance を減点・上限クリップする方式は採らない。閾値を変えるたびに全件再採点が必要になり、importance の意味（質が低いのか領域外なのか）も判別できなくなるため。relevance は素のまま `summaries.relevance_score` に保存し、`main.passes_thresholds` が2軸で足切りする。閾値調整は settings シートの1セル編集だけで済む。
  - **判定不能は通す**: Jev の呼び出しに失敗した場合（None）と、`summaries.relevance_score` が NULL の旧データはゲートを通す。取りこぼし防止を優先する。
  - **通知経路にもゲートが要る**: `/recalculate` はスコアを下げるだけで行を削除しないため、`bq_client.get_unnotified_summaries` 側にも閾値条件がある。ここが抜けると、再採点で閾値割れした未通知記事がそのまま Slack に流れる。
  - **オフライン評価**: プロンプト品質はモック前提のユニットテストでは測れない。`scripts/eval_scoring.py` が正解セット（お気に入り＝keep／対象外指定＝drop）を本番と同じ経路（importance は Claude、relevance は Jev）で採点して正解率を出す。通過帯のサンプルは `--sample N`。**プロンプトや `relevance.DOMAIN_DEFINITION` を変えたらデプロイ前にこれを回す。** `scripts/eval_jev.py` は Jev の判定を Claude（切り替え前に退避した `summaries_claude_relevance_v3`）と比べる評価で、AUC・一致率・最良閾値を出す（応答はキャッシュされ再実行は無料）。
- **上限到達時の即時中断と予算カウンタ**: クレジット枯渇・支出上限の到達（400 で `credit balance is too low` / `usage limits`）はリトライしても回復しない。`summarizer.QuotaExceededError` として送出し、`/recalculate`・`/resummarize` は残りを呼ばずにループを中断する。これが無いと1バッチ分（100件）を丸ごと無駄打ちする（実際に 2026-08-27 に 200 件分を空振りさせた）。
  - **上限の残量は API から取れない**: レスポンスヘッダーの `anthropic-ratelimit-*` は分あたりのスループット枠（input/output/requests）であって支出枠ではない。Admin API（`/v1/organizations/cost_report`）は実在するが Admin キー（`sk-ant-admin...`）が必要で通常キーでは 401。そのため `summarizer.CostTracker` が各レスポンスの `usage` から実コストを自前で積算する。
  - `general / batch_budget_usd`（既定 未設定＝無制限）を超えるとバッチはそこで停止する。大量の再採点・再要約を流す前に設定しておくと、月次の支出上限を一気に使い切る事故を防げる。単価は `summarizer._INPUT_USD_PER_MTOK` / `_OUTPUT_USD_PER_MTOK`（Haiku 4.5 の $1 / $5）。モデルを変えたらここも直すこと。
- **スコア再計算**: 採点ロジック（`summarizer._build_scoring_criteria` / `_DOMAIN_DEFINITION`）を変えたら `summarizer.SCORING_VERSION` を +1 してデプロイし、`POST /recalculate` を古い版が無くなるまで数回叩く。`summaries.scoring_version` で差分管理（既存行は NULL=旧版）。版4は relevance を Jev に切り替えた版で、版3の行は `scripts/backfill_jev_relevance.py` で relevance だけ付け直した（2026-09-27、Claude を呼ばず約 $0.2。切り替え前の Claude の値は `summaries_claude_relevance_v3` に退避）。1回 `recalculate_limit`（既定50）件ずつ importance と relevance の両方を更新し、行は削除しない。移行中は新旧の版が混在して通知ランキングが乱れるため、`recalculate_limit` を一時的に 200〜300 に上げて短期間で流し切るとよい。
  - **完了判定は `error_count` を見る**: `/recalculate`・`/resummarize` のレスポンスは `{"notified": 成功件数, "error_count": 失敗件数}`。`notified=0` だけでは「対象なし」と「対象はあるが全件失敗」を区別できない（実際に Anthropic API のクレジット枯渇で全件失敗し、0 が返り続けたのを完走と誤認したことがある）。**`notified=0` かつ `error_count=0` が真の完了**。`error_count>0` なら Cloud Run のログで `score failed` / `summarize failed` の原因を見る。念のため BigQuery 側でも `COUNTIF(scoring_version IS NULL OR scoring_version < N)` が 0 になったことを確認するとよい。
- **閾値未満の終端化**: `/collect` で要約したがゲート（`importance_threshold` または `relevance_threshold`）を通らなかった記事は `content_status='summarized'`（終端）で保存され、orphan にならない（新着は streaming buffer 制約を避けるため raw_articles 保存前に status を確定、繰り越し由来は DML でマーク）。
- **Sheets 設定ロードの一時障害リトライ**: Google Sheets API は一時的に 503 を返すことがあり、設定ロードの失敗は設定ガードでパイプライン全体の例外になる（＝その回の通知が丸ごとスキップされる）。実際に 2026-08-23 と 2026-08-26 の JST 6:30 `/notify` が 503 で落ちて通知が飛ばなかった（記事は未通知のまま残るため消失はせず、次回に持ち越される）。`config_loader.load_config` が 5xx・接続エラー・タイムアウトを指数バックオフ（1s→2s、最大3回）で再試行する。403（権限）や 404（シート無し）は恒久的な失敗なので再試行しない。
- **通知失敗の再送**: Slack 送信に失敗したカテゴリは通知済みマークをスキップし、次回 `/notify` で再送される。パイプライン例外時は Slack にエラーアラートが飛ぶ。設定ロード失敗（feeds/config 空）は「成功・0件」ではなくエラーになる。
- **dedup**: 既存URLとの照合は**全件スキャン**（url 列のみ・数MB規模でコスト無視できる）。過去に直近90日窓にしたところ、RSSに90日超の記事を残すフィードで窓落ち記事が再収集され重複通知が発生したため窓は使わない。同一実行内の重複（同じURLが複数フィードに載る）も排除する。収集URLは `utm_*`・`fbclid` 等のトラッキングパラメータと fragment を除去して正規化してから article_id を計算する。通知クエリ（`get_unnotified_summaries`）は summaries・raw_articles の両側を article_id ごとに1行へ絞り、raw 重複行による通知の増幅を防ぐ。
- **スコアリングのパーソナライズ**: `/collect` `/recalculate` `/resummarize` は開始時に favorites × summaries からタグ頻度上位N個（`general/personalize_top_tags`、既定5・0で無効）を取得し、採点基準の加点ヒントとして追記する（`bq_client.get_favorite_tag_counts`）。出現2回以上のタグのみ対象（偶発タグへの過適合防止）。タグは英語・小文字・スペース区切りで生成・保存する（プロンプト指示＋`summarizer._normalize_tag` による保存前の機械正規化）。既存データは 2026-07-21 に `scripts/backfill_english_tags.py` で英語統一済み。集計クエリ側にも同じ正規化を安全網として残している。keywords シート同様「ヒント入力」の変化なので `SCORING_VERSION` は上げない。タグ取得失敗時は空リストで続行（パーソナライズなしにフォールバック）。
- **要約漏れの復旧（/resummarize）**: 本文取得は成功したが要約に失敗した記事（クレジット枯渇・API障害など）は `content_status='ok'`・`content` ありで残るが `summaries` が無く、pending でもないため自動リトライされない。`POST /resummarize` はこの orphan（`ok`＋本文あり＋summaries無し）を古い順に再要約する手動バッチ。閾値超えは `summaries` に保存し通常の未通知フローで通知、閾値未満は `content_status='summarized'`（終端）にマークして以降の対象外にする（冪等）。1回 `resummarize_limit`（既定50）件・直近 `resummarize_days`（既定7）日を対象。既定の窓から外れた古い orphan をまとめて処理したいときは body で上書きできる（`curl -X POST .../resummarize -H 'Content-Type: application/json' -d '{"days":120,"limit":100}'`）。設定シートは触らず、その実行にだけ効く。`notified=0` かつ `error_count=0` になるまで数回叩く（0件でも `error_count>0` なら失敗しているだけで orphan は残っている）。

### 環境変数（news_pipeline/.env）

| 変数 | 説明 |
|------|------|
| `GCP_PROJECT_ID` | GCPプロジェクトID |
| `ANTHROPIC_API_KEY` | Claude APIキー |
| `TYPESAFE_API_KEY` | TypeSafe（Jev）APIキー。関連度判定に使う |
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
- **note_tags シート**: `tag | category | block_users` の3列。note のハッシュタグ経路の収集対象（feeds シートは RSS 専用のまま分けている）。
  - `tag`: ハッシュタグ（`#` は付けても付けなくてもよい）。
  - `category` / `block_users`: feeds シートと同じ意味。source 名 `note #<tag>` をキーに `config_loader._merge_note_tags` が feeds の category・ブロック設定へ合流させるので、通知時の分類・ブロックも同じ仕組みで効く（feeds 側に同名 source があれば feeds 優先）。`block_users` には note の urlname を書く（照合位置は `path1` 固定）。
  - シートが無い・空なら note のタグ経路が無いだけで、RSS の収集は通常どおり動く。
- **settings シート**: `group | key | value` の3列（namespace 方式）。`group` の出現順が通知順になる。
  - `general / max_summarize`: 1実行で要約する最大件数（繰り越し pending ＋ 新着の合算バジェット）
  - `general / importance_threshold`: summaries に残す importance_score の下限（未設定は 0.65）
  - `general / relevance_threshold`: データ基盤との関連度（Jev の確率）の下限（未設定は 0.2）。対象外は 0.05 前後、対象は 0.9 以上に分かれ、境界の記事だけが中間に来る。緩めたい場合はこの値を下げる（再採点は不要）
  - `general / max_content_retries`: 本文取得の最大リトライ回数（未設定は 3）
  - `general / slide_prefilter_threshold`: Speaker Deck の PDF を取得する前の関連度フィルタ下限（未設定は 0.1）。低いほど通しやすい。title だけの判定は本文ありより低く出るため `relevance_threshold` より下げている（`filtered` は終端で再取得されない）
  - `general / note_lookback_days`: note のタグ経路で何日前の記事まで遡るか（未設定は 2）。1日1回の実行に1日分の重なりを持たせている（重複は dedup で除く）
  - `general / note_max_pages`: タグ1つあたりの最大ページ数（未設定は 3、1ページ50件）。止める条件が機能しない場合の上限
  - `general / note_prefilter_threshold`: note のタグ経路の1次フィルタ下限（未設定は 0.1）
  - `general / personalize_top_tags`: お気に入り記事のタグ頻度上位N個を採点の加点ヒントに使う（未設定は 5、`0` で無効）
  - `general / batch_budget_usd`: 1回のバッチ（/recalculate・/resummarize）で使う API コストの上限（$）。未設定・0 で無制限。超えるとその時点で停止する
  - `general / recalculate_limit`: 1回の /recalculate で再採点する最大件数（未設定は 50）
  - `general / resummarize_limit`: 1回の /resummarize で再要約する最大件数（未設定は 50）
  - `general / resummarize_days`: /resummarize が対象とする収集日ウィンドウ（未設定は 7）
  - `<category> / max_notify`: そのカテゴリの通知件数上限（未設定は5）
  - `<category> / label`: Slack 通知のヘッダー表示名（未設定はカテゴリ名、`other` は `📰 その他`）

通知は feeds（と note_tags）の `category` ごとに独立した Slack メッセージとして送られる。カテゴリの追加・削除・件数変更は feeds/settings シートの編集だけで完結する。