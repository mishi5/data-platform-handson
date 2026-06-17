# 特定ユーザー（著者）ブロック機能 設計書

作成日: 2026-06-18

## 背景・目的

ニュース収集パイプライン（news_pipeline）で、特定の著者（ユーザー）の記事を
収集・通知の対象から除外したい。設定はコード変更なしで運用できるよう
Google Sheets の `feeds` シートに保持する。

きっかけ: Zenn のトピックフィードに含まれる特定ユーザー（例: `web_benriya`）の
記事をブロックしたいという要望。

## 方針

- **保持先**: 既存の `feeds` シートに列を追加（フィード＝サイトと同じ行で管理）。
- **マッチ方式**: 記事URLから抽出したユーザー識別子と、設定値の **完全一致**。
  部分一致は `sat` が `satoru_takeuchi` に誤マッチするため採用しない。
- **抽出位置**: デフォルトは「パス第1セグメント」。サブドメイン型など例外サイトは
  シートの列で抽出位置を指定する（抽出方法の実装はコード、どの位置を使うかはシート）。
- **適用範囲**: 収集時（RSS取得直後・コスト節約）と通知時（保存済み記事の除外）の両方。

## データ保持（feeds シート）

列構成: `URL | source | category | block_users | user_location`（4・5列目を追加）

- **`block_users`**（4列目）: カンマ区切りのブロック対象ユーザー識別子。完全一致で照合。
  空欄ならブロックなし。
- **`user_location`**（5列目）: `block_users` をURLのどこと照合するか。

| user_location の値 | 抽出位置 | 対象サイト例 |
|---|---|---|
| （空欄）/ `path1` | パス第1セグメント | Zenn `zenn.dev/<user>/...`、Qiita、note |
| `subdomain` | ホスト名の先頭ラベル | はてなブログ `<user>.hatenablog.com` |
| `path2` / `path3` … | パスの N 番目セグメント | 第1がカテゴリ等で第2が著者のサイト |

設定例:

| URL | source | category | block_users | user_location |
|---|---|---|---|---|
| `https://zenn.dev/topics/bigquery/feed` | Zenn BigQuery | bigquery | `web_benriya,spammer` | （空欄） |

`zenn.dev/web_benriya/articles/...` は第1セグメントが `web_benriya` に完全一致するので除外。
`web_benriya2` は別ユーザー扱いで誤ブロックされない。

## コンポーネント設計

### 1. `config_loader.py`

`_load_feed_blocks(spreadsheet) -> dict[str, dict]` を追加。

返り値の形: `{source: {"users": set[str], "location": str}}`
- `feeds` シートの4列目をカンマ分割・trim・空要素除去して `users`。
- 5列目を trim して `location`（空欄は `"path1"` 扱い）。
- `users` が空の行は登録しない。
- シートが無い／列が足りない場合は安全側（空 dict）。既存 `_load_*` と同パターン。

`load_config()` の返り値に `"feed_blocks"` キーを追加。

### 2. 新規 `blocklist.py`

純粋関数2つ（単一責務・テスト容易）。

- `extract_user(url: str, location: str) -> str | None`
  - `urlparse(url)` で hostname と path を取得。
  - `location` が空 / `path1` → パス第1セグメント。
  - `subdomain` → hostname の先頭ラベル（`split(".")[0]`）。
  - `pathN`（`path2`,`path3`…）→ パスの N 番目セグメント（1始まり）。
  - 該当セグメントが無ければ `None`。
- `is_blocked(url: str, users: set[str], location: str) -> bool`
  - `extract_user(url, location)` の結果が `users` に含まれれば `True`。
  - `users` が空、または抽出結果が `None` なら `False`。

### 3. `main.py`

- `_run_collect`: `feed_blocks = config.get("feed_blocks", {})` を読み、
  `fetch_articles` 直後に各記事を `feed_blocks.get(a["source"])` でフィルタ。
  除外件数をログ出力。フィルタ後の `articles` で以降の処理（dedup・本文取得・要約）。
- `_run_notify`: `feed_blocks` を読み、`get_unnotified_summaries()` 直後に
  各サマリー（`s["url"]`, `s["source"]`）でフィルタ。除外件数をログ出力。

source に対応する設定が無い記事はブロックしない（通常どおり処理）。

## データフロー

```
collect: RSS取得 → [block filter] → dedup → 本文取得 → 要約 → summaries保存
notify:  unnotified取得 → [block filter] → カテゴリ別通知
```

## エラーハンドリング

- Sheets 読み込み失敗時は `feed_blocks` 空＝何もブロックしない（安全側、既存方針踏襲）。
- `user_location` に未知の値が入った場合は `extract_user` が `None` を返し、
  そのフィードでは実質ブロックされない（誤動作はしない）。

## テスト（tests/、モック完結・BigQuery不要）

- `extract_user`: path1（空欄/`path1`）、`subdomain`、`path2`、該当セグメント無し→`None`。
- `is_blocked`: 完全一致でブロック／非一致（`web_benriya2`）／空 `users`／抽出 `None`。
- `_load_feed_blocks`: 4・5列のパース、`block_users` 空欄、空白 trim、location 空欄→`path1`。

## ドキュメント

CLAUDE.md「Google Sheets 設定」の feeds 説明に `block_users`・`user_location` 列と
上記対応表を追記。以下を明記する:
- マッチは「抽出した識別子の完全一致」。
- 未対応サイトは `user_location` で抽出位置を指定すれば対応可能。
- 指定しても一致しなければ無視されるだけで無害。

## やらないこと（YAGNI）

- 正規表現マッチや部分一致。
- ブロック対象を BigQuery テーブルや専用シートで管理すること。
- ブロックした記事の監査ログ保存（ログ出力のみ）。
