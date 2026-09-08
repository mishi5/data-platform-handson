# 参照文献 — 正典リスト

執筆時は、自分の回に割り当てられた記事を **WebFetch で実際に読み**、要点を自分の言葉で書く（記憶で書かない）。
ここに無い URL を本文に出さない（必要なら report に追加提案を書く）。

## 主参照（Kimball）

| 略記 | 文献 | URL |
|---|---|---|
| DWT | *The Data Warehouse Toolkit, 3rd ed.*（Kimball & Ross, 2013）。章番号で引く | https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/books/data-warehouse-dw-toolkit/ |
| Techniques | Kimball Dimensional Modeling Techniques（技法一覧 PDF, 2013） | https://www.kimballgroup.com/wp-content/uploads/2013/08/2013.09-Kimball-Dimensional-Modeling-Techniques11.pdf |
| ETL Toolkit | *The Data Warehouse ETL Toolkit*（34 サブシステム） | https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/books/data-warehouse-dw-etl-toolkit/ |
| 10 Rules | The 10 Essential Rules of Dimensional Modeling（2009） | https://www.kimballgroup.com/2009/05/the-10-essential-rules-of-dimensional-modeling/ |
| Manifesto | A Dimensional Modeling Manifesto（1997） | https://www.kimballgroup.com/1997/08/a-dimensional-modeling-manifesto/ |
| Grain | Declaring the Grain（2003） | https://www.kimballgroup.com/2003/03/declaring-the-grain/ |
| Matrix | The Matrix（1999、バスマトリクス） | https://www.kimballgroup.com/1999/12/the-matrix/ |
| Soul 1 | The Soul of the Data Warehouse, Part 1: Drilling Down | https://www.kimballgroup.com/2003/03/the-soul-of-the-data-warehouse-part-one-drilling-down/ |
| Soul 2 | Part 2: Drilling Across | https://www.kimballgroup.com/2003/04/the-soul-of-the-data-warehouse-part-two-drilling-across/ |
| Fact Tables | Fact Tables（2008） | https://www.kimballgroup.com/2008/11/fact-tables/ |
| SCD 1 | Slowly Changing Dimensions（2008, Type1） | https://www.kimballgroup.com/2008/08/slowly-changing-dimensions/ |
| SCD 2 | Slowly Changing Dimensions, Part 2（Type2/3） | https://www.kimballgroup.com/2008/09/slowly-changing-dimensions-part-2/ |
| SK | Surrogate Keys（1998） | https://www.kimballgroup.com/1998/05/surrogate-keys/ |
| ETL Subsystems | Subsystems of ETL Revisited（2007） | https://www.kimballgroup.com/2007/10/subsystems-of-etl-revisited/ |
| Data Quality | An Architecture for Data Quality（2007） | https://www.kimballgroup.com/wp-content/uploads/2007/10/An-Architecture-for-Data-Quality1.pdf |

### Design Tips

| DT | タイトル | URL |
|---|---|---|
| #1 | Guidelines For An Expressive Clickstream Data Mart | https://www.kimballgroup.com/wp-content/uploads/2012/05/DT1GuidelinesFor.pdf |
| #3 | Focus On Business Process, Not Business Departments! | https://decisionworks.com/2000/01/design-tip-3-focus-on-business-process-not-business-departments/ |
| #5 | Surrogate Keys For The Time Dimension | https://www.kimballgroup.com/wp-content/uploads/2012/05/DT5SurrogateKeys.pdf |
| #15 | Combining SCD Techniques | https://www.kimballgroup.com/wp-content/uploads/2012/05/DT15CombiningSCD.pdf |
| #43 | Dealing With Nulls In The Dimensional Model | https://www.kimballgroup.com/2003/02/design-tip-43-dealing-with-nulls-in-the-dimensional-model/ |
| #46 | Another Look At Degenerate Dimensions | https://www.kimballgroup.com/2003/06/design-tip-46-another-look-at-degenerate-dimensions/ |
| #50 | Factless Fact Tables Sounds Like Jumbo Shrimp | https://decisionworks.com/2003/10/design-tip-50-factless-fact-tables-sounds-like-jumbo-shrimp/ |
| #51 | Latest Thinking On Time Dimension Tables | https://www.kimballgroup.com/2004/02/design-tip-51-latest-thinking-on-time-dimension-tables/ |
| #77 | Warning: Summary Data Alone Is Hazardous To Your Health | https://decisionworks.com/2006/03/design-tip-77-warning-summary-data-alone-is-hazardous-to-your-health/ |
| #83 | Abstract Generic Dimensions | https://decisionworks.com/2006/09/design-tip-83-abstract-generic-dimensions/ |
| #95 | Patterns to Avoid when Modeling Header/Line Item Transactions | https://www.kimballgroup.com/2007/10/design-tip-95-patterns-to-avoid-when-modeling-headerline-item-transactions/ |
| #100 | Keep Your Keys Simple | https://www.kimballgroup.com/wp-content/uploads/2012/05/DT100KeepYourKeysSimple.pdf |
| #108 | When is the Dimensional Model Design Done | https://www.kimballgroup.com/wp-content/uploads/2012/05/DT108_WhenDimensionalModelDone.pdf |
| #127 | Creating and Managing Mini-Dimensions | https://www.kimballgroup.com/2010/09/design-tip-127-creating-and-managing-mini-dimensions/ |
| #135 | Conformed Dimensions as the Foundation for Agile Data Warehousing | https://www.kimballgroup.com/2011/06/design-tip-135-conformed-dimensions-as-the-foundation-for-agile-data-warehousing/ |
| #142 | Building Bridges | https://www.kimballgroup.com/2012/02/design-tip-142-building-bridges/ |
| #152 | Slowly Changing Dimension Types 0, 4, 5, 6 and 7 | https://www.kimballgroup.com/2013/02/design-tip-152-slowly-changing-dimension-types-0-4-5-6-7/ |
| #164 | Have You Built Your Audit Dimension Yet | https://www.kimballgroup.com/2014/03/design-tip-164-built-your-audit-dimension/ |
| #179 | Key Tenets of the Kimball Method | https://www.kimballgroup.com/2015/11/design-tip-179-key-tenets-of-kimball-method/ |

まとめ元: https://zenn.dev/manabian/scraps/e57b1c240f859b

## 現代的な再解釈

| 略記 | 文献 | URL | 主張の要点（執筆前に本文で確認） |
|---|---|---|---|
| Fowler | Dave Fowler（Chartio）, *Kimball in the context of the modern data warehouse: what's worth keeping, and what's not*（Coalesce 2020 講演） | https://www.youtube.com/watch?v=3OcS2TMXELU （関連議論: https://discourse.getdbt.com/t/is-kimball-dimensional-modeling-still-relevant-in-a-modern-data-warehouse/225 — このスレッド自体は Fowler の講演より前の別議論） | 性能のための技法（サロゲートキー、雪片回避の一部）は列指向 DWH で不要化、意味のための技法（粒度・コンフォームド・SCD）は残る |
| Fivetran OBT | Fivetran, *Star Schema vs. OBT for Data Warehouse Performance*（2022） | https://www.fivetran.com/blog/star-schema-vs-obt | BigQuery で OBT が star より 49% 速い実測。性能は設計の唯一の基準ではない |
| ECM | Maxime Beauchemin, *Entity-Centric Data Modeling for Analytics*（Preset, 2023） | https://preset.io/blog/introducing-entity-centric-data-modeling-for-analytics/ | エンティティ（会員・企業）を中心にディメンションへ指標を持たせる。Kimball の拡張 |
| FDE | Maxime Beauchemin, *Functional Data Engineering — a modern paradigm for batch data processing*（2018）— 解説 | https://www.ssp.sh/brain/functional-data-engineering/ ／ https://www.ssp.sh/brain/snapshotting/ | 不変パーティション・冪等タスク・ディメンションの日次スナップショット（SCD2 の代替） |
| SCD2 harmful | Zach Wilson, *SCD-2 considered harmful! Part 2* | https://blog.dataexpert.io/p/stop-using-slowly-changing-dimensions | SCD2 の運用コスト。日次スナップショットで代替できる条件と、できない条件 |
| dbt Kimball | Jonathan Neo, *Building a Kimball dimensional model with dbt*（dbt Developer Blog, 2023） | https://docs.getdbt.com/blog/kimball-dimensional-model | dbt での標準実装（`generate_surrogate_key`、レイヤ、snapshot） |
| Hightouch 1 | *A Guide to Modern Data Warehouse Modelling — Part 1* | https://hightouch.com/blog/data-warehouse-modelling-part-1 | Kimball → Inmon → OBT の整理 |
| Hightouch 2 | *— Part 2* | https://hightouch.com/blog/data-warehouse-modelling-part-2 | 活用側（BI/Reverse ETL）から逆算した設計 |
| Reis | Joe Reis, *Practical Data Modeling* 連載（Mixed Model Arts） | https://practicaldatamodeling.substack.com/p/table-of-contents ／ https://practicaldatamodeling.substack.com/p/ch-14-the-levels-of-data-modeling | 概念/論理/物理の階層。手法を混ぜて使う前提 |
| 10X | 10X Product Blog, *ディメンショナルモデリング勉強会を実施しました*（2024） | https://product.10x.co.jp/entry/2024/05/08/122512 | Techniques の日本語読解例 |
| BQ nested | Google Cloud, BigQuery スキーマ設計（ネスト・繰り返し列） | https://cloud.google.com/bigquery/docs/best-practices-performance-nested | 非正規化とネストの公式ガイド |
| BQ partition | Google Cloud, パーティション分割テーブルの概要 | https://cloud.google.com/bigquery/docs/partitioned-tables | パーティション/クラスタリングの仕様 |
| dbt incremental BQ | dbt, BigQuery configurations（incremental strategies） | https://docs.getdbt.com/reference/resource-configs/bigquery-configs | `merge` / `insert_overwrite`、`partition_by`、`cluster_by` |
| dbt snapshots | dbt, Snapshots | https://docs.getdbt.com/docs/build/snapshots | `timestamp` / `check` 戦略、`dbt_valid_from/to` |
| dbt contracts | dbt, Model contracts | https://docs.getdbt.com/docs/collaborate/govern/model-contracts | 列・型・制約の契約 |
| dbt structure | dbt, How we structure our dbt projects | https://docs.getdbt.com/best-practices/how-we-structure/1-guide | staging / intermediate / marts |
| MetricFlow | dbt, About MetricFlow（Semantic Layer） | https://docs.getdbt.com/docs/build/about-metricflow | 分子分母を metric として定義 |

## 回ごとの割当

| 回 | 主参照 | 再解釈 |
|---|---|---|
| 00 | DWT ch.1, ch.18; 10 Rules; Manifesto | Reis; Hightouch 1 |
| 01 | DWT ch.2–3; Grain; Matrix; DT#3 #77 #179 | Reis（概念→論理） |
| 02 | DWT ch.4; Fact Tables; DT#50 #95 | — |
| 03 | DWT ch.3 #6; SK; DT#5 #43 #46 #83 #100 #127 | dbt Kimball; ECM |
| 04 | DWT ch.1–2（加法性）; DT#77 | MetricFlow |
| 05 | DWT ch.5; SCD 1–2; DT#15 #152 | FDE; SCD2 harmful; dbt snapshots |
| 06 | DWT ch.7, 8, 10; DT#142 | BQ nested |
| 07 | DWT ch.1; Manifesto | Fowler; Fivetran OBT; Hightouch 2; BQ partition |
| 08 | DWT ch.4; Soul 1–2; DT#135 | ECM; Hightouch 2 |
| 09 | DWT ch.19–20; ETL Subsystems | FDE; dbt incremental BQ |
| 10 | DWT ch.19; ETL Subsystems; Data Quality; DT#108 #164 | dbt Kimball; dbt structure; dbt contracts |
