# 05 履歴を持つ：SCD とスナップショット — 執筆報告

- 出力: `docs/data_mart_modeling/html/05_scd.html`
- タイトル: `履歴を持つ：SCD とスナップショット — データマート設計 05`
- 図: 1 枚（as-of join の概念図、`#dg-asof`）／`check_svg.py` = **0 errors, 0 warnings**

## 1. 完了した節

| 節 | 内容 | ブリーフの必須項目 |
|---|---|---|
| §1 | 導入 1 段落 + 「この回で確定させる判断」表（7 行）+ **Type 0〜7 の表**（定義 / 履歴 / 行の増え方 / CareerVoice での適用） | ✓ `dim_company.name`=1、`employee_size_band`=2、`dim_member_profile_mini` 経由=4、`dim_company` 全体=6 相当。Type 3/5/7 は「採らない」を明記 |
| §2 | 壊れ方 3 例 | ✓ (a) `dim_company` Type1 で `C002` の `50_299` 時代の平均が出せない（`R001` 3/10 投稿 vs 5/1 の規模変化）(b) 現在の `member_key` で結んで `S001`(6/20) が 8/1 入社後の版に紐づく (c) `valid_to` NULL で `BETWEEN` が外れる |
| §3 | Kimball 原則表（Type 0〜7 の原典定義、英語原文を引用）+ aside 2 枚（DT#15 の Type 6 = 2+3+1／surrogate key pipeline） | ✓ 「ファクトはロード時点でサロゲートキーを解決する」原則を独立の aside に |
| §4 | FDE の日次スナップショット（利点/欠点の 7 行比較表）、Zach Wilson の運用コスト論と反論、「何が変わり何が残るか」、**エンティティ別の判断表** | ✓ 会員=スナップショット／企業=SCD2 を根拠付きで |
| §5 | (a) dbt snapshot YAML + `dim_company` モデル + `schema.yml` (b) `dim_member` の版畳み込み + **as-of join の `fct_scout`**、`M001`/`S001` の結果行を 3 表で (c) `dim_member_daily`（`insert_overwrite` + `partition_by(snapshot_date)`）と `snapshot_date = DATE(sent_at)` 結合、結果行 (d) `company_id` で `is_current` 版へ再結合 | ✓ 4 項目すべて。図は §5 冒頭 |
| §6 | 「行数 × 変化頻度 × 必要な時間精度 → 選択」の 8 行表 + 採らなかった Type 3/5/7 とその採用条件 | ✓ |
| §7 | 演習 3 問、各 `<details>` に解答例 | ✓ (a) `AG01` の `A01`→`A02` 移籍と成果報酬の帰属 (b) `M001` の `dim_member` 行数と `valid_from/to` (c) `dim_company.name` の Type1 で困る分析 |
| §8 | `news_pipeline` の `summaries` = Type1、`updated_at` 相当が無いので `strategy: check` になる、`dbt_logs_analysis` には SCD 対象が無い、試せる種 1 行（4 項目） | ✓ 手元の基盤への言及はこの節だけ |
| 参照文献 | 使った 12 件のみ | ✓ 全 URL が `canon/references.md` 内 |

## 2. 読んだ文献と引用した要点

WebFetch で実際に取得（DT#15 は PDF が WebFetch でテキスト化できなかったため、保存された PDF を Read で画像として読んだ）。

| 文献 | 引用・使用した要点 | 使った節 |
|---|---|---|
| SCD Part 1（Type1） | "Type 1 destroys the history of a particular field" / 事前計算集約は "taken offline and recomputed" / 規制環境では "Type 1 changes may be outlawed" | §2-a, §3 |
| SCD Part 2（Type2/3） | begin/end effective datetime、reason、current flag の 5 列。"The end-effective-datetime of a Type 2 dimension record must be exactly equal to the begin-effective-datetime of the next change"。surrogate key pipeline = "ensures facts use contemporary surrogate keys, guaranteeing the correct dimension profiles are associated with fact table activity" | §2-c（境界の重複＝`BETWEEN` の罠）, §3 |
| DT#15 Combining SCD Techniques（PDF, 2000-10-29, Margy Ross） | Type2 で "the fact table rows will reference the new surrogate key with the new roll-up thereby **perfectly partitioning history**"／"perhaps we should refer to this as Type 6 (2+3+1)"／完全な Type 6 は「当時の値」と「現在の値」を**両方**列として持つ | §3 aside, §5-a aside, §7-c |
| DT#152（Type 0,4,5,6,7） | Type0 "Facts are always grouped by this original value"／Type4 "A group of dimension attributes are split off into a separate mini-dimension"／Type5 "embedding a 'current profile' mini-dimension key in the base dimension"／Type6 "filtered or grouped by either the type 2 value in effect when the measurement occurred or the attribute's current value"／Type7 "dual foreign keys ... a surrogate key ... plus the dimension's durable supernatural key" | §1 表, §3 表, §6 |
| FDE（ssp.sh/brain/functional-data-engineering） | "the partition (not the row) is the atomic unit of state; always overwrite whole partitions instead of UPDATE/DELETE/APPEND"／ディメンションは "append a full snapshot per run; trade cheap storage for clarity and reproducibility" | §4 |
| ssp.sh/brain/snapshotting | 冪等・再現性（不変パーティションなので再実行が安全）／`GROUP BY date` で時系列が自明／欠点はストレージ重複とスナップショット間の粒度喪失 | §4 比較表 |
| SCD-2 considered harmful（Zach Wilson） | バックフィルの直列性（"Rerun November 1st... wait for it to finish..."）／クエリの複雑さ（`valid_from <= ... AND (valid_to > ...`）／日次用と backfill 用の 2 系統コード／代替は "all 30 days kick off in parallel"。**コメント欄の Chris Gambill の反論**（人手編集の業務データ・規制下の監査証跡は SCD2 でなければならない、Wilson は答えていない）も引いた | §4 modern aside |
| dbt Snapshots | 新 YAML 形式（`snapshots/*.yml` の `name` / `relation` / `config`）、`strategy: timestamp` vs `check`、`dbt_valid_from/to/scd_id/updated_at`、**現行行の `dbt_valid_to` は既定 NULL**、`dbt_valid_to_current` で上書き可 | §2-c, §5-a |
| dbt BigQuery configs / BQ partitioned tables | `insert_overwrite`、`partition_by`、`require_partition_filter` | §5-c |

## 3. `check_svg` の結果

```
$ python3 ~/.claude/skills/svg-diagram/scripts/check_svg.py docs/data_mart_modeling/html/05_scd.html
0 errors, 0 warnings
```

図の設計: viewBox 800×392、ノード 6（版 3 + イベント 3）、矢印 4（縦の解決 3 + 時間軸 1）、accent 1 系統（6/15〜7/31 の版と、そこに落ちる `S001`・`P001`）。斜めのコネクタゼロ。日本語ラベルは全て 11px 以上（`--mono` に日本語フォントのフォールバックを足した）。

## 4. 正典への変更提案

### 提案 1（要判断）: `dim_member_daily` を正典に追加する

ブリーフ §5-c が名指しで要求しているが `canon/domain.md` §4 に無い。本文では次の定義で書いた。

| テーブル | 粒度 | 列 | 物理 |
|---|---|---|---|
| `dim_member_daily` | 1 行 = 1 会員 × 1 日（その日の終わり = 翌 00:00 JST 時点の版） | `snapshot_date`(DATE), `member_id`, `member_key`, `member_profile_mini_key`, `current_company_id`, `current_job_category_code`, `annual_income_band`, `job_change_intent` | `partition_by=snapshot_date`, `cluster_by=member_id`, `require_partition_filter=true`, `insert_overwrite` |

`dim_member`（Type2）は正典どおり残し、役割を分けた（`dim_member` = ファクトが指すキーの発行元／`dim_member_daily` = 母集団と時点属性の参照先）。09 回の増分戦略と 08 回の ECM でも使えるはずなので、正典に入れるなら早い方がよい。

### 提案 2（要判断）: 6/15 の変化がどのディメンションに属するかの明記

`canon/domain.md` §5 は「`M001` は 2026-06-15 に `active`・`600_800` に変化」と書き、ブリーフ §7-b は「6/15 と 8/1 の変化で `dim_member` は何行になるか」と問う。しかし §4 では `annual_income_band` / `job_change_intent` は `dim_member_profile_mini`（Type 4）側であり、`dim_member` の属性ではない。

**本文の扱い**: 正典（Type 4 の切り分け）を優先し、**`dim_member` は 2 行**とした。6/15 の変化は `snap_members` には 3 版を作るが `dim_member` の属性は動かないので畳む、という形で §5-b に畳み込みの SQL（`TO_JSON_STRING(STRUCT(...))` + `LAG` + 累積和）を置き、§7-b の解答をそこに接続した。図の 3 つの帯も「`snap_members` の版」と明示し、注記で「v1→v2 は `dim_member` の行を増やさない」と書いた。

結果として、ブリーフの意図（S001 が最新版ではなく 6/15 以降の版に当たる）は満たしつつ、正典の Type 4 の判断も壊していない。§7-b は「3 行と答えたくなるが 2 行」という良い引っかけになった。**この読み替えを是としない場合は、`domain.md` §4 の `dim_member` に `annual_income_band` / `job_change_intent` を戻す（＝ミニディメンションをやめる）必要があり、03 回・06 回に影響する。**

### 提案 3（軽微）: `M001` の `registered_at` の値

`dim_member` の最初の版の `valid_from` に必要だが正典に無い。本文では **2026-01-05 00:00:00** を使った。正典 §5 に追記するか、別の値に揃えたい場合は指示がほしい。

## 5. 迷った判断とその理由

| 迷い | 決めたこと | 理由 |
|---|---|---|
| ブリーフは `BETWEEN valid_from AND valid_to` を要求しているが、dbt snapshot の規約（旧行の `valid_to` = 新行の `valid_from`）だと境界時刻ちょうどで 2 行に当たる | §2-c で `BETWEEN` を「壊れ方」として扱い、正しい形として**半開区間** `>= valid_from AND < valid_to` を提示。§5 の SQL は全て半開区間 | 「実際に動く SQL」を出す方が writer_prompt の要件。ブリーフの `BETWEEN` は失敗形として活かした |
| 会員をスナップショットにすると行数が爆発する（ブリーフ §4 も欠点として挙げている）のに、判断はスナップショット | `dim_member`（Type2、変化の遅い属性のみ）と `dim_member_daily`（日次全件）を**役割分担**させた。時点属性の解決と母集団の問いは後者、ファクトが指すキーは前者 | どちらか一方では説明が破綻する。`dim_member_profile_mini`（Type 4）が既に速い属性を吸収している正典の構造がこの分担を支えている |
| `dbt_valid_to_current` は Snowflake 例（`to_date('9999-12-31')`）で書かれている | BigQuery 方言で `"cast('9999-12-31' as timestamp)"` に直した。既存スナップショット向けに `COALESCE(dbt_valid_to, timestamp '9999-12-31')` も併記 | 正典が `valid_to` を TIMESTAMP・`9999-12-31` と規定しているため |
| サロゲートキーの型（INT64 か STRING か） | 踏み込まず、SQL では `dbt_utils.generate_surrogate_key(...)` を使い「生成方法は 03 回の判断に従う。この回に必要なのは版ごとに 1 つのキーがあることだけ」と明記。結果表のキーは `(v1)` / `(v2)` という表示上のプレースホルダにした | `domain.md` §4 の「それ以外の回は `_key` と書くだけで型に踏み込まない」に従った |
| 執筆中に `domain.md` が更新され `dim_agency`（`dim_agent` の縮約、SCD2）と `fct_placement.agency_key` が追加された | §7-a の演習を書き直した。`agency_key`（`placements.agency_id` 由来）と `agent_key`（scout 経由）の**2 経路が同じ答えを返すのが正しい状態**で、片方だけ Type1 にすると 1 行から 2 つの答えが出る、という論点に作り替えた。§1・§4・§6 の表にも `dim_agency` を追加 | 更新後の正典が正。結果として「縮約ディメンションは元と同じ SCD 型に揃える」という DWT ch.4 の原則を演習で扱えるようになり、ブリーフの意図（移籍の帰属は業務ルールで決める）も残した |
| `fct_scout` の `audit_key` | SQL から省き、モデルの焦点を as-of 解決に絞った（10 回で扱う旨は本文に書いていない） | 全ファクトが `audit_key` を持つのは正典どおりだが、この回の SQL に入れると監査ディメンションの生成ロジックの説明が要る。**軽微な未達**として下に再掲 |

## 6. 未達事項

1. **`fct_scout` の SQL に `audit_key` が入っていない。** 正典は「全ファクトは `audit_key` を持つ」と定めている。as-of join の説明に集中させるため省いたが、10 回（監査ディメンション）と突き合わせたときに不整合に見える可能性がある。1 行のコメントを足すか、`{{ ref('dim_audit') }}` からの解決を書き足すかは横断レビューの判断に委ねる。
2. **`dim_member_daily` が正典未収載**（提案 1）。採否が決まるまで、この回だけが持つテーブル名になる。
3. **DWT 3rd ed. ch.5 は書籍のため本文を直接参照できていない。** SCD Type 0〜7 の定義は Design Tip #152 と SCD Part 1–2（いずれも Kimball Group 公式）から取り、章番号は `p.meta` と参照文献での参照に留めた。
4. **`M001` の `registered_at`** を独自に置いた（提案 3）。

---

# 修正ラウンド 1（レビュー `review/05_review.md` への対応）

`check_svg.py` 再実行: **0 errors, 0 warnings**。4 文以上の段落は 18 → 4（残る 4 件は aside / `<details>` の太字リード文が 1 文として数えられているもの）。

| ID | 対応 |
|---|---|
| C-1 | §2(b) の「6/15 以降の版」を「送信当時の版（`current_company_id`=`C002`、`[2026-01-05, 2026-08-01)`）」に、§2(c) の「6/15〜7/31 の版」を「`dim_member` の `[2026-01-05, 2026-08-01)` の版」に差し替え。さらに §2(b) に `member_key`（`dim_member`、`[01-05, 08-01)`）と `member_profile_mini_key`（Type 4 割当、`[06-15 09:12, 08-01)`）の**切れ目が違う** 2 本を並べた表を追加し、「`dim_member` に 6/15 始まりの版は存在しない／§7-b で改めて問う」と明示した |
| I-1 | surrogate key pipeline の合成引用を削除し、SCD Part 2 を WebFetch で再確認したうえで原文 2 文（`With a dimension undergoing Type 2 processing, ... This assures that the correct dimension profiles are associated with fact table activity` ／ `The extract, transform and load (ETL) process for aligning ... is called the surrogate key pipeline`）に分けて引き直した |
| I-2 | Chris Gambill のコメントを WebFetch で再確認。「SCD2 が必要」という要約を撤回し、原文の `Those records flip after the fact, and auditors expect an immutable trail tied to who changed what and when` と `So the choice isn't "SCD2 vs datestamps." It's immutable facts at the base, with snapshots or SCD2 as views that match the model and the risk` を引いて「結論は CDC / イベントログを基盤に置くこと」に訂正。あわせて「CareerVoice は Datastream（CDC）で複製済みなので基盤の不変ログは既にある」を 1 段落追加 |
| I-3 | `dim_member` の出力を正典 §4 どおりに。`prefecture_code` の生出力をやめ、`stg_careervoice__prefectures` を結んで `prefecture` / `region` を出す形にした（変化検知は `prefecture_code` のまま） |
| I-4 | `fct_scout` の `member_key` / `member_profile_mini_key` / `scout_sender_key` / `job_posting_key` と `dim_member_daily` の 2 キーを `COALESCE(..., -1)` に。あわせて「未達だけでなく as-of が当たらなかった場合も `-1`。区間の穴を NULL で流すと `relationships` テストが素通りする。STRING キーなら `'-1'`」の段落を追加 |
| I-5 | `schema.yml` のコメントを「各版の区間が空でないことだけを見る」に訂正し、重なり／隙間を検出する singular test `tests/assert_dim_company_no_gap_or_overlap.sql`（`LEAD(valid_from) != valid_to`）を追加。§2-c で引いた Kimball の規約をそのままテストにした形である旨と、`relationships` テストでは検出できない旨を本文に書いた |
| I-6 | 図の帯ラベルを `M001 v1/v2/v3` → **`snap v1/v2/v3`** に変更（`snap_members` の版であることを記号レベルで分離）。脚注も「最新版 snap v3 ではなく snap v2 に当たる」「`snap v1→v2` は Type 4 側の変化。`dim_member` 上では snap v1・v2 が同じ `(v1)` に畳まれる」に書き換え。`<desc>` も更新。ノード数・accent は不変（6 / 1 系統）。`check_svg.py` 0 errors, 0 warnings |
| I-7 | §5-a に「スナップショットは実行を始めた日より前の履歴を作れない」以下 3 段落を追加（初回実行が 2026-07 なら第 1 版の `dbt_valid_from` は 7 月になる／Datastream の CDC ログがあるうちに初期版を投入する／実行間隔より短い変化の取りこぼしは `timestamp` でも `check` でも起きる／後から遡って作り直せるのは日次スナップショット方式だけ、という §4 の裏付け） |
| M-1 | `fct_scout` に `{{ audit_key() }} as audit_key` を追加（「監査ディメンションの解決マクロ。10 回で定義する」と注記）。`dim_member_daily` はディメンションなので付けない |
| M-2 | 4 文以上の段落を 18 → 4 に削減。Wilson の 3 点とスナップショットが成立する 3 条件は `<ul>` に開き、§5-c の丸めの副作用・§7-a の解答・§5-b の畳み込みの帰結など 10 か所を分割した |
| M-3 | 引用 3 か所を原文に戻した。Type 0 =「the dimension attribute value never changes, so facts are always grouped by this original value」／Type 7 = 末尾の `in the type 2 dimension to present current attribute values` まで／§2-a の集約 =「must be taken offline at the moment of the overwrite and must be recomputed before being brought back online」。いずれも WebFetch で逐語確認済み |
| M-4 | §1「Type 0〜7 と CareerVoice での適用」の Type 2 セルに `dim_agency` を追加 |
| M-5 | `dim_company` の `versions` CTE と SELECT から `corporate_number` を削除（裁定どおり出力から外す）。§5-a の aside と §7-c は「ソース側の `corporate_number`（法人番号）」と書き換えて論旨を維持。正典への追加提案は下記 |
| M-6 | 「`dbt_valid_to_current` と、この YAML 形式のスナップショット定義自体が dbt Core 1.9 以降。1.8 以下はブロック形式で `COALESCE` 側が吸収する」を括弧書きで追加 |
| M-7 | `fct_scout` の `profile_versions` CTE に `where deleted_at is null` を追加（`dim_member` / `dim_member_daily` と揃えた） |
| M-8 | 「この組合せを『perhaps we should ...』と呼んだ」→「原文の `As a student recently suggested, perhaps we should refer to this as Type 6 (2+3+1)` を——受講生の提案として——書き留めている」に訂正 |

## 修正ラウンド 1 で新たに出た正典への変更提案

**提案 4（軽微・要判断）: `dim_company` に `corporate_number` を足すか**

裁定に従い出力から外した。ただし §5-a の aside と §7-c の解答は「社名変更が合併を伴うか（＝別法人か）」の判定に法人番号を使っており、いま本文は「ソース側の `corporate_number`」と書いてソース参照に逃がしている。合併の検知を DWH 側でテストしたい（`dim_company` の同じ `company_id` で `corporate_number` が変わる行を落とす）なら、`domain.md` §4 の `dim_company` の属性に `corporate_number` を足す必要がある。06 回の `br_company_hierarchy`（承継関係）とも接するので、そちらの判断とあわせて決めるのがよい。

## 未対応・持ち越し

無し。Critical 1 件・Important 7 件・Minor 8 件すべてに本文で対応した（M-5 のみ、裁定どおり本文から削除したうえで提案 4 として残した）。
