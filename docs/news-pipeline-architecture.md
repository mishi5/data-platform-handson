# News Pipeline — アーキテクチャ・実装対応ドキュメント

## 1. システム全体アーキテクチャ

```mermaid
graph TD
    CS[Cloud Scheduler<br/>平日 7:30 JST<br/>30 22 * * 0-4 UTC]
    CR[Cloud Run Job<br/>news-collector]
    SM[Secret Manager<br/>anthropic-api-key<br/>slack-webhook-url]
    RSS[(RSS Feeds<br/>7 ソース)]
    WEB[(記事サイト)]
    BQ_RAW[(BigQuery<br/>tech_news.raw_articles)]
    BQ_SUM[(BigQuery<br/>tech_news.summaries)]
    BQ_CHK[(BigQuery<br/>tech_news.article_chunks<br/>将来用)]
    CLAUDE[Claude API<br/>claude-haiku-4-5]
    SLACK[Slack<br/>Incoming Webhook]

    CS -->|HTTP POST + OAuth| CR
    SM -->|シークレット注入| CR
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
    START([Scheduler 起動]) --> FETCH[RSS フィード取得<br/>rss_fetcher.fetch_articles]
    FETCH --> DEDUP{BigQuery で<br/>URL 重複チェック<br/>bq_client.get_existing_urls}
    DEDUP -->|既存 URL| SKIP([スキップ])
    DEDUP -->|新規 URL| PARSE[記事本文取得<br/>article_parser.fetch_content<br/>trafilatura]
    PARSE --> SAVE_RAW[raw_articles 保存<br/>bq_client.insert_raw_articles]
    SAVE_RAW --> FILTER{キーワードフィルタ<br/>HIGH_PRIORITY_KEYWORDS}
    FILTER -->|非関連| DROP([破棄])
    FILTER -->|関連| SUMMARIZE[LLM 要約<br/>summarizer.summarize_article<br/>claude-haiku-4-5]
    SUMMARIZE -->|失敗| WARN([warning ログ & スキップ])
    SUMMARIZE -->|成功| SAVE_SUM[summaries 保存<br/>bq_client.insert_summaries]
    SAVE_SUM --> SORT[importance_score 降順でソート]
    SORT --> TOP5[上位 5 件を選択]
    TOP5 --> NOTIFY[Slack 通知<br/>notifier.send_slack_notification]
    NOTIFY --> END([完了 / JSON レスポンス])
```

---

## 3. コンポーネント構成

```mermaid
graph LR
    subgraph collector["collector/ (Cloud Run コンテナ)"]
        MAIN[main.py<br/>Flask エントリポイント]
        RSS_F[rss_fetcher.py]
        ART_P[article_parser.py]
        BQ_C[bq_client.py]
        SUM[summarizer.py]
        NOT[notifier.py]
    end

    subgraph infra["infra/ (Terraform)"]
        TF_BQ[bigquery.tf<br/>3 テーブル定義]
        TF_MAIN[main.tf<br/>Cloud Run + Scheduler + IAM]
        TF_VAR[variables.tf]
    end

    subgraph tests["tests/"]
        T1[test_rss_fetcher.py 4件]
        T2[test_article_parser.py 3件]
        T3[test_bq_client.py 3件]
        T4[test_summarizer.py 2件]
        T5[test_notifier.py 3件]
    end

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

| 設計要件（requirements doc） | 実装 | ファイル |
|-------------------------------|------|---------|
| RSS フィードから記事収集 | `fetch_articles()` / feedparser | `collector/rss_fetcher.py` |
| 重複排除（URL 完全一致） | `get_existing_urls()` → set 差分 | `collector/bq_client.py` |
| 記事本文取得 | `fetch_content()` / trafilatura | `collector/article_parser.py` |
| raw_articles 保存（content 必須） | `insert_raw_articles()` | `collector/bq_client.py` |
| キーワードフィルタ（高優先度） | `_is_relevant()` / HIGH_PRIORITY_KEYWORDS | `collector/main.py` |
| LLM 要約（箇条書き 3〜5 項目） | `summarize_article()` / claude-haiku-4-5 | `collector/summarizer.py` |
| summaries 保存 | `insert_summaries()` | `collector/bq_client.py` |
| 通知（平日 1 回・最大 5 件） | `send_slack_notification()` + Scheduler | `collector/notifier.py` / `infra/main.tf` |
| 記事履歴を BigQuery に保存 | raw_articles / summaries テーブル | `infra/bigquery.tf` |
| RAG 対応（将来） | article_chunks テーブル（空） | `infra/bigquery.tf` |
| 低コスト運用 | Cloud Run Job（起動時のみ課金） + haiku | — |
| Secret 管理 | Secret Manager 経由で ENV 注入 | `infra/main.tf` |

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
        JOB[Cloud Run V2 Job<br/>news-collector]
        SCH[Cloud Scheduler<br/>30 22 * * 0-4 UTC]
        SA[Service Account<br/>news-pipeline-scheduler]
        IAM[IAM: roles/run.invoker]
        SCH -->|HTTP POST + OAuth| JOB
        SA --> IAM --> JOB
    end
```

---

## 7. 将来の RAG 化パス

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

> **緑 = Phase 1 で実装済み**（`content` カラムにデータが蓄積される）
> **黄 = Phase 3 で追加予定**

---

## 8. フィルタキーワード一覧

`main.py:21` の `HIGH_PRIORITY_KEYWORDS` で判定。

| 優先度 | キーワード |
|--------|-----------|
| 高（実装済み） | bigquery, dataform, data catalog, data lineage, data governance, google cloud, data modeling |
| 中（Phase 2 追加予定） | dbt, databricks, snowflake, ELT/ETL, データパイプライン, セマンティックレイヤー |
