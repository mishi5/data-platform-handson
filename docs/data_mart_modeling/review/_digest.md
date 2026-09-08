# 横断レビュー用ダイジェスト（自動抽出）

正典に定義のあるモデル名: agg_company_entity, agg_company_rating_daily, br_company_hierarchy, br_member_desired_job_category, dim_agency, dim_agent, dim_audit, dim_channel, dim_company, dim_contract_plan, dim_date, dim_job_category, dim_job_posting, dim_member, dim_member_daily, dim_member_profile_mini, dim_moderation_reason, dim_page_context, dim_review_attributes, dim_scout_sender, fct_application_pipeline, fct_contract_monthly, fct_job_posting_daily, fct_page_view, fct_placement, fct_review, fct_review_moderation, fct_scout, fct_scout_funnel, fct_selection_event, int_review_member_link, obt_scout_funnel


## 00_domain.html

meta: データマート設計 00 ／ 参照: DWT ch.1（4ステップ設計）, ch.18（設計プロセス）, 10 Rules, Manifesto, Design Tip #3 ／ 再解釈: Reis（概念/論理/物理）, Hightouch Part 1
h2: 1. このシリーズが扱うこと / 2. 題材: CareerVoice / 3. ソースシステムの簡易モデル / 4. ビジネスプロセスの棚卸し / 5. 概念 → 論理 → 物理 / 6. 判断基準: このシリーズで固定した設計判断 / 7. 演習 / 8. 参考: 手元の基盤ではどうか / 参照文献
モデル名（正典外）: stg_careervoice__reviews
他回への参照: 01, 02, 03, 04, 05, 08, 11
サンプルID: A01, C001, C002, C003, J002, M001, M002, R001, R002, S001
  is_current: 1
  corporate_number: 1

## 01_grain.html

meta: データマート設計 01 ／ 参照: DWT ch.2–3, Declaring the Grain, The Matrix, Design Tip #3 #77 #179 ／ 再解釈: Reis（概念→論理→物理）
h2: 1. この回が決めること / 2. どこで壊れるか / 3. Kimball の原則 / 4. 現代の再解釈 / 5. BigQuery + dbt での実装 / 6. 判断基準 / 7. 演習 / 8. 参考: 手元の基盤ではどうか / 参照文献
モデル名（正典外）: fct_review_vote, stg_careervoice__applications, stg_careervoice__job_postings, stg_careervoice__scouts, stg_careervoice__selection_events
他回への参照: 02, 04, 05, 06, 08, 09, 10
サンプルID: AG01, C001, C002, J001, J002, K001, M001, M003, P001, R001, S001, S002
  is_current: 1
  audit_key: 4
  dim_agency: 4
  agent_key: 6
  agency_key: 7

## 02_fact_types.html

meta: データマート設計 02 ／ 参照: DWT ch.4, Fact Tables, Design Tip #43 #50 #77 #95 ／ 再解釈: Functional Data Engineering（snapshotting）, dbt BigQuery configs
h2: 1. この回が決めること / 2. どこで壊れるか / 3. Kimball の原則 / 4. 現代の再解釈 / 5. BigQuery + dbt での実装 / 6. 判断基準 / 7. 演習 / 8. 参考: 手元の基盤ではどうか / 参照文献
モデル名（正典外）: stg_careervoice__applications, stg_careervoice__job_postings, stg_careervoice__scouts, stg_careervoice__selection_events
他回への参照: 03, 05, 06, 09, 10
サンプルID: A01, AG01, C001, J001, J002, K001, M001, M003, P001, S001, S002, S003
  audit_key: 7
  dim_agency: 4
  S003: 1
  agent_key: 5
  agency_key: 7

## 03_dimensions.html

meta: データマート設計 03 ／ 参照: DWT ch.3, ch.6, Kimball Dimensional Modeling Techniques (2013), Surrogate Keys (1998), Design Tip #5 #43 #46 #83 #100 #127 #164 ／ 再解釈: dbt Kimball (Neo 2023), ECM (Beauchemin 2023), FDE / スナップショット (Beauchemin 2018)
h2: 1. この回が決めること / 2. どこで壊れるか / 3. Kimball の原則 / 4. 現代の再解釈 / 5. BigQuery + dbt での実装 / 6. 判断基準 / 7. 演習 / 8. 参考: 手元の基盤ではどうか / 参照文献
モデル名（正典外）: snap_members, stg_careervoice__scouts, stg_product
他回への参照: 01, 04, 05, 06, 07, 08, 09, 10
サンプルID: C001, C002, J001, M001, P001, S001
  generate_surrogate_key: 3
  FARM_FINGERPRINT: 7
  is_current: 2
  9999-12-31: 2
  audit_key: 8
  require_partition_filter: 4
  +where: 1
  dim_agency: 6
  dim_member_daily: 8
  corporate_number: 1
  agent_key: 2
  agency_key: 2

## 04_additivity.html

meta: データマート設計 04 ／ 参照: DWT ch.1–2（加法・半加法・非加法）, ch.4（定期スナップショットと半加法残高）, Design Tip #77 ／ 再解釈: MetricFlow（ratio metric）
h2: 1. この回が決めること / 2. どこで壊れるか / 3. Kimball の原則 / 4. 現代の再解釈 — MetricFlow の ratio metric / 5. BigQuery + dbt での実装 / 6. 判断基準 / 7. 演習 / 8. 参考: 手元の基盤ではどうか / 参照文献
モデル名（正典外）: agg_time_dimension, stg_access_logs
他回への参照: 01, 03, 05, 08
サンプルID: AG01, AG02, C001, C002, C003, J001, K001, M001, M002, M003, S001, S002, S003
  is_current: 4
  S003: 2

## 05_scd.html

meta: データマート設計 05 ／ 参照: DWT ch.5, Slowly Changing Dimensions Part 1–2, Design Tip #15 #152 ／ 再解釈: Functional Data Engineering（ディメンションの日次スナップショット）, SCD-2 considered harmful, dbt snapshots
h2: 1. この回が決めること / 2. どこで壊れるか / 3. Kimball の原則 / 4. 現代の再解釈 / 5. BigQuery + dbt での実装 / 6. 判断基準 / 7. 演習 / 8. 参考: 手元の基盤ではどうか / 参照文献
モデル名（正典外）: snap_companies, snap_members, snap_summaries, stg_careervoice__industries, stg_careervoice__prefectures, stg_careervoice__scouts
他回への参照: 03, 06, 09, 10
サンプルID: A01, A02, AG01, C001, C002, M001, P001, R001, S001
  FARM_FINGERPRINT: 3
  is_current: 12
  9999-12-31: 14
  audit_key: 2
  require_partition_filter: 5
  dim_agency: 6
  dim_member_daily: 11
  corporate_number: 11
  agent_key: 4
  agency_key: 3

## 06_bridges.html

meta: データマート設計 06 ／ 参照: DWT ch.7 ch.8 ch.10, Design Tip #142, Kimball Dimensional Modeling Techniques ／ 再解釈: BigQuery ネスト・繰り返し列
h2: 1. この回が決めること / 2. どこで壊れるか / 3. Kimball の原則 / 4. 現代の再解釈 / 5. BigQuery + dbt での実装 / 6. 判断基準 / 7. 演習 / 8. 参考: 手元の基盤ではどうか / 参照文献
モデル名（正典外）: dim_member_with_desired, snap_agents, snap_companies, snap_members, stg_careervoice__agencies, stg_careervoice__companies, stg_careervoice__industries, stg_careervoice__member_desired_job_categories
他回への参照: 03, 05
サンプルID: AG01, AG02, C001, C003, J001, M001, M002, S001, S002, S003
  generate_surrogate_key: 1
  FARM_FINGERPRINT: 3
  is_current: 6
  9999-12-31: 3
  dim_agency: 2
  S003: 5
  agent_key: 8
  agency_key: 2

## 07_star_vs_obt.html

meta: データマート設計 07 ／ 参照: DWT ch.1, A Dimensional Modeling Manifesto (1997) ／ 再解釈: Fowler (Coalesce 2020), Fivetran Star Schema vs. OBT, Hightouch Modelling Part 2, BigQuery パーティション分割テーブル
h2: 1. この回が決めること / 2. どこで壊れるか / 3. Kimball の原則 / 4. 現代の再解釈 / 5. BigQuery + dbt での実装 / 6. 判断基準 / 7. 演習 / 8. 参考: 手元の基盤ではどうか / 参照文献
モデル名（正典外）: int_scout_keyed, obt_page_view, stg_access_logs
他回への参照: 01, 05, 06, 08
サンプルID: C001, C002, M001, M002, S001
  is_current: 3
  audit_key: 1
  require_partition_filter: 8
  +where: 1
  dim_agency: 1

## 08_conformed.html

meta: データマート設計 08 ／ 参照: DWT ch.4, The Soul of the Data Warehouse Part 1–2, Design Tip #135 ／ 再解釈: ECM, Hightouch 2
h2: 1. この回が決めること / 2. どこで壊れるか / 3. Kimball の原則 / 4. 現代の再解釈 / 5. BigQuery + dbt での実装 / 6. 判断基準 / 7. 演習 / 8. 参考: 手元の基盤ではどうか / 参照文献
モデル名（正典外）: agg_member_entity, stg_access_logs
他回への参照: 04, 06, 09, 10
サンプルID: C001, C002, C003, M001, P001, R001, R002, S001
  is_current: 18
  audit_key: 3
  dim_agency: 3
  corporate_number: 1

## 09_incremental.html

meta: データマート設計 09 ／ 参照: DWT ch.19–20, ETL サブシステム #2 #6 #13 #14 #16 #24, Design Tip #43 #164 ／ 再解釈: Functional Data Engineering, dbt の増分戦略（BigQuery configs / incremental strategies / microbatch）
h2: 1. この回が決めること / 2. どこで壊れるか / 3. Kimball の原則 / 4. 現代の再解釈 / 5. BigQuery + dbt での実装 / 6. 判断基準 / 7. 演習 / 8. 参考: 手元の基盤ではどうか / 参照文献
モデル名（正典外）: fct_scout__fingerprint, stg_careervoice__applications, stg_careervoice__reviews, stg_careervoice__scouts, stg_careervoice__selection_events
他回への参照: 02, 05, 10
サンプルID: AG02, C001, C002, J001, K001, M001, M002, P001, S001, S003
  audit_key: 16
  require_partition_filter: 2
  dim_member_daily: 8
  S003: 7

## 10_layers_tests.html

meta: データマート設計 10 ／ 参照: DWT ch.19, Subsystems of ETL Revisited, An Architecture for Data Quality, Design Tip #108 #164 ／ 再解釈: dbt structure, dbt Kimball, dbt model contracts
h2: 1. この回が決めること / 2. どこで壊れるか / 3. Kimball の原則 / 4. 現代の再解釈 / 5. BigQuery + dbt での実装 / 6. 判断基準 / 7. 演習 / 8. 参考: 手元の基盤ではどうか / 参照文献
モデル名（正典外）: dim_product, fct_sales, fct_scout_v1, fct_scout_v2, snap_companies, stg_careervoice__, stg_careervoice__reviews, stg_careervoice__scouts
他回への参照: 01, 03, 04, 05, 06, 07, 08, 09
サンプルID: C002, P001, R001
  generate_surrogate_key: 1
  FARM_FINGERPRINT: 3
  is_current: 1
  9999-12-31: 1
  audit_key: 21
  require_partition_filter: 3
  +where: 1
  dim_agency: 2
  agent_key: 1
  agency_key: 1

## 正典外モデル名の出現回

- agg_member_entity: 08
- agg_time_dimension: 04
- dim_member_with_desired: 06
- dim_product: 10
- fct_review_vote: 01
- fct_sales: 10
- fct_scout__fingerprint: 09
- fct_scout_v1: 10
- fct_scout_v2: 10
- int_scout_keyed: 07
- obt_page_view: 07
- snap_agents: 06
- snap_companies: 05,06,10
- snap_members: 03,05,06
- snap_summaries: 05
- stg_access_logs: 04,07,08
- stg_careervoice__: 10
- stg_careervoice__agencies: 06
- stg_careervoice__applications: 01,02,09
- stg_careervoice__companies: 06
- stg_careervoice__industries: 05,06
- stg_careervoice__job_postings: 01,02
- stg_careervoice__member_desired_job_categories: 06
- stg_careervoice__prefectures: 05
- stg_careervoice__reviews: 00,09,10
- stg_careervoice__scouts: 01,02,03,05,09,10
- stg_careervoice__selection_events: 01,02,09
- stg_product: 03