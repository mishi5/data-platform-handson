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
