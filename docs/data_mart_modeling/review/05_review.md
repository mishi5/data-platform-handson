# 05 履歴を持つ：SCD とスナップショット — レビュー

対象: `docs/data_mart_modeling/html/05_scd.html`（826 行）／ブリーフ `briefs/05.md`／報告 `reports/05_report.md`
正典: `canon/domain.md`（`dim_member_daily` 追加後の版）、`canon/style.md`、`canon/references.md`
前提: オーケストレータ裁定により、執筆者の提案 1〜3 は全て正典に採用済み（`dim_member_daily` を §4 に追加／6-15 の変化は Type 4 側で `dim_member` は 2 行／`M001.registered_at` = 2026-01-05）。この 3 点そのものは指摘対象にしない。

---

## 1. ブリーフ準拠表

| 節 | 必須項目 | 判定 | 該当箇所 |
|---|---|---|---|
| §1 | Type 0〜7 の表（定義 / 履歴 / 行の増え方 / CareerVoice での適用） | ✅ | 「Type 0〜7 と CareerVoice での適用」。4 列すべて揃い、8 型すべてに CareerVoice の割当（採らない型も理由つき） |
| §1 | `dim_company.name`=1 | ✅ | Type 1 行・Type 6 行・§6 表の 3 か所で一貫 |
| §1 | `employee_size_band`=2 | ✅ | Type 6 行「`name` が Type1、`employee_size_band` 等が Type2」 |
| §1 | `dim_member_profile_mini` 経由=4 | ✅ | Type 4 行（5 × 3 = 15 行、`fct_scout`/`fct_page_view`/`fct_application_pipeline` が `member_profile_mini_key` を持つ） |
| §1 | `dim_company` 全体=6 相当 | ✅ | Type 6 行。§5-a aside で「完全な Type 6 との差」も明示 |
| §2(a) | `dim_company` Type1 で `C002` の `50_299` 時代のクチコミ平均が出せない | ✅ | §2(a)。2026-04 のレポート vs 2026-06 の再実行の対比表。`R001`(3/10) vs 規模変化(5/1) の日付関係も正しい |
| §2(b) | 現在の `member_key` で結んで `S001`(6/20) が最新版に紐づく | ⚠️ | §2(b)。論点は成立しているが「6/15 以降の版」という表現が `dim_member` に存在しない版を指す（**Critical-1**） |
| §2(c) | `valid_to` を NULL にして `BETWEEN` が外れる（`9999-12-31` を入れる） | ⚠️ | §2(c)。NULL・境界重複の両方を扱い半開区間まで出しているのは加点。ただし「`S001` が当たるのは 6/15〜7/31 の版」が誤り（**Critical-1**） |
| §3 | Type2 の `valid_from/valid_to/is_current`、Type6、DT#15 の組合せ | ✅ | §3 表 + DT#15 aside。DT#15 の原文（PDF）と突合済み・引用は正確 |
| §3 | 「ファクトはロード時点でサロゲートキーを解決する」原則 | ⚠️ | §3 の 2 枚目の aside。原則の内容は正しいが引用文が原典に存在しない（**Important-1**） |
| §4 | FDE の「毎日ディメンション全体をパーティションにスナップショット」 | ✅ | §4 冒頭。ssp.sh の原文と 4 フレーズすべて逐語一致（WebFetch で確認） |
| §4 | 利点（冪等・単純・as-of が 1 述語） | ✅ | 7 行比較表の「as-of の書き方 / 冪等性 / バックフィル / コードの本数 / その日の母集団」 |
| §4 | 欠点（行数 = 会員数 × 日数、日単位に丸まる） | ✅ | 同表の「行数 / 時間精度」行 + §5-c 本文の 6/15 08:00 の例 |
| §4 | Zach Wilson の「SCD2 は運用が重い」論 | ⚠️ | modern aside。Wilson 本文の 4 引用は逐語一致。コメント欄の要約が原典を歪めている（**Important-2**） |
| §4 | 判断: 会員=スナップショット、企業=SCD2 を根拠付きで | ✅ | 「この題材での判断」表。エージェント行を足しているのは加点 |
| §5(a) | dbt snapshot（`strategy='timestamp'`, `updated_at`）→ `dim_company`、`dbt_valid_from/to` → `valid_from/valid_to`、`COALESCE(valid_to,'9999-12-31')` | ✅ | YAML の `name`/`relation`/`config` 形式・`dbt_valid_to_current`・列名すべて dbt docs と一致（確認済み）。`timestamp '9999-12-31'` は型つきリテラルで正しい |
| §5(b) | as-of join で `fct_scout.member_key` を解決 | ✅ | `fct_scout.sql`。半開区間・`dim_scout_sender` も同形で解決 |
| §5(b) | `S001`(6/20) がどの版に当たるかを表で | ✅ | 「as-of（正しい）/ `is_current`（誤り）」の 2 行表。正典（2 行）に沿って `(v1)`・`C002`・`(600_800, active)` で正しい |
| §5(c) | `dim_member_daily`（`PARTITION BY snapshot_date`）と `WHERE snapshot_date = DATE(sent_at)` | ✅ | `dim_member_daily.sql` + 利用クエリ。`require_partition_filter` を満たす `WHERE` を実際に書いているのは加点 |
| §5(d) | 現在値は `company_id` で `is_current` 版に再結合 | ✅ | §5-d の 2 段結合 + 結果表 |
| §6 | 「行数 × 変化頻度 × 必要な時間精度 → Type / スナップショット」の表 | ✅ | 8 行表 + 「採らなかった 3 型と採る条件」表 |
| §7(a) | `dim_agent` の移籍と `fct_placement` の帰属 | ✅ | 正典の `A01`=エージェンシー / `AG01`=担当者 を正しく使い分け（ブリーフの表記より正確）。`dim_agency` 追加後の正典に追従済み |
| §7(b) | `M001` の 6/15・8/1 の変化で `dim_member` は何行か | ✅ | 2 行。`valid_from/to` も §5-b の表と一致 |
| §7(c) | `dim_company.name` の Type1 で困る分析 | ✅ | 「Type1 の問題」と「同一性の問題」を切り分けている |
| 図 | as-of join 概念図（3 つの帯・3 イベント・accent は 6/15〜7/31 の版と 2 イベント・ノード ≤9） | ⚠️ | `#dg-asof`。`check_svg.py` **0 errors, 0 warnings**（再実行で確認）。ノード 6、accent 1 系統、斜めコネクタゼロ。ただし帯を `snap_members` に読み替えた結果、版番号が本文と衝突（**Important-6**） |
| HTML | `<title>` 形式 / `p.meta` / 8 節 / `&lt;` エスケープ / `.table-wrap` | ✅ | title・meta とも style.md の型どおり。h2 は 1〜8 + 参照文献。`<pre>` 内の生 `<` はゼロ（機械チェック）。表 16 本すべて `.table-wrap` |
| 正典 | 本文のテーブル名がすべて `domain.md` にある | ⚠️ | 21 個すべて一致。`snap_*` / `stg_careervoice__*` は命名規約どおり。ただし `dim_member` モデルの**出力列**が正典と食い違う（**Important-3**） |
| 参照 | URL はすべて `references.md` にあるもの | ✅ | 13 本すべて一致（機械チェック） |
| 文体 | 1 段落 3 文まで / 緩衝語なし / 一般論で終わらない | ⚠️ | 緩衝語ゼロ・一般論で終わる節ゼロ。ただし 4 文以上の段落が 46 中 18（**Minor-2**） |

---

## 2. 指摘一覧

### Critical

#### C-1. §2(b)(c) が `dim_member` に存在しない「6/15〜7/31 の版」を前提にしており、§5-b・§7-b と正面から矛盾する

裁定済みの正典では `dim_member` の `M001` は **2 行**（`[2026-01-05, 2026-08-01)` と `[2026-08-01, 9999-12-31)`）。6/15 の変化は `dim_member_profile_mini`（Type 4）側で表現され、`dim_member` に 6/15 始まりの版は存在しない。ところが §2 は 2 か所でその版があるかのように書いている。

1. §2(b): 「現在の版で結ぶと、`S001` は **6/15 以降の版ではなく** 8/1 入社後の版に紐づく」
2. §2(c): 「`S001`（6/20）が当たるのは **6/15〜7/31 の版**で、この行は既に閉じている（`valid_to` が入っている）」

一方 §5-b の結果表と §7-b の解答は「`S001` → `(v1)`、`valid_from` = 2026-01-05、`valid_to` = 2026-08-01」であり、同じ 1 本の記事の中で `S001` の当たり先が 2 通り書かれている。しかも §2(c) の直前の SQL は `dm.valid_from` / `dm.valid_to`（§5-b で `dim_member` に割り当てられた別名）を使っているので、読者は `dim_member` の話だと読む。§7-b が「3 行と答えたくなるが 2 行」という引っかけとして設計されている（報告 §4 提案 2）だけに、§2 が先に「6/15〜7/31 の版」と書いてしまうと引っかけが成立しない。

**修正案**:

§2(b)（下線部を差し替え）:

> 現在の版で結ぶと、`S001` は**送信当時の版（`current_company_id` = `C002`、2026-01-05〜7/31）**ではなく 8/1 入社後の版に紐づく。

§2(c)（同）:

> `S001`（6/20）が当たるのは **2026-01-05〜7/31 の版**で、この行は 8/1 で既に閉じている（`valid_to` が入っている）。

`fct_scout` は `member_key` と `member_profile_mini_key` の 2 本を as-of 解決するので、6/15 の境界を §2 でも見せたいなら「`dim_member` は 1/05〜7/31 の版、`dim_member_profile_mini` の割当は 6/15〜7/31 の版」と 2 本を明示的に並べるのが筋が通る。その場合 §2(c) の SQL の別名も `dm`（`dim_member`）ではなく `pv`（§5-b の `profile_versions`）に変えること。

---

### Important

#### I-1. §3 の surrogate key pipeline の「引用」が原典に存在しない

該当（§3 の 2 枚目の aside）:

> Kimball はこれを surrogate key pipeline と呼び、「ensures facts use contemporary surrogate keys, guaranteeing the correct dimension profiles are associated with fact table activity」とする。

`SCD Part 2`（https://www.kimballgroup.com/2008/09/slowly-changing-dimensions-part-2/ ）を WebFetch で全文確認したが、この文字列は存在しない。原文は次の 2 文に分かれている。

- 「With a dimension undergoing Type 2 processing, great care must be taken to use the correct contemporary surrogate keys from this dimension in every affected fact table. **This assures that the correct dimension profiles are associated with fact table activity.**」
- 「The extract, transform and load (ETL) process for aligning the dimension tables with fact tables at load time is called the surrogate key pipeline」

「surrogate key pipeline」という呼称の帰属は正しいが、`「」` で括った英文は原典を要約して 1 文に合成したもので、逐語引用ではない。この記事の他の英文引用（DT#15・DT#152・SCD Part 1・FDE・Wilson）は全て逐語一致で確認できたため、ここだけが例外になっている。

**修正案**（原文の 2 文に分ける）:

> Kimball は「The extract, transform and load (ETL) process for aligning the dimension tables with fact tables at load time is called the surrogate key pipeline」と呼び、その目的を「great care must be taken to use the correct contemporary surrogate keys from this dimension in every affected fact table. This assures that the correct dimension profiles are associated with fact table activity」とする。

#### I-2. Chris Gambill のコメントの要約が、彼の主張を「SCD2 が必要」に寄せすぎている

該当（§4 の modern aside 2 段落目）:

> 人手で編集される業務データ（Salesforce / NetSuite）や、監査証跡が法的要件になる領域では、「誰がいつ何を変えたか」を行として残す **SCD2 が必要**で、日次スナップショットでは代替できない。

原文コメントを確認したところ、Gambill の主張の中心は SCD2 ではなく **CDC（不変の変更ログ）を基盤に置くこと**で、SCD2 もスナップショットもその上のビューとして扱う、という二者択一の否定である。

- 「If you need real auditability, capture changes first (CDC or event log). Then layer convenience: a 'latest' view for analysts and, if needed, an SCD2 history table.」
- 「The choice isn't 'SCD2 vs datestamps.' It's immutable facts at the base, with snapshots or SCD2 as views.」

「records flip after the fact, and auditors expect an immutable trail tied to who changed what and when」という監査への言及は確かにあるので、後半（日次スナップショット単体では足りない）は原文どおり。歪んでいるのは「だから SCD2」という接続で、原文は「だから CDC を基盤に置き、SCD2 はその上の便宜レイヤ」である。

**修正案**:

> ただし記事のコメント欄で Chris Gambill が反論している。人手で編集される業務データ（Salesforce / NetSuite / HubSpot）は「records flip after the fact, and auditors expect an immutable trail tied to who changed what and when」であり、日次スナップショットだけでは監査に耐えない。ただし彼の結論は SCD2 への回帰ではなく「The choice isn't 'SCD2 vs datestamps.' It's immutable facts at the base, with snapshots or SCD2 as views」——CDC / イベントログを基盤に置き、スナップショットも SCD2 もその上のビューにする、である。Wilson はこれに答えていない。

この直し方には副次的な利点もある。CareerVoice のソースは **Datastream（CDC）で複製されている**（正典 §2）ので、Gambill の言う「基盤の不変ログ」は既に手元にある。`snap_members` も `dim_member_daily` もその上のビューだ、と 1 行で自分の設計に接続できる。

#### I-3. `dim_member` モデルの出力列が正典と食い違う（`prefecture` / `region` が無い）

正典 §4 の `dim_member` の属性は `birth_year`, `gender`, **`prefecture`**, **`region`**, `current_company_id`, `current_job_category`, `registered_date`。§5-b のモデルは `prefecture_code` をそのまま出し、`region` を出していない。同じ記事の `dim_company` では `stg_careervoice__prefectures` を結んで `p.name as hq_prefecture` にしているので、`dim_member` だけが非正規化されずに残っている形になる。`prefectures` は `name` と `region` を持つ（正典 §2）ので、必要な材料は揃っている。

**修正案**（`versions` CTE は `prefecture_code` のままでよい。変化検知も code で行う方が安定する）:

```sql
select
    {{ dbt_utils.generate_surrogate_key(['v.member_id', 'min(v.valid_from)']) }} as member_key,
    v.member_id,
    any_value(v.birth_year)                as birth_year,
    any_value(v.gender)                    as gender,
    any_value(pf.name)                     as prefecture,
    any_value(pf.region)                   as region,
    any_value(v.current_company_id)        as current_company_id,
    ...
from collapsed as v
left join {{ ref('stg_careervoice__prefectures') }} as pf
    on pf.prefecture_code = v.prefecture_code
group by v.member_id, v.version_no
```

#### I-4. コメントは「未知行へ寄せる」と書いているのに、SQL は `member_key` を NULL のまま出す

`fct_scout` の SELECT:

```sql
    dm.member_key,                    -- 未解決なら NULL。未知行（-1 / '-1'）へ寄せる（Design Tip #43, 03 回）
```

コメントは「寄せる」と書くが、`LEFT JOIN` の結果をそのまま出しているので寄せていない。正典 §6 の固定判断は「NULL 外部キー禁止（DT#43）」であり、§2(c) 本文自身も「外部結合なら `member_key` が NULL になって `-1`（未知）へ落ちる」と書いている。SQL がその通りになっていない。同じ問題が `member_profile_mini_key` / `scout_sender_key` / `job_posting_key`、および `dim_member_daily` の `member_key` / `member_profile_mini_key` にもある。

さらに実務上ここが効くのは、まさにこの回が扱う「区間の穴」のときである。`dim_member` の版が `sent_at` をカバーしない（遅延到着・スナップショット開始前のイベント）と静かに NULL になり、`relationships` テストは NULL 行を無視するので素通りする。

**修正案**（`fct_scout`）:

```sql
    coalesce(dm.member_key,              -1) as member_key,
    coalesce(pm.member_profile_mini_key, -1) as member_profile_mini_key,
    coalesce(ss.scout_sender_key,        -1) as scout_sender_key,
    coalesce(jp.job_posting_key,         -1) as job_posting_key,
```

あわせて 1 行: 「**未達だけでなく、as-of 解決が当たらなかった場合も `-1` に落とす。区間の穴を NULL のまま流すと、`relationships` テストが NULL を無視して素通りする。**」`dim_member_daily` の `member_key` / `member_profile_mini_key` も同様に包む。

#### I-5. `schema.yml` のコメントが、実際のテストが検証していないことを主張している

```yaml
      # 版の区間が重なっていない / 隙間が無いことの確認
      - dbt_utils.expression_is_true:
          expression: "valid_from &lt; valid_to"
```

`valid_from < valid_to` は **1 行の区間が空でないこと**しか見ない。重なりも隙間も検出しない。SCD2 の as-of join がこの回の中心であり、重なれば `fct_scout` の行が増え、隙間があれば `member_key` が NULL になる（I-4）。この記事で最も検証したい 2 つが、検証されているように見えて検証されていない。

**修正案**: コメントを実態に合わせたうえで、重なり／隙間は別に立てる。`dbt_utils.sequential_values` は SCD の区間には使えないので、singular test を 1 本置くのが素直。

```yaml
      # 各版の区間が空でないこと（重なり・隙間は tests/assert_dim_company_no_overlap.sql）
      - dbt_utils.expression_is_true:
          expression: "valid_from &lt; valid_to"
```

```sql
-- tests/assert_dim_company_no_overlap.sql
-- 隣り合う版が「前の valid_to = 次の valid_from」で連続していない行を返す
select company_id, valid_from, valid_to, next_valid_from
from (
    select
        company_id, valid_from, valid_to,
        lead(valid_from) over (partition by company_id order by valid_from) as next_valid_from
    from {{ ref('dim_company') }}
)
where next_valid_from is not null
  and next_valid_from != valid_to
```

これは §2(c) で引いた Kimball の規約（「The end-effective-datetime ... must be exactly equal to the begin-effective-datetime of the next change」）をそのままテストにした形になるので、本文との接続もよい。

#### I-6. 図の `v1/v2/v3`（`snap_members`）と本文の `(v1)/(v2)`（`dim_member`）が同じ記号で別物を指している

図は帯を `snap_members` の 3 版に読み替えており、この判断自体は正典（`dim_member` は 2 行）に照らして正しい。問題は版番号の記号が本文と衝突していること。

- 図の脚注: 「太線 ＝ as-of の解決先。**`S001` と `P001` は最新版 v3 ではなく v2 に当たる**」
- §5-b の表: 「`S001` … as-of（正しい）→ **`(v1)`**」
- §7-b の解答表: 「**`(v1)`** … `valid_from` 2026-01-05 / `valid_to` 2026-08-01」

図を見た読者は「`S001` は v2」、表を見た読者は「`S001` は (v1)」と読む。図の 2 本目の脚注（「v1 から v2 は `annual_income_band` / `job_change_intent` の変化 ＝ `dim_member` の行は増えない」）が緩和してはいるが、同じ記号を別の名前空間で使っている限り誤読は残る。C-1 を直した後もこの衝突は残るので、別立てで直す必要がある。

**修正案**（どちらか）:

- (a) 図のラベルを `snap` 側と分かる記号にする。`M001 v1/v2/v3` → **`snap v1 / snap v2 / snap v3`**、脚注も「`S001` と `P001` は `snap_members` の最新版 snap v3 ではなく snap v2 に当たる。`dim_member` 上ではどちらも同じ版（§5-b の `(v1)`）」とする。ノード数は変わらない（6）。
- (b) 帯を `dim_member`（2 版）に戻し、`dim_member_profile_mini` の割当変化を 6/15 の縦の破線 1 本として重ねる。ブリーフの「3 つの帯」からは外れるが、記事の主張（`dim_member` は 2 行、速い属性は Type 4）とは最も素直に一致する。ただしノードの意味が 2 層になるので (a) の方が安全。

#### I-7. dbt snapshot の「初回実行より前は作れない／実行間隔より短い変化は取りこぼす」が抜けており、§8 では `check` 固有の制約として書かれている

§5 の全ての結果表（`snap_members` の 3 版、`dim_member` の `valid_from` = 2026-01-05 00:00:00 ＝ 登録時点）は、**スナップショットが 2026-01-05 以前から毎日走っていて、6/15 09:12 の変化を取りこぼしていない**ことを前提にしている。dbt snapshot は実行時点のソースの現在値しか見ないので、この前提が崩れると `dbt_valid_from` は「最初にスナップショットが走った日の `updated_at`」になり、表の値は再現しない。SCD2 と日次スナップショットの比較（§4）でも、この「過去に遡れない」性質は SCD2 側の実務上の欠点として効く（バックフィルできるのはスナップショット方式の方だけ、という §4 の主張を補強する材料でもある）。

加えて §8 の「試せる種」は次のように書いている。

> `check` 戦略が「実行間隔より短い変化を取りこぼす」ことも同時に確認できる。

これは `check` 固有ではない。`timestamp` 戦略も同じで、`updated_at` が 2 回進んでも次の実行時には最新の 1 状態しか見えない。取りこぼしは戦略ではなく**スナップショットの実行間隔**に由来する。

**修正案**: §5-a の `dbt_valid_to_current` を説明する段落の後ろに 1 段落足す。

> スナップショットは**実行した日以降しか作れない**。`snap_members` の初回実行が 2026-07 なら、`M001` の第 1 版の `dbt_valid_from` は 2026-01-05 ではなく 7 月の値になり、6/15 の変化は永久に取れない。ソース側に履歴があるうち（Datastream の CDC ログ）に初期版を投入するか、無ければ「この日から履歴がある」を明示して下流に伝える。実行間隔より短い変化を取りこぼすのも同じ理由で、`timestamp` と `check` のどちらでも起きる。

§8 の「試せる種」は「`check` 戦略が」→「スナップショットが」に直す。

---

### Minor

#### M-1. `fct_scout` の SQL に `audit_key` が無い

正典 §4 は「**全ファクトは `audit_key` を持つ**」と定める。執筆者も報告 §6 で自己申告済み。02 回のレビュー（I-5）で `CROSS JOIN` 版が否定され、スカラーサブクエリ版が採用されているので、そのまま 1 行足せば済む。

```sql
    coalesce((
        select min(audit_key) from {{ ref('dim_audit') }}
        where dbt_invocation_id = '{{ invocation_id }}'
    ), -1) as audit_key,
```

`dim_member_daily` はディメンションなので不要。

#### M-2. 4 文以上の段落が 46 中 18（style.md「1 段落は 3 文まで」）

機械チェック（`<p>` から SVG / `<pre>` を除き `。` を数えた）で 18 件。02 回はゼロだったので、シリーズ内で 05 だけが緩い。特に長いのは次の 2 つ（6 文）。

- §3 の surrogate key pipeline の aside（I-1 の修正時にあわせて分割できる）
- §4 の Zach Wilson の aside 1 段落目（(1)(2)(3) の列挙は `<ul>` に開いた方が読みやすい）

5 文が 4 件（§5-a の `dbt_valid_to_current` 段落、§5-c の「丸めの副作用」段落、§7-a の解答 1 段落目、§7-c の「困るのは 2 つの場面」直前）。aside の太字リード文が 1 文としてカウントされている分は割り引けるが、それを除いても超過は 12 件前後残る。

#### M-3. 引用の改変が数か所ある（`「」` で括る以上は原文どおりか省略記号を）

| 箇所 | 記事 | 原文 |
|---|---|---|
| §3 表 Type 0 | 「The attribute value never changes. Facts are always grouped by this original value.」 | 「the dimension attribute value never changes, so facts are always grouped by this original value」（DT#152） |
| §3 表 Type 7 | 「... plus the dimension's durable supernatural key linked to the current row.」 | 「... linked to the current row **in the type 2 dimension**」（DT#152、末尾が切れている） |
| §2(a) | 事前計算した集約テーブルは「taken offline and recomputed」が必要 | 「must be taken offline at the moment of the overwrite and must be recomputed before being brought back online」（SCD Part 1） |

いずれも意味は保たれているので実害は小さいが、他の引用が全て逐語一致で確認できるだけに、ここだけ基準が緩い。原文に戻すか `…` を入れる。

#### M-4. §1 の Type 2 セルに `dim_agency` が抜けている

§1「Type 0〜7 と CareerVoice での適用」の Type 2 行は `dim_member` / `dim_company` / `dim_agent` / `dim_scout_sender` の 4 本。正典 §4 の `dim_agency` も SCD 2 で、§1 の判断表・§4 の判断表・§6 の基準表には入っている。この 1 セルだけ更新漏れ。

#### M-5. `dim_company` の出力に `corporate_number` を足している（正典の属性一覧に無い）

正典 §4 の `dim_company` の「主な属性」に `corporate_number` は無い（`companies` のソース列にはある）。§5-a の aside と §7-c の解答が `corporate_number` を「企業の同一性の担保」として使っており論旨上は必要なので、**削るのではなく正典への追加提案として報告に書く**のが筋（報告 §4 の提案 1〜3 と同じ扱い）。「主な属性」という書き方なので網羅列挙ではない、と読む余地はある。

#### M-6. `dbt_valid_to_current` が dbt Core 1.9+ 限定である旨が無い

`dbt_valid_to_current` と YAML 形式のスナップショット（`snapshots/*.yml` に `name` / `relation` / `config`）はどちらも dbt Core v1.9 で入った。1.8 以下では `snapshots/*.sql` + `{% snapshot %}` ブロックで、`dbt_valid_to_current` も無い。「既に NULL で運用しているスナップショットには `COALESCE` を挟む」という 1 文が実質そのフォールバックになっているので、「（`dbt_valid_to_current` は dbt Core 1.9+。それ以前は `COALESCE` 側で吸収する）」と括弧書きで足せば足りる。

#### M-7. `fct_scout` の `profile_versions` に `where deleted_at is null` が無い

`dim_member`（§5-b）と `dim_member_daily`（§5-c）の `versions` CTE は `where deleted_at is null` を付けているが、`fct_scout` の `profile_versions` だけ付いていない。退会会員のスカウトで `member_key` は `-1`（I-4 適用後）なのに `member_profile_mini_key` は解決される、という非対称が起きる。どちらかに揃える。

#### M-8. DT#15 の「Type 6 (2+3+1)」の命名は Margy Ross 自身の造語ではない

§3 の aside:

> この組合せを「perhaps we should refer to this as Type 6 (2+3+1)」と呼んだ。

DT#15 の原文は「**As a student recently suggested,** perhaps we should refer to this as Type 6 (2+3+1)…」で、命名の出所は受講生である。「呼んだ」を「受講生の提案としてこう呼び始めた」程度に緩めると原文に忠実になる。DT#15 の他の 2 つの引用（`perfectly partitioning history` / `For all prior dimension rows ...`）は逐語一致（PDF を画像として確認）。

---

## 3. 検算・静的検証の記録

やった検証と結果を残す。指摘に至らなかったものも含む。

| 検証 | 結果 |
|---|---|
| `check_svg.py html/05_scd.html` | **0 errors, 0 warnings**（再実行で確認）。ノード 6（版 3 + イベント 3）≤ 9、accent 1 系統、斜めコネクタゼロ、`#dg-asof` スコープ・marker id 前置・ダーク 3 系統すべて規約どおり |
| `S001`(6/20 11:30) の as-of 解決 | `dim_member` の版は `[2026-01-05, 2026-08-01)` の 1 本のみが `sent_at >= valid_from and sent_at < valid_to` を満たす。`current_company_id` = `C002` ✅。`profile_versions` 側は `[2026-06-15 09:12, 2026-08-01)` が当たり `(600_800, active)` ✅。§5-b の表は正しい |
| `P001`(6/23) / `R001`(3/10) | `P001` → 同じ `(v1)`、mini は `(600_800, active)` ✅。`R001` → `dim_member` は同じ `(v1)`、mini は `(400_600, passive)` ✅。`fct_review` が `member_key` を持たない旨の注記も正典 §6 どおり |
| `dbt snapshot` の設定と列名 | dbt docs（Snapshots）と突合。YAML の `name` / `relation` / `config`、`strategy: timestamp` + `updated_at`、`dbt_valid_from` / `dbt_valid_to` / `dbt_scd_id` / `dbt_updated_at`、現行行の `dbt_valid_to` が既定 NULL、`dbt_valid_to_current` の存在と用途、すべて一致。docs の例は Snowflake 方言（`to_date('9999-12-31')`）で、BigQuery 向けに `cast('9999-12-31' as timestamp)` に直したのは妥当 |
| `COALESCE(valid_to, '9999-12-31')` の型 | 本文は全 4 か所で `coalesce(dbt_valid_to, timestamp '9999-12-31')` と型つきリテラル ✅。裸の文字列は 1 か所も無い（grep 確認）。`timestamp '9999-12-31'` は BigQuery の TIMESTAMP 有効範囲（〜9999-12-31 23:59:59.999999 UTC）の内側で有効 |
| `TO_JSON_STRING(STRUCT(...))` + `LAG` の畳み込み | 論理的に正しい。先頭行は `LAG` が NULL → `X = NULL` が UNKNOWN → `else 1` で `version_no` が 1 から始まる ✅。`SUM(is_change) OVER (... ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)` で連続する同値の版が同じ `version_no` に落ちる ✅。`TO_JSON_STRING` は NULL を `null` 文字列にするので NULL 同士の比較も正しく「変化なし」になる ✅。`MIN(valid_from)` / `MAX(valid_to)` は区間が連続なので畳んだ区間の端になる ✅ |
| `generate_surrogate_key(['member_id', 'min(valid_from)'])` | BigQuery では `TO_HEX(MD5(...))` の中に集約関数が入る形になるが、`member_id` は `GROUP BY` にあるので構文・意味とも有効 ✅ |
| `QUALIFY` 単独使用（`dim_company` の `current_name`） | BigQuery は `WHERE` / `GROUP BY` / `HAVING` 無しの `QUALIFY` を受け付ける（ZetaSQL パーサだけが拒否する）。問題なし |
| `dim_member_daily` の「その日の終わり」判定 | `v.valid_from < T and v.valid_to >= T`（`T` = 翌 00:00 JST）は「`T` の直前の瞬間に有効だった版」を返す。区間が連続なので常にちょうど 1 行 ✅。7/31 の行が 8/1 00:00 に始まる版を拾わないことも確認 ✅。`TIMESTAMP(date, 'Asia/Tokyo')` / `TIMESTAMP_ADD(..., INTERVAL 1 DAY)`（DAY は TIMESTAMP_ADD の対応単位）とも BigQuery で有効 |
| `dim_member_daily` の結果表 | 6/15 の行が変化後（`600_800` / `active`）になるのは「その日の終わり」定義どおり ✅。`member_key` が 6/14〜6/23 で `(v1)`、8/1 で `(v2)` になるのも `dim_member` の 2 版と整合 ✅ |
| `require_partition_filter` | 利用側クエリに `where md.snapshot_date between date '2026-06-01' and date '2026-06-30'` が実際に書かれている ✅（JOIN の `ON` だけでは BigQuery のパーティションフィルタ要求を満たさないので、これは正しい配慮）。`require_partition_filter` が dbt-bigquery のモデルレベル config であることも docs と一致 |
| 行数の検算 | 会員 300 万 × 365 日 = 10.95 億 ≒「約 11 億行」✅。`dim_member_profile_mini` = 5（`annual_income_band`）× 3（`job_change_intent`）= 15 行 ✅ |
| §5-d のクエリ | `now` は BigQuery の予約語ではないので別名として有効。`and now.is_current` の裸のブール述語も有効。`R001` が両方の切り口で 3.5 になるのは正典（`overall_score` = 3.5、`C002` の規模変化は 5/1）と整合 ✅ |
| §7-a の ID 対応 | 正典 §5 の「`A01` / `AG01` キャリアブリッジ（`gold`）/ 担当 佐藤」を `A01`=エージェンシー、`AG01`=担当者と正しく読んでいる（`S002` の「`AG01`(agent)」とも整合）。ブリーフ §7-a の「`A01`→`A02` に移籍」より正確 |
| 本文のテーブル名 | 21 個すべて `domain.md` に存在。`snap_companies` / `snap_members` / `snap_summaries` / `stg_careervoice__{industries,prefectures,scouts}` は命名規約（`snap_*` / `stg_careervoice__<table>`）どおりで問題なし |
| URL | 13 本すべて `references.md` 内 |
| 原典引用の逐語確認（WebFetch / PDF） | SCD Part 1 の 3 引用 ✅／SCD Part 2 の end-effective-datetime の規約 ✅／DT#152 の Type 0/4/5/6/7 の 5 引用 ✅（Type 0・Type 7 に軽微な改変、M-3）／DT#15 の 3 引用 ✅（PDF を画像で確認、Margy Ross・2000-10-29）／FDE の 4 フレーズ ✅ 逐語一致／Wilson の 4 引用 ✅ 逐語一致。**不一致は I-1 の 1 件のみ** |
| HTML 体裁 | `<title>` = 「履歴を持つ：SCD とスナップショット — データマート設計 05」✅／`p.meta` の 3 部構成 ✅／h2 は 1〜8 + 参照文献 ✅／`<pre>` 内の生 `<` `>` はゼロ ✅／表 16 本すべて `.table-wrap` ✅／CSS 変数は style.md の骨格と一致 ✅ |

---

## 4. 総合判定

**REVISE**

- Critical: 1（C-1）
- Important: 7（I-1 〜 I-7）
- Minor: 8（M-1 〜 M-8）

内容の水準は高い。ブリーフの必須項目は §1〜§7 の全項目が埋まっており、`BETWEEN` をブリーフ指定どおりに使わず「壊れ方」として扱って半開区間に置き換えた判断、`require_partition_filter` を満たす `WHERE` を利用側クエリに実際に書いた点、`snap_members` の版を畳む `TO_JSON_STRING` + `LAG` の SQL、`dim_agency` 追加後の正典に追従した §7-a は、いずれもブリーフを超えている。引用も 20 件中 19 件が逐語一致で、記憶で書いていないことが確認できる。

差し戻す理由は 1 点に集約される。**正典の「`dim_member` は 2 行」という読み替えが §5・§7 には反映されているのに、§2 に反映されていない**（C-1）。同じ記事の中で `S001` の当たり先が 2 通り書かれており、§7-b の引っかけが先に割れる。図の版番号の衝突（I-6）も同じ読み替えの残滓なので、この 2 つは一緒に直すのが早い。

Important のうち I-1・I-2 は原典の扱いの問題で、この記事の他の引用が正確なだけに例外を残す意味が無い。I-3〜I-5 は SQL / 正典の整合で、いずれも数行の差分で閉じる。I-7 は不足の指摘で、足すと §4 の「バックフィルできるのはスナップショット方式だけ」という主張が強くなる。

Minor は M-2（段落の長さ）以外は局所的な直しで済む。M-5 は本文を直すのではなく、報告の「正典への変更提案」に 1 項目足すのが正しい対処。
