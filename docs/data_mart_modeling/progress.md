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
- 03 再レビュー: 17件 ADDRESSED、新規 Critical 1（dim_member_daily テストが require_partition_filter で落ちる）+ Important 1 → 修正ラウンド 2/3 送付
- 06 再レビュー: 13件 ADDRESSED、新規 Important 1（ARRAY 対案が dim_member を作り直して畳み込みを落とす）→ 修正ラウンド 2/3 送付。Ruling: 対案は ref('dim_member') を参照し dim_member_with_desired と命名
- 09 執筆完了（DONE_WITH_CONCERNS）。Ruling: references に dbt incremental-strategy / microbatch を追加、fct_scout の物理設計（partition sent_date / cluster scout_sender_key, member_key）を正典に明記、検証用一時表は正典外で可、ブリーフの dbt.partition_range は実在しないため置換を是認 → レビュー起動
- 2026-09-08 09:45 頃 2度目のレート制限（resets 14:00）。20:41 再開。状態: 06 ラウンド2 完了（HTML/report とも）、03 ラウンド2 は着手直後（3行差分・report 未追記）、07 再レビュー REVISE（新規 Critical 1: モデル単位 +where は効かない / Important 1 / Minor 3）、08・09 レビュー未着手、10 は HTML 完成・report 無し
- 06: complete（ラウンド2 N-1 を grep で確認: ref('dim_member') 参照・dim_member_with_desired・svg 0 errors。Ruling: 再々レビュー省略）
- 20:45 再開バッチ: 03 ラウンド2 再開（resume）/ 07 ラウンド2（resume）/ 08・09・10 レビュー（fresh）を起動
- 03: complete（ラウンド2: テスト config.where / 想定規模 / +where 非伝播の注記 を grep で確認。Ruling: 再々レビュー省略）
- 07: complete（ラウンド2: テスト config.where / dbt_project.yml data_tests の +where は正しい用法 / §8 圧縮 を確認。Ruling: 再々レビュー省略。Fowler 一次資料未読は report に明記＝二次要約依拠として parked）
- 09 レビュー REVISE（important=4 minor=7。cluster_by 正典差 / FDE 要約の取り違え / 検算 / 原典の歪み）→ 修正ラウンド 1/3 送付
- 09 修正ラウンド1 完了（11件 FIXED）→ 再レビュー起動
- 08 レビュー REVISE（critical=2 important=3 minor=8。MV 制約の事実誤認 / 手元基盤の記述の事実誤認 / 演習の窓）→ 修正ラウンド 1/3 送付
- 10 レビュー REVISE（critical=2 important=3 minor=11）→ 修正ラウンド 1/3 送付。Ruling: audit_key() は 10 回が正本（引数=値、quality_flag 3値、loaded_at=run_started_at、source_system='src_careervoice'）。03 回 §5(e) の下書き定義は横断レビュー後の修正ウェーブで 10 回に揃える（TODO）
- 09 再レビュー: 11件 ADDRESSED、新規 Important 1（AVG の検算）→ 修正ラウンド 2/3 送付
- 08 修正ラウンド1 完了（13件 FIXED。執筆者が bq query で SQL を実行確認したと報告）→ 再レビュー起動
- 09: complete（ラウンド2 N1 を grep で確認。Ruling: 再々レビュー省略）
- 10 修正ラウンド1 完了（16件 FIXED、report 新規作成）。Ruling: references の dbt structure URL を実在する 1-guide-overview に訂正、model versions / source freshness の URL 追加、dim_audit の quality_flag 値域・source_system・loaded_at を正典に明記。各ファクトの DATE 列名は規約（<role>_date）から導出可能なので個別列挙はしない → 再レビュー起動
- 08 再レビュー: 13件 ADDRESSED、新規 Critical 1（公式に無い英文引用）+ Important 1（置換手順の粒度混在）+ Minor 4 → 修正ラウンド 2/3 送付
- 10: complete（再レビュー APPROVE、16/16 addressed）
- 08: complete（ラウンド2 N-1〜N-6 を grep で確認: 創作引用 0 件、URL 全て references 内。Ruling: 再々レビュー省略）
- 全11本 完了。次: 横断レビュー（一貫性）→ 修正ウェーブ（03 §5(e) audit_key の 10 回への整合を含む）→ Playwright 目視 → publish --dry-run
- 横断レビュー起動（ダイジェスト review/_digest.md を自動生成して渡した）。全11本 <title> 形式一致、check_svg 全て 0 errors を確認済み

## 一時中断（2026-09-08 夜、ユーザー指示）

**状態**: 全11本の執筆・個別レビュー・修正が完了。横断レビューは起動直後に停止（成果物なし。`review/cross_review.md` は未作成）。

**再開手順**（次のセッションで）:
1. `docs/data_mart_modeling/progress.md`（このファイル）と `canon/plan.md` を読む
2. 横断レビューを再起動: 横断レビュー用のプロンプトは本ファイル末尾「横断レビューの依頼文」を再利用。入力は `canon/domain.md` / `canon/style.md` / `canon/plan.md` / `review/_digest.md`（自動抽出ダイジェスト。HTML を変えたら `_digest.md` を再生成する — 生成スクリプトは git log `横断レビュー用ダイジェストを追加` のコミット時の Bash 履歴には残っていないため、必要なら同等の抽出を書き直す: 各 HTML の p.meta / h2 / 正典外モデル名 / 「NN 回」参照 / サンプル ID / 規約キーワード出現数）
3. 横断レビューの指摘 + 既知の TODO を1つの修正ウェーブ（1エージェント）で処理:
   - **既知 TODO**: `html/03_dimensions.html` §5(e) の `audit_key()` 下書き定義を 10 回の正本（引数=値、`quality_flag` は `ok`/`estimated`/`suspect`、`loaded_at`=`run_started_at`、`source_system`=`'src_careervoice'`）に揃える。または「下書き。正本は 10 回」と明記して差分を注記
4. 修正後に `python3 ~/.claude/skills/svg-diagram/scripts/check_svg.py html/*.html` を全本 0 errors に
5. Playwright でライト/ダーク両方をレンダリングして目視（news-digest SKILL.md 手順7のスクリプトを `digest.html` → 各 HTML に読み替え）
6. `cd news_pipeline && uv run python scripts/digest/publish.py --html ../docs/data_mart_modeling/html/NN_*.html --title "<title の文字列>" --dry-run` を11本分。**公開（--dry-run なし）はユーザーの指示があるまで実行しない**。公開単位（1本ずつ／一括）も未確認
7. 公開後は family-share の URL を `progress.md` に記録

**モデル**: 執筆・レビューとも opus。レート制限に2回当たった（session limit）。同時実行は 5 本程度に抑える

**横断レビューの依頼文**（再利用用）:
- 00 の全11回一覧が各 `<title>` と一致するか
- 「NN 回で扱う」参照の参照先が実際にその論点を扱っているか
- 裁定済み規約（正典 §4・§6）: SCD2 SK は INT64 FARM_FINGERPRINT で 5 本／未知値 -1（STRING は '-1'）／fct_review は member_key を持たない／M001 の dim_member は 2 行／agency_key と agent_key の持ち方／DATE パーティション列／テスト where は各テストの config か dbt_project.yml data_tests 配下／audit_key() は 10 回が正本／agg_* は audit_key なし／dim_audit.quality_flag の値域
- サンプル ID の事実（S003, C002 5/1, M001 6/15・8/1, P001, K001）の回間一致
- 正典外モデル名（`review/_digest.md` 末尾）が「演習内提案／対案／他プロジェクト例／手元基盤の実名」と明示されているか
- p.meta・参照文献節・.table-wrap の有無
- 22:20 再開。横断レビュー起動。Playwright でライト/ダーク全11本レンダリング（横スクロール無し）、図7枚をコンタクトシートで目視 → 破綻なし（review/shots/）
- 横断レビュー REVISE（critical=3 important=4 minor=7）。Ruling: C1 は 01 が正（R001 は差し戻し1回・3遷移）→ 正典 §5 に固定、10 を直す／C2 は 01 の定義（判定回数=2）が正 → 00 を直す／C3 は 07 が正（star 正本に require_partition_filter を付けない）→ 10 を直し、materialization は incremental+insert_overwrite に統一（正典に明記）／I1 STRING キーは '-1' に機械置換／I4 は data_tests: に統一（正典に明記）／M1〜M7 も同じ修正ウェーブで処理（M3 = 03 audit_key 下書きの整合）
- 横断修正ウェーブ完了（14件 FIXED）。check_svg 全本 0 errors、data_tests: 統一、10 の require_partition_filter 除去、03 audit_key 整合を grep で確認。Ruling: 横断再レビューは省略（局所修正のみ・grep 検証済み）
- publish.py --dry-run 11本すべて rc=0（新規アップロード・タイトル重複なし・Slack なし）。**公開はユーザー指示待ち**

## Rulings（一覧・公開前に確認用）
progress.md 内の `Ruling:` 行を参照。主要なもの: dim_agency 追加 / dim_member_daily 追加 / SCD2 SK は INT64 FARM_FINGERPRINT で 5 本 / M001 の dim_member は 2 行 / R001 差し戻し1回 / fct_scout は incremental+insert_overwrite・star 側に require_partition_filter なし / audit_key() は 10 回が正本 / agg_* は audit_key なし / 再々レビューは局所修正のみの場合 grep 検証で省略

## 公開（2026-09-08）

タイトルを `DMnn <題> — データマート設計` に変更、タグ `Doc/データモデリング`、Slack はシリーズで1通。

| タイトル | URL | content_id |
|---|---|---|
| DM00 題材と簡易データモデル — データマート設計 | https://family-share-76mm33owba-an.a.run.app/view/01M20MVCZ8V6WXSJ66TMD2CYGX | `01M20MVCZ8V6WXSJ66TMD2CYGX` |
| DM01 粒度を宣言する — データマート設計 | https://family-share-76mm33owba-an.a.run.app/view/01M20MVEKJ8X8VNQXM0N3PZ4QP | `01M20MVEKJ8X8VNQXM0N3PZ4QP` |
| DM02 ファクトの3型とファクトレス — データマート設計 | https://family-share-76mm33owba-an.a.run.app/view/01M20MVG19D0J9NGM5609M0MNH | `01M20MVG19D0J9NGM5609M0MNH` |
| DM03 ディメンションの設計 — データマート設計 | https://family-share-76mm33owba-an.a.run.app/view/01M20MVHG8SBGVVPVAD2Q4HDKY | `01M20MVHG8SBGVVPVAD2Q4HDKY` |
| DM04 加法性と派生指標 — データマート設計 | https://family-share-76mm33owba-an.a.run.app/view/01M20MVJX3BSB0KK9DCA48C2T3 | `01M20MVJX3BSB0KK9DCA48C2T3` |
| DM05 履歴を持つ：SCD とスナップショット — データマート設計 | https://family-share-76mm33owba-an.a.run.app/view/01M20MVM7NQBWT49VN9PXT9TQE | `01M20MVM7NQBWT49VN9PXT9TQE` |
| DM06 多対多・不揃い階層・異種ディメンション — データマート設計 | https://family-share-76mm33owba-an.a.run.app/view/01M20MVNYTYZS2WD4YYV1MPSPK | `01M20MVNYTYZS2WD4YYV1MPSPK` |
| DM07 star か One Big Table か — データマート設計 | https://family-share-76mm33owba-an.a.run.app/view/01M20MVQD5116BKKKCMZ4ABPKR | `01M20MVQD5116BKKKCMZ4ABPKR` |
| DM08 コンフォームドとドリルアクロス — データマート設計 | https://family-share-76mm33owba-an.a.run.app/view/01M20MVRT0VVAVK15P7WXKYKXG | `01M20MVRT0VVAVK15P7WXKYKXG` |
| DM09 増分・遅延到着・冪等性 — データマート設計 | https://family-share-76mm33owba-an.a.run.app/view/01M20MVT2ZS15346QW3P5D2B0Z | `01M20MVT2ZS15346QW3P5D2B0Z` |
| DM10 レイヤ・命名・契約・テスト・監査 — データマート設計 | https://family-share-76mm33owba-an.a.run.app/view/01M20MVVG25GSAGBX819GZJJTP | `01M20MVVG25GSAGBX819GZJJTP` |

上書きは `publish.py --html <file> --title <title> --content-id <id>`（--slack なし）。
- 2026-09-09 DLP 追記: DMBOK07 §3 に Sensitive Data Protection の節、DM03 §1 に k-匿名性の計測、DM10 演習(c) に再識別リスクの監査を追記して上書き公開（--slack なし）。DMBOK 17本のタイトルを DMBOKnn 接頭辞に改名
- 2026-09-11 ユーザーレビュー: ID 未説明・『回』・未翻訳語・AI 的語彙・他資料依存 → style.md に読みやすさ規約を追加し、全11本を書き直し（rewrite_prompt.md、4本ずつ並列）
- DM00 書き直し完了（禁止語 0、ID 表 OK）。DM04 起動
- DM01 書き直し完了。DM05 起動
- DM02 書き直し完了。DM06 起動
- DM03 書き直し完了。DM07 起動（注: 私の途中コミットが並行作業中のファイルを巻き込むことがある。最終確認は全本完了後に一括で行う）
- ユーザー補足: 問題は『シリーズ外の資料（domain.md）を前提にしていた』こと。DM00 にサンプル ID 定義表が無かったのが原因（ブリーフ漏れ）。style.md を緩和（シリーズ内参照は DMnn『題名』で可、定着語はカタカナ＋注釈）。DM00 にサンプルデータ表の追加を依頼
- DM00 にサンプルデータ表（18 ID）追加、次元モデ→ディメンショナル修正 完了
- DM04 書き直し完了。DM08 起動
- DM06 書き直し完了（SVG 内キャプション『畳まれる』2件は最終パスで私が直す）。DM09 起動
- DM05 書き直し完了（図中ラベルの as-of join / 畳まれる / 落ちる は最終パスで私が直す）。DM10 起動
- DM07 書き直し完了
- 2026-09-11 DM00〜07 の書き直し版を上書き公開（URL 不変、Slack なし）。図中ラベルの『畳まれる/as-of/効く』を修正、検査スクリプト canon/check_readability.py を追加。DM08〜10 は完了次第公開
- DM09 書き直し完了・上書き公開
- DM08 書き直し完了・上書き公開
- DM10 書き直し完了・上書き公開。全11本の書き直し版が family-share に反映済み（check_readability 全本 OK、01 の 2 件は Kimball 原文引用＋和訳付き）
- 2026-09-12 DM00 のソースモデル表に『説明』列を追加（17 テーブル）、正典 §2 にも追記。上書き公開
- 2026-09-12 表の列幅調整: 全本に td{overflow-wrap:anywhere} th{nowrap}、DM00 ソースモデル表は説明列 min-width 15em・値リストの / に空白、バスマトリクスは型/粒度宣言列に min-width（横スクロールは .table-wrap 内）。全11本を上書き公開
