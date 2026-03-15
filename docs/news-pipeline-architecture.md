# News Pipeline — アーキテクチャ・実装対応ドキュメント

## 1. システム全体アーキテクチャ

```mermaid
graph TD
    CS[Cloud Scheduler<br/>平日 7:30 JST<br/>30 22 * * 0-4 UTC]
    SLACK_CMD[Slack スラッシュコマンド<br/>/news-update]
    CR[Cloud Run Service<br/>news-collector<br/>Flask]
    SM[Secret Manager<br/>anthropic-api-key<br/>slack-webhook-url<br/>slack-signing-secret]
    GS[Google Sheets<br/>news-pipeline-config<br/>feeds / keywords / settings]
    RSS[(RSS Feeds<br/>6 ソース)]
    WEB[(記事サイト)]
    BQ_RAW[(BigQuery<br/>tech_news.raw_articles)]
    BQ_SUM[(BigQuery<br/>tech_news.summaries)]
    BQ_CHK[(BigQuery<br/>tech_news.article_chunks<br/>将来用)]
    CLAUDE[Claude API<br/>claude-haiku-4-5]
    SLACK[Slack<br/>Incoming Webhook]

    CS -->|HTTP POST + OAuth| CR
    SLACK_CMD -->|HTTP POST| CR
    SM -->|シークレット注入| CR
    GS -->|gspread / ADC| CR
    CR -->|feedparser| RSS
    CR -->|trafilatura| WEB
    CR -->|insert_rows_json| BQ_RAW
    CR -->|messages.create| CLAUDE
    CR -->|insert_rows_json| BQ_SUM
    CR -->|POST| SLACK
    BQ_RAW -.->|将来: chunk + embedding| BQ_CHK
```

---

## 2. 処理フロー詳細

```mermaid
flowchart TD
    START([Scheduler / /slack 起動]) --> CONFIG[設定読み込み<br/>config_loader.load_config<br/>Google Sheets から feeds/max_summarize]
    CONFIG --> FETCH[RSS フィード取得<br/>rss_fetcher.fetch_articles]
    FETCH --> DEDUP{raw_articles で<br/>URL 重複チェック<br/>bq_client.get_existing_urls}
    DEDUP -->|既存 URL| SKIP([スキップ])
    DEDUP -->|新規 URL あり| LIMIT[max_summarize 件に絞り込み<br/>デフォルト 10 件]
    LIMIT --> PARSE[記事本文取得<br/>article_parser.fetch_content<br/>trafilatura]
    PARSE --> SAVE_RAW[raw_articles 保存<br/>bq_client.insert_raw_articles]
    SAVE_RAW --> SUMMARIZE[LLM 要約<br/>summarizer.summarize_article<br/>claude-haiku-4-5]
    SUMMARIZE -->|失敗| WARN([warning ログ & スキップ])
    SUMMARIZE -->|成功| SCORE{importance_score<br/>>= IMPORTANCE_THRESHOLD<br/>デフォルト 0.5}
    SCORE -->|閾値未満| DROP([破棄])
    SCORE -->|閾値以上| SAVE_SUM[summaries 保存<br/>bq_client.insert_summaries]
    DEDUP -->|新規 URL なし| UNNOTIFIED
    SAVE_SUM --> UNNOTIFIED{未通知サマリー取得<br/>bq_client.get_unnotified_summaries<br/>notified_at IS NULL}
    UNNOTIFIED -->|0 件| NO_NEWS[send_no_news_notification<br/>新着・関連記事なし]
    UNNOTIFIED -->|1 件以上| TOPN[importance_score 降順<br/>上位 MAX_NOTIFY 件を選択<br/>環境変数・デフォルト 5 件]
    TOPN --> NOTIFY[Slack 通知<br/>notifier.send_slack_notification]
    NOTIFY --> MARK[通知済みマーク<br/>bq_client.mark_summaries_notified<br/>notified_at = CURRENT_TIMESTAMP]
    MARK --> END([完了 / JSON レスポンス])
    NO_NEWS --> END
```

---

## 3. コンポーネント構成

```mermaid
graph LR
    subgraph collector["collector/ (Cloud Run コンテナ)"]
        MAIN[main.py<br/>Flask エントリポイント<br/>/ と /slack]
        CFG[config_loader.py<br/>Google Sheets 設定読み込み]
        RSS_F[rss_fetcher.py]
        ART_P[article_parser.py]
        BQ_C[bq_client.py]
        SUM[summarizer.py]
        NOT[notifier.py]
    end

    subgraph infra["infra/ (Terraform)"]
        TF_BQ[bigquery.tf<br/>3 テーブル定義]
        TF_MAIN[main.tf<br/>Cloud Run + Scheduler + IAM<br/>Sheets API 有効化]
        TF_VAR[variables.tf]
    end

    subgraph tests["tests/"]
        T1[test_rss_fetcher.py 4件]
        T2[test_article_parser.py 3件]
        T3[test_bq_client.py 7件]
        T4[test_summarizer.py 2件]
        T5[test_notifier.py 3件]
    end

    MAIN --> CFG
    MAIN --> RSS_F
    MAIN --> ART_P
    MAIN --> BQ_C
    MAIN --> SUM
    MAIN --> NOT
```

---

## 4. データモデルと処理の対応

```mermaid
erDiagram
    raw_articles {
        STRING article_id PK
        STRING title
        STRING url
        STRING source
        TIMESTAMP published_at
        TIMESTAMP collected_at
        STRING content
    }

    summaries {
        STRING article_id PK
        STRING title
        STRING url
        STRING source
        STRING summary
        ARRAY_STRING tags
        FLOAT64 importance_score
        TIMESTAMP notified_at
    }

    article_chunks {
        STRING chunk_id PK
        STRING article_id FK
        STRING chunk_text
        ARRAY_FLOAT64 embedding
    }

    raw_articles ||--o{ summaries : "article_id"
    raw_articles ||--o{ article_chunks : "article_id (将来)"
```

---

## 5. 設計要件と実装の対応表

| 設計要件 | 実装 | ファイル |
|---------|------|---------|
| RSS フィードから記事収集 | `fetch_articles()` / feedparser | `collector/rss_fetcher.py` |
| フィード一覧の外部管理 | Google Sheets feeds シート | `collector/config_loader.py` |
| 重複排除（URL 完全一致・raw_articlesベース） | `get_existing_urls()` → set 差分 | `collector/bq_client.py` |
| 記事本文取得 | `fetch_content()` / trafilatura | `collector/article_parser.py` |
| raw_articles 保存（content 必須） | `insert_raw_articles()` | `collector/bq_client.py` |
| LLM 要約（箇条書き 3〜5 項目） | `summarize_article()` / claude-haiku-4-5 | `collector/summarizer.py` |
| importance_score フィルタ（閾値以上のみ保存） | `IMPORTANCE_THRESHOLD` 環境変数（デフォルト 0.5） | `collector/main.py` |
| summaries 保存 | `insert_summaries()` | `collector/bq_client.py` |
| 未通知サマリー取得 | `get_unnotified_summaries()` / notified_at IS NULL | `collector/bq_client.py` |
| 通知済みマーク | `mark_summaries_notified()` / notified_at 更新 | `collector/bq_client.py` |
| 通知（平日 1 回・最大 MAX_NOTIFY 件） | `send_slack_notification()` + Scheduler | `collector/notifier.py` / `infra/main.tf` |
| ネタ切れ時の通知 | `send_no_news_notification()` | `collector/notifier.py` |
| 記事履歴を BigQuery に保存 | raw_articles / summaries テーブル | `infra/bigquery.tf` |
| RAG 対応（将来） | article_chunks テーブル（空） | `infra/bigquery.tf` |
| 低コスト運用 | Cloud Run Service（cpu_idle=false） + haiku | — |
| Secret 管理 | Secret Manager 経由で ENV 注入 | `infra/main.tf` |
| 手動実行 | Slack スラッシュコマンド `/news-update` | `collector/main.py` |

---

## 6. インフラ構成（Terraform リソース）

```mermaid
graph TD
    subgraph bq["BigQuery (bigquery.tf)"]
        DS[dataset: tech_news]
        T1[table: raw_articles]
        T2[table: summaries]
        T3[table: article_chunks]
        DS --> T1 & T2 & T3
    end

    subgraph gcp["GCP (main.tf)"]
        API[google_project_service<br/>sheets.googleapis.com]
        SVC[Cloud Run V2 Service<br/>news-collector]
        SCH[Cloud Scheduler<br/>30 22 * * 0-4 UTC]
        SA[Service Account<br/>news-pipeline-scheduler]
        IAM1[IAM: roles/run.invoker<br/>scheduler SA]
        IAM2[IAM: roles/run.invoker<br/>allUsers]
        IAM3[IAM: roles/secretmanager.secretAccessor<br/>Compute default SA]
        SCH -->|HTTP POST + OAuth| SVC
        SA --> IAM1 --> SVC
        IAM2 --> SVC
        IAM3 --> SVC
    end
```

---

## 7. 設定管理（Google Sheets）

| シート | 内容 | 変更反映タイミング |
|--------|------|-----------------|
| feeds | RSS フィード URL / ソース名 | 次回パイプライン実行時 |
| settings | max_summarize（デフォルト 10） | 次回パイプライン実行時 |

変更手順：Google Sheets アプリでセルを編集するだけ。デプロイ不要。

環境変数で管理するもの（変更頻度低い・Terraform で設定）：

| 変数 | 用途 | デフォルト |
|------|------|----------|
| `MAX_NOTIFY` | importance_score フィルタ後の通知件数上限 | 5 |
| `IMPORTANCE_THRESHOLD` | summaries 保存・通知対象とする importance_score の閾値 | 0.5 |

---

## 8. 将来の RAG 化パス

```mermaid
flowchart LR
    RAW[(raw_articles<br/>content 保存済み)]
    CHUNK[Chunker<br/>800 tokens]
    EMB[Embedding 生成]
    VI[Vector Index<br/>COSINE 距離]
    SEARCH[VECTOR_SEARCH<br/>top_k=5]

    RAW -->|Phase 3| CHUNK --> EMB --> VI --> SEARCH

    style RAW fill:#d4edda
    style CHUNK fill:#fff3cd
    style EMB fill:#fff3cd
    style VI fill:#fff3cd
    style SEARCH fill:#fff3cd
```

> **緑 = 実装済み**（`content` カラムにデータが蓄積される）
> **黄 = Phase 3 で追加予定**
