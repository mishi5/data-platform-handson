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
- batch2 dispatch: 04, 05, 06, 07 の執筆エージェント（opus）を並列起動。01 のレビュー（opus）起動
- 00 執筆完了（DONE, svg 0 errors）。00 のレビュー（opus）起動
- 03 執筆完了（DONE_WITH_CONCERNS）。Ruling: `dim_date` の役割数はブリーフの「7」ではなく正典 FK 列どおり「8（7マイルストーン + closed）」を正とする／`dim_date.date_label` を正典に追加／STRING キーの未知値は `'-1'` と正典に明記 — 誤りなら 02/05 との表記差が横断レビューで出る
- 02 執筆完了（DONE_WITH_CONCERNS）。Ruling: `dim_agency`（`dim_agent` の縮約ディメンション, Type2）を正典に追加し、`fct_job_posting_daily` と `fct_placement` は `agency_key` を持つ。`fct_placement.agent_key` は scout 経由で解決（無ければ -1）。`current_stage` 初期値 `applied` を正典に明記 — 担当者粒度のディメンションに求人を結ぶと粒度が壊れるため — 誤りなら 06/08/10 で agency の扱いが揺れる（横断レビューで検出）。02 本文の `agent_key=-1` 固定は修正ラウンドで `agency_key` に差し替える
- 01 レビュー REVISE（critical=2 important=5 minor=8）→ 修正ラウンド 1/3 を執筆エージェントに送付
- 04 執筆完了（DONE_WITH_CONCERNS）。Ruling: `agg_company_rating_daily.rating_date`（DATE）と `fee_amount = annual_income × fee_rate` を正典に採用。HLL スケッチ列を持つ新集約表は**追加しない**（正典を増やさない。CTE 内の説明で足りる）。§2(b) の 600→440 の置換はブリーフの意図を保っているので採用
- 07 執筆完了（DONE_WITH_CONCERNS）。Ruling: Fowler 講演の URL を YouTube（Coalesce 2020）に訂正し references.md を更新（discourse スレッドは別議論と注記）。`obt_*` プレフィクスと `obt_scout_funnel` を正典に採用。図の accent 変更（OBT の方がスキャンバイトが多い）はレビューで妥当性を判定させる
- 00 レビュー REVISE（critical=1 important=3 minor=8）→ 修正ラウンド 1/3 を執筆エージェントに送付。04/07 のレビュー起動
- 01 修正ラウンド1 完了（15件 FIXED）。Ruling: `fct_selection_event` / `fct_application_pipeline` に `agency_key` を追加（dim_agency 経由）、`agent_key` はスカウト経由のみ — 01 の I5 で判明した一対多を正典側で解消 — 01 にラウンド2で反映させる
- 2026-09-08 00:29 頃 レート制限（session limit）で 00 修正・01 ラウンド2報告・02/03/04/07 レビュー・05 執筆が途中終了。09:05 再開。状態: 00 HTML は途中修正（report 未追記）、01 は HTML/report ともラウンド2完了、02 レビューは書き上がり REVISE、05 は HTML/report 完了、06 完了
- 05 Ruling: `dim_member_daily` を正典に追加／6/15 の変化は Type4（mini）・8/1 は Type2 と正典 §5 に明記（`dim_member` は 2 行）／`M001.registered_at`=2026-01-05
- 06 Ruling: `S003`（AG02→M002, J001, 6/18）を正典に追加／ブリッジは `dim_member` の全 SCD2 版に展開と明記／supertype/subtype の章は DWT ch.10（brief 06 と references を訂正）／`br_review_tag` は追加しない（演習内の将来提案のまま）
- 09:10 再開バッチ: 00 修正（fresh）/ 02 修正ラウンド1（resume）/ 01 再レビュー / 03 レビュー / 05 レビュー を起動。04/06/07 レビューと 08〜10 執筆は順次
- 00 修正ラウンド1 完了（12件 FIXED）→ 再レビュー起動。04 レビュー起動
- 02 修正ラウンド1 完了（14件 FIXED）→ 再レビュー起動
- 01 再レビュー: 15件 ADDRESSED、新規 Important 2（N1 agency_key の -1 の意味づけ / N2 縮約ディメンションの定義）+ 軽微4 → 修正ラウンド 3/3 送付
- 00: complete（再レビュー APPROVE、12/12 addressed）
- 01: complete（修正ラウンド3 N1〜N6 反映をオーケストレータが grep で確認: -1 文言 / 縮約ディメンション定義 / DT#164 参照 / moderation_rounds 定義 / audit_key コメント。Ruling: 再々レビューは省略 — 6件とも文言修正で SQL 不変のため — 誤りなら横断レビューで検出）
- 02 再レビュー: 14件 ADDRESSED、新規 Important 2（S003 未反映 / パーティション列でないキーで絞るクエリ例）→ 修正ラウンド 2/3 送付
- 05 レビュー REVISE（critical=1 important=7 minor=8。C-1 は dim_member の版数の前提ズレ＝正典裁定と整合させる）→ 修正ラウンド 1/3 送付
- 04 レビュー REVISE（critical=2 important=5 minor=7）→ 修正ラウンド 1/3 送付。Ruling: 04 の DWT 章は ch.1–2（加法性は 3rd ed. の ch.1/2）に訂正可
- 02: complete（修正ラウンド2: N-1/N-2 反映を grep で確認。n-3 は執筆者の理由（直積で水増し）を妥当として parked、n-5 は 05 回へ送付）
- batch3 dispatch: 08, 09 の執筆エージェント（opus）起動。先行回で確定した規約（audit_key / DATE パーティション列 / as-of 半開区間 / 引用の創作禁止）を補足として渡した。10 は次の空きで起動
- 03 レビュー REVISE（critical=1 important=5 minor=11）→ 修正ラウンド 1/3 送付。Ruling: SK は SCD2 の 5 ディメンション（agency 含む）、dim_member_daily はミニの代替でなく併存
- 04 修正ラウンド1 完了（14件 FIXED）→ 再レビュー起動
- 05 修正ラウンド1 完了（16件 FIXED）。Ruling: `dim_company.corporate_number`（Type0）を正典に追加（法人番号は不変の実体キーとして遅延到着ディメンションの照合に使える）→ 再レビュー起動
- 06 レビュー REVISE（critical=2 important=4 minor=7）→ 修正ラウンド 1/3 送付。05 再レビュー起動
- 07 レビュー REVISE（critical=3 important=7 minor=7。Fowler を戻す / Type1 全版更新 / ビュー課金の誤り / 手元基盤の記述の事実誤認）→ 修正ラウンド 1/3 送付。10 執筆起動（audit_key マクロの正本）
- 03 修正ラウンド1 完了（17件 FIXED）。Ruling: 正典 §4 散文の SCD2 を 5 本に訂正、ミニは 15 + 未知行と明記、想定規模を §5 に追加 → 再レビュー起動
- 06 修正ラウンド1 完了（13件 FIXED、4文段落は列挙型として parked）。Ruling: references に BQ 再帰 CTE ドキュメントを追加、`snap_companies`/`snap_agents` は命名規約の具体化として可、BI 側一次情報は追加しない（断定を弱める方針） → 再レビュー起動
- 04 再レビュー: 14件 ADDRESSED、新規 Important 4（MetricFlow legacy 残件 / 半加法の但し書き / 週の定義 / semantic model の一意性）→ 修正ラウンド 2/3 送付
- 05 再レビュー: 16件 ADDRESSED、新規 Important 3（corporate_number 復元 / 遡及生成の誤記述 / member_key の型不一致）→ 修正ラウンド 2/3 送付。Ruling: SCD2 SK の型は INT64（FARM_FINGERPRINT）で統一
- 07 修正ラウンド1 完了（17件 FIXED）。Ruling: obt_page_view は節内仮定として可、int_scout_keyed は規約内 → 再レビュー起動
- 08 執筆完了（DONE）。Ruling: agg_company_entity に dim_company 属性の平坦化と audit_key 不要を明記、dim_scout_sender の sender_id の意味を明記、references に BQ MV を追加。agg_member_entity は正典に入れない（演習内の候補のまま）→ レビュー起動
- 04: complete（修正ラウンド2 N1〜N7 を grep で確認: window_agg 統一 / ISOWEEK / 但し書き削除 / ch.1–2。Ruling: 再々レビュー省略 — 局所修正のみ）
- 05: complete（修正ラウンド2 N-1〜N-3 を grep で確認。Ruling: 再々レビュー省略 — 局所修正のみ）
