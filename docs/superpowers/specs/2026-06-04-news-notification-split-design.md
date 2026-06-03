# ニュース通知の公式/コミュニティ分割 設計書

作成日: 2026-06-04

## 目的

news_pipeline の Slack 通知を、**公式ブログ系**（Google, dbt などベンダー公式）と
**それ以外**（ユーザー企業ブログ・個人ブログ）の2グループに分割し、
それぞれ独立した Slack メッセージとして通知する。

## 方針（確定事項）

| 項目 | 決定 |
|------|------|
| 分類の情報源 | `feeds` Google Sheet に `category` 列（3列目）を追加 |
| category の永続化 | **しない**。通知時に source→category マップで動的に振り分け（変更しやすさ優先） |
| 通知形式 | 2つの**独立した** Slack メッセージ |
| 件数上限 | グループ別の個別上限（`MAX_NOTIFY_OFFICIAL` / `MAX_NOTIFY_COMMUNITY`） |
| 公式判定値 | `category` 列が `official`（大文字小文字無視）→ 公式。空欄・その他 → コミュニティ |
| ヘッダーラベル | 公式: `📢 公式ブログ` / その他: `👥 コミュニティ・個人ブログ` |

BQ スキーマ変更・`fetch_articles`・`bq_client` は**変更しない**。
変更箇所は `config_loader.py` / `main.py` / `notifier.py` に限定する。

## アーキテクチャ

### データ分類（Sheets）

`feeds` シートのレイアウト:

| URL (col1) | Source Name (col2) | category (col3, 新規) |
|------------|--------------------|-----------------------|
| https://... | Google Cloud Blog | official |
| https://... | 個人ブログX | （空欄） |

- `category == "official"`（trim + lower 後）→ 公式グループ
- それ以外（空欄含む）→ コミュニティグループ（デフォルト）

### コンポーネントと変更内容

#### config_loader.py
- `_load_feeds`（`{url: source}` を返す）は**そのまま維持** → `fetch_articles` は無変更
- 新規 `_load_feed_categories(spreadsheet) -> dict[str, str]`
  - feeds シートの2列目(source)→3列目(category) のマップを返す
  - 3列目が無い行は `""`（空文字）
- `load_config()` の戻り dict に `feed_categories` キーを追加

#### main.py
- 新規ヘルパ `_is_official(source: str, categories: dict[str, str]) -> bool`
  - `categories.get(source, "").strip().lower() == "official"`
- 定数の置き換え:
  - `MAX_NOTIFY`（廃止）
  - `MAX_NOTIFY_OFFICIAL = int(os.environ.get("MAX_NOTIFY_OFFICIAL", 5))`
  - `MAX_NOTIFY_COMMUNITY = int(os.environ.get("MAX_NOTIFY_COMMUNITY", 5))`
- `_run_pipeline()` のステップ10〜11を改修:
  1. `config` から `feed_categories` を取得
  2. `unnotified` を `_is_official` で official / community に分割
  3. 各グループを importance_score 降順ソートし、グループ別上限で絞る
     - `official_top = sorted(...)[:MAX_NOTIFY_OFFICIAL]`
     - `community_top = sorted(...)[:MAX_NOTIFY_COMMUNITY]`
  4. official_top が非空 → `send_slack_notification(official_top, SLACK_WEBHOOK_URL, header="📢 公式ブログ")`
  5. community_top が非空 → `send_slack_notification(community_top, SLACK_WEBHOOK_URL, header="👥 コミュニティ・個人ブログ")`
  6. **両方空** → 現状通り `send_no_news_notification`
  7. 通知済みマーク: 両グループの `article_id` の**和集合**を `mark_summaries_notified`
  8. `log["notified_count"]` = 両グループ合計件数 / 戻り値も合計

#### notifier.py
- `_format_blocks(articles, header_text)` … ヘッダー文言を引数化
- `send_slack_notification(articles, webhook_url, header)` … `header` 引数を追加
  - `payload["text"]` も `header` を使用

## データフロー

```
load_config() ──→ feed_categories {source: category}
                          │
get_unnotified_summaries() ──→ unnotified [{source, importance_score, ...}]
                          │
              _is_official(source, feed_categories)
                          │
         ┌────────────────┴────────────────┐
   official グループ                  community グループ
   sort + [:MAX_OFFICIAL]            sort + [:MAX_COMMUNITY]
         │                                  │
  send_slack_notification            send_slack_notification
   (header="📢 公式ブログ")          (header="👥 コミュニティ・個人ブログ")
         └────────────────┬────────────────┘
              mark_summaries_notified(和集合)
```

## エラー処理 / エッジケース

- **片方のグループが空**: そのグループのメッセージは送らない（空通知を出さない）
- **両グループとも空**: `send_no_news_notification`（現状の挙動を維持）
- **未知の source**（feed_categories に無い）: デフォルトでコミュニティ扱い
- **feed_categories が空**（Sheets 読込失敗時など）: 全件コミュニティ扱いで1メッセージ送信。例外で落とさない
- **通知済みマーク**: 片方の送信が成功し片方が失敗しても、和集合をまとめてマークする現行方針を踏襲（重複通知防止を優先）

## テスト

- `test_notifier.py`
  - `send_slack_notification` が `header` をヘッダーブロック / `text` に反映すること
  - `_format_blocks` がグループごとのヘッダーで生成されること
- `_is_official` のユニットテスト（official / 空欄 / 大文字 OFFICIAL / 未知 source）
- 既存テストのシグネチャ追従修正（`send_slack_notification` 呼び出し）

## 環境変数 / ドキュメント

- `MAX_NOTIFY` → `MAX_NOTIFY_OFFICIAL` / `MAX_NOTIFY_COMMUNITY` に置換
- CLAUDE.md の環境変数表を更新

## 非対象（YAGNI）

- BQ summaries テーブルへの category 永続化
- 3グループ以上への分割
- グループごとの Slack チャンネル（Webhook）分け
