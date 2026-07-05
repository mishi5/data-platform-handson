# 要約漏れ記事の復旧（/resummarize）設計書

作成日: 2026-07-05

## 背景・課題

2026-07-01〜07-03、Anthropic API のクレジット残高枯渇により `summarize_article` が例外を送出し、`/collect` が「0 relevant summaries」の状態に陥った。

このとき記事は本文取得まで成功して `raw_articles` に `content_status='ok'`・`content` ありで保存されたが、要約が失敗したため `summaries` に行が作られなかった。これらは `'ok'` 扱いのため `get_pending_articles`（`'pending'` のみ対象）に拾われず、**自動リトライされない**。7/1:37, 7/2:36, 7/3:33 件程度が該当（通常の閾値未満記事も一部含む）。

## ゴール

本文はあるのに `summaries` が無い記事（orphan）を再要約し、閾値超えを復旧する手段を提供する。再実行しても無駄な再要約が起きない冪等な設計にする。

## 方針

`/recalculate` と同じ「手動トリガー・バッチ処理」方式の新エンドポイント `/resummarize` を追加する。

### orphan の定義と区別問題

orphan = `content_status='ok'` かつ `content` 非空 かつ `summaries` に行が無い記事。

この集合には次の2種が混在し、データ上は区別できない:
- (a) 障害の巻き添え（要約されなかった）… 復旧したい
- (b) 要約したが `importance_score < importance_threshold` で捨てられた通常記事 … 再処理は無駄

(b) の無限再処理を防ぐため、再要約して閾値未満だった記事は `content_status='summarized'`（終端状態）にマークし、以降の対象から除外して冪等化する。

## データフロー（`_run_resummarize`）

1. `bq.get_unsummarized_articles(days, limit)` で orphan を取得:
   - `content_status='ok'` AND `content IS NOT NULL AND content != ''` AND `summaries` に無い（LEFT JOIN, `s.article_id IS NULL`）
   - `collected_at >= 直近 days 日`、`ORDER BY collected_at ASC`（古い順）、`LIMIT limit`
   - DL無効スライド（`content` NULL）は条件で自動除外
2. 各 orphan を `summarize_article(title, content, keywords)` で再要約:
   - `score >= importance_threshold` → `insert_summaries()`（`scoring_version=SCORING_VERSION`）。`notification_log` 未記録なので次回 `/notify` で通常通り通知される
   - `score < importance_threshold` → `bq.mark_article_summarized(article_id)` で `content_status='summarized'` に更新
   - 要約失敗（None/例外）→ `error_count++`、`'ok'` のまま（次回リトライ）
3. 復旧件数（summaries に挿入した件数）を返す

## 新規コンポーネント

### bq_client
- `get_unsummarized_articles(days, limit) -> list[dict]`:
  ```sql
  SELECT r.article_id, r.title, r.url, r.source, r.content
  FROM raw_articles r
  LEFT JOIN summaries s ON r.article_id = s.article_id
  WHERE r.content_status = 'ok' AND r.content IS NOT NULL AND r.content != ''
    AND s.article_id IS NULL
    AND r.collected_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL @days DAY)
  ORDER BY r.collected_at ASC
  LIMIT @limit
  ```
- `mark_article_summarized(article_id) -> None`: `UPDATE raw_articles SET content_status='summarized' WHERE article_id=@id`。streaming buffer エラーは `update_article_content` 同様に握りつぶす（対象は数日前の記事なので通常は問題なし）。

### main
- `_run_resummarize(triggered_by='manual') -> int`
- `@app.post("/resummarize")` → `asyncio.to_thread(_run_resummarize)` → `PipelineResponse(status, notified=recovered)`

### 設定（settings シート `general`、コード既定値をフォールバック）
- `resummarize_limit`（既定 50）: 1回の処理上限
- `resummarize_days`（既定 7）: 対象収集日ウィンドウ（障害 7/1〜7/3 を包含）

## `content_status='summarized'` の影響

終端状態を新設。既存の参照との整合:
- orphan クエリ（`='ok'` 条件）→ 除外される（意図通り）
- `get_pending_articles`（`='pending'` のみ）→ 無影響
- `get_existing_urls`（全URL）→ 無影響（dedup は維持）
- deepdive / favorites / 通知系は `summaries` を JOIN → 無影響

## 通知の扱い

復旧した summaries は `notification_log` 未記録のため `get_unnotified_summaries` が拾い、次回 `/notify` で Slack 通知される。発行日/取得日ラベル（🗓 発行: 7/1 等）で古さが分かる。ユーザー選択に従い「通常通り通知」。

## テスト

- bq_client:
  - `get_unsummarized_articles`: LEFT JOIN・`s.article_id IS NULL`・`content_status='ok'`・days/limit パラメータ・`ORDER BY collected_at`
  - `mark_article_summarized`: `UPDATE`・`summarized`・対象 article_id
- main（`test_main.py`）:
  - orphan が閾値以上 → `insert_summaries` 呼び出し、`mark_article_summarized` 未呼び出し
  - orphan が閾値未満 → `mark_article_summarized` 呼び出し、`insert_summaries` 未呼び出し（または空）
  - 要約失敗（None）→ どちらも未実行、`error_count` 増

## 運用（デプロイ後）

`POST /resummarize` を `recovered=0`（かつ orphan 枯渇）まで数回実行して 7/1〜7/3 の巻き添えを復旧する。CLAUDE.md に手順を追記。

## 非対象（YAGNI）

- `/collect` 側での閾値未満記事の即時マーク（挿入直後は streaming buffer で UPDATE 不可のため不採用。新規 orphan は次回 `/resummarize` がまとめて処理）
- クレジット枯渇の自動検知アラート（別途の改善提案。本設計には含めない）
- Cloud Scheduler による定期実行（手動運用で足りる）
