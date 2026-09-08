# 04 加法性と派生指標 — レビュー

対象: `docs/data_mart_modeling/html/04_additivity.html`
ブリーフ: `docs/data_mart_modeling/briefs/04.md`／報告: `docs/data_mart_modeling/reports/04_report.md`

判定: **REVISE**（critical=2 / important=5 / minor=7）

---

## 1. ブリーフ準拠表

| 節 | 必須項目 | 判定 | 該当箇所 |
|---|---|---|---|
| §1 | 3分類の表（加法 / 半加法 / 非加法） | ✅ | h3「メジャーの3分類（DWT ch.4）」の3行表 |
| §1 | `review_count` 加法 | ✅ | メジャー分類表 1行目 |
| §1 | `score_*` 非加法 | ✅ | 同 2行目 |
| §1 | `scouts_remaining` 半加法（時間で足せない） | ✅ | 同 4行目「半加法（企業 ○ / 時間 ✗）」 |
| §1 | `fee_rate` 非加法 | ✅ | 同 9行目 |
| §1 | `avg_overall_score` は持たない | ✅ | 同 3行目 + 末尾の `agg_company_entity` 但し書き |
| §2(a) | 平均の平均 / `agg_company_rating_daily` / `C002` 3日分（件数 1,1,10）を実計算 | ✅ | 表 + `11.0/3=3.67` vs `33.5/12=2.79`（検算一致） |
| §2(b) | `fct_contract_monthly.scouts_remaining` を 1〜3月で SUM | ✅ | 600→440 への置換は裁定済み。600 は上限値として本文に残っている（ただし I4） |
| §2(c) | `COUNT(DISTINCT member_id)` を日次で持って週次に足す | ✅ | `member_key` で実施。2/2/2→6 vs 実 2（検算一致） |
| §3 | 加法性の定義 | ✅ | 表1行目 + Techniques 引用の aside |
| §3 | 半加法の「期末値・平均残高」 | ✅ | 表「残高の扱い」行 |
| §3 | 非加法は分子分母を分けて持つ | ✅ | 表「非加法メジャーの分解」行 + 引用 |
| §3 | パーセンタイルは再集約不可 | ✅ | 表末尾の DT#77 行 + 直後の段落 |
| §4 | MetricFlow の ratio metric としての位置づけ | ✅ | 導入段落 + modern aside |
| §4 | `metrics.yml` の例（`reply_rate = replied / sent`） | ⚠️ | 内容は充足。ただし YAML が現行 spec で不正（C2） |
| §5 | `agg_company_rating_daily`（`SUM(score_*)`, `COUNT(*)`） | ⚠️ | モデル SQL あり。正典の `rating_date` を欠く（I1） |
| §5 | 月次への再集約 SQL | ✅ | `SAFE_DIVIDE(SUM(sum_overall_score), SUM(review_count))` |
| §5 | 企業グループ（`br_company_hierarchy` 経由で `C001`+`C003`） | ⚠️ | SQL あり。SCD2 キーの扱いが未宣言（I2） |
| §5 | 半加法 `scouts_remaining` を月末値で出す `QUALIFY ROW_NUMBER()` | ✅ | 四半期末 = 120（`SUM` の 440 ではない）。検算一致 |
| §5 | `APPROX_QUANTILES` は原子ファクトから直接、の指針 | ✅ | h3「パーセンタイルは原子ファクトから直接（DT#77）」 |
| §6 | 「メジャー → 分類 → マートに持つ形 → BI で計算する形」の表 | ✅ | 10行。`agg_company_entity` の例外行も裁定どおり |
| §7(a) | `overall_score` の企業別・年別中央値に何を持つか | ✅ | 「何も新しく持たない」+ SQL |
| §7(b) | `SUM(is_open)` の意味と月末時点の掲載数 | ⚠️ | 延べ掲載日数 = 30（検算一致）。SQL 内コメントが事実誤認（C1） |
| §7(c) | 返信率を送信主体別に見る時の分子分母の粒度 | ✅ | 12%/24% の平均 18% vs 全体 24/150=16%（検算一致） |
| §8 | `dbt_logs_analysis` / `news_pipeline` へ 3〜5行 | ✅ | 4行。列名・マクロは実物と一致（`mart_url_performance.sql`, `macros/performance_metrics.sql` を照合済み） |
| 図 | 比較図型・2パネル・同じ3日分の数値・結果の差だけ accent・ノード ≤9 | ✅ | ノード6・accent は右結果ノード + 直前の矢印 + `WEIGHTED` タグのみ |
| 図 | `check_svg.py` 0 errors | ✅ | `0 errors, 0 warnings`（自分でも実行） |
| HTML | `<title>` 形式 / `p.meta` / 8節 / `&lt;` エスケープ / `.table-wrap` | ✅ | table 6件すべて `.table-wrap`、`<pre><code>` 内に生の `<` なし、h2 は 1〜8 + 参照文献 |
| 正典 | `domain.md` に無いテーブル名・列名 | ✅ | grep で拾ったテーブル名は全て正典（+ §8 の手元基盤テーブル）に存在 |

---

## 2. 指摘一覧

### Critical

#### C1. §7(b) の SQL コメントが BigQuery の評価順を逆に書いている

該当（`html/04_additivity.html` §7(b) の `<pre>` 内）:

```sql
    -- QUALIFY は集約の前に評価されるので、GROUP BY は外側の SELECT に置く
```

BigQuery（GoogleSQL）の評価順は `FROM → WHERE → GROUP BY と集約 → HAVING → WINDOW → QUALIFY → DISTINCT → ORDER BY → LIMIT`。**`QUALIFY` は集約の「後」**に評価される。だから同じ SELECT に `GROUP BY` を置くと、`QUALIFY` の中の `f.snapshot_date_key` はグループ化列でも集約式でもないため参照できない。CTE に分けた判断は正しいが、理由が正反対に書かれている。

執筆者自身の `reports/04_report.md`「迷った判断」4 では「BigQuery の `QUALIFY` は集約の後に評価されるため」と正しく書いており、HTML 側だけが逆。読者はこの記事しか読まないので、この1行が誤りとして残る。

修正案:

```sql
    -- QUALIFY は GROUP BY / HAVING の後に評価されるので、同じ SELECT に GROUP BY を置くと
    -- snapshot_date_key（非グループ列）を QUALIFY で参照できない。月末行の絞り込みを CTE に分ける
```

#### C2. §4 の MetricFlow YAML が現行 spec でパースされない（legacy と v1.12 の混成）

該当: §4 の2つの `<pre><code>` ブロック。冒頭に `# models/marts/schema.yml（dbt v1.12+ の spec）` と明記されているが、書かれている形はどちらの spec とも一致しない。

dbt docs（[Migrate to the latest YAML spec](https://docs.getdbt.com/docs/build/latest-metrics-spec) / [Semantic models](https://docs.getdbt.com/docs/build/semantic-models) / [Simple metrics](https://docs.getdbt.com/docs/build/simple) / [Ratio metrics](https://docs.getdbt.com/docs/build/ratio)）を確認した結果:

| 要素 | 本文の書き方 | legacy spec | latest spec (v1.12+) |
|---|---|---|---|
| コンテナ | `semantic_models:`（トップレベル）+ `model: ref('...')` | ✅ これが legacy | ❌ `models: - name: X` の下の `semantic_model:` |
| 時間軸 | `defaults: agg_time_dimension:` | ✅ legacy | ❌ `semantic_model: agg_time_dimension:`（`defaults:` は無い） |
| エンティティ | `entities: - name: member / type: foreign / expr: member_key` | ✅ legacy | ❌ `columns: - name: member_key / entity: {type: foreign, name: member}` |
| ディメンション | `dimensions: - name: sent_date / type: time / type_params.time_granularity` | ✅ legacy | ❌ `columns: - name: sent_date / dimension: {type: time}` |
| 集約の定義 | セマンティックモデル直下の `metrics:`（`type: simple` + `agg` + `expr`） | ❌ legacy は `measures:` のみ | ✅ latest |
| ratio | メトリクス直下の `numerator:` / `denominator:` | ❌ legacy は `type_params:` 配下で `{measure: ...}` | ✅ latest |
| `non_additive_dimension` | simple metric 配下 | ❌ legacy は measure 配下 | ✅ latest |

つまり **legacy のコンテナに latest のメトリクス定義を入れている**。legacy パーサは `semantic_models[].metrics` を知らず、latest パーサは `semantic_models:` トップレベルを受け付けない。どちらでも落ちる。`# dbt v1.12+ の spec` というコメントも誤りになる。

ratio metric を `numerator:` / `denominator:` 直下に書いた判断（report の「迷った判断」6）は **latest spec として正しい**。直すべきはコンテナ側。

修正案（latest spec に統一。1本目）:

```yaml
# models/marts/_marts__models.yml（dbt v1.12+ の spec）
models:
  - name: fct_scout_funnel
    description: "1行 = 1スカウトの送信→開封→返信→応募"
    semantic_model:
      enabled: true
      agg_time_dimension: sent_date
      primary_entity: scout
      columns:
        - name: member_key
          entity:
            type: foreign
            name: member
        - name: scout_sender_key
          entity:
            type: foreign
            name: scout_sender
        - name: sent_date
          dimension:
            type: time
      metrics:
        - name: scouts_sent
          label: スカウト送信数
          type: simple
          agg: count_distinct
          expr: scout_id
        - name: scouts_replied
          label: スカウト返信数
          type: simple
          agg: sum
          expr: is_replied

metrics:
  - name: reply_rate
    label: スカウト返信率
    description: "返信数 ÷ 送信数。どの粒度で切っても分子分母を先に集計してから割る"
    type: ratio
    numerator: scouts_replied
    denominator: scouts_sent
```

2本目（`fct_contract_monthly`）も同じ形に直す。`non_additive_dimension` は simple metric 配下のままでよい（latest spec で正）。

なお legacy 一本で書き直す選択肢もあるが、その場合は `measures:` + トップレベル `metrics:` + `type_params: {numerator: {measure: ...}}` になり、docs が deprecated としている形になる。latest に寄せるほうがよい。

---

### Important

#### I1. `agg_company_rating_daily` のモデル SQL / schema.yml が正典の `rating_date` を欠く

正典 `canon/domain.md` §4 は執筆後に更新され、`agg_company_rating_daily` のキー欄が `date_key`, **`rating_date`(DATE, パーティション列)**, `company_key` になっている。§4 の共通規約「ファクトは主要な日付キーと並べて DATE 型の `<role>_date` を持つ。`partition_by` はこの DATE 列に張る」も同様。

本文の §5 モデル SQL は `{{ config(materialized='table') }}` のみで、`rating_date` を選択しておらず `partition_by` も無い。schema.yml 例にも列が無い。正典違反。

修正案:

```sql
-- models/marts/agg_company_rating_daily.sql
{{ config(
    materialized='table',
    partition_by={'field': 'rating_date', 'data_type': 'date'},
    cluster_by=['company_key']
) }}

WITH review AS (
    SELECT * FROM {{ ref('fct_review') }}
)

SELECT
    submitted_date_key AS date_key,
    submitted_date     AS rating_date,
    company_key,
    COUNT(*) AS review_count,
    ...
FROM review
GROUP BY date_key, rating_date, company_key
```

schema.yml にも `rating_date`（`not_null`）を1行足す。

#### I2. 企業グループ再集約が SCD2 サロゲートキーで結合・グループ化していて、正典の `C002` で破綻する

該当: §5「企業グループへ再集約する（`br_company_hierarchy` 経由）」。

```sql
JOIN {{ ref('br_company_hierarchy') }} AS b
    ON a.company_key = b.descendant_company_key
...
GROUP BY b.ancestor_company_key, d.year
```

`agg_company_rating_daily.company_key` は `fct_review` 由来＝**投稿時点の SCD2 版**（正典 §6「企業属性の時点」）。`dim_company` は Type 2 で、`C002` は 2026-05-01 に `employee_size_band` が変わって 2 版になる。この状態でブリッジを `company_key` で結ぶと、

- ブリッジが `is_current` 版のキーだけを持つなら → 5/1 以前の `C002` 行が **join で落ちる**（沈黙する欠損）
- ブリッジを全 SCD2 版に展開するなら → `GROUP BY b.ancestor_company_key` が版ごとに分かれ、`WHERE d.year = 2026` の年次集計が **`C002` について2行に割れる**

例に選ばれた `C001`+`C003` は 2026 年に属性変化が無いので表面化しないが、SQL としては正しい結果を返さない。正典は `br_member_desired_job_category` について「`member_key` は `dim_member` の全 SCD2 版に展開する」と明記しており、企業ブリッジ側の前提が本文にも正典にも無い。

修正案（どちらか）:

a. 耐久キーで束ねる:

```sql
JOIN {{ ref('br_company_hierarchy') }} AS b
    ON a.company_key = b.descendant_company_key
JOIN {{ ref('dim_company') }} AS anc
    ON b.ancestor_company_key = anc.company_key
...
GROUP BY anc.company_id, d.year   -- SCD2 版ではなく自然キーで束ねる
```

b. 本文に前提を1文足す:「`br_company_hierarchy` は `dim_company` の全 SCD2 版に展開して作る（`br_member_desired_job_category` と同じ理由）。年次で束ねるときは `ancestor_company_key` ではなく `company_id` でグループ化する」。

あわせて「**集計式が月次のときと1文字も変わらない**」という一文は、この前提込みで初めて成立するので、注記を添えたい。

#### I3. DWT の章番号が3箇所で誤っている（ch.4 → ch.2）

DWT 3rd ed. の構成は ch.2 =「Kimball Dimensional Modeling Techniques Overview」、ch.4 =「Inventory」。§3 に verbatim 引用した Techniques PDF の "Basic Fact Table Techniques"（Additive/Semi-Additive/Non-Additive Facts、Periodic Snapshot Fact Tables、Aggregate Fact Tables or Cubes）は **ch.2 の内容そのもの**。

| 箇所 | 現在 | 正しい |
|---|---|---|
| §1 h3「メジャーの3分類（DWT ch.4）」 | ch.4 | ch.1（primer の Facts for Measurement）／ch.2（技法定義） |
| §3 表「加法・半加法・非加法の分類（DWT ch.4）」 | ch.4 | ch.2 |
| §5 h3「集約ファクト（DWT ch.4 の aggregate fact table）」 | ch.4 | ch.2（ch.4 Inventory に aggregate fact table の節は無い） |

§3 表の「定期スナップショット（DWT ch.4）」は、ch.4 Inventory が定期スナップショットと半加法残高の主戦場なので **そのままでよい**。`p.meta` の「DWT ch.1, ch.4」はブリーフ指定どおりなので変更不要だが、上記3箇所の章番号は直す。style.md「数値・技法名は原典どおり。DWT 3rd ed. の章番号で参照する」に照らして必要。

#### I4. `scout_quota` の分類が §2(b) の表と矛盾する

§1 のメジャー分類表は `scouts_remaining`, `scout_quota` を同じ行にまとめて「半加法（企業 ○ / 時間 ✗）」としている。一方 §2(b) の表は `SUM` 行で **`scout_quota` = 600 を太字で出し**、直後の本文は `SUM(scouts_sent)=160` を「正しい」、`SUM(scouts_remaining)=440` を「存在しない枠」と評価するが、**600 には触れない**。読者には「太字の 600 は正しいのか間違いなのか」が判定できない。

さらに同じ §1 の表で `monthly_fee`（同じく1ヶ月あたりの定額）は「加法（時間で足すと期間売上）」と分類されている。`scout_quota` を時間で足した 600 も同じ意味で「1〜3月に付与された総枠」であり、扱いが割れている。

修正案（どちらか）:

a. `scout_quota` を `monthly_fee` と同じ「加法（時間で足すと期間付与枠）」に移し、`scouts_remaining` だけを半加法の行に残す。§2(b) 本文に「`SUM(scout_quota)=600` は『1〜3月に付与された総枠』として意味がある。壊れているのは `scouts_remaining` の 440 だけ」を1文足す。

b. `scout_quota` を半加法のまま残すなら、§2(b) の表の 600 セルに `—`（または打ち消し）を入れ、本文で「600 も足してはいけない」と明示する。

a を推す。本文が既に「200 × 3 = 600 にしかならない」と 600 を意味のある上限として使っているため。

#### I5. MetricFlow のメトリクス名 `scouts_sent` が2つのブロックで衝突する

§4 の1本目（`scout_funnel`）は `scouts_sent`（`agg: count_distinct`, `expr: scout_id`）、2本目（`contract_monthly`）も `scouts_sent`（`agg: sum`, `expr: scouts_sent`）を定義している。MetricFlow のメトリクス名はプロジェクト内で一意でなければならず、同一プロジェクトに両方を置くと duplicate resource でパースが落ちる。

修正案: 2本目を `contract_scouts_sent`（label「契約枠の消化数」）にリネームする。ついでに「同じ『送信数』でも `fct_scout_funnel` 由来と `fct_contract_monthly` 由来では意味が違うので名前を分ける」の1文を添えると、§6 の「名前を分ける」という主張とつながる。

---

### Minor

#### M5-1. 3文超の段落が7つある（style.md「1段落は3文まで」）

| 節 | 文数 | 冒頭 |
|---|---|---|
| §2(a) | 4 | 「0.88 ポイントずれる。…」 |
| §2(c) | 4 | 「3倍の過大計上。…」 |
| §5（期末値） | 5 | 「`K001` について `scouts_remaining` = 120…」 |
| §6 末尾 | 4 | 「運用の落とし所を1つ。…」 |
| §7(a) | 4 | 「何も新しく持たない。…」 |
| §7(b) | 4 | 「`SUM(is_open)` は延べ掲載日数…」 |
| §7(c) | 4 | 「分子分母は同じ行から出すのが原則。…」 |

体言止めの短文が多く読みづらくはないが、規約は3文。§5 の5文段落だけでも割りたい。

#### M5-2. §5 の `SAFE_DIVIDE` の説明が同節の schema.yml と矛盾する

「その企業のその月にクチコミが 0 件でも（分母 0 でも）エラーではなく `NULL` が返る」とあるが、`agg_company_rating_daily` は 0 件の日に行を立てないので、その企業月は **グループ自体が現れない**（分母 0 は発生しない）。同じ §5 の schema.yml も `review_count` に `accepted_range: min_value: 1` を張っている。

修正案:「`SAFE_DIVIDE` は、後段で `dim_date` 側から 0 件月を埋める（`LEFT JOIN` / timespine）ときに分母 0 を通すための保険。素の集計では `review_count >= 1` が保証されるので発火しない」に置き換えるか、この1文を落とす。

#### M5-3. §6 の行ラベル「在籍フラグ」が題材と合っていない

`is_open` は求人の掲載フラグ、`is_active` は契約の稼働フラグで、どちらも「在籍」ではない（CareerVoice で在籍を表すのは `employment_status` = `current`/`former`）。「状態フラグ（`is_open`, `is_active`）」に直す。

#### M5-4. DT#77 の引用が原文の途中で切れている（省略記号なし）

- 1つ目: 原文は "**While** you can roll up detailed data in unpredictable ways, the converse is not true – you can't magically explode summary data into its underlying components." — 本文は "While" を落として小文字始まりにしている。
- 2つ目: 原文は "…then both the data model and ETL system must change **to accommodate new data**." — 本文は "must change." で終えている。

verbatim 引用として枠に入れている以上、`&hellip;` を置くか原文どおりにする。意味は変わっていないので Minor。

#### M5-5. パーティション列を使わないフィルタが2箇所

正典 §4 は「`partition_by` は DATE 列（`<role>_date`）に張る」と決めている。

- §5 の期末値 SQL: `WHERE month_date_key BETWEEN 20260101 AND 20260301` → パーティション列は `month_date` なので全パーティションスキャン。`WHERE month_date BETWEEN DATE '2026-01-01' AND DATE '2026-03-01'` を併記したい。
- §7(b): `dim_date` 結合で月を絞っている → `fct_job_posting_daily` 側は `snapshot_date` で絞れる。

§8 で「原子から都度計算する経路を残すか」を論じる回なので、スキャン量の書き方は揃えておきたい。

#### M5-6. §2(c) のスカウト受信日が正典のサンプル値と噛み合わない

「`M001` と `M003` が 6/20・6/21・6/22 の各日にスカウトを受けたとする」とあるが、正典のサンプルは `S001`（`C001`→`M001`, 6/20）、`S002`（`AG01`→`M003`, **6/25**）、`S003`（`AG02`→`M002`, 6/18）。「とする」で仮定を明示しているので誤りではないが、既存 ID から外れた日付を新たに置いている。`M002`（`S003`）を含めて既存3件で「送信日が3日に散る／会員は3人」の形に組み替えると、直後の HLL の窓（6/20〜6/26）とも整合する。

#### M5-7. 図の右パネル上段のハイフンが減算に読める

`3.5 / 5.0 / 25.0 - 1 / 1 / 10` の `-` が「25.0 − 1」に見える。`sum 3.5 / 5.0 / 25.0` と `count 1 / 1 / 10` の2行に分けるか、中黒（`・`）で区切る。図の他の要素・`check_svg.py`（0 errors, 0 warnings）は問題なし。

---

## 3. 正典・報告に関する補足（指摘ではない）

- 報告の「正典への変更提案」1（`agg_company_rating_daily` の DATE 列）と 3（`fee_amount = annual_income × fee_rate`）は正典に反映済み。1 は反映済みゆえに本文が追随できていない（I1）。
- 提案 2（HLL スケッチ列）は正典に足さない裁定。本文が CTE 内で完結させているのは裁定どおりで、修正不要。
- §2(b) の 600→440 置換、`agg_company_entity` の但し書きは裁定どおり。
- 正典の執筆後更新のうち、`dim_agency` / `dim_member_daily` / `S003` / 全ファクト `audit_key` については本文が触れていないため矛盾は生じていない（`S003` のみ M5-6 で言及）。`<role>_date` 列は §5 の `sent_date`（`fct_scout`）、§4 の `month_date` / `sent_date` で正しく使えている。

---

## 総合判定

**REVISE**

- Critical 2: C1（BigQuery の `QUALIFY` 評価順の事実誤認）、C2（MetricFlow YAML が legacy/latest の混成でパースされない）
- Important 5: I1（`rating_date` 欠落＝正典違反）、I2（SCD2 キーでの企業グループ再集約）、I3（DWT 章番号 ch.4→ch.2 が3箇所）、I4（`scout_quota` の分類と §2(b) の 600 の矛盾）、I5（メトリクス名 `scouts_sent` の衝突）
- Minor 7

数値例（平均の平均 3.67 / 2.79 / 差 0.88、残枠 180+140+120=440・期中平均 146.67、ユニーク 2/2/2→6 vs 2、延べ掲載日数 30、送信主体別 12%/24% の平均 18% vs 全体 24/150=16%）は**全て検算一致**。図はブリーフ指定どおりの比較図で `check_svg.py` 0 errors。HTML 骨格・エスケープ・`.table-wrap`・テーブル名の正典準拠も問題なし。修正対象は上記 SQL コメント1行、YAML 2ブロック、章番号3箇所、`agg` モデル定義、企業グループ SQL の前提、`scout_quota` の分類。
