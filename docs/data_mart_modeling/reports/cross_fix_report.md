# 横断修正レポート — cross_review.md の指摘対応

対象: `docs/data_mart_modeling/html/*.html`（全11本）
出典: `review/cross_review.md`（Critical 3 / Important 4 / Minor 7）
方針: 指摘箇所の局所修正のみ。正典（`canon/`）は変更していない。行番号は**修正後**のもの。

## Critical

| ID | 回・行 | 何をどう直したか |
|---|---|---|
| C1 | `10_layers_tests.html:129` | `R001` の審査イベントを「`submitted`→`screening`→`submitted`（03-11 の差し戻し `low_quality`）→`published` で 3 行」に直し、「クチコミが 2 行に増える」を「3 行に増える」に変更（01 が正・正典 §5 に一致） |
| C1 | `10_layers_tests.html:131,134,136` | SQL のコメントを 3 行前提に更新（`R001 が 3 行入った状態`、`review_count` = `3（正しくは 1）`、平均は `分子も分母も 3 倍`） |
| C1 | `10_layers_tests.html:143` | 「件数だけが 2 倍になり」→「3 倍になり」 |
| C2 | `00_domain.html:438` | `moderation_rounds` の説明を「`review_moderation_events` のうち**審査担当者が判定を下した遷移の数**（イベント行数そのものではない）」に修正。「差し戻しを表現するなら正典の `status` 遷移に足す必要がある（01回で検討）」を「正典 §5 の `R001` に差し戻し1回を固定した（01回）」に書き換え |
| C3 | `10_layers_tests.html:314` | `fct_scout` の `config:` から `require_partition_filter: true` を削除し、`# require_partition_filter は付けない（star = 正本。07回）` に置換（07 が正） |
| C3 | `10_layers_tests.html:296` | 導入文を「star 側の `fct_scout` には付けない（07回）。付けるのは配布物 `obt_*` と `dim_member_daily`」に書き換え、下の `where` は「フィルタ必須テーブルで必要になる形と同じなのでこの形で示す」と位置づけ直した |
| C3 | `10_layers_tests.html:452` | aside の窓の説明を「`require_partition_filter` を張る配布物（`obt_*`）や `dim_member_daily` で**必要になる**形。star 側の正本では必須ではなく、スキャン量を抑える運用上の選択」に修正 |
| C3 | `07_star_vs_obt.html:317-318` | `fct_scout` の config 直前に「増分化（`materialized='incremental'` + `insert_overwrite`）は 09回・10回。この回の論点は物理設計だけなので `table` のまま示す」の注記 2 行を追加（`materialized='table'` は据え置き） |
| C3 | `05_scd.html:572-573` | 同じ注記を追加（「この回の論点は as-of join の書き方だけ」） |

## Important

| ID | 回・行 | 何をどう直したか |
|---|---|---|
| I1 | `01_grain.html:419-421` | `COALESCE(dj.job_posting_key, -1)` / `dcat.job_category_key` / `dch.channel_key` の既定値を `'-1'`（STRING）に変更 |
| I1 | `02_fact_types.html:360-362` | `jp.job_posting_key` / `jc.job_category_key` / `ch.channel_key` の既定値を `'-1'` に変更（桁揃えは維持） |
| I1 | `02_fact_types.html:737,739` | `jp.job_posting_key` / `jc.job_category_key` の既定値を `'-1'` に変更 |
| I1 | `02_fact_types.html:423` | 但し書きを「上の SQL で `job_posting_key` / `job_category_key` / `channel_key` だけ `'-1'` になっているのは、自然キーをそのまま使う STRING キーだから（`COALESCE(STRING, INT64)` は BigQuery で型エラー）」に更新（SQL を直したので旧文が陳腐化していた） |
| I1 | `09_incremental.html:358` | `coalesce(jp.job_posting_key, '-1')` に変更 |
| I1 | `00_domain.html:445` | `moderation_reason_key` = `-1` → `'-1'`（`dim_moderation_reason` の自然キー `reason_code` が STRING である旨を併記） |
| I1 | （非対象の確認） | INT64 キー（`member_key` / `member_profile_mini_key` / `scout_sender_key` / `date_key` 系）の `-1` は全て据え置き。全 HTML を再走査し STRING キーへの INT64 センチネルの残りは 0 件 |
| I2 | `05_scd.html:578` | `cluster_by = ['member_key', 'scout_sender_key']` → `['scout_sender_key', 'member_key']`（正典 §4 / 07・09・10 と同順） |
| I3 | `04_additivity.html:415` | 「（03回の conformed の話と同じ構図）」→「（08回のコンフォームドの話と同じ構図）」 |
| I4 | `02_fact_types.html`（6 箇所） | `schema.yml` 内の `tests:` を全て `data_tests:` に |
| I4 | `03_dimensions.html`（10 箇所） | 同上 |
| I4 | `05_scd.html`（4 箇所） | 同上 |
| I4 | `06_bridges.html`（4 箇所） | 同上 |
| I4 | `07_star_vs_obt.html`（5 箇所） | 同上（`dbt_project.yml` 側の `data_tests:` は元から正しく、同一ファイル内の 2 綴り混在が解消） |
| I4 | `08_conformed.html:489,491,496,507` | 同上（cross_review の列挙には無いが、「全回 `data_tests:` に統一」の裁定に従い追加で修正）。全11本で旧 `tests:` の残りは 0 件 |

## Minor

| ID | 回・行 | 何をどう直したか |
|---|---|---|
| M1 | `06_bridges.html:487` | `-- 生成方式（FARM_FINGERPRINT / generate_surrogate_key）は 03回の判断に従う` → `-- 生成方式は 03回の判断（FARM_FINGERPRINT の INT64）に従う` |
| M2 | `10_layers_tests.html:261` | ETL サブシステム表の実装欄を `dbt_utils.generate_surrogate_key / FARM_FINGERPRINT` → `FARM_FINGERPRINT`（03回で `dbt_utils.generate_surrogate_key` は不採用） |
| M3 | `03_dimensions.html:557` | 「正本は 10回。ここでは**呼び出し側の形**だけを示す」の一文を §5(e) の冒頭に追加 |
| M3 | `03_dimensions.html:559-562` | マクロ定義を 10 の正本に合わせ、引数を SQL 式 `quality_flag_expr` → 値 `quality_flag='ok'` に変更（コメントに「正本は 10回」を明記） |
| M3 | `03_dimensions.html:565-577` | `dim_audit` モデルの `quality_flag` 値域を `ok`/`late_arriving_dimension`/`missing_natural_key` → `ok`/`estimated`/`suspect`、`loaded_at` を `CURRENT_TIMESTAMP()` → `run_started_at` に変更 |
| M3 | `03_dimensions.html:588` | ファクト側の呼び出しを `{{ audit_key("'ok'") }}` → `{{ audit_key() }}`（他回と同形） |
| M3 | `03_dimensions.html:591` | 解説に `loaded_at` に `run_started_at` を使う理由と、値域・引数形が 10 の正本に合わせてあることを追記 |
| M3 | `10_layers_tests.html:459` | 03 を揃えたため「03回の下書きとの差分 3 点」の記述が陳腐化。「03回 §5(e) は呼び出し側の形だけを示す。正本はこちらで、ここで初めて足すのは `{%- do ref('dim_audit') -%}` の依存と `incremental_strategy = 'merge'`」に書き換え |
| M4 | `07_star_vs_obt.html:315` | `int_scout_keyed` の導入文を 1 段落追加（`stg_careervoice__scouts` にキー解決を済ませた intermediate、正典 §4 の `int_<entity>_<verb>` 規則、正典にモデル登録は無い、中身は 05回） |
| M5 | `00_domain.html:45` | `p.meta` の再解釈欄「Hightouch Part 1」→「Hightouch Modelling Part 1」 |
| M5 | `08_conformed.html:44` | 同「Hightouch 2」→「Hightouch Modelling Part 2」（07 は既に「Hightouch Modelling Part 2」で無修正） |
| M5 | `06_bridges.html:44` | `p.meta` の参照欄「DWT ch.7 ch.8 ch.10」→「DWT ch.7, ch.8, ch.10」 |
| M6 | `05_scd.html:359` | 参照の範囲を明示 —「（1 パーティションを作り直す手順は 09 回の演習(c)。1〜6 月をまとめて作る話はそこには無い）」 |
| M7 | `05_scd.html:572-573` / `07_star_vs_obt.html:317-318` | C3 と同じ扱い。`materialized='table'` の直前に「増分化は 09回・10回」の注記を添え、`fct_scout` の materialization が 3 通りに読める状態を解消 |

## 検証

- `check_svg.py`: 全 11 本 **0 errors**（warning は 01 / 03 / 08 / 10 に各 1、いずれも今回の修正前から存在し SVG は未編集）
- `<pre>` 内の生 `<`: 全 11 本で **0 件**（`</code>` を除いた本文を走査）
- `.table-wrap` と `<table>` の対応: 全 11 本で 1:1（`<div>` の開閉数も全本一致）
- 旧 `tests:` キーの残存: **0 件**
- STRING キーへの INT64 センチネル（`COALESCE(..., -1)`）の残存: **0 件**
