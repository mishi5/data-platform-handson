# 03 ディメンションの設計 — レビュー

対象: `docs/data_mart_modeling/html/03_dimensions.html` / ブリーフ `briefs/03.md` / 報告 `reports/03_report.md`
レビュー日: 2026-09-08
レビュー担当: 執筆者とは別。報告は参照したが判定の根拠にはせず、HTML と原典を直接読んで判定した。

オーケストレータ裁定済み（指摘対象外）: `dim_date` の役割数 8 本／`dim_date.date_label` と STRING キーの `'-1'`。

---

## 1. ブリーフ準拠表

| 節 | ブリーフの必須項目 | 判定 | 該当箇所 |
|---|---|---|---|
| §1 | 技法一覧表（技法 / 定義 / CareerVoice での適用先） | ✅ | 「技法の一覧」表（8行） |
| §1 | サロゲートキー | ✅ | 同表1行目。`dim_member` / `dim_company` / `dim_agent` / `dim_scout_sender` |
| §1 | 自然キー | ✅ | 同表2行目。耐久キーの説明つき |
| §1 | 退化（`review_id`, `scout_id`, `application_id`） | ✅ | 同表3行目。`event_id` / `session_id` / `template_id` も収録 |
| §1 | ロールプレイング（`dim_date` in `fct_application_pipeline`） | ✅ | 同表4行目。正典どおり8本（7マイルストーン＋`closed_date_key`） |
| §1 | ジャンク（`dim_review_attributes` 30行、`dim_page_context` 72行） | ✅ | 同表5行目 |
| §1 | ミニディメンション（`dim_member_profile_mini` 15行） | ✅ | 同表6行目 |
| §1 | 監査（`dim_audit`） | ✅ | 同表7行目 |
| §1 | `-1` 行 | ⚠️ | 同表8行目。列挙に `dim_agency` が無い → **Important-1** |
| §2(a) | `dim_member` の Type2 肥大 → ミニへ | ⚠️ | 3つの壊れ方は揃うが「正典の形では全部消える」が誤り → **Important-5** |
| §2(b) | `dim_date` 無しで年度・営業日がバラける | ✅ | 4行の対比表 |
| §2(c) | 未達を NULL にして `LEFT JOIN` と `COUNT` がずれる（DT#43） | ⚠️ | 例示 SQL の注釈が自己矛盾 → **Important-4** |
| §3 | SK の理由（ソースキーの再利用・SCD2・**性能**・未知値） | ❌ | 7行表に結合性能の理由が無く、「7つ挙げた」も原典と不一致 → **Important-3** |
| §3 | DT#100「キーは単純に」 | ✅ | `aside kimball`。9理由のうち3つを引用 |
| §3 | ミニディメンションの設計（属性の帯化、行数＝組合せ数） | ✅ | 「ミニディメンションの設計」3段＋DT#127 の但し書き |
| §4 | ECM の「ディメンションに指標を持たせてよい」 | ✅ | `aside modern` ＋ `agg_company_entity` への隔離 |
| §4 | dbt Kimball（`generate_surrogate_key`） | ✅ | 3方式の整理と「何が変わり何が変わらないか」 |
| §5(a) | `dim_date` 生成（`GENERATE_DATE_ARRAY` + `-1` 行 UNION） | ✅ | 構文・列数・型とも整合（末尾セミコロン無し） |
| §5(b) | `dim_review_attributes` を `CROSS JOIN` で生成 | ⚠️ | 内容は ✅ だが末尾セミコロンで dbt が落ちる → **Critical-1** |
| §5(c) | `dim_member_profile_mini` | ⚠️ | 同上 → **Critical-1** |
| §5(d) | `FARM_FINGERPRINT` と `generate_surrogate_key` の比較表（型/衝突/可読性/結合コスト） | ✅ | 6観点。事実関係は全て検証済み（§4 参照） |
| §5(d) | 結論表「SCD2 の4本だけ SK、Type0/1 は自然キー」 | ⚠️ | 表はあるが正典の `dim_agency`（SCD2）が漏れ → **Important-1** |
| §5(e) | `dim_audit` の列と `invocation_id` マクロ | ✅ | `macros/audit_key.sql` ＋ `dim_audit.sql` ＋ `fct_scout` 抜粋 |
| §6 | 「変化速度 × カーディナリティ → 置き場所」の表 | ✅ | 8行表＋タイブレーク表 |
| §7(a) | `scouts.template_id` は退化かディメンションか | ✅ | 判断基準表の行を明示 |
| §7(b) | `is_unlocked` はジャンクかメジャーか | ✅ | 反論つきで却下 |
| §7(c) | `M001` の 6/15 の変化 | ✅ | 時系列表つき |
| 図 | なし（技法一覧・置き場所は表） | ✅ | SVG 0個。`check_svg.py` 0 errors |
| 体裁 | 8節構成・`<title>`・`p.meta` | ✅ | §1〜§8＋参照文献 |

---

## 2. 正典準拠（grep による機械照合）

本文の `dim_*` / `fct_*` / `agg_*` / `stg_*` / `snap_*` / `src_*` を全て抽出し `canon/domain.md` と突合した。

- 抽出 25 個中、`domain.md` に無いのは 3 個のみ:
  - `snap_members` / `stg_careervoice__scouts` — §4 の命名規約（`snap_*` / `stg_careervoice__<table>`）に適合。個別名は正典に列挙が無いだけ。report の提案6で明示済み。**問題なし**
  - `stg_product` — dbt Kimball 記事のコード引用内。**問題なし**
- 列名の逸脱: 無し。`dim_member` の属性（`birth_year`, `gender`, `prefecture`, `region`, `current_company_id`, `current_job_category`, `registered_date`）は正典と完全一致。`dim_date.date_label`、STRING キーの `'-1'` も正典どおり。
- サンプル ID（`M001`, `C001`, `C002`, `S001`, `P001`, `J001`, `R001`, `ENG-DATA` …）の使い方も正典と矛盾なし。
- **逆方向の欠落**が2件ある（正典が更新されたのに本文が追随していない）→ Important-1 / Important-2。

---

## 3. 数値の検算（全て自分で計算し直した）

| 本文の数値 | 検算 | 判定 |
|---|---|---|
| `dim_review_attributes` = 2 × 3 × 5 = 30 | `current`/`former`=2、`fulltime`/`contract`/`parttime`=3、`lt1`/`1_3`/`3_5`/`5_10`/`ge10`=5 → 30 | ✅ |
| `dim_page_context` = 3 × 3 × 4 × 2 = 72 | `page_type`=3、`device`=3、`referrer_type`=4、`is_unlocked`=2 → 72 | ✅ |
| `dim_member_profile_mini` = 5 × 3 = 15 | `annual_income_band`=5、`job_change_intent`=3 → 15（＋既定行で実装は16） | ✅（表記の揺れは Minor-9） |
| 年 600 万行 / 5年で 3,000 万行超 | 300万 × 2 = 600万、× 5 = 3,000万（＋基底300万） | ✅ |
| ECM 日次スナップショット 約 11 億行/年 | 3,000,000 × 365 = 1,095,000,000 | ✅ |
| 属性10個 × 各5値 の直積 = 977 万行 | 5¹⁰ = 9,765,625 | ✅ |
| FARM_FINGERPRINT 衝突: 1,000万行で約 3×10⁻⁶ | n²/(2·2⁶⁴) = 10¹⁴ / 3.689×10¹⁹ = 2.71×10⁻⁶ | ✅ |
| FARM_FINGERPRINT 衝突: 10億行で約 2.7% | 10¹⁸ / 3.689×10¹⁹ = 0.0271 | ✅ |
| MD5 衝突: 10億行で 10⁻²¹ 台 | 10¹⁸ / (2·3.403×10³⁸) = 1.47×10⁻²¹ | ✅ |
| `dim_date` の `-1` 行込みで列数10・型一致 | 両ブランチとも10列、`day_of_week` STRING / `is_holiday_jp` BOOL まで整合 | ✅ |
| `dim_member` 既定行の12値 | 12列 12値、`member_key` INT64 / `registered_date` DATE / `valid_*` TIMESTAMP まで一致 | ✅ |
| singular test の 16 | 5×3＋既定行 = 16 | ✅ |
| 2026年の祝日18件 | 成人の日 1/12、海の日 7/20、敬老の日 9/21、スポーツの日 10/12、春分 3/20、秋分 9/23、振替 5/6 を個別確認 | ✅ |

**検算不一致は無し。**

---

## 4. Kimball 原典・再解釈記事との照合（全て原典を再取得して確認）

取得したもの: SK(1998) 全文 / DT#5 PDF / DT#100 PDF / Techniques PDF（`pdftotext -layout`）/ DT#43 / DT#46 / DT#83 / DT#127 / ECM / dbt Kimball / dbt-utils `generate_surrogate_key` ソース / dbt-bigquery `hash` マクロ。

| 本文の主張 | 原典 | 判定 |
|---|---|---|
| Techniques「主キーはソースの自然キーであってはならない…」(p.7) | "This primary key cannot be the operational system's natural key because there will be multiple dimension rows for that natural key when changes are tracked over time."（p.7） | ✅ |
| Techniques 耐久キー「版が増えてもサロゲートキーは複数になるが耐久キーは決して変わらない」(p.7) | "While multiple surrogate keys may be associated with an employee over time as their profile changes, the durable key never changes."（p.7） | ✅（原文 employee → 会員 の置換は Minor-4） |
| Techniques ロールプレイング「各 FK は別のビューを参照」(p.9) | "It is essential that each foreign key refers to a separate view of the date dimension… These separate dimension views (with unique attribute column names) are called roles."（p.9） | ✅ |
| Techniques ジャンク「直積である必要はなく実際に出現する組合せだけ」(p.9) | "does not need to be the Cartesian product of all the attributes' possible values, but should only contain the combination of values that actually occur in the source data."（p.9）／「transaction profile dimension」も一致 | ✅ |
| Techniques ミニディメンション Type 4(p.12) | "a group of attributes in a dimension rapidly changes and is split off to a mini-dimension… the primary keys of both the base dimension and mini-dimension are captured in the associated fact tables."（p.12） | ✅（"Type 4 / 5" 併記は Minor-10） |
| Techniques NULL 外部キー禁止（本文は p.5 と表記） | "nulls must be avoided in the fact table's foreign keys… Rather than a null foreign key, the associated dimension table must have a default row (and surrogate key) representing the unknown or not applicable condition." — **目次でも本文でも p.4** | ⚠️ Minor-2 |
| Techniques 監査ディメンション | "When a fact table row is created in the ETL back room, it is helpful to create an audit dimension containing the ETL processing metadata known at the time."／"These environment variables are especially useful for compliance and auditing purposes because they enable BI tools to drill down to determine which rows were created with what versions of the ETL software."（p.20） | ✅ |
| Techniques 日付キーの YYYYMMDD 例外 | "To facilitate partitioning, the primary key of a date dimension can be more meaningful, such as an integer representing YYYYMMDD, instead of a sequentially-assigned surrogate key… Filtering and grouping should be based on the date dimension's attributes, not the smart key."（p.8） | ✅ 引用も「立場が緩められた」という読みも正しい |
| DT#5「キーはアプリケーション上の意味を持ってはならない。ただの整数で計算に使えない」 | "the keys in the time dimension must have no applications significance. They are just integers and you can't compute with them."（2000-03-19） | ✅ 年も正しい |
| DT#5 の `Time_Type` 4分類 | `Time_Type (Normal, Not_Applicable, Hasnt_Happened_Yet, Corrupted)` | ✅ |
| DT#100「固定キー＋日付範囲は明確に間違い」「理由は9つ」 | "It is definitely wrong to make the SCD 2 key be a combination of a fixed key (1-1 with the natural key) plus a date range." ＋ 1)〜9) の9項目 | ✅ |
| DT#100「最良の結合性能は単一フィールドの整数キー」 | "The best join performance is achieved by using single field integer keys between dimension tables and fact tables."（理由1） | ✅ |
| DT#100「開始日と次の行の終了日が一致すると `BETWEEN` が2行を返す」 | 原文は逆: "If the **end** effective date of one record is exactly equal to the **begin** effective date of the **next** record… you could land on the exact dividing line and get two records."（理由3） | ⚠️ Minor-3 |
| DT#100「単純な SK を使えばこの反論は消える…ETL 時に解決される」 | "Using simple surrogate keys eliminates this objection, since the correct correspondence between dimension and fact records is resolved at ETL time."（理由6） | ✅ |
| DT#46 の DD 定義と「同速度で伸びていたら退化が潜む」 | "acts as a dimension key in the fact table, however does not join to a corresponding dimension table because all its interesting attributes have already been placed in other analytic dimensions."／"Usually when a dimension table is growing at roughly the same rate as the fact table, there is a degenerate dimension lurking that has been missed in the initial design." | ✅ 2箇所とも一致 |
| DT#43 の NULL 3分類（FK 禁止 / メジャーは NULL 可 / 属性は記述文字列） | 記事どおり。数値属性への言及は原典に無く、本文もそれを前提に「文字列属性の話だ」と自分の読みとして書いている | ✅ |
| DT#83「内部エンティティと外部エンティティで知っている情報が大きく異なる」「抽象化は明快さを減じ、より大きな表を生む」 | "We collect and know vastly different information about our own internal entities than we do about external entities."／"the abstraction process reduces clarity for the business users and inevitably creates a larger table." | ✅ |
| DT#127「サロゲートキー列を持つ新表を `SELECT DISTINCT` で埋めるだけ」 | "Simply create a new table with a surrogate key column, and populate the table using a SELECT DISTINCT of the columns from the base dimension along with an IDENTITY field or SEQUENCE…" | ✅ |
| DT#127「属性がファクトイベントを伴わず変化しうるなら完全な履歴を捉えないかもしれない」 | "This may not capture a complete history of changes if customer attributes can change without an associated fact event." ／ 続く「ファクトレスファクト表を別に置く」も原典どおり | ✅ |
| 「DT#127 は帯化を前提にしている（帯化そのものは書いていない）」 | 原典全文を確認。**帯化への言及は無い。** 本文の書き方は正確 | ✅ |
| dbt Kimball の3方式・「おそらく最も簡単」・「結合の手間が省ける」 | "We are using arguably the easiest approach which is to perform a hash on the unique key columns"／"This approach removes the hassle of performing a join with dimension tables when generating the surrogate key for the fact tables later." | ✅ |
| 記事のコードが `generate_surrogate_key(['stg_product.productid'])` ＝自然キー1列 | 原文どおり | ✅ この指摘は正しい |
| ECM「Kimball の弟子」「Kimball なら眉をひそめるが ECM はむしろ推奨」「日次フルスナップショット」「`7d_visits`」 | "As a Ralph Kimball disciple…"／"Where Ralph Kimball would frown upon bringing many metrics in dimension tables… the entity-centric approach actually prescribes doing this."／"keeping a full snapshot of your dimension, for every single day in the past… Easy point-in-time querying / comparisons"／`7d_visits` `28d_visits` | ✅ 4点とも一致 |
| `generate_surrogate_key` は BigQuery で `TO_HEX(MD5(...))` の32文字16進 | `dbt-utils` は `dbt.hash(dbt.concat(fields))`、`bigquery__hash` は `to_hex(default__hash(field))` = `to_hex(md5(cast(... as string)))` → 32 hex | ✅ |
| 区切りが `-` 固定 / NULL は `_dbt_utils_surrogate_key_null_` | ソースどおり（`surrogate_key_treat_nulls_as_empty_strings` で上書き可） | ✅ |
| SK(1998)「7つ挙げた」 | **不一致。** 原典は「本番系があなたの足を踏む」6項目＋未知値の符号化＋4バイト整数の容量削減＋結合性能（"The final reason I can think of for surrogate keys…"）で最低8つ | ❌ Important-3 |
| SK(1998) の個別引用（パージ済みキーの再利用 / キー空間の再圧縮 / 4バイト整数と20億） | "Production may reuse keys that it has purged but that you are still maintaining"／"Production may re-compact its key space"／"The beauty of a four-byte integer key is that it can represent more than 2 billion different values." | ✅ 3つとも一致 |

---

## 5. 指摘一覧

### Critical-1 — dbt モデル3本が末尾セミコロンで実行できない

**該当:** §5(b) `dim_review_attributes.sql`（HTML 319行目）、§5(c) `dim_member_profile_mini.sql`（352行目）、§5(d) `dim_member.sql`（422行目）。

```
CROSS JOIN bands  AS b;   -- 2 × 3 × 5 = 30 行
SELECT -1 AS member_profile_mini_key, '不明' AS annual_income_band, '不明' AS job_change_intent;
    TIMESTAMP '1900-01-01', TIMESTAMP '9999-12-31', TRUE;
```

`materialized='table'` の dbt モデルは `create or replace table <relation> as ( <compiled sql> );` に包まれる。モデル本文の末尾にセミコロンがあると括弧の内側で文が終わり、BigQuery が構文エラーで落ちる。dbt の既知の禁止事項で、シリーズの読者がそのまま貼ると必ず踏む。§5(a) の `dim_date.sql` と `dim_audit.sql` にはセミコロンが無いので、3本だけが不整合でもある。

**修正案:** 3箇所の末尾 `;` を削除する。`dim_review_attributes.sql` は行末コメントも一緒に整理して次の形にする。

```sql
FROM statuses AS s
CROSS JOIN types  AS t
CROSS JOIN bands  AS b   -- 2 × 3 × 5 = 30 行
```

§2(c) の壊れた例（115・122行目）と §5 のロールプレイングクエリ（288行目）はモデルではなくアドホッククエリなのでセミコロンがあってよい。ただし後者は `{{ ref() }}` を含み見た目がモデルと同じなので、`-- 分析クエリ（モデルではない）` の1行を足すと誤読が減る。

---

### Important-1 — 正典の `dim_agency`（SCD2）が SK の結論から3箇所とも欠落している

**該当:** §1 技法一覧表1行目・8行目、§3「SK (1998) の理由」表の Type2 行、§5「判断: どのディメンションにどのキーを使うか」表の SCD2 行、§1 冒頭「この回の決定」表。

`canon/domain.md` §4 のディメンション表は執筆後に `dim_agency` を追加しており、SCD は **2**（`dim_agent` の縮約ディメンション、`fct_job_posting_daily` / `fct_placement` の主軸が結ぶ）。本文はどの表でも SCD2 を「`dim_member` / `dim_company` / `dim_agent` / `dim_scout_sender` の4本のみ」と書き切っており、`dim_agency` は本文に1度も現れない。`-1` 行の列挙にも `dim_agency`（`fct_job_posting_daily.agency_key` の `-1` = 直接掲載）が無い。

なお `domain.md` §4 の散文（「SCD2 のディメンション（`dim_member` / `dim_company` / `dim_agent` / `dim_scout_sender`）は一律に…」）は表の追加に追随しておらず、正典自体が内部で食い違っている。**本文を直すだけでなく、正典側の齟齬を report で提起する必要がある。**

**修正案:**
1. §1「この回の決定」表・技法一覧表・§3 の Type2 行・§5 判断表の SCD2 対象を `dim_member` / `dim_company` / `dim_agent` / `dim_agency` / `dim_scout_sender` の **5本**に揃える。文中の「SCD2 の4ディメンション」も「5本」に。
2. §1 の `-1` 行の列挙に `dim_agency`（直接掲載）を追加し、既存の `dim_agent`（直接送信）と役割を書き分ける。
3. `dim_agency` は `dim_agent` の縮約（shrunken rollup, Techniques p.10）なので、§5 判断表に1行足すなら「同じ自然キー階層の2本（`dim_agent` / `dim_agency`）は同じ SK 規則で作る（`agency_id` + `valid_from`）。担当者が特定できないファクトは `dim_agency` に結ぶ」と書くと、06回・08回のコンフォーマンスに接続する。
4. report に「`domain.md` §4 の散文が SCD2 を4本と書いているが、同 §4 の表は `dim_agency` を SCD2 としている。散文側の訂正を提案」を追加する。

---

### Important-2 — 正典の `dim_member_daily` を無視して「ミニを採る」と結論している（§4）

**該当:** §4 末尾の3手法比較表と、その直後の「CareerVoice は `fct_page_view` が日次 2,000 万行あるのでミニを採る」。

正典には `dim_member_daily`（1行 = 1会員 × 1日、`partition_by=snapshot_date`, `cluster_by=member_id`, `require_partition_filter=true`、**`member_profile_mini_key` を列に持つ**）が追加されている。備考は「FDE 方式の代替（05回）」。つまり CareerVoice はミニと日次スナップショットを**両方**置く設計で、本文の排他的な「ミニを採る」は正典と矛盾する。

さらに比較表の「約 11 億行/年」は、`require_partition_filter=true` のパーティションテーブルでは1クエリのスキャンが1日分（約300万行）に閉じるため、コスト論としてミスリードになる。行数そのものではなく「保管コストは増えるがスキャンは1日分に閉じる」が正しい比較軸。

**修正案:**
- 比較表の3行目を「ECM / FDE の日次スナップショット（正典では `dim_member_daily`、05回）」に改め、「行数」欄を「約 11 億行/年（ただし `snapshot_date` パーティション＋`require_partition_filter=true` なので1クエリのスキャンは1日分 ≒ 300 万行）」にする。
- 結論の1文を排他的でない形に直す。例: 「`fct_page_view`（日次 2,000 万行）に毎日結合するのはミニの側で、`dim_member_daily` は会員断面の時系列分析用に別に置く（05回）。同じ属性を2つの経路で持つので、`dim_member_daily.member_profile_mini_key` がミニ側と一致することが整合条件になる。」
- 併記するなら §5 の schema.yml に `dim_member_daily.member_profile_mini_key` の `relationships` テストを1行足すと、この回の「`-1` 行はテストの前提条件」という締めと繋がる。

---

### Important-3 — SK(1998) の理由を「7つ」と書き、原典が挙げる結合性能の理由を落としている（§3）

**該当:** §3「サロゲートキーが要る理由（SK, 1998）と、この題材での成否」の `aside kimball` と直下の7行表。

原典を全文取得して数え直した。SK(1998) の理由は次の構成で、少なくとも8つある。

| 原典の並び | 本文の表 |
|---|---|
| 本番系がパージ済みキーを再利用する | 行1（行2と統合） |
| 本番系が誤ってキーを再利用する（UPC の例） | 行1に吸収 |
| 本番系がキー空間を再圧縮する（全顧客キー再割当の実例） | 行2 |
| Slowly Changing Dimension | 行3 |
| キー書式の一般化（整数→英数字、12→20バイト） | 行5 |
| 買収による複数ソース統合 | 行6 |
| 未知値の符号化（匿名顧客・未特定・取得失敗・そもそも該当なし） | 行4 |
| 4バイト整数による容量削減（20億値） | 行7 |
| **結合性能**: "The final reason I can think of for surrogate keys is one that I strongly suspect but have never proven. Replacing big, ugly natural keys and composite keys with beautiful, tight integer surrogate keys is bound to improve join performance." | **無し** |

落ちた1つがブリーフ §3 の必須項目「SK の理由（ソースキーの再利用・SCD2・**性能**・未知値）」で名指しされている項目である。しかも Kimball 自身が「強く疑ってはいるが証明したことはない」と留保をつけている理由なので、この回の「性能のための技法は列指向 DWH で不要化する」という筋にとって**最も都合のよい材料**でもある（原典の時点で既に実証されていない主張だった）。

**修正案:**
1. `aside kimball` の「理由を7つ挙げた」を「理由を並べた（本番系がキーを踏む6通り＋未知値の符号化＋容量削減＋結合性能）」に改める。
2. 表に行を1つ足す。

| SK (1998) の理由 | CareerVoice + BigQuery で成立するか |
|---|---|
| 結合性能（「大きく醜い自然キー・複合キーを小さな整数キーに置き換えれば結合性能は上がるはずだ」） | **△** 原典自身が「強く疑ってはいるが証明したことはない」と断っている。BigQuery ではシャッフル量の差として実在するが（§5(d) の結合コスト行）、`M001` 程度の短い STRING では測定に埋もれる。**測ってから決める** |

3. 直後の「SK (1998) の7理由を1つも満たさない」（§4）と「§3 の表の7理由」（§4）も行数の変更に合わせて直す。

---

### Important-4 — §2(c) の `LEFT JOIN` 例が、注釈と本文の主張を同時には満たさない

**該当:** §2(c) の2本目のクエリ（HTML 117–122行目）と直後の段落。

```sql
SELECT d.year, COUNT(*) AS a, COUNT(d.date_key) AS b        -- a と b がずれる
FROM fct_application_pipeline AS f
LEFT JOIN dim_date AS d ON f.hired_date_key = d.date_key
WHERE d.year = 2026                                          -- NULL 行がここで落ちる
GROUP BY d.year;
```

`WHERE d.year = 2026` が付いている以上、外部結合で NULL になった行はここで全て落ちる。残った行の `d.date_key` は必ず非 NULL なので、**このクエリでは `a` と `b` は必ず一致する**。「`a` と `b` がずれる」と「`WHERE` が NULL 行を落として INNER JOIN と同じ結果に戻る」は同じクエリでは両立しない。本文の段落も同じ矛盾をそのまま書いている（「LEFT JOIN 版は `COUNT(*)` と `COUNT(d.date_key)` が食い違い、さらに `WHERE d.year = 2026` が NULL 行を静かに落として…」）。

壊れ方としては2つの独立した罠なので、クエリを2本に割るのが正しい。

**修正案:**

```sql
-- 壊れる形 2: LEFT JOIN にすると行は残るが COUNT がずれる
SELECT COUNT(*) AS applications, COUNT(d.date_key) AS hired  -- 未入社の分だけ食い違う
FROM fct_application_pipeline AS f
LEFT JOIN dim_date AS d ON f.hired_date_key = d.date_key;

-- 壊れる形 3: 絞り込みを足した瞬間に INNER JOIN と同じ結果に戻る
SELECT d.year, COUNT(*) AS applications
FROM fct_application_pipeline AS f
LEFT JOIN dim_date AS d ON f.hired_date_key = d.date_key
WHERE d.year = 2026        -- NULL 行がここで静かに落ちる
GROUP BY d.year;
```

段落も「2本目は `COUNT(*)` と `COUNT(d.date_key)` が食い違い、集計関数の選び方で答えが変わる。3本目は絞り込みを1つ足しただけで INNER JOIN と同じ結果に戻る。どちらもエラーにならない」の3文に分ける。

---

### Important-5 — §2(a) の「正典の形ではこれが全部消える」は誤り（自分の §7 問3 と矛盾する）

**該当:** §2(a) 末尾の段落と、§5(c) 末尾の「§2(a) の 3,000 万行への範囲結合と比べてほしい」。

§2(a) は Type2 肥大の壊れ方を3つ挙げる: (i) 行数の爆発、(ii) `COUNT(DISTINCT member_key)` の二重計上、(iii) ロード時の範囲結合。その直後に「正典の形（ミニディメンション）ではこれが全部消える」と書く。

しかし正典の `dim_member` は SCD2 のままである。本文自身が §7 問3 で「8/1 の `current_company_id` は `dim_member` の Type2 属性なので新しい `member_key` が出る」「`dim_member` は 2 行になる」と書いている。したがって:

- (ii) は消えない。`M001` は 8/1 以降 `member_key` が2種類あり、`COUNT(DISTINCT member_key)` は依然として二重に数える。正しく数えるには `member_id`（耐久キー）で数える必要がある。
- (iii) も消えない。`fct_scout` / `fct_application_pipeline` / `fct_page_view` のロードは、イベント時点の `member_key` を引くために `valid_from <= event_ts AND event_ts < valid_to` の as-of 結合が要る（05回の中心テーマ）。

ミニディメンションが消すのは「速く変わる属性のせいで版が増える」分だけで、**規模を桁で下げるが現象そのものは残る**。この誇張は 05回の as-of join の前振りを潰してしまう。

**修正案:** 該当段落を次のように書き換える。

> 正典の形（ミニディメンション）では (i) が消え、(ii)(iii) が桁で軽くなる。`dim_member` は 6/15 に**行が増えない**（増えるのは `current_company_id` が変わる 8/1 だけ）。`dim_member_profile_mini` も 15 行のまま動かない。残るのは「`dim_member` は SCD2 なので `member_key` は依然として `M001` に2つあり、会員数は `member_id` で数え、時点解決の as-of 結合も残る」という点で、これは 05回で扱う。

§5(c) 末尾も「§2(a) の 3,000 万行への範囲結合と比べてほしい」→「§2(a) の 3,000 万行への範囲結合が、正典では 2 行（`M001` の版）への as-of 結合に縮む」に直す。

---

### Minor-1 — 3文超の段落が19箇所ある

`style.md`「1段落は3文まで」に対し、`<pre>` を除いた `<p>` のうち19本が4文以上。特に長いもの:

| 文数 | 冒頭 | 場所 |
|---|---|---|
| 8 | 「DT#100 は「SCD2 のキーを…」 | §3 `aside kimball` |
| 7 | 「何が変わったか。連番が使えなくなった。…」 | §4 |
| 6 | 「ミニディメンションを作る手順は3段。…」 | §3 |
| 6 | 「何が変わっていないか。要否の判断。…」 | §4 |
| 6 | 「Kimball の但し書きも1つ入れておく。…」 | §6 |
| 5 | 「`fct_review` が `member_key` を持たないのは…」 | §1 |
| 5 | 「Techniques は「ジャンクディメンションは…」 | §5(b) `aside kimball` |
| 5 | 「この主張は現在も生きている。…」 | §3 |
| 5 | 「Kimball が指標をディメンションに置くのを嫌うのは…」 | §4 |
| 5 | 「この回のディメンション（`dim_member`, `dim_company`）は…」 | §4 |
| 5 | 「反論も書いておく。…」 | §7 問2 |
| 4 | 他8本（§1 冒頭、§2(a)(c)、§4、§5(c)、§7 問3 ×3） |

**修正案:** 00回の再レビューで採った方式（`aside` 内は `<br>` で3文以内の塊に分ける、地の文は段落を割る）を踏襲する。特に DT#100 の8文 aside は「原典の主張3点」と「この題材への当てはめ」で2ブロックに割ると読みやすい。

### Minor-2 — Techniques の NULL 外部キー引用のページ番号が誤り

§3 の表で「（Techniques, p.5）」としているが、"Nulls in Fact Tables" は目次・本文とも **p.4**。他の引用（p.7 / p.9 / p.12）は全て正しいので、ここだけ直せばよい。

**修正案:** `（Techniques, p.5）` → `（Techniques, p.4）`。

### Minor-3 — DT#100 の `BETWEEN` 二重ヒットの説明が逆になっている

本文「開始日と次の行の終了日が一致すると `BETWEEN` が2行を返す」。原典は「ある行の**終了日**と次の行の**開始日**が一致すると」。方向が逆で、SCD2 の区間の張り方を知らない読者は誤って実装する。

**修正案:** 「ある行の `valid_to` と次の行の `valid_from` が一致すると、その境界の瞬間に `BETWEEN` が2行を返す」。

### Minor-4 — 原文の "employee" を「会員」に置換したまま鉤括弧で引用している

§3 の耐久キー行「「会員の版が増えてもサロゲートキーは複数になるが、耐久キーは決して変わらない」（Techniques, p.7）」。原文は employee。他の引用は原文に忠実なので、ここだけ体裁が揃っていない。

**修正案:** 鉤括弧を「従業員の版が増えても…」と原文どおりにして、直後に「CareerVoice では会員（`member_id`）が耐久キー」と地の文で繋ぐ。

### Minor-5 — `p.meta` の Design Tip 番号に #164 が無い

`p.meta` は `Design Tip #5 #43 #46 #83 #100 #127` だが、本文は DT#164（監査ディメンション）を §1・§3・§5(e) で3回引き、参照文献にも載せている。`style.md` の自己チェック「原典参照（DWT 章 / DT#）が `p.meta` と各節にある」に反する。

**修正案:** `p.meta` を `Design Tip #5 #43 #46 #83 #100 #127 #164` にする。

### Minor-6 — ロールプレイングのクエリで `hired` をテーブル別名と出力列名の両方に使っている

```sql
COUNTIF(hired.date_key <> -1)     AS hired
INNER JOIN {{ ref('dim_date') }} AS hired   ON f.hired_date_key   = hired.date_key
```

BigQuery では通るが、同じ識別子がレンジ変数と出力列を兼ねるので、`HAVING` や外側からの参照を足した瞬間に読み手が迷う。

**修正案:** 出力列を `hired_count`、テーブル別名を `hired_d` のどちらかに変える。`still_open` と対にするなら `applications` / `still_open` / `hired_count` が揃う。

### Minor-7 — §2(b) の前提（`applied_date DATE`）と例示式（`applied_at`）が食い違う

段落は「`fct_application_pipeline` に `applied_date DATE` を直接置いた場合」と宣言しているのに、表の中の式は `EXTRACT(YEAR FROM applied_at)` / `EXTRACT(YEAR FROM DATE_SUB(applied_at, INTERVAL 3 MONTH))` とソース列名 `applied_at`（TIMESTAMP）を使っている。BigQuery の `DATE_SUB` は DATE 専用なので、TIMESTAMP に当てると型エラーになる（`TIMESTAMP_SUB` か `DATE(applied_at)` が要る）。壊れ方の例示とはいえ、型エラーで落ちる式は「必ず起きる食い違い」の説得力を削ぐ。

**修正案:** 表内を `EXTRACT(YEAR FROM applied_date)` / `EXTRACT(YEAR FROM DATE_SUB(applied_date, INTERVAL 3 MONTH))` に統一する。

### Minor-8 — 正典に無い規模（会員300万人・`fct_page_view` 日次2,000万行）を断定形で置いている

§2(a)・§4・§7 問2 の議論はこの2つの数字に乗っている。`canon/domain.md` にデータ量の記述は無く、この回で初めて出てくる。判断（ミニ vs 日次スナップショット、ジャンク vs メジャー）が数字で決まると本文自身が言っている（「この分岐は行数で決まるので、題材が変われば結論も変わる」）以上、出自を1行明示しておかないと後続の回が別の数字を使ったときに矛盾する。

**修正案:** §2(a) の初出に「（以下、規模は会員 300 万人・`fct_page_view` 日次 2,000 万行を仮定する。正典はデータ量を定めていない）」を足す。あるいは report で正典への追加（§5 に規模の前提行）を提案する。

### Minor-9 — `dim_member_profile_mini` の行数が 15 と 16 で揺れている

§1・§2(a)・§4・§5(c) コメント・§6・§7 問3 は「15行」、§5(c) の実装と schema.yml の description（「15 行 + 既定行」）と singular test（`<> 16`）は16行。正典は15行としか書いていない（report の提案4で追加を提起済み）。

**修正案:** §1 技法一覧の該当セルを「`dim_member_profile_mini`（5 × 3 = 15 行 ＋ `-1` の既定行 = 16 行）」として最初に断り、以降の「15行」は「組合せは 15 通りで固定」と組合せ数の話であることが分かる書き方に統一する。

### Minor-10 — ミニディメンションを「Type 4 / 5」と併記している

§3 の表は「ミニディメンション（Type 4 / 5, DT#127）」。Techniques の Type 5 は「Type 4 に加えて本体ディメンションに現在のミニキーを Type1 アウトリガーとして埋める」形で、正典の `dim_member` はミニキーを持たないので **Type 4 のみ**。§1 の表は正しく「Type 4」と書いており、§3 とだけ食い違う。

**修正案:** §3 を「ミニディメンション（Type 4, DT#127）」にし、Type 5 に触れるなら「本体に現在のミニキーを Type1 で埋めると Type 5。正典は採らない（`dim_member` にミニキーを持たせると 05回の as-of 解決が2経路になる）」と1行で差を書く。

### Minor-11 — 「DT#100 の要件は満たす」が原典の理由9を落としている

§3「`FARM_FINGERPRINT(member_id || '|' || valid_from)` は…DT#100 の要件は満たす」。DT#100 の理由9は「ソースシステム由来の自然キーの中身に明示的に依存する設計は、複数ソース統合の課題に対応できない」で、自然キーを入力にするハッシュはこれに正面から当たる。本文は §3 の表で「複数ソース統合は起きない（単一ソース）」と既に判定しているので結論は変わらないが、「要件は満たす」と無条件に書くと原典を過小に引いたことになる。

**修正案:** 「DT#100 の要件（単一列・整数・ETL 時に対応付け解決）は満たす。残る理由9（自然キーの中身への依存）は、ソースが `src_careervoice` 単一である限り効かない——2つ目のソースが来たら §3 の表の6行目と一緒に ✓ に変わる。」

---

## 6. 図 / HTML / 文体の機械チェック

| 項目 | 結果 |
|---|---|
| `check_svg.py` | `0 errors, 1 warnings`（warning は「`<svg>` が見つからない」＝ブリーフ「図: なし」どおりなので正常） |
| SVG 個数 | 0（ブリーフ指定どおり。表で足りるものを図にしていない） |
| `<title>` | `ディメンションの設計 — データマート設計 03` ✅ 規約形 |
| `p.meta` | 有り。DT#164 のみ欠落（Minor-5） |
| 節構成 | `<h2>` が 1〜8 ＋ 参照文献 = 9本 ✅ 減らしていない |
| `.table-wrap` | 表12個すべて `<div class="table-wrap">` に包まれている ✅ |
| HTML エスケープ | `<pre><code>` 11ブロックすべてで `<` `>` がエスケープ済み。生の山括弧 0 ✅ |
| タグ対応 | 開閉の不一致 0 ✅ |
| CSS 変数 | `style.md` の骨格と完全一致（変数名の改変なし）✅ |
| 前後の回へのリンク | 無し。回番号参照のみ（01/04/05/06/07/08/09回）✅ |
| 緩衝語（「でしょう」「と思われる」等） | 0 件 ✅ |
| URL | 13本すべて `canon/references.md` に存在 ✅ |
| 8節の分量 | `.aside` 1本・4項目（うち1つは「試せる種」）✅ 規約どおり |
| 演習 | 3問すべて `<details><summary>解答例</summary>` ✅ 同回内に解答 |
| 3文ルール | **19箇所で違反**（Minor-1） |

---

## 7. 報告（`reports/03_report.md`）について

- 文献の読了と引用の対応づけは正確で、実際に原典と突き合わせて食い違ったのは SK(1998) の理由の数（Important-3）と Techniques のページ番号（Minor-2）、DT#100 の日付境界（Minor-3）の3点のみ。記憶で書いた形跡は無い。
- 「正典への変更提案」7件は妥当。うち提案1（`date_label`）と提案3（8本）は既に正典へ反映済み。提案4（ミニの16行）は未反映なので、Minor-9 の対応と合わせて再提出するとよい。
- **報告の「12 個の表すべてが `.table-wrap` に包まれている」「`<` `>` がエスケープ済み」は独立に検証して事実と確認した。**
- 一方、報告の「check_svg は n/a（実行していない）」は、レビュー側で実行して `0 errors` を確認した。図が無い回でも実行して結果を report に貼るほうがシリーズで揃う。
- 報告に無い問題として、Critical-1（末尾セミコロン）と Important-1/2（正典更新への未追随）と Important-4/5（自己矛盾）がある。特に Important-1/2 は執筆後に正典が動いた分なので、修正時に `canon/domain.md` を読み直すこと。

---

## 総合判定

**REVISE**

- Critical: 1（Critical-1）
- Important: 5（Important-1 〜 5）
- Minor: 11（Minor-1 〜 11）

原典の照合と数値の検算はほぼ全て通っており（表・SQL の行数、衝突確率、祝日、`UNION ALL` の列数と型まで一致）、Kimball の引用精度も高い。落ちているのは (a) dbt モデルとして実行すると落ちるセミコロン、(b) 執筆後に更新された正典（`dim_agency` / `dim_member_daily`）への未追随、(c) SK(1998) の理由の数え落とし、(d) §2 の2箇所の自己矛盾。いずれも局所的な修正で済む。
