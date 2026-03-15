# Google Sheets 設定外部化 実装プラン

## 概要

`FEEDS` / `HIGH_PRIORITY_KEYWORDS` / `MAX_ARTICLES` を Google Sheets で管理し、
スマホからセルを編集するだけでデプロイなし即反映できるようにする。

---

## スプレッドシート構成

```
スプレッドシート名: news-pipeline-config
│
├── feeds シート
│    A列: URL
│    B列: Source Name
│    1行目: ヘッダー（URL | Source Name）
│    2行目〜: データ
│
├── keywords シート
│    A列: keyword
│    1行目: ヘッダー（keyword）
│    2行目〜: データ
│
└── settings シート
     A列: key
     B列: value
     1行目: ヘッダー（key | value）
     2行目〜: データ
```

settings シートの内容:

| key | value |
|-----|-------|
| max_articles | 10 |

例（feeds シート）:

| URL | Source Name |
|-----|-------------|
| https://cloud.google.com/feeds/bigquery-release-notes.xml | Google Cloud BigQuery |
| https://www.getdbt.com/blog/rss.xml | dbt Blog |
| https://www.databricks.com/feed | Databricks Blog |
| https://www.snowflake.com/blog/feed/ | Snowflake Blog |
| https://www.infoq.com/data-engineering/rss/ | InfoQ Data Engineering |
| https://zenn.dev/topics/bigquery/feed | Zenn BigQuery |

例（keywords シート）:

| keyword |
|---------|
| bigquery |
| dataform |
| data catalog |
| data lineage |
| data governance |
| data modeling |
| data pipeline |
| data warehouse |
| data lake |
| dbt |
| apache spark |
| apache iceberg |
| data mesh |
| analytics engineering |
| data quality |
| data platform |
| metadata |
| data discovery |
| looker |
| tableau |
| metabase |
| bi tool |
| business intelligence |
| data observability |

---

## 変更ファイル一覧

| ファイル | 変更種別 | 内容 |
|---------|---------|------|
| `news_pipeline/infra/main.tf` | 変更 | `SHEET_ID` env var 追加 |
| `news_pipeline/collector/config_loader.py` | 新規 | Google Sheets から設定を読む |
| `news_pipeline/collector/main.py` | 変更 | 実行時に config をロード・keywords を引数化 |
| `news_pipeline/collector/rss_fetcher.py` | 変更 | `FEEDS` ハードコードを削除 |
| `news_pipeline/collector/requirements.txt` | 変更 | `gspread` 追加 |
| `news_pipeline/.env.example` | 変更 | `SHEET_ID` 追加 |

---

## Step 1: スプレッドシートを作成してSAと共有

1. Google Sheets で `news-pipeline-config` を新規作成
2. `feeds` シートと `keywords` シートを作成してデータを入力
3. Cloud Run のデフォルト SA のメールアドレスを確認:

```bash
gcloud iam service-accounts list --project=$GCP_PROJECT_ID \
  --filter="email:*-compute@*" --format="value(email)"
```

4. スプレッドシートの「共有」→ SA のメールアドレスを **閲覧者** で追加
5. スプレッドシートの URL から `SHEET_ID` を取得:
   `https://docs.google.com/spreadsheets/d/<SHEET_ID>/edit`

---

## Step 2: Terraform — SHEET_ID env var 追加

`news_pipeline/infra/main.tf` の Cloud Run Service の `containers {}` に追加:

```hcl
env {
  name  = "SHEET_ID"
  value = "<your-sheet-id>"
}
```

---

## Step 3: requirements.txt に追加

```
gspread==6.1.4
```

`gspread` は Cloud Run 上で ADC（Application Default Credentials）を自動的に使用するため、
SA キーファイルの管理は不要。

---

## Step 4: config_loader.py を新規作成

`news_pipeline/collector/config_loader.py`:

```python
"""Google Sheets から設定を読み込むモジュール。"""
import logging
import os

import gspread

logger = logging.getLogger(__name__)

SHEET_ID = os.environ.get("SHEET_ID", "")


def load_config() -> dict:
    """Google Sheets から feeds / keywords / settings を読み込む。失敗時は空 dict を返す。"""
    if not SHEET_ID:
        logger.warning("[config_loader] SHEET_ID not set, returning empty config")
        return {}
    try:
        gc = gspread.auth.default(
            scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
        )
        spreadsheet = gc.open_by_key(SHEET_ID)
        feeds = _load_feeds(spreadsheet)
        keywords = _load_keywords(spreadsheet)
        settings = _load_settings(spreadsheet)
        logger.info(
            "[config_loader] loaded %d feeds, %d keywords, settings=%s from Sheets",
            len(feeds), len(keywords), settings,
        )
        return {"feeds": feeds, "keywords": keywords, **settings}
    except Exception as e:
        logger.error("[config_loader] failed to load from Google Sheets: %s", e)
        return {}


def _load_feeds(spreadsheet) -> dict[str, str]:
    """feeds シートを {URL: Source Name} の dict で返す。"""
    try:
        ws = spreadsheet.worksheet("feeds")
        rows = ws.get_all_values()[1:]  # 1行目はヘッダー
        return {row[0]: row[1] for row in rows if len(row) >= 2 and row[0]}
    except Exception as e:
        logger.warning("[config_loader] failed to load feeds sheet: %s", e)
        return {}


def _load_keywords(spreadsheet) -> list[str]:
    """keywords シートをキーワードのリストで返す。"""
    try:
        ws = spreadsheet.worksheet("keywords")
        rows = ws.get_all_values()[1:]  # 1行目はヘッダー
        return [row[0].lower() for row in rows if row and row[0]]
    except Exception as e:
        logger.warning("[config_loader] failed to load keywords sheet: %s", e)
        return []


def _load_settings(spreadsheet) -> dict:
    """settings シートを {key: value} の dict で返す。数値は int 変換。"""
    try:
        ws = spreadsheet.worksheet("settings")
        rows = ws.get_all_values()[1:]  # 1行目はヘッダー
        result = {}
        for row in rows:
            if len(row) >= 2 and row[0]:
                key, val = row[0], row[1]
                try:
                    result[key] = int(val)
                except ValueError:
                    result[key] = val
        return result
    except Exception as e:
        logger.warning("[config_loader] failed to load settings sheet: %s", e)
        return []
```

---

## Step 5: rss_fetcher.py — FEEDS ハードコード削除

モジュールレベルの `FEEDS = {...}` 定数を削除し、`feeds` 引数を必須にする:

```python
def fetch_articles(feeds: dict[str, str]) -> list[dict]:
    """RSSフィードから記事リストを返す。feeds が空の場合は空リストを返す。"""
    if not feeds:
        logger.warning("[rss_fetcher] feeds is empty")
        return []
    results = []
    for feed_url, source_name in feeds.items():
        ...
```

---

## Step 6: main.py — 実行時にコンフィグ読み込み

変更箇所:
- `from config_loader import load_config` を import 追加
- モジュールレベルの `HIGH_PRIORITY_KEYWORDS = [...]` と `MAX_ARTICLES` を削除
- `_run_pipeline()` 先頭で毎回ロード（Sheets を更新→次回実行から即反映）
- `MAX_ARTICLES` は `settings` シートの値を使用（未設定時は 10 件）

```python
from config_loader import load_config

_DEFAULT_MAX_ARTICLES = 10

def _run_pipeline() -> int:
    config = load_config()
    feeds: dict[str, str] = config.get("feeds", {})
    keywords: list[str] = config.get("keywords", [])
    max_articles: int = config.get("max_articles", _DEFAULT_MAX_ARTICLES)

    articles = fetch_articles(feeds)
    ...
    new_articles = new_articles[:max_articles]

    relevant = [a for a in new_articles if _is_relevant(a["title"], a["content"], keywords)]
    ...

def _is_relevant(title: str, content: str, keywords: list[str]) -> bool:
    text = (title + " " + (content or "")).lower()
    return any(kw in text for kw in keywords)
```

モジュールレベルから削除する変数:
- `MAX_ARTICLES = int(os.environ.get("MAX_ARTICLES", 0)) or None`
- `HIGH_PRIORITY_KEYWORDS = [...]`

---

## Step 7: .env.example に追加

```
# Google Sheets の設定スプレッドシート ID（URL の /d/<SHEET_ID>/ 部分）
SHEET_ID=
```

---

## ローカル開発認証

Cloud Run は ADC を自動使用。ローカルでは:

```bash
gcloud auth application-default login
# ブラウザで認証後、~/.config/gcloud/application_default_credentials.json が生成される
```

---

## デプロイ手順（初回）

```bash
# リポジトリルートで実行すること
cd /path/to/data-platform-handson

# 1. スプレッドシートを作成・SA と共有（手動）

# 2. Terraform で SHEET_ID を反映
cd news_pipeline/infra
terraform apply -var="project_id=$GCP_PROJECT_ID"

# 3. Docker ビルド＆プッシュ（リポジトリルートから実行）
cd /path/to/data-platform-handson
docker build --platform linux/amd64 \
  -t asia-northeast1-docker.pkg.dev/$GCP_PROJECT_ID/news-collector/news-collector:latest \
  news_pipeline/collector/
docker push asia-northeast1-docker.pkg.dev/$GCP_PROJECT_ID/news-collector/news-collector:latest

# 4. Cloud Run 更新
gcloud run services update news-collector \
  --image=asia-northeast1-docker.pkg.dev/$GCP_PROJECT_ID/news-collector/news-collector:latest \
  --region=asia-northeast1 --project=$GCP_PROJECT_ID
```

---

## 設定変更時（デプロイ不要）

スマホの Google Sheets アプリでセルを編集するだけ。
次のパイプライン実行（`/news-update` または Scheduler）から即反映。
