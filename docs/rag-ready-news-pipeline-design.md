# Data Engineering News Collection System
## Requirements Document

Version: 0.1
Status: Draft
Purpose: 個人利用の技術ニュース収集・要約・通知システムの要件整理

---

## 1. 背景

データエンジニアリング領域（特に BigQuery 周辺）の技術ニュースを効率的に把握するため、ニュース収集・要約・通知を自動化するシステムを構築する。

従来の AI 通知では以下の問題があった。

- 同一ニュースの重複報告
- URL ハルシネーション
- 記事本文未読の要約
- ノイズ記事混入

これらを解決するため、RSS を中心とした安定したニュース収集基盤を構築する。また将来の拡張として、RAG ベースの技術検索基盤への発展を可能にする。

---

## 2. 目的

1. データエンジニアリング領域の最新記事を自動収集
2. BigQuery 関連ニュースを重点的に抽出
3. 重複ニュースを排除
4. 記事本文を基に要約生成
5. 毎日ユーザーに通知
6. 記事履歴を BigQuery に保存
7. 将来的な RAG 検索基盤への拡張を可能にする

---

## 3. 対象領域

### 高優先度

- BigQuery
- Google Cloud Data Analytics
- Dataform
- データ基盤アーキテクチャ
- データモデリング
- データマネジメント
- Data Catalog / Lineage / Governance

### 中優先度

- dbt
- Databricks
- Snowflake
- ELT / ETL
- データパイプライン
- セマンティックレイヤー

---

## 4. 想定ユーザー

個人のデータエンジニア。利用目的は技術トレンド把握、BigQuery 関連アップデート把握、技術学習、将来的なトレンド分析。

---

## 5. システム概要

```
Cloud Scheduler
      │
      ▼
Cloud Run Collector
      │
      ▼
RSS Fetch
      │
      ▼
Article Parser
      │
      ▼
BigQuery Storage
      │
      ▼
Filtering / Deduplication
      │
      ▼
LLM Summarization
      │
      ▼
Notification
```

---

## 6. 機能要件

### 6.1 ニュース収集

RSSフィードから以下の記事情報を取得する。

取得対象フィード:

- Google Cloud Blog
- BigQuery Release Notes
- dbt Blog
- Databricks Blog
- Snowflake Blog
- InfoQ Data Engineering
- Zenn / Qiita

収集項目: 記事タイトル、URL、公開日時、ソース、記事本文

### 6.2 重複排除

同一 URL の記事は登録しない。判定方法は URL 完全一致（将来的にはタイトル類似度による判定を追加）。

### 6.3 記事本文取得

記事ページから本文を抽出する。目的は LLM 要約の精度向上と RAG 対応。

### 6.4 要約生成

LLM を使用して記事要約を生成する。

- 形式: 箇条書き（技術ポイント中心、3〜5 項目）
- 出力: `summary`、`tags`

### 6.5 通知

- 頻度: 平日 1 回
- 内容: 記事タイトル、要約、URL、ソース
- 件数: 最大 5 件

---

## 7. 非機能要件

| 項目 | 内容 |
|------|------|
| 可用性 | 個人利用のため高可用性不要。許容停止時間 24 時間以内 |
| コスト | 月額数百円以内（Cloud Run / Cloud Scheduler / BigQuery / LLM API） |
| 拡張性 | RAG 検索、トレンド分析、ダッシュボード、GitHub / HackerNews 収集 |

---

## 8. データ要件

### `raw_articles`（記事原文保存）

```
article_id   STRING
title        STRING
url          STRING
source       STRING
published_at TIMESTAMP
collected_at TIMESTAMP
content      STRING
```

### `summaries`（通知用）

```
article_id       STRING
title            STRING
url              STRING
source           STRING
summary          STRING
tags             ARRAY<STRING>
importance_score FLOAT64
```

### `article_chunks`（将来用 / RAG 対応）

```
chunk_id    STRING
article_id  STRING
chunk_text  STRING
embedding   ARRAY<FLOAT64>
```

---

## 9. 外部システム

- Google Cloud Run
- Cloud Scheduler
- BigQuery
- LLM API
- Slack / Email

---

## 10. 処理フロー

```
1.  Scheduler 起動
2.  RSS 取得
3.  URL 抽出
4.  URL 重複チェック
5.  記事本文取得
6.  raw_articles 保存
7.  フィルタリング
8.  LLM 要約
9.  summaries 保存
10. 通知
```

---

## 11. 将来拡張（RAG 検索基盤）

```
raw_articles
      │
      ▼
chunk split
      │
      ▼
embedding 生成
      │
      ▼
vector index
      │
      ▼
semantic search
```

---

## 12. 成功指標

- 重複ニュースがほぼ発生しない
- URL ハルシネーションがない
- 要約精度が高い
- 毎日 3〜5 件の有益記事が届く

---

## 13. 開発フェーズ

| Phase | 内容 |
|-------|------|
| Phase 1 | ニュース収集・本文保存・要約生成・通知 |
| Phase 2 | フィルタリング強化・ランキング・重複排除改善 |
| Phase 3 | RAG 検索・トレンド分析・ダッシュボード |