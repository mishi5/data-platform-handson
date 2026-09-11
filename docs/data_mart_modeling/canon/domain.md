# 題材の正典 — HR クチコミ × 転職エージェント × 直接スカウト

全11本のドキュメントはこのファイルの定義だけを使う。テーブル名・列名・サンプル値をここから逸脱させない。
逸脱が必要なら、その回の report に「正典への変更提案」として書く（勝手に変えない）。

## 1. サービス概要（架空）

サービス名 **CareerVoice**。社員・元社員の企業クチコミを軸に、以下を1つのプラットフォームで提供する。

| 機能 | 概要 | 収益 |
|---|---|---|
| クチコミ | 会員が在籍/退職した企業を8軸で採点しテキストを書く。審査を通ると公開 | 閲覧権限（投稿するか課金するか）で会員を集める |
| 求人 | 企業（またはエージェント）が求人を掲載 | 掲載プラン月額 |
| 直接スカウト | 企業の採用担当が会員へ直接スカウト | 契約プランの月次スカウト枠 |
| エージェントスカウト | 転職エージェントの担当者が会員へスカウト | 入社時の成果報酬（年収 × 料率） |
| 応募・選考 | 検索/スカウト経由で応募、書類→面接→内定→入社 | — |

**分析側が答えたい問い**（各回の演習の種）:
- クチコミ数・評価スコアの推移と、求人応募率・スカウト返信率への影響
- スカウト送信主体（企業 vs エージェント）別の開封→返信→応募→入社ファネル
- 応募から入社までのリードタイムと歩留まり（職種・企業規模・チャネル別）
- 契約枠の消化率、MRR、成果報酬売上
- 会員属性（年収帯・転職意欲）の**変化前後**での行動差

## 2. ソースシステム（OLTP）の簡易モデル

BigQuery には Datastream（CDC）で `src_careervoice` データセットに複製されている前提。
`updated_at` / 論理削除 `deleted_at` を持つ。**列は下記が全てで、これ以外を持ち出さない。**

### 会員・企業（マスタ）

| テーブル | 説明 | 主キー | 列 |
|---|---|---|---|
| `members` | 会員（求職者）。登録者1人が1行 | `member_id` | `email_hash`, `birth_year`, `gender`, `prefecture_code`, `current_company_id`(nullable), `current_job_category_code`, `annual_income_band`(`lt400`/`400_600`/`600_800`/`800_1000`/`ge1000`), `job_change_intent`(`active`/`passive`/`none`), `registered_at`, `updated_at`, `deleted_at` |
| `member_desired_job_categories` | 会員の希望職種（最大3件、優先順位つき） | (`member_id`,`job_category_code`) | `priority`(1..3), `updated_at` |
| `companies` | 企業。クチコミ対象かつ求人・直接スカウトの主体。親会社は自己参照 | `company_id` | `name`, `corporate_number`(法人番号13桁), `industry_code`, `employee_size_band`(`lt50`/`50_299`/`300_999`/`ge1000`), `listing_status`(`listed`/`unlisted`), `hq_prefecture_code`, `parent_company_id`(nullable, 自己参照), `founded_year`, `updated_at` |
| `agencies` | 転職エージェント会社 | `agency_id` | `name`, `tier`(`gold`/`silver`/`standard`), `contract_start_date`, `updated_at` |
| `agents` | エージェント会社の担当者 | `agent_id` | `agency_id`, `name`, `joined_at`, `left_at`(nullable), `updated_at` |
| `job_categories` | 職種マスタ（最大3階層、2階層で終わる枝あり） | `job_category_code` | `name`, `parent_code`(nullable), `level`(1..3) — **不揃い階層**（level 2 で終わる枝がある） |
| `industries` | 業種マスタ | `industry_code` | `name`, `sector_code` |
| `prefectures` | 都道府県マスタ | `prefecture_code` | `name`, `region` |

### クチコミ

| テーブル | 説明 | 主キー | 列 |
|---|---|---|---|
| `reviews` | クチコミ本体（8軸採点＋本文、審査状態を1列で持つ） | `review_id` | `company_id`, `member_id`, `employment_status`(`current`/`former`), `employment_type`(`fulltime`/`contract`/`parttime`), `job_category_code`, `years_of_service_band`(`lt1`/`1_3`/`3_5`/`5_10`/`ge10`), 8軸スコア(各1.0〜5.0, 0.5刻み) `score_compensation`, `score_morale`, `score_openness`, `score_respect`, `score_growth_20s`, `score_long_term_dev`, `score_compliance`, `score_eval_fairness`, `overall_score`(8軸平均ではなく別入力), `title`, `body_text`, `submitted_at`, `status`(`submitted`/`screening`/`published`/`rejected`), `published_at`(nullable), `updated_at` |
| `review_moderation_events` | クチコミ審査の状態遷移ログ | `event_id` | `review_id`, `from_status`, `to_status`, `moderator_id`, `reason_code`(nullable: `defamation`/`pii`/`duplicate`/`low_quality`), `occurred_at` |

### 求人・スカウト・応募

| テーブル | 説明 | 主キー | 列 |
|---|---|---|---|
| `job_postings` | 求人（直接掲載／エージェント経由） | `job_posting_id` | `company_id`, `agency_id`(nullable=エージェント経由求人), `job_category_code`, `title`, `salary_min`, `salary_max`, `prefecture_code`, `employment_type`, `posted_at`, `closed_at`(nullable), `status`(`open`/`closed`), `updated_at` |
| `scouts` | 会員へのスカウト（送信主体は企業 or エージェント担当者） | `scout_id` | `member_id`, `job_posting_id`(nullable), `sender_type`(`company`/`agent`), `sender_company_id`(nullable), `sender_agent_id`(nullable), `template_id`, `sent_at`, `opened_at`(nullable), `replied_at`(nullable), `reply_type`(nullable: `interested`/`declined`) |
| `applications` | 応募（検索から／スカウト経由）。企業スカウトは 1:0〜1、求人未指定のエージェントスカウトは 1:0〜N | `application_id` | `member_id`, `job_posting_id`, `scout_id`(nullable), `source_channel`(`search`/`scout_company`/`scout_agent`/`agent_referral`), `applied_at` |
| `selection_events` | 選考の進行ログ（ステージ到達が1行） | `event_id` | `application_id`, `stage`(`document`/`first_interview`/`final_interview`/`offer`/`accepted`/`hired`/`rejected`/`withdrawn`), `occurred_at`, `note` |
| `placements` | エージェント経由の入社成約（成果報酬） | `placement_id` | `application_id`, `agency_id`, `hired_at`, `annual_income`, `fee_rate`, `fee_amount` |

### 契約・閲覧

| テーブル | 説明 | 主キー | 列 |
|---|---|---|---|
| `contracts` | 企業との契約（プラン・月次スカウト枠・月額） | `contract_id` | `company_id`, `plan_code`(`basic`/`standard`/`premium`), `scout_quota_monthly`, `monthly_fee`, `start_date`, `end_date`(nullable), `status`, `updated_at` |
| `page_views` | 閲覧ログ（表示1回が1行、未ログインあり） | `event_id` | `member_id`(nullable=未ログイン), `session_id`, `page_type`(`company_top`/`company_review`/`job_posting`), `company_id`(nullable), `job_posting_id`(nullable), `review_id`(nullable), `device`(`ios`/`android`/`web`), `referrer_type`(`organic`/`paid`/`direct`/`email`), `is_unlocked`(閲覧権限あり), `viewed_at` |

## 3. ビジネスプロセスとバスマトリクス

**行 = ビジネスプロセス（部門ではない, DT#3）。列 = コンフォームドディメンション。**

| プロセス | ファクト | 型 | 粒度宣言 | date | member | company | job_posting | agent | job_category | channel/junk |
|---|---|---|---|---|---|---|---|---|---|---|
| クチコミ投稿 | `fct_review` | トランザクション | 1行 = 投稿された1クチコミ | 投稿日 | ✗（§6参照） | ✓ | | | ✓ | `dim_review_attributes` |
| クチコミ審査 | `fct_review_moderation` | 累積スナップショット | 1行 = 1クチコミの審査ライフサイクル | 投稿/一次/公開/却下 | | ✓ | | | | `dim_moderation_reason` |
| クチコミ閲覧 | `fct_page_view` | トランザクション（イベント・ファクトレス） | 1行 = 1ページ表示 | 閲覧日 | ✓(nullable) | ✓ | ✓ | | | `dim_page_context` |
| 求人掲載 | `fct_job_posting_daily` | 定期スナップショット | 1行 = 1求人 × 掲載中の1日 | 日 | | ✓ | ✓ | ✓ | ✓ | |
| スカウト送信 | `fct_scout` | トランザクション | 1行 = 送信された1スカウト | 送信日 | ✓ | ✓(送信主体) | ✓ | ✓(送信主体) | | `dim_scout_sender` |
| スカウト反応 | `fct_scout_funnel` | 累積スナップショット | 1行 = 1スカウトの送信→開封→返信→応募 | 送信/開封/返信/応募 | ✓ | ✓ | ✓ | ✓ | | |
| 選考イベント | `fct_selection_event` | トランザクション | 1行 = 1選考ステージ遷移 | 発生日 | ✓ | ✓ | ✓ | ✓ | ✓ | `dim_channel` |
| 応募〜入社 | `fct_application_pipeline` | 累積スナップショット | 1行 = 1応募のパイプライン | 応募/書類/一次/最終/内定/承諾/入社 | ✓ | ✓ | ✓ | ✓ | ✓ | `dim_channel` |
| 契約・枠消化 | `fct_contract_monthly` | 定期スナップショット | 1行 = 1契約 × 1月 | 月 | | ✓ | | | | `dim_contract_plan` |
| 成果報酬 | `fct_placement` | トランザクション | 1行 = 1入社（エージェント経由） | 入社日 | ✓ | ✓ | ✓ | ✓ | ✓ | |

## 4. DWH 側の正典（名前・キー・SCD）

命名: staging `stg_careervoice__<table>`、intermediate `int_<entity>_<verb>`、marts `dim_*` / `fct_*` / `agg_*` / `br_*`（ブリッジ）/ `obt_*`（結合済み配布テーブル。star の下流に置く。正典: `obt_scout_funnel`）、dbt snapshot `snap_*`。
サロゲートキーは `<entity>_key`（INT64 ハッシュではなく `FARM_FINGERPRINT` 由来の INT64、または dbt_utils `generate_surrogate_key` の STRING — **03回で判断を扱う。それ以外の回は `_key` と書くだけで型に踏み込まない**）。
自然キーはソースの `<entity>_id` をそのまま持つ。日付キーは `date_key` INT64 `YYYYMMDD`（DT#5）。未知/未達は `-1`（DT#43。キーが STRING 型のディメンションでは `'-1'`）。
SCD2 のディメンション（`dim_member` / `dim_company` / `dim_agent` / `dim_agency` / `dim_scout_sender` の 5 本）は一律に `<entity>_key`, `valid_from`(TIMESTAMP), `valid_to`(TIMESTAMP, 現行行は `9999-12-31`), `is_current`(BOOL) を持つ。
**全ファクトは `audit_key` を持つ**（下表の FK 列では省略している）。`schema.yml` のテストは `data_tests:`（dbt 1.8+。`tests:` は旧称）で書く。
パーティション用に、ファクトは主要な日付キーと並べて DATE 型の `<role>_date`（例: `sent_date_key` と `sent_date`）を持つ。`partition_by` はこの DATE 列に張る。

### ディメンション

| テーブル | 自然キー | SCD | 主な属性 | 備考 |
|---|---|---|---|---|
| `dim_date` | `date_key` | 0 | `full_date`, `year`, `quarter`, `month`, `iso_week`, `day_of_week`, `is_holiday_jp`, `fiscal_year`(4月始まり), `date_label`(表示名。`-1` 行は `未到達`) | ロールプレイングで `submitted_date`, `published_date` 等に |
| `dim_member` | `member_id` | **2** | `birth_year`, `gender`, `prefecture`, `region`, `current_company_id`, `current_job_category`, `registered_date` | `member_key`, `valid_from`, `valid_to`, `is_current` |
| `dim_member_daily` | (`snapshot_date`,`member_id`) | 日次スナップショット | `snapshot_date`(DATE), `member_id`, `member_key`, `member_profile_mini_key`, `current_company_id`, `current_job_category_code`, `annual_income_band`, `job_change_intent` | FDE 方式の代替（05回）。`partition_by=snapshot_date`, `cluster_by=member_id`, `require_partition_filter=true`。1行 = 1会員 × 1日（その日の終わり時点） |
| `dim_member_profile_mini` | (`annual_income_band`,`job_change_intent`) | — | 5 × 3 = 15行（+ `-1` の未知行） | **ミニディメンション**（DT#127）。速く変わる属性を `dim_member` から分離 |
| `dim_company` | `company_id` | **2** | `corporate_number`(Type0), `name`(Type1で上書き), `industry`, `sector`, `employee_size_band`, `listing_status`, `hq_prefecture`, `parent_company_id`, `founded_year` | **Type 6 相当**: `name` は Type1、他は Type2 |
| `br_company_hierarchy` | (`ancestor_company_key`,`descendant_company_key`) | — | `depth`, `is_leaf`, `is_root` | 企業グループの**不揃い階層ブリッジ**（DWT ch.7） |
| `dim_job_category` | `job_category_code` | 1 | `level1_name`, `level2_name`, `level3_name`(nullable→level2 で埋める), `leaf_level` | 不揃い階層を固定深さに**平坦化**。ブリッジとの比較は 06回 |
| `dim_job_posting` | `job_posting_id` | 1 | `title`, `salary_min`, `salary_max`, `prefecture`, `employment_type`, `posted_date`, `closed_date`, `is_agency_posting` | `company_key` / `agency` は**ファクト側**で結ぶ（雪片化しない） |
| `dim_agent` | `agent_id` | 2 | `agent_name`, `agency_id`, `agency_name`, `agency_tier`, `joined_date`, `left_date` | agency を**平坦化**（雪片にしない）。所属変更で Type2 |
| `dim_agency` | `agency_id` | 2 | `agency_name`, `agency_tier`, `contract_start_date` | `dim_agent` の**縮約（shrunken/rollup）ディメンション**（DWT ch.4）。担当者が特定できないファクト（`fct_job_posting_daily`, `fct_placement` の主軸）はこちらに結ぶ |
| `dim_scout_sender` | (`sender_type`, `sender_id`: company なら `company_id`、agent なら `agent_id`) | 2 | `sender_type`, `sender_name`, `company_industry`(companyのみ), `agency_tier`(agentのみ) | **異種ディメンション（supertype）**。対案「2本の FK + `-1`」は 06回で比較 |
| `dim_review_attributes` | 組合せ | — | `employment_status` × `employment_type` × `years_of_service_band` = 2×3×5 = 30行 | **ジャンクディメンション** |
| `dim_moderation_reason` | `reason_code` | 0 | `reason_name`, `severity` | `-1` = 該当なし |
| `dim_channel` | `source_channel` | 0 | `channel_name`, `channel_group`(`inbound`/`scout`/`agent`) | |
| `dim_page_context` | 組合せ | — | `page_type` × `device` × `referrer_type` × `is_unlocked` = 3×3×4×2 = 72行 | ジャンク |
| `dim_contract_plan` | `plan_code` | 0 | `plan_name`, `scout_quota_monthly`, `monthly_fee` | |
| `dim_audit` | `audit_key` | — | `batch_id`, `source_system`(=`'src_careervoice'`), `loaded_at`(=`run_started_at`), `dbt_invocation_id`, `quality_flag`(`ok`/`estimated`/`suspect`) | **監査ディメンション**（DT#164）。全ファクトに `audit_key` |
| `br_member_desired_job_category` | (`member_key`,`job_category_key`) | — | `priority`, `weighting_factor`(=1/希望数) | **多値ブリッジ**（DT#142）。`member_key` は `dim_member` の**全 SCD2 版に展開**する（ファクトの `member_key` と直結するため） |

### ファクト（メジャーと退化ディメンション）

| テーブル | FK | メジャー | 退化 | 加法性 |
|---|---|---|---|---|
| `fct_review` | `submitted_date_key`, `company_key`(投稿時点), `job_category_key`, `review_attributes_key`, `audit_key` | 8軸 `score_*`, `overall_score`, `body_length_chars`, `review_count`(=1) | `review_id` | **スコアは非加法**（平均のみ意味あり）。`review_count` は加法 |
| `fct_review_moderation` | `submitted_date_key`, `screening_date_key`, `published_date_key`, `rejected_date_key`, `company_key`, `moderation_reason_key`, `audit_key` | `hours_to_screening`, `hours_to_decision`, `moderation_rounds`, `is_published`(0/1), `is_rejected` | `review_id` | 累積スナップショット。行は**更新される** |
| `fct_page_view` | `view_date_key`, `member_key`(-1=匿名), `member_profile_mini_key`, `company_key`, `job_posting_key`, `page_context_key`, `audit_key` | `view_count`(=1) | `event_id`, `session_id`, `review_id` | ファクトレス寄り。**パーティション: `view_date`、クラスタ: `company_key`** |
| `fct_job_posting_daily` | `snapshot_date_key`, `job_posting_key`, `company_key`, `agency_key`(-1=直接掲載), `job_category_key` | `is_open`(=1), `days_since_posted`, `application_count_cum`, `scout_count_cum` | `job_posting_id` | **半加法**: 日をまたいで足せない |
| `fct_scout` | `sent_date_key`, `member_key`, `member_profile_mini_key`(送信時点), `scout_sender_key`, `job_posting_key`, `audit_key` | `scout_count`(=1) | `scout_id`, `template_id` | 加法。**パーティション: `sent_date`、クラスタ: `scout_sender_key`, `member_key`**（07/09 回で共通）。`materialized='incremental'` + `insert_overwrite`（09回）。**star 側のファクトには `require_partition_filter` を付けない**（配布物 `obt_*` にだけ付ける。07回） |
| `fct_scout_funnel`（応募が複数なら最初の応募日） | `sent_date_key`, `opened_date_key`, `replied_date_key`, `applied_date_key`, `member_key`, `scout_sender_key`, `job_posting_key` | `hours_to_open`, `hours_to_reply`, `is_opened`, `is_replied`, `is_interested`, `is_applied` | `scout_id` | 累積スナップショット |
| `fct_selection_event` | `event_date_key`, `application_key`(退化でよい), `member_key`, `company_key`, `job_posting_key`, `agency_key`(`job_postings.agency_id` またはスカウト送信者の所属、無ければ -1), `agent_key`(スカウト経由のみ、無ければ -1), `job_category_key`, `channel_key` | `event_count`(=1) | `application_id`, `event_id`, `stage` | 原子粒度（DT#77）。累積の裏付け |
| `fct_application_pipeline` | `applied_date_key`, `document_date_key`, `first_interview_date_key`, `final_interview_date_key`, `offer_date_key`, `accepted_date_key`, `hired_date_key`, `closed_date_key`, `member_key`, `member_profile_mini_key`(応募時点), `company_key`, `job_posting_key`, `agency_key`, `agent_key`(スカウト経由のみ、無ければ -1), `job_category_key`, `channel_key` | `days_applied_to_offer`, `days_offer_to_hired`, `current_stage`(初期値 `applied`、以降は `selection_events.stage` の値), `is_hired`, `is_rejected`, `is_withdrawn` | `application_id`, `scout_id` | 累積スナップショット |
| `fct_contract_monthly` | `month_date_key`(月初), `company_key`, `contract_plan_key` | `scout_quota`, `scouts_sent`, `scouts_remaining`, `monthly_fee`, `is_active` | `contract_id` | **半加法**（枠残高は月をまたいで足せない、企業をまたいでは足せる） |
| `fct_placement` | `hired_date_key`, `member_key`, `company_key`, `job_posting_key`, `agency_key`, `agent_key`(`applications.scout_id`→`scouts.sender_agent_id` で解決、無ければ -1), `job_category_key` | `annual_income`, `fee_rate`, `fee_amount`(= `annual_income` × `fee_rate`) | `placement_id`, `application_id` | `fee_amount` 加法、`fee_rate` 非加法（加重平均は `SUM(fee_amount)/SUM(annual_income)`） |
| `agg_company_rating_daily` | `date_key`, `rating_date`(DATE, パーティション列), `company_key` | `review_count`, `sum_score_*`(8軸), `sum_overall_score` | | 04回: **平均を持たず和と件数を持つ** |
| `agg_company_entity` | `company_key`(`is_current` 版) | `review_count_total`, `avg_overall_score_90d`(sum/count から算出), `open_postings`, `scouts_sent_30d`, `applications_30d`, `hires_90d`, `mrr` | | 08回: ECM 風のエンティティ集約。`dim_company`（`is_current`）の属性を平坦化して同居させる。`agg_*` は `audit_key` を持たない（元ファクトで辿る） |

## 5. サンプル値（全回で共通に使う）

| 種別 | ID | 値 |
|---|---|---|
| 企業 | `C001` | アオゾラ商事（`industry`=商社, `employee_size_band`=`ge1000`, `listed`, 親会社なし） |
| 企業 | `C002` | ネクスト技研（IT, `50_299`, `unlisted`, 親なし）。**2026-05-01 に `employee_size_band` が `300_999` に変化**（SCD2 の題材） |
| 企業 | `C003` | ヒノデ物流（物流, `300_999`, `unlisted`, **`parent_company_id`=`C001`**） |
| 会員 | `M001` | `registered_at`=2026-01-05 / 1991年生 / 東京 / 現職 `C002` / `annual_income_band`=`400_600`, `job_change_intent`=`passive`。**2026-06-15 に `active`・`600_800` に変化**（＝`dim_member_profile_mini` 側の Type4。`dim_member` の行は増えない）、2026-08-01 に `C001` へ入社（＝`dim_member.current_company_id` の Type2。`dim_member` は 2 行になる） |
| 会員 | `M002` | 1985年生 / 大阪 / 現職 `C001` / `800_1000` / `none`。希望職種 2件（`ENG-BE`, `ENG-DATA`） |
| 会員 | `M003` | 1998年生 / 福岡 / 現職なし / `lt400` / `active` |
| エージェント | `A01` / `AG01` | キャリアブリッジ（`gold`）/ 担当 佐藤 |
| エージェント | `A02` / `AG02` | ワークリンク（`standard`）/ 担当 鈴木 |
| 職種 | `ENG` → `ENG-BE` → `ENG-BE-JAVA` / `ENG` → `ENG-DATA`（level 2 で終端＝不揃い） | |
| 求人 | `J001` | `C001` のデータエンジニア（`ENG-DATA`）、2026-04-01 掲載、直接 |
| 求人 | `J002` | `C002` のバックエンド（`ENG-BE-JAVA`）、`A01` 経由 |
| クチコミ | `R001` | `M001` → `C002`、2026-03-10 投稿、`former`/`fulltime`/`1_3`、`overall_score`=3.5、**03-11 に `low_quality` で差し戻し1回**（`screening`→`submitted`）、2026-03-12 公開。`review_moderation_events` は 3 行（`submitted→screening` 3/10、`screening→submitted` 3/11、`submitted→published` 3/12）。`moderation_rounds`=2（審査担当者が判定を下した回数＝差し戻しと公開） |
| クチコミ | `R002` | `M002` → `C001`、2026-04-02 投稿、却下（`defamation`） |
| スカウト | `S001` | `C001`(company) → `M001`、`J001`、2026-06-20 送信、06-21 開封、06-22 返信 `interested` |
| スカウト | `S002` | `AG01`(agent) → `M003`、`J002`、2026-06-25 送信、未開封 |
| スカウト | `S003` | `AG02`(agent) → `M002`、`J001`、2026-06-18 送信、未開封（希望職種2件の会員宛＝ブリッジの二重計上の題材） |
| 応募 | `P001` | `M001` → `J001`、`scout_company`、2026-06-23 応募 → 07-01 書類 → 07-08 一次 → 07-15 最終 → 07-20 内定 → 07-22 承諾 → 08-01 入社 |
| 契約 | `K001` | `C001` `premium`（枠 200/月, 300,000円）2026-01-01〜 |

**想定規模**（コスト・物理設計の議論で使う。断定ではなく前提）: 会員 300 万、企業 5 万、エージェント 2 千、クチコミ累計 500 万、`page_views` 日次 2,000 万行、スカウト日次 10 万件、応募日次 5 千件。

日付は全て 2026 年。時刻は JST。`M001` が 6/15 に属性変化 → 6/20 にスカウト受信 → 6/23 応募、という並びが **as-of join（05回）の核**になる。

## 6. 設計上の固定判断（回をまたいで守る）

| 論点 | 決定 | 理由 | 扱う回 |
|---|---|---|---|
| クチコミの匿名性 | `fct_review` は `member_key` を**持たない**。会員属性は投稿時点の `dim_member_profile_mini` 相当を**ジャンク化した `dim_review_attributes`** に落とす。会員×クチコミの結合が要る分析は `int_review_member_link`（アクセス制限データセット）に隔離 | 公開分析からの個人特定リスク（少人数企業では属性で特定できる） | 00, 01, 03 |
| 企業属性の時点 | ファクトには**イベント時点**の `company_key`（SCD2 版）を持つ。現在値で見たい場合は `dim_company` の `is_current` 版へ `company_id` で再結合 | 「投稿当時の規模」と「現在の規模」を両方答えられる | 05 |
| 集約テーブルの平均 | `avg_*` を持たず `sum_*` + `count` を持つ | 再集約可能性 | 04, 08 |
| 累積スナップショットの裏に原子ファクト | `fct_application_pipeline` の裏に `fct_selection_event` を必ず置く | サマリーだけは危険（DT#77） | 02 |
| 未達マイルストーン | `date_key = -1`、`dim_date` に `-1` 行（`full_date` = NULL, 表示名 `未到達`） | NULL 外部キー禁止（DT#43） | 02, 03 |
| ディメンションの雪片化 | しない（agency は `dim_agent` に平坦化、job_category も平坦化） | BigQuery の結合コストより可読性 | 03, 06 |
| 増分の単位 | パーティション単位の `insert_overwrite`、ルックバック 3 日 | 冪等性（Functional DE） | 09 |
