# 05 履歴を持つ：SCD とスナップショット — 再レビュー（修正ラウンド 1 の検証）

対象: `docs/data_mart_modeling/html/05_scd.html`（908 行）
初回レビュー: `review/05_review.md`（Critical 1 / Important 7 / Minor 8）
執筆者の対応報告: `reports/05_report.md`「修正ラウンド 1」
差分: `f31ae7a` → `23f4e90`（133 insertions, 51 deletions）

レビュー担当は初回とは別人。報告は参照するが判定は HTML の実物と原典で行った。
正典は 2026-09-08 時点の `canon/domain.md`（`dim_member` = 2 行 / 6-15 は Type 4 側 / `dim_member_daily` / `registered_at` / `dim_company.corporate_number`(Type0) を含む版）。

---

## 1. 初回指摘 16 件の判定

| ID | 重み | 判定 | 根拠（HTML の該当箇所） |
|---|---|---|---|
| C-1 | Critical | **ADDRESSED** | §2(b) は「送信当時の版（`current_company_id` = `C002`、区間 `[2026-01-05, 2026-08-01)`）」に差し替え済み。§2(c) も「`S001`（6/20）が当たるのは `dim_member` の `[2026-01-05, 2026-08-01)` の版」。「6/15 以降の版」「6/15〜7/31 の版」は `dim_member` 文脈から全て消えた（grep で残存ゼロ）。さらに `member_key` / `member_profile_mini_key` の切れ目が違うことを示す 2 行表と、「**`dim_member` に「6/15 始まりの版」は存在しない**——§7-b で改めて問う」の一文を追加。§2 → §5-b（`(v1)`）→ §7-b（2 行）が完全に一致し、§7-b の引っかけも保存された |
| I-1 | Important | **ADDRESSED** | §3 の 2 枚目 aside から合成引用（`ensures facts use contemporary...`）を削除し、原文 2 文に分割。WebFetch で SCD Part 2 を再取得して逐語確認 — 「With a dimension undergoing Type 2 processing, great care must be taken to use the correct contemporary surrogate keys from this dimension in every affected fact table. **This assures** that the correct dimension profiles are associated with fact table activity」（`assures` / `ensures` を明示的に問い直して確認）、および surrogate key pipeline の定義文、いずれも一致 |
| I-2 | Important | **ADDRESSED** | 「SCD2 が必要」の要約を撤回。WebFetch で Gambill のコメントを再取得し、「Those records flip after the fact, and auditors expect an immutable trail tied to who changed what and when」「So the choice isn't "SCD2 vs datestamps." It's immutable facts at the base, with snapshots or SCD2 as views that match the model and the risk」の 2 引用とも逐語一致。「結論は CDC / イベントログを基盤に置くこと」に訂正され、CareerVoice の Datastream（CDC）へ接続する段落も追加された（初回の修正案の副次的利点まで拾っている） |
| I-3 | Important | **ADDRESSED** | §5-b の `dim_member` は `stg_careervoice__prefectures` を `prefecture_code` で結び `any_value(pf.name) as prefecture` / `any_value(pf.region) as region` を出力。変化検知は `prefecture_code` のまま。出力列 = `member_key`, `member_id`, `birth_year`, `gender`, `prefecture`, `region`, `current_company_id`, `current_job_category`, `registered_date`, `valid_from`, `valid_to`, `is_current` で正典 §4 と一致 |
| I-4 | Important | **ADDRESSED** | `fct_scout` の 4 キー（`member_key` / `member_profile_mini_key` / `scout_sender_key` / `job_posting_key`）と `dim_member_daily` の 2 キーが `coalesce(..., -1)` に。「as-of 解決が当たらなかった場合も `-1`。区間の穴を NULL で流すと `relationships` テストが素通りする」の 2 段落も追加。※ センチネルの**型**に新たな問題が入った（後述 **N-3**） |
| I-5 | Important | **ADDRESSED** | `schema.yml` のコメントを「各版の区間が空でないことだけを見る」に訂正。singular test `tests/assert_dim_company_no_gap_or_overlap.sql`（`lead(valid_from) != valid_to`）を追加し、§2-c の Kimball の規約をテスト化した旨と `relationships` では検出できない旨を本文に明記 |
| I-6 | Important | **ADDRESSED** | 図の帯ラベルが `M001 v1/v2/v3` → `snap v1/v2/v3`。脚注も「最新版 snap v3 ではなく snap v2 に当たる」「snap v1→v2 は Type 4 側の変化。`dim_member` 上では snap v1・v2 が同じ `(v1)` に畳まれる」に。`<desc>` も「M001 について `snap_members` が持つ 3 つの版」に更新。本文の `(v1)`/`(v2)`（`dim_member`）と図の `snap vN` は記号空間が分離され、衝突は解消。ノード 6 / accent 1 系統は不変 |
| I-7 | Important | **ADDRESSED** | §5-a に 3 段落追加（実行開始日より前の履歴は作れない／結果表は 2026-01-05 以前から毎日走っている前提／取りこぼしは `timestamp` でも `check` でも起きる）。§8 の「試せる種」も「スナップショットが…（これは `check` 固有ではなく、`timestamp` でも同じ）」に訂正。※ 3 段落目に新たな誤りが入った（後述 **N-2**） |
| M-1 | Minor | **ADDRESSED** | `fct_scout` に `{{ audit_key() }} as audit_key` を追加。初回レビューはスカラーサブクエリの直書きを提案していたが、`audit_key()` マクロは 02 回（`html/02_fact_types.html:276`）で `SELECT MIN(audit_key) FROM dim_audit` として定義済みでシリーズ共通の呼び出し形。02 回・03 回と同じ形なのでこちらが正しい |
| M-2 | Minor | **ADDRESSED** | 機械カウント（`<p>` から SVG / `<pre>` を除き `。` を数える）で **4 文以上は 69 段落中 4 件**（18 → 4）。残る 4 件はいずれも aside / `<details>` で、太字リード文が 1 文としてカウントされているもの |
| M-3 | Minor | **ADDRESSED** | 3 か所とも原文に復帰。WebFetch で SCD Part 1 を再取得し「Precomputed aggregates (including materialized views and automatic summary tables) that depend on the Home City field must be taken offline at the moment of the overwrite and must be recomputed before being brought back online」が逐語一致することを確認。Type 0 は「the dimension attribute value never changes, so facts are always grouped by this original value」、Type 7 は「... linked to the current row **in the type 2 dimension to present current attribute values**」まで復元 |
| M-4 | Minor | **ADDRESSED** | §1 Type 2 行のセルが `dim_member`、`dim_company`、`dim_agent`、`dim_agency`、`dim_scout_sender` の 5 本に。正典 §4（SCD2 は 5 本）と一致 |
| M-5 | Minor | **ADDRESSED**（裁定により対応不要） | 執筆者は `dim_company` の `versions` CTE と SELECT から `corporate_number` を削除し、§5-a aside と §7-c を「ソース側の `corporate_number`」に書き換えた。裁定は「正典に追加したので外す修正は不要」だったので、この項目自体は ADDRESSED 扱い。ただし**削ったことで正典違反が新たに発生している**（後述 **N-1**） |
| M-6 | Minor | **ADDRESSED** | 「なお `dbt_valid_to_current` と、この YAML 形式のスナップショット定義自体が dbt Core 1.9 以降である（1.8 以下は `snapshots/*.sql` のブロック形式で、`dbt_valid_to_current` が無いぶん `COALESCE` 側で吸収する）」を追加 |
| M-7 | Minor | **ADDRESSED** | `fct_scout` の `profile_versions` CTE に `where deleted_at is null` を追加。`dim_member` / `dim_member_daily` の `versions` と揃った |
| M-8 | Minor | **ADDRESSED** | 「この組合せの呼び名を「As a student recently suggested, perhaps we should refer to this as Type 6 (2+3+1)」——受講生の提案として——書き留めている」に訂正 |

**集計: ADDRESSED 16 / NOT ADDRESSED 0。** 報告の自己申告と実物に食い違いは無かった（M-2 の「18 → 4」も機械カウントで再現）。

---

## 2. 修正で新たに入った箇所の検証

依頼された 6 点を個別に確認した。

| 検証項目 | 結果 |
|---|---|
| §2(b)(c) が `dim_member` 2 版（〜7/31 / 8/1〜）と `member_profile_mini_key` で組み直されているか | ✅ §2(b) の 2 行表が `member_key` = `dim_member`(Type 2) → `[2026-01-05, 2026-08-01)` → `current_company_id`=`C002`、`member_profile_mini_key` = 割当(Type 4) → `[2026-06-15 09:12, 2026-08-01)` → `600_800`/`active` を並置。区間の切れ目が違うことを明示している。§2(c) も `dim_member` の区間表記に統一 |
| as-of join の SQL で `S001`（6/20）が〜7/31 版に当たる表 | ✅ §5-b の 2 行表（as-of = `(v1)` / `C002` / `(600_800, active)` vs `is_current` = `(v2)` / `C001`）。半開区間 `sent_at >= valid_from and sent_at < valid_to` で `S001`(6/20 11:30) が `[2026-01-05, 2026-08-01)` にのみ当たることを再検算して確認。§2(b) 表・§5-b 表・§7-b 解答表の 3 か所で `S001` の当たり先が完全に一致 |
| `COALESCE(..., -1)` | 配置は ✅（`fct_scout` 4 キー、`dim_member_daily` 2 キー）。**センチネルの型が同じ記事の中で矛盾している** → **N-3** |
| `dim_member` の出力列が正典どおりか | ✅ 正典 §4 の 7 属性が過不足なく出ている（I-3 参照）。`left join` 先の `prefectures` は主キー結合なので行は増えない。`generate_surrogate_key` 内の `min(v.valid_from)` は `group by v.member_id, v.version_no` の下で構文・意味とも有効 |
| 引用のカギ括弧が原文どおりか | ✅ 修正で触れた 6 引用を WebFetch で再確認 — SCD Part 1（Type1 破壊 / Precomputed aggregates / outlawed）、SCD Part 2（contemporary surrogate keys + This assures / surrogate key pipeline）、Wilson コメント欄（flip after the fact / the choice isn't）。**全て逐語一致。** `assures` か `ensures` かは追加質問で確定させた（原文は `assures`） |
| 図の記号（`snap_members` の版 vs `dim_member` の版）が本文と一致するか | ✅ 図は `snap vN` のみ、本文の `dim_member` は `(vN)` のみで、名前空間が交差しない。脚注 2 行目が両者の対応（snap v1・v2 → `(v1)`）を明示。`<desc>` も `snap_members` と書いている。accent は snap v2 + `S001` + `P001` の 1 系統でブリーフ指定どおり。ノード 6 ≤ 9 |
| `check_svg.py` | **0 errors, 0 warnings**（自分で再実行） |
| 体裁の再確認 | 表 17 本すべて `.table-wrap`（CSS 定義を除く一致数で確認）／`<pre>` 内の生 `<` `>` ゼロ／リンク 13 本すべて `references.md` 内／本文のテーブル名は `snap_*` `stg_careervoice__*` を除き全て `domain.md` に存在 |

---

## 3. 新規指摘（修正差分の範囲）

### Critical

なし。

### Important

#### N-1. `dim_company` から `corporate_number` を削ったことで、正典 §4 に対して I-3 と同種の違反が発生した

M-5 の裁定は「`corporate_number` は正典に追加したので**外す修正は不要**」だった。ところが執筆者は本文から削る方向で対応し、同じコミット（`23f4e90`）が `canon/domain.md` に `dim_company` の属性として `corporate_number`(Type0) を追加している。結果、いま正典と本文はこうなっている。

- 正典 §4: `dim_company` の主な属性 = **`corporate_number`(Type0)**, `name`(Type1で上書き), `industry`, `sector`, `employee_size_band`, `listing_status`, `hq_prefecture`, `parent_company_id`, `founded_year`
- §5-a の `dim_company.sql` の出力 = `company_key`, `company_id`, `name`, `industry`, `sector`, `employee_size_band`, `listing_status`, `hq_prefecture`, `parent_company_id`, `founded_year`, `valid_from`, `valid_to`, `is_current` — **`corporate_number` だけが欠けている**

これは初回レビューが I-3（`dim_member` に `prefecture`/`region` が無い）で Important とした違反と全く同じ種類で、しかも I-3 を直した同じラウンドで逆向きに入った。加えて論旨も弱くなっている。

- §5-a aside: 「企業の同一性は `company_id` と、**ソース側の** `corporate_number`（法人番号）が担保する」
- §7-c 解答表: 「社名変更が合併を伴う。**ソースの** `corporate_number` も変わる」「`corporate_number` の変化を検知したら新しい `company_id` を発行し…」

「ソース側」に逃がすと、合併の検知は DWH の外の話になる。正典が `dim_company.corporate_number` を Type 0 と定めた以上、これは `dim_company` の中で扱える（＝§5-a の singular test と同じ形でテストにできる）題材である。

**修正案**: 削除を巻き戻す。

```sql
-- versions CTE に戻す
        corporate_number,
-- SELECT に戻す（Type 0 = 版をまたいで変わらない）
    v.corporate_number,
```

あわせて §5-a aside と §7-c の「ソース側の」「ソースの」を落として `dim_company.corporate_number` に戻す。さらに 1 行足せるとよい: `corporate_number` は **Type 2 のディメンションの中に置かれた Type 0 属性**で、これはこの回が §1・§3 で扱っている「1 つのディメンションに複数の Type が同居する」（Type 6 = 2+3+1）の最小例である。§1 の Type 0 行の CareerVoice セルは現在 `dim_date` / `dim_channel` / `dim_contract_plan` / `dim_moderation_reason` の 4 本だけで、正典が持っている唯一の「Type 2 の中の Type 0 属性」の例を取りこぼしている。

同じ列を `dim_company` に持てば、合併の検知もこの回の道具立てで書ける。

```sql
-- tests/assert_dim_company_corporate_number_is_type0.sql
-- 同じ company_id の版で corporate_number が変わっている（= 別法人の使い回し）行を返す
select company_id
from {{ ref('dim_company') }}
group by company_id
having count(distinct corporate_number) > 1
```

#### N-2. §5-a の新段落「後から遡って作り直せるのは日次スナップショット方式だけ」が、§5-c の `dim_member_daily` の実装と矛盾する

I-7 の修正で追加された 3 段落目。

> これは §4 の主張の裏付けでもある。**後から遡って作り直せるのは日次スナップショット方式だけ**で、SCD2 のテーブルは一度取り逃した変化を取り戻せない。

これは直前の 2 段落（＝「スナップショットは実行を始めた日より前の履歴を作れない」「初回実行が 2026-07 なら 6/15 の変化は永久に取れない」）の直後に置かれているので、読者は「取り逃した履歴を復元できるのは日次スナップショットの方だ」と読む。だが §5-c の `dim_member_daily` は

```sql
    from {{ ref('snap_members') }}
```

であり、**`snap_members` から作られている**。`snap_members` の初回実行が 2026-07 なら `dim_member_daily` の 1〜6 月のパーティションも作れない。日次スナップショット方式が持つバックフィルの優位は §4 の比較表が正しく書いているとおり「**各日のパーティションを独立に・並列で再計算できる**」ことであって、「捕捉していない履歴を復元できる」ことではない。復元にソース側の履歴（Datastream の CDC ログ）が要るのは SCD2 も日次スナップショットも同じで、そこに差は無い。

このまま残すと、I-7 で足した警告（「実行開始日より前は作れない」）を次の段落が自分で打ち消す形になる。

**修正案**（主張を §4 の表と同じ範囲に戻す）:

> これは §4 の主張の裏付けでもある。**捕捉済みの期間を作り直せる**のは日次スナップショット方式だけで、SCD2 のテーブルは MERGE の結果として状態を持つため、同じ日を流し直しても元に戻らない。ただし**どちらの方式も、捕捉していない履歴はソース側の CDC ログからしか復元できない** — `dim_member_daily` も `snap_members` の上に載っているので、この点で SCD2 より有利にはならない。

#### N-3. I-4 の `coalesce(..., -1)` が、同じ記事の `dim_member` のキー生成式および 03 回の判断と型で食い違う（この SQL は BigQuery で通らない）

`fct_scout` / `dim_member_daily` に入った形:

```sql
    coalesce(dm.member_key,              -1) as member_key,
    coalesce(pm.member_profile_mini_key, -1) as member_profile_mini_key,
    coalesce(ss.scout_sender_key,        -1) as scout_sender_key,
    coalesce(jp.job_posting_key,         -1) as job_posting_key,
```

型が 2 か所で合わない。

1. **同じ記事の中**: §5-b の `dim_member` は `{{ dbt_utils.generate_surrogate_key(['v.member_id', 'min(v.valid_from)']) }} as member_key` で `member_key` を作る。BigQuery ではこれは `TO_HEX(MD5(...))` ＝ **STRING** に展開される。したがって `coalesce(dm.member_key, -1)` は `No matching signature for function COALESCE for argument types: STRING, INT64` でコンパイルエラーになる。記事の 2 つの `<pre>` が直接矛盾している。
2. **03 回の判断との関係**: 03 回（`html/03_dimensions.html` の「判断: どのディメンションにどのキーを使うか」）は SCD2 の 5 本を `FARM_FINGERPRINT(自然キー + '|' + valid_from)` ＝ **INT64**、ミニ／ジャンクも INT64 ハッシュ、`dim_job_posting` は「**自然キーをそのまま `_key` に別名付け**」＝ソースの型（`job_posting_id` は STRING）と決めている。この判断に従うなら `member_key` / `member_profile_mini_key` / `scout_sender_key` は `-1` で正しく、**`job_posting_key` だけが `'-1'` でなければならない**。

直後の「キーが STRING 型なら `'-1'` を使う（正典 §4）」という一文は原則としては正しいが、**印刷されている SQL 自体はどちらの読み方でも通らない**。読者がコピーする対象がコンパイルできないのは、この回が「実際に動く SQL を出す」ために `BETWEEN` を捨てて半開区間にした判断とも釣り合わない。

**修正案**（03 回の判断に合わせるのが最短。`dim_member` の 1 行を直すと as-of 側は全て `-1` のままでよくなる）:

```sql
-- §5-b の dim_member（03 回の判断に合わせる）
    farm_fingerprint(concat(v.member_id, '|', cast(min(v.valid_from) as string))) as member_key,
```

```sql
-- §5-b の fct_scout（job_posting_key だけ STRING センチネル）
    coalesce(dm.member_key,              -1)   as member_key,
    coalesce(pm.member_profile_mini_key, -1)   as member_profile_mini_key,
    coalesce(ss.scout_sender_key,        -1)   as scout_sender_key,
    coalesce(jp.job_posting_key,         '-1') as job_posting_key,   -- dim_job_posting は自然キー = STRING（03 回）
```

`dim_member_daily` の 2 キーはどちらも INT64 側なので `-1` のままでよい。`dim_company` の `company_key` も同じ理由で `generate_surrogate_key` → `FARM_FINGERPRINT` に揃えると、記事全体で 03 回の判断と一貫する（本文の「生成方法は 03 回の判断に従う」という断り書きとも整合する）。

---

## 4. 新規の Minor（参考。判定には算入しない）

- **図の帯の日付と `snap_members` 表の境界が半日ずれる**: 図は `snap v1` = 「〜 2026-06-14」、`snap v2` = 「2026-06-15 〜 07-31」だが、§5-b の `snap_members` 表の境界は `2026-06-15 09:12`。§5-c 本文が「6/15 08:00 に送られたスカウトは（日次では）`active` として解決され、実際には `passive` だった」と書いているので、図のラベルだけを見た読者は 6/15 08:00 が snap v2 に入ると読む。ブリーフの図指定が日単位（〜6/14、6/15〜7/31、8/1〜）なのでラベル自体は指定どおりであり、直すなら `snap v2` の帯に `2026-06-15 09:12 〜` と時刻を入れる程度。
- **§4 modern aside で「ただし」が連続する 2 段落の頭に来ている**（「ただし記事のコメント欄で…」「ただし彼の結論は…」）。後者を「ただし彼の結論は」→「だが彼の結論は」等にすると読みやすい。
- **§2(b) 表の `member_profile_mini_key` の区間 `[2026-06-15 09:12, 2026-08-01)`** は `fct_scout` の `profile_versions`（`snap_members` を畳まずに使う CTE）が実際にマッチする行の区間なので SQL とは一致している。ただし「割当」としての `(600_800, active)` は 8/1 以降も続く（snap v3 も同値）ので、「割当の区間」と読むと 8/1 で切れているのが不自然に見える。表頭が「`S001`（6/20）が当たる区間」なので誤りではないが、`dim_member` 側は畳んで `dim_member_profile_mini` 側は畳まない非対称に 1 行の注記があると親切（畳まなくても参照先は 15 行の静的表なのでキーは変わらない、という理由が既に SQL のコメントに書いてある）。

---

## 5. 検証の記録

| 検証 | 結果 |
|---|---|
| `python3 ~/.claude/skills/svg-diagram/scripts/check_svg.py docs/data_mart_modeling/html/05_scd.html` | **0 errors, 0 warnings** |
| 4 文以上の段落（`<p>` から SVG / `<pre>` 除去、`。` カウント） | 69 段落中 **4 件**（初回 18 件から減。残りは aside / details の太字リード文起因） |
| `.table-wrap` | `<table>` 17 本、`table-wrap` 出現 18（CSS 定義 1 を含む）＝ 全表が包まれている |
| `<pre>` 内の生 `<` `>` | ゼロ |
| リンク URL | 13 本すべて `canon/references.md` 内 |
| 本文のテーブル名 | 27 個。`domain.md` に無いのは `snap_companies` / `snap_members` / `snap_summaries` / `stg_careervoice__{industries,prefectures,scouts}` の 6 個で、いずれも正典 §4 の命名規約（`snap_*` / `stg_careervoice__<table>`）どおり |
| 引用の逐語確認（WebFetch） | SCD Part 1（3 引用）／SCD Part 2（3 引用、`assures` を明示確認）／Wilson コメント欄（2 引用）— **修正で触れた引用は全て逐語一致。不一致ゼロ** |
| `S001`(6/20 11:30) の as-of 再検算 | `dim_member` は `[2026-01-05, 2026-08-01)` の 1 行のみが半開区間を満たす → `(v1)` / `C002` ✅。`profile_versions` は `[2026-06-15 09:12, 2026-08-01)` → `(600_800, active)` ✅。§2(b)・§5-b・§7-b の 3 表が一致 |
| `dim_member` の出力列 vs 正典 §4 | 7 属性すべて一致 ✅ |
| `dim_company` の出力列 vs 正典 §4 | **`corporate_number` が欠落**（N-1） |
| `dim_member_daily` の出力列 vs 正典 §4 | `snapshot_date`, `member_id`, `member_key`, `member_profile_mini_key`, `current_company_id`, `current_job_category_code`, `annual_income_band`, `job_change_intent` — 一致 ✅。`partition_by` / `cluster_by` / `require_partition_filter` も正典どおり |
| `audit_key()` マクロ | 02 回（`html/02_fact_types.html:276`）で定義済み。05 回の呼び出しはシリーズの既存形と一致 ✅ |
| singular test の SQL | `lead(valid_from) over (partition by company_id order by valid_from)` をサブクエリで包み `next_valid_from is not null and next_valid_from != valid_to` — BigQuery で有効、意味も「隙間 or 重なり」を正しく返す ✅ |
| `coalesce(key, -1)` の型 | **STRING キーと INT64 センチネルの混在**（N-3） |
| §5-a の新 3 段落 | 1・2 段落目は正確。3 段落目に誤り（N-2） |

---

## 6. 総合判定

**REVISE**

- 初回指摘 16 件: **ADDRESSED 16 / NOT ADDRESSED 0**
- 新規 Critical: **0**
- 新規 Important: **3**（N-1 `dim_company.corporate_number` の欠落／N-2 バックフィルの主張と `dim_member_daily` の実装の矛盾／N-3 `coalesce(key, -1)` の型不整合）
- 新規 Minor: 3（参考、上記 §4）

修正ラウンド 1 の質は高い。C-1 は §2 の文言を直すだけでなく `member_key` と `member_profile_mini_key` の切れ目の違いを表にして「`dim_member` に 6/15 始まりの版は存在しない」と明言するところまで踏み込んでおり、§7-b の引っかけが保存されている。原典の引用は修正後に自分で再取得して直しており、こちらの WebFetch でも全件逐語一致した（`assures`/`ensures` のような 1 語の差まで正しい）。I-5 の singular test、I-7 の実行開始日の制約、M-2 の段落分割（18 → 4）はいずれも初回の修正案を上回るか同等。

差し戻す理由は 3 点で、いずれも**修正ラウンドで新たに入った**もの。N-1 は裁定（「外す修正は不要」）と逆方向に動いた結果の正典違反で、I-3 と同種の欠陥が同じラウンドで再発している。N-3 は印刷された SQL が BigQuery で通らない状態で、この回が「動く SQL を出す」ために `BETWEEN` を捨てた判断と釣り合わない。N-2 は I-7 で足した警告を次の段落が打ち消しており、放置すると記事の主張が自己矛盾する。

3 件とも差分は小さい。N-1 は `corporate_number` の 2 行を戻して aside と §7-c の「ソース側の」を落とす、N-2 は 1 段落の言い換え、N-3 は `dim_member` のキー生成式 1 行と `job_posting_key` のセンチネル 1 個。次のラウンドで閉じられる。
