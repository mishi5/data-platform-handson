# Slack通知に発行日/取得日を表示 設計書

作成日: 2026-06-19

## 背景・目的

Slack のニュース通知メッセージで、各記事の情報の鮮度が分からない。
各記事に発行日（無ければ取得日）を表示して鮮度を把握できるようにする。

## 方針

- 日付は `raw_articles`（`published_at` / `collected_at`）にあり、`summaries` には無い。
  通知時の `get_unnotified_summaries` で raw_articles を JOIN して取得する。
- 表示は **発行日（published_at）優先・無ければ取得日（collected_at）**。
- 表示形式は **絶対日付（YYYY-MM-DD）＋種別ラベル（発行/取得）**、タイムゾーンは **JST**。

## データ取得（bq_client）

`get_unnotified_summaries` の SELECT に raw_articles を LEFT JOIN し、
`published_at` / `collected_at` を加える。

```sql
SELECT s.*, r.published_at, r.collected_at FROM (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY article_id ORDER BY importance_score DESC) AS _rn
  FROM `<proj>.<ds>.summaries`
) s
LEFT JOIN `<proj>.<ds>.notification_log` n ON s.article_id = n.article_id
LEFT JOIN `<proj>.<ds>.raw_articles`     r ON s.article_id = r.article_id
WHERE n.article_id IS NULL AND s._rn = 1
ORDER BY s.importance_score DESC
```

`_rn` は従来どおり返却 dict から除外する。

## 日付フォーマット（notifier.py に純粋関数を追加）

`format_date_label(published_at, collected_at) -> str`

- `published_at` が有効ならそれ、無ければ `collected_at` を採用。
- 採用値を UTC 前提でパースし JST（Asia/Tokyo）に変換、`YYYY-MM-DD` で整形。
- ラベル: published_at 採用なら「発行」、collected_at 採用なら「取得」。
- 両方とも無効（None / 空文字）なら空文字 `""` を返す。
- 入力は `datetime` と ISO 8601 文字列の両方を許容（BQ 列型差異に対応）。
  パースに失敗した値は「無効」とみなす。
- 戻り値例: `🗓 発行: 2026-06-18` / フォールバック時 `🗓 取得: 2026-06-18`。

## 表示位置（notifier._format_blocks）

各記事セクションの「出典」行に併記する。日付ラベルが空なら付けない。

```
*1. 記事タイトル*
要約本文…
_出典: Zenn BigQuery ・ 🗓 発行: 2026-06-18_
```

## エラーハンドリング

- `published_at` / `collected_at` が NULL・空・パース不能でも例外を投げず、
  `format_date_label` は可能な範囲で最良の値（または空文字）を返す。
- JOIN で日付が引けない記事（raw_articles に無い等）も空文字となり、日付行なしで通知される。

## テスト（tests/、モック完結）

`format_date_label` の単体テスト:
- 発行日あり → 「発行」ラベル＋日付。
- 発行日が None/空 → collected_at にフォールバックし「取得」ラベル。
- 両方 None/空 → `""`。
- UTC → JST 変換で日付が繰り上がるケース（例: UTC 2026-06-18T20:00Z → JST 2026-06-19）。
- 入力が `datetime` の場合と ISO 文字列の場合の両方で動作。

## スコープ外（YAGNI）

- お気に入り一覧（`format_favorites_blocks`）・深堀り表示への日付追加。
- 相対表記（「3日前」）や時刻（HH:MM）の表示。
