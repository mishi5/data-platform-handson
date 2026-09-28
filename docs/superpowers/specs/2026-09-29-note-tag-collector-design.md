# note ハッシュタグ経由の収集（note_fetcher）設計書

作成日: 2026-09-29

## 背景・課題

feeds シートに note.com の RSS が1つも無く、note に投稿されるデータ基盤関連の記事（例: 「Claude Codeで分析エージェントを作って3か月運用した話」）が収集対象に入っていなかった。

note の RSS はユーザー単位（`note.com/<user>/rss`）とハッシュタグ単位（`note.com/hashtag/<tag>/rss`）があるが、どちらも最新25件しか返さない。ハッシュタグ RSS には次の問題がある。

- 流量の多いタグは25件の枠がすぐ入れ替わる（`#ClaudeCode` は約1.5時間、`#データ分析` は約12分）。1日1回の収集では大半を取りこぼす
- タグの意味が衝突する（`#DBT` の約半分は弁証法的行動療法、`#データ分析` は競艇・競馬予想が大半）
- RSS の item にハッシュタグが含まれない

## ゴール

データ基盤関連のハッシュタグに付いた note 記事を、取りこぼさず、かつノイズで要約コストを浪費せずに収集する。

## 調査結果（2026-09-17〜09-27 に実測）

- 非公式 API `GET https://note.com/api/v3/hashtags/{tag}/notes?order=new&page=N` はログイン不要で、1ページ50件を返す。各記事は `key` / `name` / `body`（本文冒頭240字のプレーンテキスト）/ `user.urlname` / `price` / `type` / `publish_at` / `like_count` を持つ。ハッシュタグは含まない
- `order=popular` / `order=hot` は note の読者層での人気順で、技術的な関連度とは無関係（`#データ分析` の hot は「フォロワー7,000人に…」「特別な記念日」等）。スキ数による足切りも同じ理由で採用しない
- 冒頭240字を Jev（`relevance.judge_relevance`）に渡すと明確に分離できる。新着50件あたり 0.5 以上の件数は `#データエンジニアリング` 30件、`#データ分析` 1件、`#ClaudeCode` 0件。競艇・競馬予想は 0.01〜0.10
- note の記事ページは既存の `article_parser.fetch_content`（trafilatura）で本文を取得できる（7,072字を確認）。非公式 API への依存は記事一覧の取得だけに限定できる
- 参考: 「note非公式APIを徹底調査｜2026年版エンドポイント一覧完全版」（note.com/marie_222/n/n6a10366298b0）。著者は規約・robots.txt 上グレーゾーンであり、低頻度・最小限の利用に留めるべきと明記している

## 方針

- **対象タグは流量の少ないものに限る**（初期: `データエンジニアリング` `データ基盤` `dbt` `BigQuery` `Snowflake`）。`#データ分析` `#ClaudeCode` 等の大きいタグは1週間の実測後に判断する
- **タグ AND 絞り込みは採用しない**。一覧 API にタグが無く、突き合わせには両方のタグの全件列挙が必要になる。Jev の単価（入力 $0.042/100万トークン）なら冒頭240字の判定の方が精度・保守性ともに上回る
- **1次フィルタは note のタグ経路にだけかける**。タグ経路は著者を選んでいない流入のため。feeds に登録した RSS（note の著者 RSS を含む）は従来どおり本文を読んでから判断する
- **feeds シートには入れない**。feeds は RSS フィードの一覧という意味を保ち、専用の `note_tags` シートで管理する

## 構成

### note_tags シート

| 列 | 内容 |
|---|---|
| `tag` | ハッシュタグ（`#` なし。付いていても除去する） |
| `category` | 通知カテゴリ。空欄は `other` |
| `block_users` | ブロックする note の urlname（カンマ区切り・完全一致） |

source 名はコードが `note #<tag>` を生成する。照合位置は `path1` 固定（note の URL は常に `note.com/<urlname>/n/<key>`）。

### collector/note_fetcher.py（新規）

```python
def source_name(tag: str) -> str  # "note #<tag>"
def fetch_articles(tags: list[str], lookback_days: int, max_pages: int) -> list[dict]
```

戻り値は `rss_fetcher.fetch_articles` と同じ形の dict（`article_id` / `title` / `url` / `source` / `published_at` / `collected_at` / `description`）に、一時情報 `origin="note_tag"` を加えたもの。

タグごとに page=1 から順に取得し、次のいずれかで止める。
- `publish_at` が `lookback_days` 日より前の記事に到達した
- `is_last_page` が真
- `max_pages` に到達した

変換:
- URL: `https://note.com/{user.urlname}/n/{key}` を `rss_fetcher._normalize_url` に通し、`article_id` も `rss_fetcher._make_article_id` で計算する（RSS 経由の同一記事と dedup で一致させる）
- `description`: `body`（冒頭240字）
- 除外: `price > 0`（有料。trafilatura では無料部分しか取れない）、`type != "TextNote"`（本文が無い投稿）

負荷: リクエスト間に1秒待つ。タイムアウト30秒。User-Agent は既存と同じ。認証が必要なエンドポイントは使わない。

失敗時: タグ単位で例外を捕捉し warning を出して次のタグへ進む（HTTP エラー・JSON 形状の変化・タイムアウト）。ページ途中の失敗はそれまでの取得分を返す。`tags` が空なら何もリクエストしない。

ログ: タグごとに件数・ページ数・除外件数を出す。

### config_loader

- `_load_note_tags(spreadsheet) -> list[dict]` を追加
- `_load_config_once` で `note #<tag>` をキーに `feed_categories` / `feed_blocks` へ合流させる。feeds 側に同名 source があれば feeds を優先する。戻り値に `note_tags: list[str]` を加える
- シートが無い・読めない場合は warning を出して空リスト（既存の `_load_*` と同じ扱い）

source 名の生成は `note_fetcher.source_name` の1か所に置く。収集時と通知時で名前がずれると category とブロックが適用されなくなるため。

### main._run_collect

1. `fetch_articles(feeds)` と `fetch_note_articles(note_tags, …)` を連結する。`articles_fetched` は合計、ログは内訳も出す
2. 2.5 の1次フィルタを一般化する
   - Speaker Deck → `slide_prefilter_threshold`（既存）
   - `origin == "note_tag"` → `note_prefilter_threshold`（新規）
   - それ以外は判定しない
   - 判定不能（None）は通す。弾いた記事は `content_status='filtered'`（終端）で保存する
3. 保存前に `description` と `origin` を除去する

`/notify`・`/recalculate`・`/resummarize` は変更しない。BigQuery スキーマの変更は無い。

### settings シート（新規キー）

| key | 既定 | 理由 |
|---|---|---|
| `general / note_lookback_days` | 2 | 1日1回の実行に1日分の重なりを持たせる。重複は dedup で除く |
| `general / note_max_pages` | 3 | 対象タグは通常1ページで止まる。止める条件が機能しない場合の上限 |
| `general / note_prefilter_threshold` | 0.1 | Speaker Deck と同じ値。対象記事は冒頭240字で 0.57 |

通知カテゴリは `note` を新設する（`note / label = 📝 note`、`note / max_notify = 5`）。`other` の通知枠（10件）と競合させず、効果測定で note 由来を分けるため。

## テスト

- `tests/test_note_fetcher.py`（新規）: RSS と同形への変換、URL・article_id の一致、有料・非 TextNote の除外、3つの停止条件、タグ単位の失敗の隔離、空タグ時の無通信、リクエスト間の sleep
- `tests/test_config_loader.py`: `_load_note_tags` の解析（`#` 除去・空行）、`feed_categories` / `feed_blocks` への合流（`path1`、feeds 優先）、シート欠落時の空リスト
- `tests/test_main.py`: タグ経路の低スコア記事が `filtered` になり本文取得・要約されない、RSS 経由の note 記事には1次フィルタがかからない、保存前に `origin` が除去される
- デプロイ前に本番 API で使い捨ての確認を1回行う（タグごとの件数と Jev の分布）

## 導入手順

1. 実装とテスト
2. `note_tags` シートと settings の `note` カテゴリを追加する
3. `gcloud run services update` でデプロイする（スキーマ変更が無いため `terraform apply` は不要）
4. 翌朝の `/collect` のログと BigQuery（`source LIKE 'note #%'`）で取得・除外・通知件数を確認する
5. 1週間後、大きいタグへ広げるかを実測で判断する
6. CLAUDE.md に仕組み・シート・設定キーを追記する
