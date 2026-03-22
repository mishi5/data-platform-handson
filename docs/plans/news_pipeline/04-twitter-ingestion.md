# Plan 4: Twitter/X 情報取り込み機能

idea: #3

## 概要

Twitter/X のキーワード検索や特定アカウントのツイートをRSSと並行して取り込む。
データエンジニアリング界隈のリアルタイムな動向（新ライブラリのリリース告知、障害情報など）
をキャッチするための補完ソースとして活用する。

---

## 前提・制約

### X API アクセスレベル

| レベル | 月額 | 検索API | 制限 |
|--------|------|---------|------|
| Free | $0 | 制限付き（Read: 1req/15min） | ほぼ使えない |
| Basic | $100 | v2 Recent Search | 10,000 reads/月 |
| Pro | $5,000 | v2 Full Archive | 1,000,000 reads/月 |

**Basic（$100/月）が現実的な最低ライン**。実装前にAPIキー取得が必要。

代替案として **Nitter RSS**（非公式）があるが、安定性が低いため本番利用は推奨しない。

---

## 機能仕様

### 対象データ

- **キーワード検索**: `data engineering`, `dbt`, `BigQuery`, `Apache Iceberg` 等
  - キーワードは Google Sheets の既存 `keywords` シートから流用
- **対象ツイートの条件**:
  - 英語 or 日本語
  - like数 >= 50 以上（ノイズ除去）
  - リプライは除外
  - 直近24時間分のみ取得（定期実行の周期に合わせる）

### パイプラインへの統合

既存のRSSパイプラインと並列で実行し、同じ `raw_articles` / `summaries` テーブルに書き込む。

```
RSS取得       → dedup → 本文取得 → 要約 → 通知
Twitter取得  ↗
```

- `source` カラムに `twitter` を設定して識別
- URLは該当ツイートのパーマリンク
- `content` にはツイート本文（+ 引用元があれば引用ツイート本文も）

---

## 実装方針

### 新規ファイル: `collector/twitter_fetcher.py`

```python
def fetch_tweets(keywords: list[str], api_key: str, max_results: int = 20) -> list[dict]:
    """
    X API v2 の Recent Search で直近24時間のツイートを取得する。
    RSS の article 形式に変換して返す。
    返すdict: {article_id, title, url, source, content, published_at}
    """
```

**ライブラリ**: `tweepy`（X API v2 対応）

### article 形式への変換ルール

| ツイートフィールド | articleフィールド | 変換方法 |
|------------------|-----------------|---------|
| `text`（先頭50文字） | `title` | 短縮して使う |
| `text` | `content` | そのまま |
| `id` | `article_id` | `tweet_{id}` |
| ツイートURL | `url` | `https://x.com/i/web/status/{id}` |
| `created_at` | `published_at` | ISOフォーマット |
| `"twitter"` | `source` | 固定値 |

### `main.py` の変更

`_run_pipeline()` の RSS 取得部分を並列化：

```python
# 1. RSS + Twitter を並列取得
import concurrent.futures

with concurrent.futures.ThreadPoolExecutor() as executor:
    rss_future = executor.submit(fetch_articles, feeds)
    twitter_future = executor.submit(fetch_tweets, keywords, TWITTER_BEARER_TOKEN)

    rss_articles = rss_future.result()
    twitter_articles = twitter_future.result(default=[])  # 失敗してもRSSは続行

articles = rss_articles + twitter_articles
```

Twitter取得失敗時もRSSパイプラインは継続する（フォールバック設計）。

### 環境変数追加

| 変数 | 説明 |
|------|------|
| `TWITTER_BEARER_TOKEN` | X API Bearer Token（Basic以上） |

`news_pipeline/.env` と Cloud Run の Secret Manager に追加。

---

## Terraform変更

- `infra/main.tf`: Cloud Run サービスに `TWITTER_BEARER_TOKEN` のSecret追加

---

## 依存パッケージ追加

`collector/requirements.txt` に `tweepy>=4.14` を追加。

---

## 変更ファイル

- `collector/twitter_fetcher.py`: 新規作成
- `collector/main.py`: `_run_pipeline()` にTwitter取得を追加
- `collector/requirements.txt`: `tweepy` 追加
- `infra/main.tf`: Secret 追加
- `news_pipeline/.env.example`（あれば）: `TWITTER_BEARER_TOKEN` 追記

---

## テスト方針

- `twitter_fetcher.py` のユニットテスト（tweepy クライアントをモック）
- `_run_pipeline()` でTwitter失敗時にRSSが続行することの確認

## 実装前の準備作業（手動）

1. X Developer Portal でアプリ作成（Basic プラン契約）
2. Bearer Token の取得
3. GCP Secret Manager に `TWITTER_BEARER_TOKEN` を登録
4. Terraform で Cloud Run にシークレットを紐付け

## 実装順序

1. tweepy のインストール確認・requirements.txt 更新
2. `twitter_fetcher.py` 作成
3. `main.py` に並列取得ロジック追加
4. Terraform で Secret 追加・`gcloud run services update` で再デプロイ
5. テスト追加
