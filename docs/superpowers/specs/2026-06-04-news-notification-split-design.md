# ニュース通知のカテゴリ別分割（N分割・動的カテゴリ）設計書

作成日: 2026-06-04

## 目的

news_pipeline の Slack 通知を、記事のソース種別（公式ブログ / ベンダー / 個人ブログ など）で
**カテゴリ別に分割**し、カテゴリごとに独立した Slack メッセージとして通知する。
カテゴリ・件数上限・表示名は **Google Sheets（news-pipeline-config）だけで動的に追加・変更**でき、
コード変更を不要にする。

## 方針（確定事項）

| 項目 | 決定 |
|------|------|
| 分類の情報源 | `feeds` シートに `category` 列（3列目）を追加。値は**任意の文字列**（N分割） |
| category の永続化 | **しない**。通知時に source→category マップで動的に振り分け |
| 通知形式 | カテゴリごとに**独立した** Slack メッセージ（N通） |
| 件数上限・表示名 | `settings` シートを **namespace 3列化**（`group | key | value`）し、group=カテゴリ名で管理 |
| 空欄カテゴリ | `DEFAULT_CATEGORY = "other"`。settings に該当 group が無ければヘッダーは `📰 その他` |
| 通知順序 | `settings` シートで group が最初に登場する行順。未定義カテゴリは後ろにアルファベット順 |

BQ スキーマ変更・`fetch_articles`・`bq_client` は**変更しない**。
変更箇所は `config_loader.py` / `main.py` / `notifier.py` に限定する。

## アーキテクチャ

### feeds シート

| URL (col1) | source (col2) | category (col3, 新規) |
|------------|---------------|-----------------------|
| https://... | Google Cloud Blog | official |
| https://... | 某社テックブログ | vendor |
| https://... | 個人ブログX | personal |
| https://... | 分類なしフィード | （空欄 → other） |

- category は任意の文字列。前後空白を trim し、空欄は `DEFAULT_CATEGORY`（`"other"`）に正規化

### settings シート（namespace 3列化）

| group | key | value | 意味 |
|-------|-----|-------|------|
| general | max_summarize | 10 | 既存の要約上限（汎用設定） |
| official | label | 📢 公式ブログ | Slack ヘッダー表示名 |
| official | max_notify | 5 | このカテゴリの通知件数上限 |
| vendor | label | 🏢 ベンダーブログ | |
| vendor | max_notify | 3 | |
| community | label | 👥 コミュニティ・個人ブログ | |
| community | max_notify | 5 | |

- `label` 未設定 → カテゴリ名（group 文字列）をそのままヘッダーに使用
- `max_notify` 未設定 → `DEFAULT_MAX_NOTIFY`（`5`）
- **カテゴリ追加 = settings に group 行を足すだけ**。コード変更不要

### コンポーネントと変更内容

#### config_loader.py

- `_load_feeds`（`{url: source}` を返す）は**そのまま維持** → `fetch_articles` は無変更
- 新規 `_load_feed_categories(spreadsheet) -> dict[str, str]`
  - feeds シートの `{source(col2): category(col3)}` マップを返す
  - col3 が無い／空欄の行は `""`（呼び出し側で `DEFAULT_CATEGORY` に正規化）
- `_load_settings` を **ネスト dict `{group: {key: typed_value}}` に変更**
  - `group | key | value` の3列を読む（1行目ヘッダーはスキップ）
  - group の**出現順を保持**（dict の挿入順）
  - value は従来通り int 変換可能なら int 化
  - group / key / value のいずれかが欠ける行はスキップ
- `load_config()` の戻り値を変更
  - `{"feeds": ..., "keywords": ..., "feed_categories": ..., "settings": <nested>}`
  - **従来の `**settings` フラット spread は廃止**

#### main.py

- 定数:
  - `DEFAULT_CATEGORY = "other"`
  - `DEFAULT_MAX_NOTIFY = 5`
  - `DEFAULT_OTHER_LABEL = "📰 その他"`（group=other かつ label 未設定時のヘッダー）
  - 既存 `MAX_NOTIFY` 環境変数（廃止）／ `IMPORTANCE_THRESHOLD` は維持
- 既存 `max_summarize` の読み出しを変更:
  - `config.get("max_summarize", _DEFAULT_MAX_SUMMARIZE)`
  - → `config.get("settings", {}).get("general", {}).get("max_summarize", _DEFAULT_MAX_SUMMARIZE)`
- 新規ヘルパ:
  - `_categorize(source, feed_categories) -> str`
    - `feed_categories.get(source, "").strip() or DEFAULT_CATEGORY`
  - `_category_label(category, settings) -> str`
    - `settings.get(category, {}).get("label")`、無ければ category（other の場合は `DEFAULT_OTHER_LABEL`）
  - `_category_limit(category, settings) -> int`
    - `settings.get(category, {}).get("max_notify", DEFAULT_MAX_NOTIFY)`
- `_run_pipeline()` のステップ10〜11を改修:
  1. `feed_categories` と `settings` を config から取得
  2. `unnotified` を `_categorize` でカテゴリ別 dict にグルーピング
  3. 通知順を決定: settings の group 出現順を優先し、settings に無いカテゴリはその後ろにアルファベット順
  4. 各カテゴリを importance_score 降順ソート → `_category_limit` 件で絞る
  5. **非空カテゴリだけ** 1メッセージずつ
     `send_slack_notification(top, SLACK_WEBHOOK_URL, header=_category_label(cat, settings))`
  6. **全カテゴリ空** → 現状通り `send_no_news_notification`
  7. 通知済みマーク: 全カテゴリの通知分 `article_id` の**和集合**を `mark_summaries_notified`
  8. `log["notified_count"]` / 戻り値 = 全カテゴリ合計件数

#### notifier.py

- `_format_blocks(articles, header_text)` … ヘッダー文言を引数化
- `send_slack_notification(articles, webhook_url, header)` … `header` 引数を追加
  - `payload["text"]` も `header` を使用

## データフロー

```
load_config() ──→ feed_categories {source: category}, settings {group: {key: value}}
                          │
get_unnotified_summaries() ──→ unnotified [{source, importance_score, ...}]
                          │
              _categorize(source, feed_categories)   ← 空欄は DEFAULT_CATEGORY
                          │
        グルーピング {category: [summaries...]}
                          │
   通知順 = settings の group 出現順 → 未定義カテゴリはアルファベット順
                          │
   各カテゴリ: sort(importance desc)[:_category_limit] が非空なら
        send_slack_notification(header=_category_label)
                          │
              mark_summaries_notified(全カテゴリの和集合)
```

## エラー処理 / エッジケース

- **あるカテゴリが空**: そのメッセージは送らない（空通知を出さない）
- **全カテゴリ空**: `send_no_news_notification`（現状の挙動を維持）
- **未知の source**（feed_categories に無い）: `DEFAULT_CATEGORY`（other）扱い
- **settings に該当カテゴリ無し**: label=カテゴリ名（other は `📰 その他`）、max_notify=`DEFAULT_MAX_NOTIFY`
- **feed_categories / settings が空**（Sheets 読込失敗時など）: 全件 other カテゴリ1通で送信。例外で落とさない
- **通知済みマーク**: 一部カテゴリの送信が失敗しても、和集合をまとめてマーク（重複通知防止を優先する現行方針を踏襲）

## テスト

- `test_notifier.py`
  - `send_slack_notification` が `header` をヘッダーブロック / `text` に反映すること
  - `_format_blocks` が指定ヘッダーで生成されること
- `_categorize` / `_category_label` / `_category_limit` のユニットテスト
  - 空欄→other、未知 source→other、label/max_notify のフォールバック、大文字小文字の trim
- 通知順序ロジック（settings group 出現順 + 未定義カテゴリのアルファベット順）のテスト
- 既存テストのシグネチャ追従修正（`send_slack_notification` 呼び出し、`load_config`/`_load_settings` のネスト化）

## 環境変数 / ドキュメント

- 環境変数 `MAX_NOTIFY` を廃止（件数上限は settings シートへ移行）
- CLAUDE.md の環境変数表・news_pipeline 設定の記述を更新
  - settings シートが `group | key | value` の3列構成になったこと
  - feeds シートに category 列が増えたこと

## 非対象（YAGNI）

- BQ summaries テーブルへの category 永続化
- カテゴリごとの Slack チャンネル（Webhook）分け
- カテゴリの優先度スコア重み付け（カテゴリ横断の importance 正規化など）
