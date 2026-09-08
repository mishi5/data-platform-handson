# 08 コンフォームドとドリルアクロス — 執筆報告

ファイル: `docs/data_mart_modeling/html/08_conformed.html`（約 50KB, 単一ファイル・外部依存ゼロ）

## 完了した節

| 節 | 内容 | ブリーフの必須項目 |
|---|---|---|
| 1. この回が決めること | 判断一覧表（6行）／コンフォームドの3条件表（同じ意味・同じキー・同じ属性名）／CareerVoice のコンフォームドディメンション表（`dim_date`, `dim_company`, `dim_member`, `dim_job_category`, `dim_agent`+`dim_agency`） | ✓ |
| 2. どこで壊れるか | (a) SCD2 版のずれ（`C002` の 2026-05-01 変化、`fct_review` 投稿時点 vs `fct_application_pipeline` 応募時点、`fct_scout` は `company_key` 非保持）(b) 直接 JOIN の fan-out（`C001` 2026-06 の 3 クチコミ × 5 スカウト = 15 行、対比表）(c) 問いごとの集約増殖（ずれる場所の表 4 行） | ✓ |
| 3. Kimball の原則 | 技法表（コンフォームド/縮約/コンフォームドファクト/ドリルダウン/ドリルアクロス）＋ Soul 1・Soul 2・DT#135 の aside 3 枚＋バスマトリクスが正本の段 | ✓ |
| 4. 現代の再解釈 | ECM aside 2段／Hightouch 2 aside／「Kimball vs 現代 vs この題材」の 3 段比較表（5行） | ✓ |
| 5. BigQuery + dbt での実装 | 5-1 ドリルアクロス SQL（3 パス＋`FULL OUTER JOIN USING`）／5-2 `br_company_hierarchy` でのグループ畳み込み／5-3 `agg_company_entity` の dbt モデル＋`schema.yml`／5-4 マテリアライズド・ビューの選択肢と制約表（6行） | ✓（5-2 は追加） |
| 6. 判断基準 | 「集約テーブルを持つ条件」表（クエリ頻度 × 元ファクト行数 × 再集約可能性、6行）／「エンティティ表に指標を入れる条件」表（7行） | ✓ |
| 7. 演習 | (a) クチコミ平均 × 応募率の SQL 骨格（`LAG` + `WINDOW`）(b) `avg_overall_score_90d` と 04 回の原則（条件表 3 行）(c) `agg_member_entity` の可否表（7 行） | ✓ |
| 8. 参考: 手元の基盤 | `mart_url_performance` / `mart_error_analysis` の共通行ヘッダ問題、`news_pipeline` の日付軸不在、試せる種 1 行 | ✓ |
| 参照文献 | 7 件 | ✓ |

## 読んだ文献と引用した要点

すべて WebFetch で実読。カギ括弧付きの創作引用はせず、原文の英語表現をそのまま引くか日本語で要約した。

| 文献 | 引用・利用した要点 |
|---|---|
| Soul 1（Drilling Down） | ドリルダウン＝ SELECT に "adding a row header" すること。"Row headers and grouping columns are the same thing"。"drilling down has nothing to do with descending a predetermined hierarchy" → §3 aside、§5-1 の「3 パス全部に同じ列を足す」に接続 |
| Soul 2（Drilling Across） | "separate requests to the target fact tables followed by a simple sort/merge on the identical row headers returned from each request"。"All fact tables in a drill-across query must use conformed dimensions"。"Two dimensions are conformed if the fields that you use as common row headers have the same domain"（部分集合でも可＝縮約ディメンションが使える）。単一 SQL で結ぶと結果が "too low or too high, or both" → §2(b), §3 |
| DT#135 | コンフォームドは アジャイルを妨げず可能にする。"the development crank starts turning faster and faster"。合意は全属性でなく "identify a subset of attributes that have significance across the enterprise" から。サイロの弊害は "inconsistent categorizations and labels" と、一見比較可能だが業務ルールが "slightly different" → §3 の最後 2 段、§2(c) の根拠 |
| DWT ch.4 | エンタープライズ DWH バスアーキテクチャ、コンフォームドディメンション、縮約（shrunken/rollup）ディメンション、コンフォームドファクト、ドリルアクロス。書籍のため URL は書籍ページのみ。§1・§3 の表で参照 |
| ECM（Beauchemin 2023） | 出発点は Kimball の禁止事項 "A BI application must never issue SQL that joins two fact tables together across the fact table's foreign keys"。解は窓付き指標（`visits_7d`/`visits_28d`/`visits_90d`）をエンティティ表に持たせ "simple queries (without having to use JOIN, UNION ALL, or subqueries)" を可能にすること。保証は "every row is an instance of an entity"。欠点は保存の冗長・幅広テーブルの性能・"column overload" で、"restraint and limit the number of metrics" を勧める → §4 aside、§5-3 のスパイン設計、§6 の列数行 |
| Hightouch 2 | 3 層（staging / core / consumption）。"To get the best of both worlds, we can still utilize Kimball's Star Schema as an intermediate step after the staging layer, then materialize Wide Tables out of it"。Wide Table は "25-50% faster in Redshift, Snowflake and BigQuery than Star Schema and joins"。結論は "there is no one-size-fits-all model" → §4 aside と比較表 |
| dbt BigQuery configurations | `materialized='materialized_view'` の設定キー（`enable_refresh`, `refresh_interval_minutes`, `max_staleness`, `on_configuration_change`, `partition_by`, `cluster_by`）と、MV の SQL は後から変更不可・`partition_by` はベーステーブルと一致という制約 → §5-4 |
| BigQuery マテリアライズド・ビューのドキュメント（`materialized-views-create` / `materialized-views-intro`） | 増分 MV で使える集約関数の一覧（`SUM`, `COUNT`, `COUNTIF`, `AVG`, `MIN`, `MAX`, `APPROX_COUNT_DISTINCT`, `HLL_COUNT.INIT` ほか）、`RIGHT`/`FULL OUTER JOIN`・自己結合・ウィンドウ関数・非決定的関数・UDF の禁止、"Aggregates in the materialized view query must be outputs"、MV の上に MV 不可、パーティション粒度の一致要求 → §5-4 の制約表。**URL は正典に無いので本文には出さず、事実だけを書いた**（下記の変更提案を参照） |

## 実際に BigQuery で検証したこと

`bq query` でダミー CTE に置き換えて実行し、構文と意味論を確認した。

1. `FULL OUTER JOIN ... USING (k)` を 3 段チェーンしたときに結合キーが 1 列に併合され、どの側にしか無い行もキーが埋まること（`k = 1,2,3,4` が全部出た）。§5-1 の SQL 形はこの確認に基づく。
2. §5-1 のドリルアクロス SQL 全体（`company_map` / `review_monthly` / `scout_monthly` / `application_monthly` / `drilled` / 最終 SELECT）をダミーテーブルで実行し、期待どおり 2 行（3月＝クチコミのみ、6月＝スカウトと応募のみ）が返ることを確認。
3. §7(a) の `LAG` + 名前付き `WINDOW` 句が BigQuery で動くこと。

## check_svg の結果

図なし（ブリーフで「なし」と指定）。`check_svg.py` は実行していない。

## 正典への変更提案

1. **`agg_company_entity` にディメンション属性列を追記**。ブリーフ §5(b) が「`dim_company` の現在値属性」を要求しているため、実装では `company_id`, `name`, `industry`, `sector`, `employee_size_band`, `listing_status`, `hq_prefecture`, `parent_company_id`, `founded_year` を持たせた。正典の `agg_company_entity` 行はメジャーしか列挙していないので、「+ `dim_company`（`is_current`）の属性を平坦化」と備考に追記したい。
2. **`agg_member_entity` の扱い**。ブリーフ §7(c) が名前を指定しているが正典に無い。本文では「正典未登録の候補」と明示して扱った。正典に載せるなら、匿名性の固定判断により **クチコミ由来の指標を持てない** ことを備考に書くのが要点。
3. **BigQuery マテリアライズド・ビューの URL を `references.md` に追加**したい。§5-4 の制約は公式ドキュメントの事実だが、正典に URL が無いため本文にリンクを張れなかった。候補: `https://cloud.google.com/bigquery/docs/materialized-views-intro` と `https://cloud.google.com/bigquery/docs/materialized-views-create`（後者に増分 MV の対応集約関数と禁止構文の一覧がある）。
4. **`dim_scout_sender` の自然キー列名の明示**。§5-1 / §5-3 で `s.sender_id = c.company_id` と書いた。正典は自然キーを (`sender_type`, `sender_id`) と書いているので列としては存在する読みだが、「`sender_id` は `company` なら `company_id`、`agent` なら `agent_id` を格納する」と明記されているとブレない。

## 迷った判断とその理由

| 論点 | 決定 | 理由 |
|---|---|---|
| ドリルアクロスの行ヘッダを `company_key` にするか `company_id` にするか | `company_key` にしたうえで、各パスの先頭で `company_id` 経由で `is_current` 版へ寄せる（`company_map` CTE） | ブリーフが `USING (company_key, month_key)` を指定。§2(a) の壊れ方の解決策をそのまま SQL に埋め込む形になり、教材としても一貫する |
| `month_key` の型 | クエリ内の派生列 `DATE_TRUNC(<role>_date, MONTH)`（DATE 型） | 正典に月キー列は無い。DATE 型にすることでパーティション列（`submitted_date` 等）を直接使え、プルーニングも効く。`_key` という名前はブリーフ指定に従った |
| `fct_scout` に `company_key` が無い問題 | 正典どおり `dim_scout_sender` 経由で企業に戻す一段を明示し、それ自体を §2(a) の壊れ方の一部として書いた | ブリーフの (a) は「`fct_review` と `fct_scout` で `company_key` の SCD2 版がずれる」だが、正典の FK 一覧に `fct_scout.company_key` は無い。正典を曲げず、ブリーフの意図（版のずれ→行が消える）は `fct_review` × `fct_application_pipeline` で表現した |
| `agg_company_entity` の `audit_key` | 持たせない | 正典は「全**ファクト**は `audit_key` を持つ」であり `agg_*` はファクトではない。代わりに「監査は元ファクトの `audit_key`（`{{ audit_key() }}`。10 回で定義するマクロ、それまでは `-1`）と `dim_audit` で辿る」と本文に明記した |
| `hires_90d` のパーティションプルーニング | `hired_date` で絞りつつ `applied_date >= DATE_SUB(asof, INTERVAL 365 DAY)` を併記 | `fct_application_pipeline` は累積スナップショットで `applied_date` がパーティション列。`hired_date` だけで絞るとフルスキャンになる。SQL のコメントにも書いた |
| `agg_company_rating_daily` を MV にするか | しない（MV は「単一ファクト集約を BI が直接叩く」場合の選択肢として保留） | MV の上に MV を作れないため、MV 化すると `agg_company_entity` がそれを `ref` できなくなる。§5-4 の最後に理由を書いた |
| §2(c) の具体例 | `C001` の 4 月（`R002` が却下）で「`published` のみ = 0 / `submitted` 全件 = 1」に分かれる例に差し替えた | 初稿では `C002` の 3 月で「1 と 2」と書いたが、正典のサンプルには C002 の 3 月クチコミは `R001` 1 件しかなく、架空の 2 件目を作ることになるため |
| MV の制約の出典 | 本文には URL を張らず事実のみ記述 | 正典の URL 制限を守るため。上記の変更提案 3 に回した |

## 未達事項

- なし。ブリーフの §1〜§7 の必須内容と図の指定（なし）はすべて満たした。
- ただし §5-2（グループ企業の畳み込み）はブリーフに無い追加節である。オーケストレータから「企業グループの再集約は `br_company_hierarchy` の子孫側から `company_id` で畳む（祖先側は `is_current`、子孫側は全版）」という規約が来ていたため、ドリルアクロスの行ヘッダの話題に接続する形で入れた。不要なら削除できる独立した h3 にしてある。

---

## 修正ラウンド 1

正典・`references.md` を再読し、裁定済みの項目（`agg_company_entity` への `dim_company`(`is_current`) 属性平坦化と `audit_key` 非保持、`dim_scout_sender.sender_id` の意味、BQ MV の URL 追加）を反映した。

| ID | 対応 |
|---|---|
| C-1 | §5-4 制約表の最終行を公式の事実に修正（`partition_by` は「ベーステーブルと**同じ列**に同粒度」、ネスト禁止は参照側が `materialized='table'` なので効かない）。結論の段を、MV は直接クエリ可（"You can query your materialized views directly, the same way you query a regular table or standard view."）で `ref` の障害にならない → MV 化を止めているのは定義 SQL の不変性、に書き直し。§1 判断一覧表の MV 行も同じ理由に揃えた |
| C-2 | §8 第 1 段を実物に合わせて全面差し替え。`mart_url_performance` = `url_path` × `date`（`GROUP BY url_path, date`）、`mart_error_analysis` = `date` × `hour` × `error_detail`（`access_error_summary` が `GROUP BY date, hour, status_code` で `url_path` を捨てる）、`url_path` の導出は `stg_access_logs` の `split(url, '?')[offset(0)]` 1 か所に閉じている、を確認して記述。`exposures.yml` の依存（`error_monitoring_alert` → `mart_error_analysis`、`url_performance_dashboard` → `mart_url_performance_incremental`）も追記。「試せる種」は `url_path` を残した派生モデルを作る案に変更（`dim_url_path` 案は撤回） |
| I-1 | §7(c)「応募数（30 日）・入社（90 日）」行を「固定窓なので両方には立たない。`asof` が 7/23 以前なら `applications_30d`、8/1〜10/30 なら `hires_90d`」に修正。窓幅がファネルの見え方を決めるという教材化 |
| I-2 | §5-2 の `group_map` を `(des.company_key, anc.company_key AS group_company_key)` 出力に変更し、`company_map` とそのまま差し替えられる形に。置き換え手順（`USING (company_key)` と `g.group_company_key AS company_key`）を明記。`anc.is_current` が 06 回の実装に対する安全網である旨を 1 文追加 |
| I-3 | §5-1 の `application_monthly` に `dim_channel` を結合し `COUNTIF(ch.source_channel = 'scout_company')` を追加。最終 SELECT の `applications_per_scout` を `apply_rate_scout_company`（分子分母とも企業送信スカウト）に変更。§7(a) の解答 SQL と定義文も同じ母集団に揃えた |
| M-1 | §1「同じキー」行を「`fct_scout` / `fct_scout_funnel` を除く全ファクトが `company_key` を持つ。この 2 本は `dim_scout_sender`（`sender_id` が company なら `company_id`）経由」に修正 |
| M-2 | §1「結ぶファクト」列に `dim_member` 行へ `fct_selection_event`、`dim_agent`/`dim_agency` 行へ `fct_scout_funnel` を追記 |
| M-3 | §5-1 に「`month_key` は `DATE_TRUNC` が返す DATE で、正典の `date_key`（INT64 `YYYYMMDD`）とは別物」の 1 文を追加 |
| M-4 | `schema.yml` の `review_count_total` を「`fct_review` の粒度どおり `submitted` 全件、審査中・却下を含む」に、`avg_overall_score_90d` にも同じ母集団を明記 |
| M-5 | §7(c) 開封率・返信率のセルに「(b) と同じ条件で比率を持たせてもよいが、返信率は分母が『送信』か『開封』かで 2 通りあるため分子分母を残して下流に選ばせる」を追記 |
| M-6 | §5-3 `applications` CTE のコメントに「応募から入社まで 365 日を超えた案件は `hires_90d` から落ちる。許容できないなら `fct_placement`（`hired_date` がパーティション列）から取る」を追記 |
| M-7 | §5-1 の読み方に「`company_map` は `INNER JOIN` なので、`-1`（未知）行が `is_current` で存在しないと未知企業のファクト行が黙って消える（DT#43）」を 1 段追加 |
| M-8 | §5-4 のパーティション制約を公式の "Materialized views must be partitioned on the same column as the base table with matching granularity" に合わせ、`rating_date` が `fct_review.submitted_date` の別名なので条件を満たす、と対応づけた |

参照文献に BigQuery マテリアライズド・ビューの 2 URL（`materialized-views-intro` / `materialized-views-create`）を追加した。

### 再検証

- 修正後の §5-1 SQL（`dim_channel` 結合と `apply_rate_scout_company` を含む）と §5-2 の `group_map` を `bq query` でダミーテーブル実行し、コンパイルと期待値を確認（3 月＝クチコミのみ、6 月＝スカウトと応募のみ、`apply_rate_scout_company` = 1.0）。
- `check_svg.py`: `0 errors, 1 warnings`（warning は「`<svg>` が見つからない」＝図なし指定どおり）。
- 正典外テーブル名は `agg_member_entity`（裁定済み）と §8 の手元基盤名（`mart_url_performance` / `mart_url_performance_incremental` / `mart_error_analysis` / `stg_access_logs`、いずれも実在）のみ。`dim_url_path` は削除。
- 本文の URL はすべて `references.md` 掲載か kimballgroup.com。3 文超の `<p>` / `<li>` は 0。タグ balance・`<pre>` 内の生 `<` なしを再確認。

---

## 修正ラウンド 2

| ID | 対応 |
|---|---|
| N-1 | §5-4 のパーティション制約から出典不明の英文引用を削除し、`materialized-views-create` を WebFetch で再確認して実在の 3 文に差し替え。義務と選択を分けて「MV のパーティションは任意だが、張るならベーステーブルと同じパーティション列でなければならない」（"If the base table is partitioned, then you can partition a materialized view on the same partitioning column."）／「時間パーティションでは粒度も一致」（"For time-based partitions, the granularity must match (hourly, daily, monthly, or yearly)."）／「非パーティションのベーステーブルの上にパーティション MV は作れない」（"You cannot partition a materialized view over a non-partitioned base table."）と書き直した。影響列も「3 条件を満たす」に対応づけ |
| N-2 | §5-2 の置き換え手順を 3 パス全部に閉じる形へ書き直し。`review_monthly` / `application_monthly` は `company_map` → `group_map` の置換、`scout_monthly` は `company_map` を経由しないため `INNER JOIN group_map AS g ON g.company_key = c.company_key` を足して `g.group_company_key AS company_key` を出す、と明記。「1 本でも畳み忘れると行ヘッダのドメインが揃わず §2(a) と同じ割れ方をする」を追記 |
| N-3 | `materialized-views-use` からの引用（"You can query your materialized views directly…"）を削除し、参照文献に載せている `materialized-views-intro` の自動書き換えの文（"If any part of a query against a base table can be resolved by querying the materialized view, then BigQuery reroutes the query to use the materialized view for improved performance."）に差し替え。「直接参照できる」は引用ではなく要約として残した。`references.md` は変更していない |
| N-4 | §5-2 に「`C001` のグループ行と `C003` 単体のグループ行が同時に出る（`depth = 0` で自分自身も自グループの子孫）。全行の合計は取れない。レベルを選ぶなら `b.depth` を行ヘッダに足すか `is_root` で絞る」の 1 段を追加 |
| N-5 | §5-1 に「分母はその月に送信されたスカウト、分子はその月に応募された `scout_company` 応募でコホートが一致しない。`S001`（6/20 送信）→ `P001`（6/23 応募）は同月だが月末送信では割れる。送信起点で揃えるなら `fct_scout_funnel` を使う」の 1 段を追加 |
| N-6 | §8 の `mart_error_analysis` の行ヘッダを `date` × `hour` × `error_source` × `error_detail` に修正（`app_error_summary` と `access_error_summary` の `UNION ALL` で `error_source` が粒度に入る） |

### 正典への追加提案（再掲・未反映）

- `references.md` の BQ MV 行に `https://cloud.google.com/bigquery/docs/materialized-views-use` を追加したい。今回は引用元を `materialized-views-intro` に差し替えて回避したが、「MV を通常のテーブルと同じように直接クエリできる」の一次出典はこのページにしかない。

### 再検証

- 本文の英文引用 5 件（MV パーティション 3 文・ネスト禁止・自動書き換え）を `materialized-views-create` / `-intro` の WebFetch 結果と突合し verbatim 一致を確認。出典不明の 1 文と参照文献外の 1 文は本文から消えていることを文字列検索で確認。
- 本文の URL はすべて `canon/references.md` 掲載か kimballgroup.com。正典外テーブル名は `agg_member_entity`（裁定済み）と §8 の手元基盤名のみ。
- 3 文超の `<p>` / `<li>` は 0、タグ balance OK、`<pre>` 内の生 `<` なし、§8 限定の語（`dbt_logs_analysis` / `news_pipeline` / `mart_*` / `stg_access_logs` / `error_source`）はすべて §8 内。
- `check_svg.py`: `0 errors, 1 warnings`（`<svg>` なし＝図なし指定どおり）。
- BigQuery への実クエリは今回の裁定どおり実施していない（SQL 変更は §5-2 の手順文と §5-1 の説明段のみで、コードブロックの SQL 本体は無変更）。
