# 収集の取りこぼし防止（全新着保存＋繰り越し処理）設計書

作成日: 2026-06-21

## 背景・課題

`news_pipeline` の `/collect` は1実行あたり新着を `max_summarize`（本番設定30）件で切り捨てており、超過分は **raw_articles にすら保存されず消滅**していた。

```python
# main.py（現状）
new_articles = [a for a in articles if a["url"] not in existing_urls]
new_articles = new_articles[:max_summarize]   # ← 超過分を破棄
```

一度落ちた記事は次回の RSS フィードから消えていれば二度と収集できない。DevelopersIO のような高頻度フィードが30件枠を圧迫すると、低頻度フィードの記事が取りこぼされるリスクがある。

## ゴール

1. 新着記事は**全件 raw_articles に保存**する（取りこぼしゼロ）。
2. `max_summarize` を超過した分は破棄せず、**次回以降の実行で要約処理**する。
3. 1実行あたりの要約処理量（Claude API 呼び出し）は予測可能に保つ。

## 方針

`max_summarize` を「1実行の要約バジェット（繰り越し＋新着の合算）」と再定義し、**繰り越し（バックログ）を優先消化**する。繰り越しは既存の `content_status='pending'` 機構を再利用する。

### 変更後の `_run_collect` フロー

1. RSS取得 → ブロック除外 → dedup（`existing_urls`）→ `new_articles`（**全件、切り捨てない**）
2. **繰り越し処理を先に**：`get_pending_articles` を古い順・最大 `max_summarize` 件取得 → 本文取得 → 成功分を `to_summarize` へ
3. 残りバジェット `remaining = max(0, max_summarize - len(to_summarize))` を算出
4. 新着を分割：
   - `new_articles[:remaining]` → 今回本文取得＋要約（従来通り `content_status` 判定）
   - `new_articles[remaining:]` → **繰り越し**：`content=None, content_status='pending', retry_count=0` で保存
5. **`new_articles` 全件を raw_articles に保存**（取りこぼしゼロ）
6. 要約生成 → importance_threshold フィルタ → summaries 保存（従来通り）

## 設計上のポイント

- **既存の `pending` 機構を再利用**：繰り越し記事は「本文未取得の pending」として保存され、次回の繰り越し処理パス（ステップ2）が拾う。`pending` は「本文取得失敗」と「バジェット繰り越し」の両方を意味するが、どちらも「本文未取得 → 要処理」で意味が一致する。
- **`retry_count=0` の正当性**：繰り越し記事は本文取得を試行していないため `retry_count=0` が正確。バジェット待ちの間は増えず、実際の取得失敗時のみ増えるので、待機によって誤って `failed` 化しない。
- **FIFO 消化**：`get_pending_articles` に `limit` 引数と `ORDER BY collected_at ASC`（古い順）を追加。古いバックログから先に処理する。
- **バックログ優先**：バジェットが繰り越しで埋まれば新着は全件繰り越しになり、バックログが先に枯れる。

## 影響範囲

- `collector/bq_client.py`：`get_pending_articles(max_retries, limit)` に `limit` 引数と `ORDER BY collected_at ASC` を追加
- `collector/main.py`：`_run_collect` のステップ2〜5を書き換え（バジェット配分・全件保存・繰り越しマーク）
- `tests/`：
  - 新着 > バジェット時に全件 raw_articles に保存され、超過分が `content_status='pending'` でマークされること
  - 繰り越し（pending）がバジェットを消費し、`remaining` に応じて新着処理数が減ること
  - `get_pending_articles` の `limit` 適用

## 非対象（YAGNI）

- `pending` とは別の `deferred` ステータス新設（意味が一致するため不要）
- 繰り越しの優先度づけ（カテゴリ・スコア予測などによる並べ替え）。FIFO で十分。
- 1実行のバジェットを超えるバックログが恒常化した場合の自動スケール（運用で `max_summarize` を調整）
