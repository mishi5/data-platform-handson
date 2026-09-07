# SDD ledger — plan: docs/data_mart_modeling/canon/plan.md

## 事前スキャン
- 00 は全11回一覧と domain.md §2/§3/§6 を転載する。01 がバスマトリクス正本、00 は予告 → 重複は意図的（00 は導入）。
- 03 と 05 が両方サロゲートキーに触れる: 03 が「要るか」を決め、05 は「SCD2 で使う」前提で書く（domain.md §4 の注記どおり）。
- 04 と 08 が両方 `agg_company_entity` の平均に触れる: 04 の原則（平均を持たない）を 08 で「窓付き指標は sum/count から算出」と整合させる（brief 08 §5 に明記済み）。
- 07 と 09 が両方 `partition_by` を書く: 07 は物理設計の理由、09 は増分戦略。同じ `fct_scout` の config を使うが矛盾しないよう 09 側が `incremental_strategy` を追加する形。
- Ruling: 執筆エージェントは各回独立ファイルを書くため並列実行する — ファイル競合なし — 誤りなら回間の不整合が横断レビューで出る。

## 進捗
- 2026-09-07 batch1 dispatch: 00, 01, 02, 03 の執筆エージェント（opus）を並列起動
- 01 執筆完了（DONE_WITH_CONCERNS）。Ruling: report の提案 1〜3 を正典に採用（SCD2 列名の統一 / 全ファクト audit_key / パーティション用 `<role>_date` 列）— 以降の回の一貫性のため — 誤りなら 00/02/03 との差異が横断レビューで出る。提案 4（`fct_review_vote`）は演習内に隔離のまま、正典に入れない
