# Plan 1: 出力フォーマット改善 + 処理ログ保存

ideas: #6 (出力フォーマット調整) + #4 (処理ログ保存)

## 概要

通知の見やすさを改善しつつ、パイプラインの実行状況をBigQueryに蓄積する。
どちらも既存コードへの局所的な追加で完結し、外部依存も増えない。

---

## Part A: 出力フォーマット改善 (#6)

### 現状の課題

`notifier.py` の `_format_message()` は以下の形式で出力している：

```
*1. <url|title>*
summary
_出典: source_
```

- `article_id` が表示されない → 深堀り機能（Plan 2）で `/news-deepdive <article_id>` を使う際に困る
- URLがSlackのリンクとして埋め込まれているためコピーしにくい

### 変更内容

**`notifier.py` の `_format_message()` を修正**

```
*1. title*
summary
_出典: source_ | ID: `abc123` | <url|リンクを開く> | `url` ← コピー用
```

具体的には：
- タイトルとURLを分離（タイトルはプレーンテキスト、URLは別行でコピー可能な形式で表示）
- `article_id` を短縮形（先頭8文字）で表示（Plan 2の `/news-deepdive` で使う前提）
- Slack Block Kit への移行は今回スコープ外（テキスト形式で改善）

### 変更ファイル

- `collector/notifier.py`: `_format_message()` のみ修正

---

## Part B: 処理ログ保存 (#4)

### 概要

パイプラインの各実行結果をBigQueryの `pipeline_logs` テーブルに記録する。
「何件処理した」「エラーは何件」「何回実行した」等を後から分析できるようにする。

### BigQueryテーブル設計

**テーブル名**: `tech_news.pipeline_logs`

| カラム | 型 | 説明 |
|--------|-----|------|
| `run_id` | STRING | UUID（実行ごとのユニークID） |
| `triggered_by` | STRING | `scheduler` / `slack_command` |
| `started_at` | TIMESTAMP | 実行開始時刻 |
| `finished_at` | TIMESTAMP | 実行終了時刻 |
| `articles_fetched` | INT64 | RSS取得件数 |
| `new_articles` | INT64 | dedup後の新着件数 |
| `summaries_generated` | INT64 | 要約生成件数 |
| `notified_count` | INT64 | Slack通知件数 |
| `error_count` | INT64 | 要約失敗件数 |
| `status` | STRING | `success` / `error` |
| `error_message` | STRING | エラー時のメッセージ（NULLABLE） |
| `keywords` | ARRAY<STRING> | 要約時に使用したキーワード一覧 |

### 実装方針

1. `bq_client.py` に `insert_pipeline_log(log: dict)` メソッドを追加
2. `main.py` の `_run_pipeline()` を修正：
   - 実行開始時に `run_id`（UUID）と `started_at` を記録
   - 各ステップの件数を変数に蓄積
   - `config.get("keywords")` で取得したキーワードリストも記録
   - 正常終了・例外どちらでも `finally` で `pipeline_logs` に書き込み

### Terraformでのテーブル追加

- `news_pipeline/infra/bigquery.tf` に `pipeline_logs` テーブルのリソースを追加

### 変更ファイル

- `collector/bq_client.py`: `insert_pipeline_log()` 追加
- `collector/main.py`: `_run_pipeline()` にログ収集ロジック追加
- `infra/bigquery.tf`: `pipeline_logs` テーブル定義追加

---

## テスト方針

- `tests/` 配下の既存テスト構造に倣い、`bq_client` のモックを使ってログ書き込みが呼ばれることを確認
- フォーマット変更は `notifier.py` の `_format_message()` に対するユニットテストで検証

## 実装順序

1. BigQuery テーブル追加（Terraform）
2. `bq_client.py` に `insert_pipeline_log()` 追加
3. `main.py` にログ収集ロジック追加
4. `notifier.py` のフォーマット改善
5. テスト追加・更新
