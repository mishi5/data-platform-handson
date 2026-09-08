# 10 レイヤ・命名・契約・テスト・監査 — レビュー

対象: `docs/data_mart_modeling/html/10_layers_tests.html`
ブリーフ: `docs/data_mart_modeling/briefs/10.md`
執筆者報告: **無し**（`reports/10_report.md` が存在しない）。`canon/style.md`「出力前の自己チェック」はレビュー側で全項目実施した。

---

## 1. ブリーフ準拠表

| 節 | 必須項目 | 判定 | 該当箇所 |
|---|---|---|---|
| §1 | 層の表（staging / intermediate / marts(dim,fct,agg,br,obt) / snapshots） | ✅ | L66–82。8 行すべて存在 |
| §1 | 層 × 役割 × マテリアライズ × テストの種類 | ✅ | L70 の 4 列 |
| §1 | 命名規約（domain.md §4）を正本として転載 | ✅ | L84–103。10 行。`stg_careervoice__<table>` / `int_<entity>_<verb>` / `dim_*` / `snap_*` / `<entity>_key` / `<entity>_id` / `date_key` / `<role>_date` / `-1` / `valid_from`–`valid_to`–`is_current` / `audit_key` を網羅 |
| §2(a) | `mart_scout_v2` 的なモデル名バージョン埋め込みで両方が本番参照される | ✅ | L107–111（`fct_scout_v2` で表現。`obt_scout_funnel` は旧版のまま／Looker Studio だけ新版） |
| §2(b) | staging に集約が入る／marts に型変換が入る | ✅ | L113–125。両方向とも記述あり |
| §2(c) | `not_null` だけで粒度が保証されず `fct_review` に `R001` が2行 | ✅ | L127–143 |
| §2(d) | `dim_audit` が無く、どの実行が壊れた行を入れたか追えない | ✅ | L145–161 |
| §3 | ETL 34 サブシステムのうちマート設計に効くもの（プロファイリング / SCD マネージャ / SK 生成 / 遅延到着 / 監査ディメンション / 集約ビルダー）を表で | ✅ | L169–182。6 つ＋Error Event Tracking の 7 行。番号・原名は原典と完全一致（検証済） |
| §3 | DT#108「設計完了の条件」（ビジネスユーザーのレビュー、バスマトリクス） | ✅ | L188–207。3 種の聴衆・バスマトリクス先行・1/3 の時間配分、いずれも原典どおり |
| §3 | Data Quality の「スクリーン」概念 | ✅ | L209–229。定義・2 責務・3 種スクリーン・3 択、すべて原典どおり |
| §4 | dbt structure（`stg_` は 1 ソース 1 モデル・型変換のみ、`int_` は結合・ピボット、marts は公開面） | ✅ | L269–277。許す 4 変換／結合・集約の禁止理由も原典どおり |
| §4 | dbt Kimball 記事の dim/fct 分離 | ⚠️ | L279–283。テストの有無の指摘は正確だが「4 ステップ」の記述が原典に無い（→ Important I2） |
| §4 | model contracts（`enforced: true`, `data_type`, `constraints`）で列契約を BI へ保証 | ✅ | L285–287。BigQuery の強制範囲（`not_null` のみ強制、`primary_key`/`foreign_key` は宣言のみ、`unique`/`check` は宣言不可）は dbt docs と完全一致（検証済） |
| §4 | `versions:` による改版と `deprecation_date` | ✅ | L289 |
| §5(a) | `fct_scout` の contract（列・型） | ✅ | L297–361。domain.md の 10 列を過不足なく列挙。型も 03回の割当と整合 |
| §5(a) | 粒度テスト `dbt_utils.unique_combination_of_columns` | ✅ | L365–370 |
| §5(a) | `relationships`（`member_key → dim_member`、`-1` の扱い `where: "member_key != -1"`） | ✅ | L389–397、L419 |
| §5(a) | 加法性チェック `dbt_utils.expression_is_true`: `scouts_remaining = scout_quota - scouts_sent` | ⚠️ | 加法性テスト自体は L373–377（`scout_count = 1`）で満たすが、ブリーフの式は §3 の表（L224）にしか無く、`fct_contract_monthly` は本文に 1 度も出ない（→ Minor M8） |
| §5(a) | `accepted_values` for `sender_type` | ✅ | L408–415（`dim_scout_sender` 側に置いたのは正典的に正しい） |
| §5(b) | `audit_key()` マクロ（`invocation_id` + `run_started_at`） | ⚠️ | L443–476。回内は整合するが 03回の同名マクロと非互換（→ Critical C2） |
| §5(c) | `versions:` 設定と `latest_version`、`ref('fct_scout', v=1)` | ✅ | L515–551。`deprecation_date` の version エントリ直置き・`include: all`/`exclude:`・`fct_scout.v1` セレクタ・生成リレーション名、すべて dbt docs と一致（検証済） |
| §5(d) | `dbt source freshness`（`loaded_at_field: updated_at`） | ❌ | L555–598。`filter:` の位置が誤り（→ Critical C1） |
| §5(e) | `exposures` で BI ダッシュボードを依存に登録 | ✅ | L600–636 |
| §6 | 「テストを置く層と種類」の表 | ✅ | L640–656。source/staging/intermediate/dim/fct/agg/obt/snapshots の 8 行、必須・任意・置かない（理由）付き |
| §6 | 「改版 vs 上書き」の表 | ✅ | L658–674。8 行 |
| §7(a) | `fct_application_pipeline` のテスト列挙と対応する壊れ方 | ⚠️ | L678–699。9 行。FK 16 本の数え上げは正しいが `P001` の行数が誤り（→ Important I3） |
| §7(b) | `dim_company` に `industry` の分類を1階層足す変更は改版か上書きか | ✅ | L701–717 |
| §7(c) | `int_review_member_link` の層・データセット・テスト | ✅ | L719–747 |
| §8 | `dbt_logs_analysis` / `news_pipeline` への言及 3〜5 行（＋種 1 行） | ✅ | L749–760。実ファイルと突き合わせて **全 5 項目とも事実**（下記「§8 の事実確認」参照） |
| 図 | なし | ✅ | `check_svg.py` → `0 errors, 1 warnings`（「`<svg>` が見つからない」＝正常） |

### §8 の事実確認（`dbt_logs_analysis` / `news_pipeline` 実ファイルと突き合わせ）

| 本文の主張 | 実ファイル | 判定 |
|---|---|---|
| `mart_url_performance` / `_v2` / `_incremental` の 3 本が別モデル名で並ぶ | `models/marts/` に 3 ファイルとも存在 | ✅ |
| `exposures.yml` の `weekly_performance_report` が `_incremental` と `_v2` の両方に依存 | `exposures.yml` の `weekly_performance_report.depends_on` が両方を列挙 | ✅ |
| `_incremental` は `unique_key=['url_path','date']` を持つが `models/marts/schema.yml` に項目自体が無くテスト 0 件 | config は該当行どおり。`schema.yml` の `models:` は `mart_url_performance` と `mart_error_analysis` の 2 件のみ | ✅ |
| `models/staging/sources.yml` に `loaded_at_field` と `freshness` が無い | 両キーとも不在 | ✅ |
| `exposures.yml` は 3 件（dashboard / application / notebook） | `url_performance_dashboard`(dashboard) / `error_monitoring_alert`(application) / `weekly_performance_report`(notebook) | ✅ |
| `dbt_utils` を `packages.yml` に入れて…（＝まだ入っていない前提） | `packages.yml` 自体が存在しない | ✅ |
| `news_pipeline` の `summaries.scoring_version`、`raw_articles.collected_at` | `news_pipeline/infra/bigquery.tf` に両列あり（`scoring_version` INT64 NULLABLE / `collected_at` TIMESTAMP REQUIRED） | ✅ |

### 正典（domain.md）準拠

本文に出るテーブル名を全抽出して照合。domain.md に無いのは以下だけで、いずれも問題なし。

- `dim_product` / `fct_sales` … dbt Kimball 記事（AdventureWorks）の引用として明示（L281）
- `fct_scout_v1` / `fct_scout_v2` … dbt の版付きモデルが生成する物理リレーション名
- `snap_companies` … `snap_*` 規約に沿った例示

列名・ID（`C001`〜`C003`, `M001`, `R001`, `S001`〜`S003`, `P001`, `J001`/`J002`, `K001`）も domain.md §5 の範囲内。固定判断（§6）との衝突なし。`fct_review` が `member_key` を持たない匿名性の判断は §7(c) で契約に翻訳されており、むしろ強化されている。

### 原典との照合（すべて WebFetch で確認）

| 主張 | 原典 | 判定 |
|---|---|---|
| 34 サブシステムの群と件数「抽出(3)・クレンジングとコンフォーム(5)・デリバリ(13)・管理(13)」 | Subsystems of ETL Revisited と完全一致 | ✅ |
| 番号と名前: 1 Data Profiling / 5 Error Event Tracking / 6 Audit Dimension Creation / 9 SCD Manager / 10 Surrogate Key Generator / 16 Late Arriving Data Handler / 19 Aggregate Builder / 22 Job Scheduler / 29 Lineage and Dependency | 全 9 件が原典の名称・番号どおり | ✅ |
| 「残る 27 は…インフラ側」 | 誤り | ❌ I1 |
| DT#108 著者 Bob Becker / 2008 | Number 108, December 3, 2008, By Bob Becker | ✅ |
| 3 種の聴衆・IT レビューは 3NF 志向でDM教育が要る・まずバスマトリクス・広い層では約 1/3 を実演に | 原文どおり | ✅ |
| DT#108 の締め（軽微な修正／感動しない／業務の反射／うまくいった印） | 原文どおり | ✅ |
| 品質スクリーン＝診断フィルタ、成功時は副作用なし、失敗時に 2 責務 | 原文どおり | ✅ |
| 列 / 構造 / 業務ルールスクリーンの定義と例 | 原文どおり（Jack Olson の分類） | ✅ |
| error event fact の粒度＝1 スクリーンイベント、error event detail の粒度＝1 エラーに関わった 1 フィールド | Figure 1 の `grain=screen event` / `grain=error field in each error event` と一致 | ✅ |
| 3 択で原典が推すのはタグ付け通過。停止は手動介入、保留は「いつ戻るか不明で整合性が疑わしい」 | 原文どおり | ✅ |
| least biased estimator で埋め、監査ディメンションに記述。NULL や 0 より合計が実態に近い | 原文どおり | ✅ |
| 監査ディメンションの粒度＝1 つの異なる監査条件、完璧な実行なら 1 行、その日の全ファクト行が同じ行を指す | Figure 2 の `1 record for each distinct audit condition` ＋本文と一致 | ✅ |
| 「メタデータを通常のデータに格上げし、BI ツールの画面の第一階層に出す」 | DT#164 原文 "elevates metadata to the status of ordinary data and makes this metadata available at the top level of any BI tool user interface" の忠実な訳 | ✅ |
| out-of-bounds 指標を行ヘッダに 1 つ足すだけで品質評価付きレポートになる | DQ 白書 Figure 3（Instrumented Report） | ✅ |
| DT#164 の 2 分類と列（ETL マスタ版番号・通貨換算版・配賦ロジック版／欠損・推定値・ありえない値） | 原文どおり | ✅ |
| 「単純に始めよ、最初から理想主義になるな、優雅さで賞を狙うな」 | "keep it simple and not get too idealistic in the beginning" / "Don't try to win the elegance award" | ✅ |
| DQ 白書の監査ディメンション完全版（completeness / validation / out-of-bounds / screens failed / record modified / 3 つの時刻） | Figure 2 の列と一致 | ✅ |
| dbt structure: staging の許す 4 変換、結合・集約の禁止と理由 | 原文どおり | ✅ |
| dbt structure: intermediate「DAG を狭め、テーブルを広くする」「入力は複数・出力は 1 つ」「`ephemeral` 既定／本番外スキーマに view を置き権限を絞る」 | 原文どおり | ✅ |
| dbt structure: marts は業務エンティティの平易な名前、`fct_`/`dim_` に触れない | 原文どおり | ✅ |
| dbt Kimball 記事のテスト（`product_key`/自然キー/`sales_key` の not_null+unique、FK の not_null）と、relationships・契約・加法性の不在 | 原文どおり | ✅ |
| 「4 ステップ（… スキーマの選択 …）」 | 原典に無い（Part 1〜7 構成） | ❌ I2 |

### dbt / BigQuery 仕様の照合（すべて WebFetch で確認）

| 主張 | 判定 |
|---|---|
| `arguments:` は dbt 1.10.5 以降、それ以前はテスト名直下（`config:` の位置は同じ） | ✅ 完全一致 |
| `where` はテスト対象（`model`）だけを `(select * from … where …) dbt_subquery` に差し替え、`to:` には効かない | ✅ |
| 版付きモデルのファイル名 `<model_name>_v<v>.sql`／最新版は接尾辞無しでもよい／生成リレーションは `<model_name>_v<v>` | ✅ |
| 旧名維持は該当版に `config: alias:` | ✅ |
| `deprecation_date` を `versions:` の各エントリに直置きできる | ✅ |
| `latest_version` / `ref('fct_scout', v=1)` / `fct_scout.v1` セレクタ | ✅ |
| `deprecation_date` は dbt Core 1.6 | ✅ |
| 破壊的変更は版付き＝エラー、版無し＝警告 | ✅ |
| BigQuery の制約: `not_null` のみ強制、`primary_key`/`foreign_key` は宣言のみ、`unique`/`check` は宣言不可 | ✅ |
| 制約の変更が破壊的扱いになるのは 1.6 以降 | ✅（ただし「足す」は dbt の定義に含まれない → M7） |
| `freshness: null` で 1 テーブルだけ無効化 | ✅ |
| `freshness` / `loaded_at_field` を `config:` 配下に置くのは新しめ（それぞれ 1.9 / 1.10） | ✅ |
| `filter` の位置 | ❌ C1 |
| `latest_version_pointer` の存在 | ✅ 実在（dbt v1.12 以降）。ただし導入版を確認していない → M1 |
| `invocation_id` は実行ごとの UUID、`run_started_at` は UTC の Python datetime | ✅ |

### 数値の検算

| 本文の計算 | 検算 | 判定 |
|---|---|---|
| §2(c) `R001` の審査イベントが 2 行（submitted→screening→published） | 遷移は 2 本 | ✅ |
| §2(c) `SUM(review_count)`=2、`SAFE_DIVIDE(SUM(overall_score), SUM(review_count))`=3.5 | `overall_score`=3.5 の行が 2 行 → 7.0 / 2 = 3.5 | ✅ |
| §3「34 のうち残る 27」 | 34 − 7 = 27 | ✅（算術のみ。中身は I1） |
| §7(a) `fct_application_pipeline` の FK 16 本 | 日付 8 ＋ `member_key`/`member_profile_mini_key`/`company_key`/`job_posting_key`/`agency_key`/`agent_key`/`job_category_key`/`channel_key` = 16 | ✅ |
| §7(a) 日付キー 8 本 → `dim_date` | applied/document/first_interview/final_interview/offer/accepted/hired/closed = 8 | ✅ |
| §7(a) `P001` が 7 行に増える | `selection_events` は 6 行 | ❌ I3 |
| §5(a) 契約の列数 vs domain.md の `fct_scout` | 10 列で過不足なし | ✅ |

### HTML / 体裁

| 項目 | 判定 |
|---|---|
| `<title>` = `レイヤ・命名・契約・テスト・監査 — データマート設計 10` | ✅ |
| `p.meta` あり・形式どおり | ✅ |
| h2 が 1〜8 ＋「参照文献」の 9 本 | ✅ |
| CSS 変数名がシリーズ骨格どおり | ✅ |
| `<` / `>` のエスケープ漏れ（`<pre><code>` 内を機械チェック） | ✅ 0 件 |
| 表 13 個すべてが `.table-wrap` で包まれている | ✅ 13/13 |
| 前後回へのリンクなし（回番号参照のみ） | ✅ |
| `check_svg.py` | ✅ 0 errors |

---

## 2. 指摘一覧

### Critical

#### C1. §5(d) `filter:` の位置が誤り。`page_views` の全件スキャン回避が効かない（L578–585）

現状:

```yaml
      - name: page_views
        config:
          loaded_at_field: viewed_at
          freshness:
            warn_after: {count: 1, period: hour}
            error_after: {count: 3, period: hour}
          # 全件スキャンを避ける（日次 2,000 万行）
          filter: viewed_at >= timestamp_sub(current_timestamp(), interval 2 day)
```

`filter` は **`freshness:` ブロックの内側のキー**であり、`loaded_at_field` / `freshness` と並ぶ兄弟ではない（dbt docs `resource-properties/freshness` で確認）。この位置では `filter` は `freshness` に渡らず、`dbt source freshness` は `page_views` を**フィルタ無しで走査する**。本文コメントが宣言している目的（日次 2,000 万行の全件スキャン回避）が達成できないうえ、`filter` を効かせる書き方の正本としてこの回が参照される。

修正案:

```yaml
      - name: page_views          # updated_at を持たない
        config:
          loaded_at_field: viewed_at
          freshness:
            warn_after: {count: 1, period: hour}
            error_after: {count: 3, period: hour}
            # 全件スキャンを避ける（日次 2,000 万行）
            filter: viewed_at >= timestamp_sub(current_timestamp(), interval 2 day)
```

（`filter` はソースレベルの `config: freshness:` にも同じ入れ子で書ける。ソース既定に `filter` を置くとテーブルごとに列名が違って壊れるので、この回の書き方どおりテーブル側に置くのが正しい。その旨を 1 文添えると `+where` の議論と対になる。）

#### C2. §5(b) の `audit_key()` が 03回 §5(e) の同名マクロと非互換。正本回として上書き宣言が無い（L470–476）

この回の定義:

```jinja
{% macro audit_key(quality_flag='ok') -%}
    {%- do ref('dim_audit') -%}
    farm_fingerprint(concat('{{ invocation_id }}', '|', '{{ quality_flag }}'))
{%- endmacro %}
```

`03_dimensions.html` L557–560 の定義:

```jinja
{% macro audit_key(quality_flag_expr) -%}
    FARM_FINGERPRINT(CONCAT('{{ invocation_id }}', '|', {{ quality_flag_expr }}))
{%- endmacro %}
```

- **引数の意味が逆**。03回は SQL 式を受け取る前提で `{{ audit_key("'ok'") }}`（L586）と `{{ audit_key('quality_flag') }}`（L567、列参照）で呼ぶ。この回のマクロに 03回の呼び方をそのまま渡すと `concat('<uuid>', '|', ''ok'')` になり **BigQuery で構文エラー**、`audit_key('quality_flag')` は `'quality_flag'` というリテラルになって全行が同じキーに潰れる。
- **`quality_flag` の語彙が違う**。03回の `dim_audit` は `['ok', 'late_arriving_dimension', 'missing_natural_key']`、この回は `['ok', 'estimated', 'suspect']`。どちらが正典か本文からは決まらない。
- **`source_system` の値が違う**。03回は `'src_careervoice'`、この回は `'careervoice'`。
- **`loaded_at` の作り方が違う**。03回は `CURRENT_TIMESTAMP()`（＝行ごと・実行ごとにぶれる）、この回は `run_started_at`（＝実行単位で確定）。この回のほうが正しいが、その理由が書かれていない。

01回 L433 / 02回 L275 / 05回 L608 / 08回 L453 / 09回 L373 は「10 回で定義する」と注記しており、この回が正本であることは確定している。**正本側が 03回の先行定義に一言も触れていないのが欠陥**。回内の整合（マクロと `dim_audit` が同じ `FARM_FINGERPRINT(CONCAT(invocation_id, '|', flag))` を作ること、INT64 が契約の `data_type: int64` と合うこと、`{% do ref() %}` が依存辺を張ること）はすべて正しいので、直すのは記述だけでよい。

修正案: §5(b) の 1 段落目の直後に次の趣旨を 3 文以内で足す。

> 03回 §5(e) はこのマクロの下書きを載せている。正本はこちらで、変更点は 3 つ。引数を SQL 式から値に変える（`{{ audit_key('suspect') }}`）、`quality_flag` を `ok` / `estimated` / `suspect` の 3 値に固定する（Data Quality 白書の「タグを付けて通す」に対応）、`loaded_at` を `CURRENT_TIMESTAMP()` から `run_started_at` に変える（同一実行の全ファクト行が同じ時刻を指すため）。

あわせて `source_system` を `'src_careervoice'` に揃える（domain.md §2 のデータセット名が `src_careervoice`）。または 03回を直す提案を report に書く。

### Important

#### I1. §3 の aside「残る 27 は…インフラ側」は原典の歪み（L184–186）

現状: 「34 のうち、残る 27 は『ジョブスケジューラ』『バックアップ』『リネージと依存』『並列化』のようなインフラ側である。」

原典の 34 のうち、選ばれなかった 27 には次が含まれる。いずれもインフラではなく、**このシリーズが実際にマート設計として扱ってきた主題**そのものである。

| # | サブシステム | このシリーズでの対応 |
|---|---|---|
| 11 | Hierarchy Manager | `dim_job_category` の平坦化 / `br_company_hierarchy`（06回） |
| 12 | Special Dimensions Manager | ジャンク `dim_review_attributes` / ミニ `dim_member_profile_mini`（03回） |
| 14 | Surrogate Key Pipeline | ファクト側の as-of join によるキー解決と `-1`（05回・09回） |
| 15 | Multi-Valued Bridge Table Builder | `br_member_desired_job_category` と `weighting_factor`（06回） |
| 4, 7, 8 | Data Cleansing / Deduplication / Data Conformance | 08回のコンフォームドディメンション |
| 13, 17, 18 | Fact Table Builders / Dimension Manager / Fact Table Provider | 02回・08回 |

修正案: 「残る 27 はインフラ側」を撤回し、次の 2 点に分ける。

> 選ばなかった 27 のうち、11（階層マネージャ）・12（特殊ディメンション）・14（SK パイプライン）・15（多値ブリッジ）は 03・05・06 回で既に扱った。この回で残るのは 22（ジョブスケジューラ）・23（バックアップ）・29（リネージ）・31（並列化）のような、モデルの形ではなく実行環境を規定する群である。dbt を採ると 22 と 29 は道具に置き換わるが、1（データプロファイリング）だけは代われない。

#### I2. §4「Neo の記事は 4 ステップ（…）」は原典に無い構成（L281）

現状: 「Neo の記事は 4 ステップ（ビジネスプロセスの特定 → ファクトとディメンションの特定 → スキーマの選択 → モデルの作成と文書化）を AdventureWorks で実演し」

実際の構成は Part 1〜7（Setup / Identify the business process / Identify the fact and dimension tables / Create the dimension tables / Create the fact table / Document the dimensional model relationships / Consume dimensional model）で、**「スキーマの選択」に相当する段は存在しない**。「4 ステップ」という数え方も記事には無い（Kimball の 4 ステップ設計プロセス＝プロセス・粒度・ディメンション・ファクト とも一致しない）。この節の他の記述（置かれているテスト、relationships・契約・加法性の不在）は原典どおりで正しいので、直すのは冒頭の 1 句だけでよい。

修正案:

> Neo の記事は AdventureWorks の受注を題材に、ビジネスプロセスの特定 → ファクトとディメンションの特定 → ディメンションの作成 → ファクトの作成 → 関係の文書化、という順で実装を追う。ディメンションには…

#### I3. §7(a) 「`P001` が 7 行に増える」は検算不一致（L686）

domain.md §2 の `selection_events.stage` は `document` / `first_interview` / `final_interview` / `offer` / `accepted` / `hired` / `rejected` / `withdrawn` の 8 値で、**`applied` を含まない**（`fct_application_pipeline.current_stage` の定義も「初期値 `applied`、以降は `selection_events.stage` の値」＝ `applied` はイベントではない）。domain.md §5 の `P001` は「6-23 応募 → 07-01 書類 → 07-08 一次 → 07-15 最終 → 07-20 内定 → 07-22 承諾 → 08-01 入社」なので、`selection_events` は **6 行**。`applications` に素朴に結合すると `P001` は 6 行になる。

修正案: 「`P001` が 7 行に増える」→「`P001` が 6 行に増える（`selection_events` に `applied` は無く、書類〜入社の 6 イベント）」。02回 L468 の記述と数が合う。

### Minor

#### M1. §5(c) `latest_version_pointer` の導入版を確かめていない（L553）

「新しめの config なので、使う前に導入版を dbt docs で確認する」は、`style.md` の自己チェック「原典を WebFetch で実際に読む」を読者に外注している。実在する config で、**dbt v1.12 以降**。
修正案: 「常に最新版を指すビューを自動生成する `latest_version_pointer`（dbt v1.12 以降）を使う」。

#### M2. 参照文献の抜けと URL 表記のずれ（L764–774）

- §4・§5(c) は model versions ドキュメント、§5(d) は source freshness ドキュメント、§5(a) は `dbt_utils` に全面的に依拠しているが、参照文献に URL が無い。
- dbt structure の URL が `…/how-we-structure/1-guide-overview` で、`canon/references.md` の表記 `…/how-we-structure/1-guide` と食い違う（実在するのは前者）。

修正案: 参照文献に `https://docs.getdbt.com/docs/collaborate/govern/model-versions` と `https://docs.getdbt.com/reference/resource-properties/freshness` を足す。references.md 側の URL 誤りは report に「正典への変更提案」として書く（この回では references.md を直さない）。

#### M3. 3 文を超える段落が 3 箇所

| 箇所 | 文数 | 修正案 |
|---|---|---|
| L276（§4 aside modern） | 5 | 「ただし marts の命名では、dbt の 2 つの公式文書が食い違う。」＋対比 2 文で切り、「ファクトとディメンションの区別は…」を別段落に |
| L705（§7(b) 解答例 1 段落目） | 4 | 「ただし `contract: enforced: true` を張っているなら…」を別段落へ |
| L723（§7(c) 解答例 1 段落目） | 4 | 「ただし `ephemeral` にはしない。」以降を別段落へ |

#### M4. §2(c) 「（偶然一致する）」は誤り（L135）

行の複製は分子と分母を同率で増やすので、平均が一致するのは**構造的**であって偶然ではない。直後の段落の「平均が正しく見えるので気づかない」（L143）とも噛み合わない。
修正案: コメントを `-- 3.5（分子も分母も 2 倍になるので変わらない）` に。

#### M5. §5(a) 2 つ目の YAML で `member_key` が重複定義に見える（L389–397）

1 つ目のブロック（L335–339）で `member_key` に `data_type` と `constraints` を書き、2 つ目のブロックで同じ `- name: member_key` を `data_tests:` 付きで再掲している。断片であることは文脈で分かるが、そのままコピーすると YAML のキー重複になる。
修正案: 2 つ目のブロックの先頭に `# 上の columns: の該当エントリに data_tests: を足す（再掲は差分のみ）` を 1 行入れる。

#### M6. §5(b) `dim_audit.sql` がマクロを使わず同じ式をベタ書きしている（L462 と L475）

`dim_audit` 自身がマクロを呼ぶと自己参照になるため直書きにしたのは正しいが、**片方だけ直すと全ファクトの `audit_key` が `dim_audit` に解決しなくなる**という結合の弱さが本文に書かれていない。L508 の aside が `relationships` テストでこの手の事故を捕まえると書いているので、そこに 1 文足すだけで済む。
修正案: L508 の aside の末尾に「`dim_audit` 側は自己参照を避けるためマクロを呼ばず同じ式を直書きしている。式を変えるときは 2 箇所を同時に直す。この `relationships` テストはその取り違えも捕まえる。」

#### M7. §6「制約（`not_null`）を足す・外す｜破壊（1.6 以降）」は dbt の定義より広い（L667）

dbt が破壊的変更として扱うのは "Removing or **modifying** one of the constraints on an existing column"（1.6 以降）で、**新規に足す**ことは列挙されていない。実務上は `not_null` を足すと NULL 前提の下流が壊れるので「新版」の判断自体は妥当だが、契約列の記述が dbt の挙動と読める。
修正案: 契約での扱いを「外す・変える＝破壊（1.6 以降）／足す＝dbt は検知しないが下流は壊れる」に分ける。

#### M8. §5(a) の加法性テストがブリーフの例（`fct_contract_monthly`）に届いていない

ブリーフ §5(a) が指定した `scouts_remaining = scout_quota - scouts_sent` は §3 の表（L224）にしか無く、`fct_contract_monthly` は本文に 1 度も出ない。`fct_scout` に載せるのは正典違反になるので `scout_count = 1` に置き換えた判断は正しいが、**「加法性チェック」の代表例は半加法メジャーの側にある**ので、§5(a) の末尾に 5 行の追加ブロックが欲しい。
修正案:

```yaml
  - name: fct_contract_monthly
    data_tests:
      # 半加法メジャーの整合（枠残高 = 枠 - 消化）
      - dbt_utils.expression_is_true:
          arguments:
            expression: "scouts_remaining = scout_quota - scouts_sent"
```

#### M9. §3 の DT#108 の「」引用が原文 2 文の圧縮（L190）

「モデルが書けた時点ではまだ終わっていない。最後の主要な設計活動はレビューと検証である」は、原文 "we'd like to remind you that you're not quite done when you think you might be. The last major design activity that needs to be completed is a review and validation of the dimensional data model" を 2 文に畳んだもので、内容は忠実だが逐語ではない。同じ節の L206（DT#108 の締め）は「」を使わず地の文で書いているので、そちらに揃えたほうが一貫する。
修正案: 「」を外し「Bob Becker は、モデルが書けた時点ではまだ終わっておらず、最後の主要な設計活動はレビューと検証だと位置づける。」に。

#### M10. §5(a) aside の `+where` は書ける場所を明示すべき（L440）

「`+where` は `dbt_project.yml` にパス単位で既定値を書ける」だけだと、`models:` 配下に書いて効かない事故を誘う。`where` はテストの config なので、`dbt_project.yml` では **`data_tests:` 配下**（またはテストの `config:`）にしか効かない。
修正案: 「`+where` は `dbt_project.yml` の `data_tests:` 配下にパス単位で既定値を書けるが（`models:` 配下に書いても効かない）、ファクトごとにパーティション列名が違うので…」。

#### M11. `reports/10_report.md` が無い

`style.md` の自己チェック最終項目（「report を `reports/NN_report.md` に書いた」）が未達。00〜09 は全て存在する。references.md の URL 誤り（M2）や、ブリーフの `scouts_remaining` を `fct_scout` に置けない理由（M8）は report に書くべき事項なので、修正時にあわせて起こすこと。

---

## 3. 総合判定

**REVISE**

- Critical: 2（C1 `filter` の位置、C2 `audit_key()` の 03回との非互換）
- Important: 3（I1 「残る 27 はインフラ側」、I2 dbt Kimball 記事の「4 ステップ」、I3 `P001` の行数）
- Minor: 11

原典（ETL 34 サブシステムの番号と名前、DT#108、DT#164、Data Quality 白書）と dbt 仕様（`arguments:` の 1.10.5、`where` の適用範囲、BigQuery の制約強制範囲、`versions:` 一式、破壊的変更の定義）は、細部までほぼ完全に一致している。§8 の `dbt_logs_analysis` / `news_pipeline` への言及も全項目が実ファイルどおりで、事実として書ける水準にある。落とすべきは、(1) 動作に直結する `filter` の位置、(2) この回が正本になるはずの `audit_key()` が先行回の定義を無言で覆している点、(3) 原典の要約が 2 箇所で実体からずれている点、(4) `P001` の行数の 4 点。いずれも局所修正で済む。
