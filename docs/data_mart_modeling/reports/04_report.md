# 04 加法性と派生指標 — 執筆報告

ファイル: `docs/data_mart_modeling/html/04_additivity.html`

## 完了した節

| 節 | 内容 | ブリーフ必須項目の充足 |
|---|---|---|
| 1. この回が決めること | 加法/半加法/非加法の3分類表 + CareerVoice のメジャー分類表（13行） | ✓ `review_count` 加法、`score_*` 非加法、`scouts_remaining` 半加法、`fee_rate` 非加法、`avg_overall_score` は持たない、を全て収録 |
| 2. どこで壊れるか | (a) 平均の平均（`C002` 3日分、件数 1/1/10 を実計算） (b) `scouts_remaining` の四半期 SUM (c) 日次 `COUNT(DISTINCT member_key)` の週次加算 | ✓ 3例とも数値を検算できる形 |
| 3. Kimball の原則 | 技法6行の表 + Techniques PDF と DT#77 の verbatim 引用 2枠 | ✓ 加法性の定義／期末値・期中平均／分子分母を分けて持つ／パーセンタイル再集約不可 |
| 4. 現代の再解釈 | MetricFlow の ratio metric（`reply_rate = scouts_replied / scouts_sent`）と `non_additive_dimension`（`window_choice: max` = 期末値） | ✓ + 半加法の宣言まで拡張 |
| 5. BigQuery + dbt での実装 | `agg_company_rating_daily` モデル / schema.yml / 月次再集約 / `br_company_hierarchy` 経由のグループ再集約 / `QUALIFY ROW_NUMBER()` の期末値 / `APPROX_QUANTILES` / `HLL_COUNT.INIT`+`MERGE` | ✓ |
| 6. 判断基準 | 「メジャー → 分類 → マートに持つ形 → BI で計算する形」10行 + 列名規約（`avg_`/`rate_`/`pct_`/`median_`/`unique_` 禁止）の運用案 | ✓ |
| 7. 演習 | (a) 企業別・年別の中央値 (b) `SUM(is_open)` = 延べ掲載日数と月末時点の出し方 (c) 送信主体別の返信率の分子分母 | ✓ 3問、`<details>` 内に SQL 付き解答 |
| 8. 参考: 手元の基盤 | `mart_url_performance` の `avg_response_time` / `error_rate_percent` / `unique_visitors`、`percentile()` マクロ、HLL の種 | ✓ 4行、この節にのみ登場（grep で確認済み） |
| 図 | 比較図「平均の平均 vs 和と件数」1枚（ノード6、矢印4、accent 1系統） | ✓ |

## 読んだ文献と引用した要点

- **Kimball Dimensional Modeling Techniques（2013, PDF）** — WebFetch では PDF がテキスト化されなかったため、取得済み PDF を `pdftotext` で抽出して該当箇所を直接読んだ。
  - 引用（§3 の aside、verbatim）: "Semi-additive measures can be summed across some dimensions, but not all; balance amounts are common semi-additive facts because they are additive across all dimensions except time. Finally, some measures are completely non-additive, such as ratios. A good approach for non-additive facts is, where possible, to store the fully additive components of the non-additive measure and sum these components into the final answer set before calculating the final non-additive fact. This final calculation is often done in the BI layer or OLAP cube."
  - Periodic Snapshot Fact Tables: 「粒度は期間でありトランザクションではない」「活動が無くても行が立つので FK が密」→ §3 の表と §2(b) の「行は素直に3行ある」に反映。
  - Aggregate Fact Tables or Cubes: "built solely to accelerate query performance"、原子ファクトと同時に BI へ公開する（aggregate navigation）→ §3 の「性能のためなので原子と答えが一致しなければならない」という論法の根拠。
- **Design Tip #77（Margy Ross, 2006）** — "you can roll up detailed data in unpredictable ways, the converse is not true – you can't magically explode summary data into its underlying components." および "Summary data naturally pre-supposes the typical business questions..." を §3 に引用。§2(c)・§7(a) の「分解不能なメジャーは原子を残すしかない」の論拠に使った。
- **dbt / MetricFlow** — `docs/build/about-metricflow` に加え、YAML を実在の spec に合わせるため `docs/build/ratio`・`docs/build/measures`・`docs/build/simple` も参照した（本文の参照文献リストには `references.md` にある `about-metricflow` のみ掲載）。
  - ratio metric は dbt v1.12+ で `numerator:` / `denominator:` をメトリクス直下に書く形（旧 spec の `type_params:` 配下ではない）。本文はこの v1.12+ 形で統一し、コメントにも明記した。
  - simple metric も v1.12+ では `agg:` / `expr:` を直接持ち、`measures:` は simple metric に置き換えられる方向（docs に deprecation の注記あり）。
  - `non_additive_dimension`（`name` / `window_choice: min|max` / `window_groupings`）が半加法メジャーの宣言そのもの。docs のサンプルは MRR とサブスクリプションで、CareerVoice の `scouts_remaining` にそのまま対応する。

## check_svg の結果

```
python3 ~/.claude/skills/svg-diagram/scripts/check_svg.py docs/data_mart_modeling/html/04_additivity.html
0 errors, 0 warnings
```

初回は `UNWEIGHTED` / `WEIGHTED` のタグがノード内側パディングを割ってエラーになったため、タグを結果ノードの外（真上 8px）へ逃がして解消。

## 正典への変更提案

1. **`agg_company_rating_daily` にパーティション用の DATE 列が無い。** 正典 §4 は「ファクトは主要な日付キーと並べて DATE 型の `<role>_date` を持つ」としているが、この agg のメジャー欄は `date_key` / `company_key` のみ。今回は `dim_date` 結合で月次へ上げる書き方にして DATE 列を使わずに済ませたが、09回（増分・パーティション）で `insert_overwrite` を書く際に必要になる。`agg_company_rating_daily` に `full_date` ではなく `snapshot_date`（または `date`）を1列足すか、agg は例外とするかを決めておきたい。
2. **ユニーク数のスケッチ列の置き場所。** §2(c)・§6 で `HLL_COUNT.INIT` のスケッチを「集約可能なユニーク数の持ち方」として挙げたが、正典にはスケッチ列を持つ集約表が無い。本文では新テーブルを作らず CTE 内で完結させた。スカウト系の日次集約（例: `agg_scout_sender_daily`）を正典に足すなら、`unique_member_sketch`（BYTES）を持つ形が 04/08 回の議論と噛み合う。
3. **`fee_rate` の分母。** 正典の `fct_placement` は `annual_income`・`fee_rate`・`fee_amount` を持つので `SAFE_DIVIDE(SUM(fee_amount), SUM(annual_income))` で加重平均料率が出る。この関係（`fee_amount = annual_income × fee_rate`）を正典に1行明記しておくと、他の回でも分子分母の対応を迷わない。

## 迷った判断とその理由

1. **§2(b) の合計を 600 ではなく 440 にした。** ブリーフは「1〜3月で SUM して『残枠 600』と出る」だが、`premium` の枠は 200/月で `scouts_remaining = 200 − scouts_sent` なので、3ヶ月の SUM が 600 になるのは**3ヶ月とも送信 0 のとき**だけ。それでは「枠を消化している契約」の例にならないため、送信 20/60/80（残枠 180/140/120）として `SUM = 440` にし、本文で「上限まで積んでも 200 × 3 = 600 にしかならない量を残枠として報告している」と 600 を上限値として明示した。ブリーフの意図（実在しない大きな数が出る）は保っている。
2. **`agg_company_entity.avg_overall_score_90d` との矛盾を明示的に処理した。** 正典は「集約テーブルの平均: `avg_*` を持たず `sum_*` + `count` を持つ」としつつ、`agg_company_entity` には `avg_overall_score_90d` がある。§1 末尾に「1エンティティ1行の終端テーブルは再集約しない契約なので平均を持ってよい（08回）」という但し書きを置き、§6 の判断基準表にも1行として入れた。08回の ECM の議論と衝突させないための処理。
3. **§2(c) のユニーク数の題材に `fct_scout` を選んだ。** `fct_review` は正典の固定判断で `member_key` を持たない（匿名性）ため、クチコミ側では COUNT(DISTINCT 会員) の例が作れない。スカウト受信会員のユニーク数（`M001`・`M003` が3日連続で受信）に置き換えた。新しいスカウト ID は作らず、受信者だけを既存 ID で書いている。
4. **§7(b) の SQL で `QUALIFY` と `GROUP BY` を同じ SELECT に置かなかった。** BigQuery の `QUALIFY` は集約の後に評価されるため、`GROUP BY` を持つ SELECT で非グループ列（`snapshot_date_key`）を `QUALIFY` の条件にすると構文エラーになる。CTE で月末行に絞ってから外側で `SUM` する形に直し、その理由をコメントに残した。
5. **図の accent を右パネル全体ではなく結果ノード1つ＋その手前の矢印に絞った。** 比較図は3段とも左右で内容が違うため全段を accent にできてしまうが、ブリーフの「結果の違いだけ accent」に従い、構造を完全に同じ座標で並べたうえで最終値だけを focal にした。色を落としても `UNWEIGHTED` / `WEIGHTED` のタグで意味が読めるようにしてある。
6. **MetricFlow の YAML を v1.12+ spec で書いた。** 旧 spec（`measures:` + `type_params.measure`）との二本立てにすると紙面が倍になるため、docs が現行としている形に統一し、コード内コメントに「dbt v1.12+ の spec」と明記した。

## 未達事項

- DWT 3rd ed. の ch.1 / ch.4 は書籍本体を参照できないため、同じ内容を要約した Kimball Group 公式の *Kimball Dimensional Modeling Techniques*（正典 references.md に「Techniques」として収載）から引用した。章番号での参照は `p.meta` と §3 に残してある。
- `metrics.yml`（MetricFlow）の YAML は dbt docs の spec に照らして書いたが、実際に `dbt parse` で検証していない。手元に Semantic Layer を有効化した dbt プロジェクトが無いため。
- 図は1枚のみ（ブリーフ指定どおり）。§5 の「原子 → 日次 agg → 月次 → 企業グループ」の流れも図にしたくなったが、表と SQL で足りるため描いていない。

---

## 修正ラウンド1（レビュー `review/04_review.md` 対応）

- **C1**: §7(b) の SQL コメントを「`QUALIFY` は `GROUP BY` / `HAVING` の後に評価されるので、同じ SELECT では非グループ列 `snapshot_date_key` を参照できない」に訂正（評価順の記述が正反対だった）。
- **C2**: §4 の MetricFlow YAML 2ブロックを dbt v1.12+ の latest spec に統一（`models: - name: X` 配下の `semantic_model:` + `columns:` の `entity:` / `dimension:` + モデル直下の `metrics:`、ratio はトップレベル `metrics:` で `numerator:` / `denominator:`）。`docs.getdbt.com/docs/build/latest-metrics-spec` を WebFetch して before/after を確認。`columns:` は `semantic_model:` の子ではなくモデル直下（docs の記載に合わせ、レビュー案の入れ子から1段上げた）。§4 導入にも spec の位置づけを1段落追加。
- **I1**: `agg_company_rating_daily` のモデル SQL に `submitted_date AS rating_date` と `partition_by={'field':'rating_date','data_type':'date'}` / `cluster_by=['company_key']` を追加、`GROUP BY` にも追加。schema.yml に `rating_date`（`not_null`）を追加。
- **I2**: 企業グループ再集約を、子孫側は全 SCD2 版のブリッジで結合し、祖先側は `dim_company` へ `is_current` で結んで `anc.company_id` でグループ化する形に変更。ブリッジの展開前提と「足し上げの単位は企業という実体であって SCD2 の版ではない」旨を3段落で明記。
- **I3**: DWT 章番号を修正。§1 h3 → ch.1–2、§3 表「加法・半加法・非加法の分類」→ ch.2、§5 h3「集約ファクト」→ ch.2。`p.meta` を「ch.1–2（加法・半加法・非加法）, ch.4（定期スナップショットと半加法残高）」に更新。§3 表の「定期スナップショット（DWT ch.4）」は据え置き。
- **I4**: §1 分類表で `scout_quota` を `monthly_fee` と同じ「加法（時間で足すと期間付与枠・期間売上）」行へ移し、`scouts_remaining` を半加法の行に単独で残した。§2(b) 本文に「`SUM(scout_quota) = 600` と `SUM(scouts_sent) = 160` は加法なフローとして意味がある。壊れているのは 440 だけ」を追加。
- **I5**: 2本目の `scouts_sent` を `contract_scouts_sent`（label「契約枠の消化数」）にリネーム。メトリクス名の一意性と「数え方も分母も違うなら名前を分ける」の1段落を §4 に追加。
- **M5-1**: 3文超の段落7つを分割（§2a, §2c, §5 期末値, §6 末尾, §7a, §7b, §7c）。§4 の導入段落も分割時に4文になったため2段落へ。
- **M5-2**: `SAFE_DIVIDE` の説明を「素の集計では発火しない（0 件の日に行が立たないため `review_count >= 1`）。効くのは後段で 0 件月を `LEFT JOIN` で埋めたとき」に置換。
- **M5-3**: §6 の行ラベル「在籍フラグ」→「状態フラグ」。
- **M5-4**: DT#77 の引用を原文どおりに（"While you can roll up…" / "…must change to accommodate new data."）。
- **M5-5**: パーティション列でのフィルタに統一。月次再集約は `a.rating_date BETWEEN DATE '2026-03-01' AND DATE '2026-03-31'`、期末値・期中平均は `month_date`、§7(b) は `f.snapshot_date`。期末値 SQL の出力列も `scouts_remaining AS scouts_remaining_month_end` にして本文と揃えた。
- **M5-6**: §2(c) を正典サンプル `S003`(6/18)・`S001`(6/20)・`S002`(6/25) に接地。3件だけなら日次ユニークの合計と実ユニークが一致すること、`M001` が 6/22 にも受け取った瞬間に 4 vs 3 で壊れること、膨らみが「会員あたりの受信日数 d 倍」であることを表と本文で示す形に組み替えた。HLL の窓も 6/18〜6/25 に合わせた。数値例は 6 vs 2 から 4 vs 3 に変わっている（正典サンプルに接地した結果、差は小さくなったが一般式 `N × d` を併記した）。
- **M5-7**: 図の右パネル上段を `sum 3.5 / 5.0 / 25.0` と `count 1 / 1 / 10` の2行に分割（ハイフンが減算に読めた）。左パネルも `avg 3.5 / 5.0 / 2.5` / `count は捨てる` にして構造を対称にした。`check_svg.py` 再実行で `0 errors, 0 warnings`。

未対応: なし（Critical 2 / Important 5 / Minor 7 すべて反映）。

---

## 修正ラウンド2（再レビュー `review/04_rereview.md` 対応）

- **N1**: `non_additive_dimension` の子キーを現行 spec に統一。`window_choice` → `window_agg`（`docs.getdbt.com/docs/build/metrics-overview` を WebFetch し、`name` / `window_agg`(min|max) / `group_by` が latest spec であることを確認。`window_choice` / `window_groupings` は measures 時代の名前）。散文も `window_agg: max` に直し、「旧 spec ではこのキーが `window_choice`」を括弧で添えた。YAML 内の legacy 記法は残っていない（`window_choice` の出現は散文の対比1箇所のみ）。
- **N2**: §1 分類表の「残高（`scouts_remaining`）と同じ行に置かない」を削除し、「残高と同じ行に共存してよい（足す軸が違うので列ごとに扱いを変える）」に置換。正典 §4 の `fct_contract_monthly`（5メジャーが同居）と DWT ch.4 の在庫スナップショット（加法な販売量と半加法な在庫量の共存）に合わせた。
- **N3**: §2(c) を ISO 週で定義し直し、§5 の HLL SQL と窓を一致させた。窓は **2026-06-15 〜 06-21（ISO 週、`dim_date.iso_week` = 月曜始まり）**。この週に入る正典サンプルは `S003`(6/18, `M002`) と `S001`(6/20, `M001`)、`S002`(6/25, `M003`) は翌週で窓外であることを明記。`M001` が 6/16 にも受け取ったという仮定を1件だけ置き、日次ユニークの合計 3 vs 実ユニーク 2 とした。HLL SQL は `WHERE sent_date BETWEEN DATE '2026-06-15' AND DATE '2026-06-21'`、`GROUP BY sent_date` → `DATE_TRUNC(sent_date, ISOWEEK) AS iso_week_start` で `GROUP BY iso_week_start`。直後に「返るのは 2。日次ユニークを足した 3 ではない」を追加して §2(c) と数値を接続した。前回報告の「HLL の窓も合わせた」は誤記（実際は未変更）で、今回実施した。
- **N4**: 参照文献リストの DWT 行を「ch.1–2（加法性）, ch.4（定期スナップショットと半加法残高）」に更新し、`p.meta` と `canon/references.md` の割当に揃えた。
- **N5**: 月次再集約 SQL を `dim_company` へ結んで `c.company_id` でグループ化する形に変更し、「`C002` は 5/1 に2版になるので SCD2 版で束ねると年内が2行に割れる」を1段落追加。企業グループ節では祖先側の前提も明文化（「祖先側も全 SCD2 版で持ち、クエリ側で `anc.is_current` に絞る。無いと祖先の版数だけ子孫行が複製されてファンアウトする」）。
- **N6**: `fct_contract_monthly` の `contract_id` を `type: primary` → `type: foreign`（`name: contract`）に変更し、YAML にコメントを付けた。散文2段落を追加: 粒度宣言（01回）と `entity` 宣言は一致しなければならないこと、`type: primary` は「行を一意に識別する」という嘘の宣言になり join で増幅すること、一意なのは `(contract_id, month_date)` でありエンティティは複合キーを取らないので primary を宣言するならモデル側に連結した代理列（`contract_month_id` のような1列）を足すこと、足さないなら `foreign` のままで simple / ratio metric は作れること。`fct_scout_funnel` の `scout_id`（1行 = 1スカウト）は粒度と一致しているので `primary` のまま。
- **N7**: §7(b) の `WHERE` 行末スペースを削除（ファイル全体で行末スペース 0 を確認）。「6月第4週」の表記は N3 の書き換えで消滅。

検証: `check_svg.py` = `0 errors, 0 warnings`／HTML 入れ子検証 OK／3文超の段落 0／行末スペース 0／正典外のテーブル名・列名なし。

未対応: なし（N1〜N7 すべて反映）。
