# 06 多対多・不揃い階層・異種ディメンション — 再レビュー（修正ラウンド 1 後）

対象: `docs/data_mart_modeling/html/06_bridges.html`（715 行、修正後）
初回レビュー: `review/06_review.md`（critical=2 / important=4 / minor=7）
執筆者報告: `reports/06_report.md` §「修正ラウンド 1」
正典: `canon/domain.md`（`S003` / SCD2 5 本 / ブリッジの全版展開 / 想定規模）、`canon/style.md`、`canon/references.md`（`BQ recursive` 追加後）
差分: `git diff f31ae7a 8cbc1bb -- docs/data_mart_modeling/html/06_bridges.html`
判定: **REVISE**（addressed=13 / not_addressed=0 / new_critical=0 / new_important=1）

再レビューは (1) 初回 13 件の実地確認、(2) 修正で入った箇所の検証、(3) `check_svg.py`、(4) 差分範囲の新規指摘に限る。未変更箇所の掘り起こしはしていない。

---

## 1. 初回指摘 13 件の判定

報告の記述は参照せず、HTML の該当箇所を直接見て判定した。

| ID | 重み | 内容 | 判定 | 確認した実物 |
|---|---|---|---|---|
| C-1 | Critical | `p.meta` / 参照文献の DWT 章番号が `ch.6–8` | **ADDRESSED** | L44 `参照: DWT ch.7 ch.8 ch.10, Design Tip #142, Kimball Dimensional Modeling Techniques`。L706 の参照文献 DWT 行が `ch.7（不揃い階層）, ch.8（多値ディメンションとブリッジ）, ch.10（heterogeneous products と口座-顧客ブリッジの weighting factor）`。L132 の DT#142 aside 末尾が「**DWT ch.10（Financial Services）**の口座-顧客ブリッジ側の議論」。`grep "ch\.6"` = **0 件**。`references.md` L85（`06 \| DWT ch.7, 8, 10; DT#142 \| BQ nested`）と一致 |
| C-2 | Critical | `dim_scout_sender` の SK に版が入らず SCD2 が成立しない | **ADDRESSED** | L473–475 が `FARM_FINGERPRINT(CONCAT(sender_type, '\|', sender_id, '\|', CAST(valid_from AS STRING))) AS scout_sender_key`。**版ごとに生成されている**。入力の `valid_from` は実在する（両ブランチが `snap_companies.dbt_valid_from` / `snap_agents.dbt_valid_from` を `valid_from` として持ち上げ、`unioned` を通って到達する）。出力にも `valid_from` / `valid_to` / `valid_to = TIMESTAMP '9999-12-31' AS is_current` が並ぶ。直後 L484 に「キーの入力に `valid_from` を入れるのは省略可能なオプションではない」＋「自然キーだけでハッシュすると全版が同一キーになり、`fct_scout` の結合が版の数だけ増え §2(a) と同じ二重計上が supertype 側で起きる」の段落が入り、03回 L416 の割当（`FARM_FINGERPRINT(自然キー + '\|' + valid_from)`、`dim_scout_sender` を名指し）と噛み合った |
| I-1 | Important | §2(a) が `S003` を使わず架空の「10 件」 | **ADDRESSED** | L68 が `S003`（`AG02` → `M002`、`J001`、2026-06-18 送信）1 行から始まる。検算表 L73–75 が **1 / 2 / 1**、L79 が `ENG-BE` 0.5 / `ENG-DATA` 0.5 で合計 1・重みなし 1/1 で合計 2。規模の話は L81 の別段落（1,240 件）に分離済み。図の `fct_scout` ノードの `sub` も左右とも `S003 / member_key = M002` に更新（ただし表記に難あり → **N-2**） |
| I-2 | Important | BI の繰り返しフィールド挙動を無出典で断定（3 箇所） | **ADDRESSED** | 3 箇所とも条件文化。L241「繰り返しフィールドを『ディメンションとして直接選べるか』は BI ツールごとに違う。直接選べないツールでは…」／L583（§5(d) の `<ol>` 3 項目目）「BI のセルフサービス画面が繰り返しフィールドを直接扱えないなら、カスタムクエリかモデリング層のどちらかで…」／L594（§6 第 1 表）「セルフサービス BI が直結する（`UNNEST` を書かせられない）」。製品名を主語にした断定は消え、`LookML 等` は例示に留まる。いずれも初回レビューの修正案と逐語一致 |
| I-3 | Important | §7(a) の重みの理由が誤り（タグ別の平均は引っ張られない） | **ADDRESSED** | L644–645。「タグ別の平均が引っ張られる」は削除され、「タグ別の件数を**合計して総クチコミ数と突き合わせる**とき」「タグ展開後の全行をプールして 1 本の平均を出すとき」に限定。「**タグ 1 つの中での平均には掛けない**（掛けると多タグのクチコミだけが不当に軽くなり、答えが変わる）」まで明記。論理は正しい（タグ 1 グループ内では 1 クチコミが 1 観測） |
| I-4 | Important | §6「共有所有は再帰 CTE でも表現できない」が §5(b) と矛盾し原典の射程を超える | **ADDRESSED** | L620 の第 4 列が「クエリ時に親子表を辿るだけでは解けず（pathstring も同じ）、あり得る全経路を持つ表が要る。再帰 CTE は §5(b) と同じくその**生成手段**としては使える。経路が複数になるので重み付けも要る」。Techniques PDF の原文（"With SQL extensions … at query time"）の射程に収まった。§5(b) 直後の L427 は指摘どおり無修正 |
| m-1 | Minor | 4 文以上の段落が 43 中 20 | **ADDRESSED（parked）** | 機械チェック（`<p>` を `。` で分割）で **5 文以上 = 0**、4 文 = **13**（報告の「12」と 1 件ずれるが誤差）。列挙型として parked 済みなので指摘対象にしない。分割は §3 の当てはめ / §5(a) の aside / §5(d)（`<ol>` 化）/ DT#142 aside / §7(b)(c) で実施済み |
| m-2 | Minor | ragged 階層の引用が途中で切れているのに「.」で閉じている | **ADDRESSED** | L127 が `…for every possible path in the ragged hierarchy and enables all forms of hierarchy traversal to be accomplished with standard SQL rather than using special language extensions.` まで延長。訳の括弧書きに「しかも標準 SQL のまま辿れる」を追加。初回レビューが推した後者の案 |
| m-3 | Minor | ブリッジにグループキーが無いことの説明が抜けている | **ADDRESSED** | L296（`br_member_desired_job_category` の SQL 直後）に「ここでは `member_key` がグループキーを兼ねる。会員ごとに希望職種のグループが 1 つしかないので、DT#142 の『組合せを重複排除してグループを作る』段は利得を生まない」 |
| m-4 | Minor | `WITH RECURSIVE` の 500 反復上限に出典が無い／「循環参照検出」は推論 | **ADDRESSED** | L412 が「反復上限は 500 で、それを超えるとエラーで止まる。`C001` の親を `C003` にして循環を作ってしまった場合も、新しい行が出続けて 500 反復に達しエラーで落ちる。**無限ループにはならない。**」。「この上限が実質的な循環参照検出になる」という推論は消えた。報告の変更提案 8 に `references.md` への追加要望も記載済み（→ 追加は通ったが本文が追従していない。**N-3**） |
| m-5 | Minor | ARRAY 版 `dim_member` が `member_key` を作らないのに直後のクエリが `m.member_key` で結合 | **ADDRESSED（ただし新たな欠陥を持ち込んだ）** | L537–546 の `member_versions` が `FARM_FINGERPRINT(CONCAT(member_id, '\|', CAST(dbt_valid_from AS STRING))) AS member_key` を明示。`SELECT m.*` を通って L577 の `ON f.member_key = m.member_key` と列名としては噛み合う。`IFNULL` のコメントも「クエリ内では NULL 配列と空配列は別値なので、下流で取り違えないようここで揃える」に因果を修正。**ただしこのキー生成が 05回の `dim_member` の作り方と食い違う → N-1** |
| m-6 | Minor | 図のゾーンラベルの accent が右だけ非対称 | **ADDRESSED** | L198 が `<text class="tag" x="452" y="59">ARRAY IN DIM</text>`。左（`BRIDGE`, L194）と同格。accent は差分ノード（`box-focal` 2 つ）だけになった。`tag-accent` の CSS 定義は L185 に残るが未使用で `check_svg.py` は 0 warnings |
| m-7 | Minor | §6 多値表の 3 行目と 4 行目の切り分けが弱い | **ADDRESSED** | L596 の 3 行目が更新頻度「高」→「**問わない**」、理由列が「更新頻度ではなく**カーディナリティ**で落ちる。ガイドが明示的に外す形で、ディメンションが肥大する」。4 行目（個数が可変で頻繁に変わる・高 → ブリッジ）との条件が重ならなくなった |

**集計: ADDRESSED = 13 / NOT ADDRESSED = 0**

---

## 2. 修正で入った箇所の検証

### 2.1 `dim_scout_sender` の SK は版ごとに生成されているか → はい

```sql
FARM_FINGERPRINT(
    CONCAT(sender_type, '|', sender_id, '|', CAST(valid_from AS STRING))
) AS scout_sender_key,
```

| 検証 | 結果 |
|---|---|
| `valid_from` が `unioned` に到達するか | ✅ 両ブランチが 7 列（`sender_type`, `sender_id`, `sender_name`, `company_industry`, `agency_tier`, `valid_from`, `valid_to`）を同順・同型で出す。`UNION ALL` の列数・順序・型すべて整合 |
| 版ごとに一意か | ✅ (`sender_type`, `sender_id`, `valid_from`) は SCD2 の版の一意キー。`sender_type` 前置により `company_id` と `agent_id` の値域衝突も起きない |
| `CAST(TIMESTAMP AS STRING)` の決定性 | ✅ BigQuery の正準形式。03回 L444 の `member_key` と同形 |
| 03回の割当との一致 | ✅ 03回 L416「SCD2（1自然キーに複数行）→ `FARM_FINGERPRINT(自然キー + '\|' + valid_from)`」に `dim_scout_sender` が名指しで入っている |
| `is_current` の導出 | ✅ `IFNULL(dbt_valid_to, TIMESTAMP '9999-12-31')` の後で `valid_to = TIMESTAMP '9999-12-31'`。現行行だけ true |
| 入力ソースの実在 | ✅ `companies.industry_code` / `industries.name` / `agents.name` / `agents.agency_id` / `agencies.tier` はすべて `domain.md` §2。`snap_companies` は 05回で既出、`snap_agents` は命名規約 `snap_*`（`domain.md` L86）に従う新規（報告の変更提案 10 で申告済み） |
| 05回との整合（company 側） | ✅ 05回 `dim_company` も `snap_companies.dbt_valid_from` を畳まずそのまま `valid_from` にしている（05回 L370）。company ブランチはシリーズ内で一貫 |
| `agency_tier` が現在値である点 | ✅ L486 に明記。正直な自己申告 |

### 2.2 `S003` を使った二重計上の例（2 行、weight 0.5 で合計 1）→ 正しい

- `S003` = `AG02`(agent) → `M002`、`J001`、2026-06-18 送信（`domain.md` L152）✅
- `M002` の希望職種 = `ENG-BE`, `ENG-DATA` の 2 件（`domain.md` L141）✅
- `fct_scout` の `scout_count`(=1)、加法（`domain.md` L124）✅
- 検算: `SUM(scout_count)` = 1 / ブリッジ結合で 2 / `SUM(scout_count * weighting_factor)` = 0.5 + 0.5 = 1 ✅ 本文の表と一致
- 職種別: `ENG-BE` 0.5 / `ENG-DATA` 0.5、`level2_name` でグループ化しても両方 level2 なので潰れない ✅
- `sent_date` = 2026-06-18 は §5(a) の `BETWEEN DATE '2026-06-01' AND DATE '2026-06-30'` に入る ✅（`sent_date` は `domain.md` L91 の `<role>_date` 規約どおり実在）
- L81 の「1,240 件」: 2 件希望の会員宛スカウトが 1,240 件なら内訳合計は 2,480 で「1,240 を超える」✅

### 2.3 `WITH RECURSIVE` の構文 → 変更なし・引き続き妥当

L343–411 は今回の差分外（変わったのは L412 の解説文のみ）。再確認した範囲では `WITH RECURSIVE` の位置（WITH 句全体に掛かる）、非再帰 CTE（`base`, `flags`）の同居、再帰項の `paths` 参照ちょうど 1 回、`UNION ALL`、集計・分析関数・`LIMIT` なし、depth 0 の自己行、いずれも BigQuery 仕様に適合。L412 の書き換え後の記述（500 反復でエラー・無限ループにならない）も事実ベースに収まっている。

### 2.4 ARRAY 版 `dim_member` の `member_key` 出力 → 出力はされるが、作り方が 05回と食い違う（→ N-1）

`member_versions` が `member_key` を選び、`SELECT m.*` で下流に流れ、L577 の `ON f.member_key = m.member_key` と列名では噛み合う。m-5 の指摘（列が存在しない）は解消。ただしキーの**入力**が 05回の `dim_member` と違う。詳細は N-1。

### 2.5 BI 断定の弱め方 → 3 箇所とも条件文化済み

I-2 の行に記載。初回レビューの修正案と逐語一致。§4 の結論（「性能は決め手にならない。決め手は BI からの見え方」）は、断定ではなく「直接選べないツールでは平坦化が要る」という条件付きの主張に載り替わっており、無出典の前提の上に結論が立つ状態は解消した。

### 2.6 `p.meta` / 参照文献の章番号 → 一致

`p.meta`（L44）・参照文献（L706）・本文 aside（L132）の 3 箇所すべてが `ch.7 / ch.8 / ch.10`。`ch.6` は 0 件。`references.md` L85 と一致。

### 2.7 機械チェック（再実行）

| 項目 | 結果 |
|---|---|
| `python3 ~/.claude/skills/svg-diagram/scripts/check_svg.py docs/data_mart_modeling/html/06_bridges.html` | **0 errors, 0 warnings** |
| `<pre><code>` 内の生 `<` | 0 件（9 ブロック全走査） |
| `<code>` トークン × `domain.md` 突合 | 正典に無いテーブル名・列名・ID は 0 件（残差はすべて SQL キーワード / CTE 名 / dbt 設定キー / `stg_careervoice__*`・`snap_*` の規約名 / 手元基盤の実名） |
| 本文の全 URL（6 本） | 6 本とも `references.md` に存在 |
| `<p>` の文数 | 5 文以上 = 0、4 文 = 13（parked） |
| `<title>` | `多対多・不揃い階層・異種ディメンション — データマート設計 06`（ブリーフ指定と一致） |
| 節構成 | h2 が 1〜8 + 参照文献 |
| `.table-wrap` | 幅広の表はすべて包まれている |

---

## 3. 新規指摘（修正差分の範囲）

### Critical

なし。

### Important

#### N-1. §5(d) の `member_versions` が 05回の `dim_member` の作り方を飛ばしている（m-5 の修正で持ち込まれた）

L537–546:

```sql
member_versions AS (

    -- dim_member の既存本体。05回の SCD2 変換（snapshot → 版付きキーの付与）まで
    -- 済んだ会員行。この対案では一切変えない
    SELECT
        FARM_FINGERPRINT(
            CONCAT(member_id, '|', CAST(dbt_valid_from AS STRING))
        ) AS member_key,
        member_id,
        …
    FROM {{ ref('snap_members') }}

)
```

05回（`html/05_scd.html` L455–525）の `dim_member` はこう作られていない。

1. **畳み込みが必要**と明記されている。L455:「`snap_members` は `members` の**どの列が変わっても**版を切るので、`dim_member` の属性だけを見ると同じ内容の版が連続する。**これを畳まないと `member_key` が意味なく増える**」。実装は `flagged`（`to_json_string(struct(...))` を `lag` と比較）→ `collapsed`（`sum(is_change) over (…)` で `version_no`）→ `group by v.member_id, v.version_no`。
2. **キーの入力は `min(v.valid_from)`**（畳んだ版グループの先頭）であって、生の `dbt_valid_from` ではない。05回 L509: `generate_surrogate_key(['v.member_id', 'min(v.valid_from)'])`。
3. **`where deleted_at is null`** のフィルタもある（05回 L470）。
4. 05回 L527 は結果を明示している——「`snap_members` は 3 版だが、`dim_member` は **2 行**になる」（`M001`）。

06 の書き方だと `M001` は **3 行**になる。この CTE のヘッダーコメントは「05回の SCD2 変換まで済んだ会員行」「この対案では一切変えない」と言っているのに、SQL は 05回の変換を実際には**変えている**（畳み込みと削除フィルタを落としている）。ブロックの見出しも `models/marts/dim_member.sql（ARRAY を内包する対案。列を 1 本足すだけ）` なので、読者はこれを `dim_member` の本体として読む。結果:

- `dim_member` の粒度が 05回と変わる（版が余分に増える）。この回自身が §5(c) で「版が増えるとファクトが増殖する」と論じているのと同じ土俵の問題。
- `member_key` の値域が 05回のものと一致しない版が生まれ、`fct_scout.member_key`（05回の `dim_member` に対する as-of 解決の産物）と突き合わない行ができる。L570 の「結果は (a) と同じ」という主張が `M001` のような多版会員では成り立たない。

なお §5(c) の company ブランチが `snap_companies.dbt_valid_from` を直に使っているのは**正しい**（05回の `dim_company` L370 が同じことをしており、company 側には畳み込みが無い）。食い違っているのは member 側だけである。

**修正案**（L537–546 を、05回の再現ではなく参照に留める。この回の主題は ARRAY 列の追加なので、`dim_member` の版の作り方を再掲する必要が無い）:

```sql
member_versions AS (

    -- dim_member の既存本体。05回の versions → flagged → collapsed（同内容の連続版を
    -- 畳む）→ member_key = 自然キー + min(valid_from) のハッシュ、までは一切変えない。
    -- ここでは member_key / member_id / valid_from / valid_to / is_current が
    -- 揃っている前提だけを使う（05回 §5-b の SELECT をそのまま置く）
    SELECT
        member_key,
        member_id,
        -- 属性列（birth_year, prefecture, region, …）は省略
        valid_from,
        valid_to,
        is_current
    FROM {{ ref('snap_members') }}  -- ← 05回の畳み込み CTE 群を経由する
)
```

キー生成式を残したいなら、入力を `min(valid_from)`（畳んだ版の先頭）にし、`deleted_at` フィルタと畳み込み CTE を省略した旨をコメントに書く。どちらでもよいが、**現状の「生の `dbt_valid_from` を直接ハッシュしつつ『05回の変換まで済んだ行』と書く」形は残さない。**

### Minor

#### n-2. 図の `fct_scout` ノードの `sub` が `member_key = M002`（`member_key` ではなく `member_id` の値）

L215 / L225 とも `<text class="sub">S003 / member_key = M002</text>`。この シリーズでは `member_key` は `FARM_FINGERPRINT(...)` の INT64（03回 L416, L444）であって `M002` ではない。同じ図の右パネル L230 は `member_id = M002` と正しく書いており、1 枚の図の中で同じ値に 2 つの列名が付いている。I-1 の対応で `sub` を書き換えた際に混入した。

**修正案**: 両方の `fct_scout` ボックスの `sub` を `S003 / member_id = M002` にするか、キー名を出さず `S003（M002 宛）` にする。文字数はほぼ変わらないので `check_svg.py` には影響しない。

#### n-3. `references.md` に `BQ recursive` が入ったのに、§5(b) と参照文献が追従していない

`canon/references.md` L68 に `BQ recursive | Google Cloud, 再帰 CTE（WITH RECURSIVE） | https://cloud.google.com/bigquery/docs/recursive-ctes | 構文・反復上限などの仕様` が追加された（報告の変更提案 8 が通った形）。初回レビュー m-4 の「本文は現状のままでよい」は「正典に無いから URL を出せない」という前提の上の判断だったので、前提が消えた。

L412 は自己参照ちょうど 1 回・`UNION ALL`・集計/分析関数と `LIMIT` の禁止・反復上限 500 という**仕様上の事実**を出典なしで並べている。参照文献リスト（L704–711）にも BigQuery 側の文献は nested ガイド 1 本しか無い。

**修正案**: 参照文献に 1 行足す。

```html
<li>Google Cloud, BigQuery 再帰 CTE（<code>WITH RECURSIVE</code>）— <a href="https://cloud.google.com/bigquery/docs/recursive-ctes">cloud.google.com</a>（自己参照 1 回・<code>UNION ALL</code>・反復上限 500）</li>
```

`p.meta` の「再解釈」は BQ nested のままでよい（再帰 CTE は再解釈ではなく実装の仕様確認）。

---

## 4. 総合判定

**REVISE**

- 初回指摘 **13 件すべて ADDRESSED**。報告の記述と HTML の実物が一致しており、水増しは無かった。特に C-2 は「キー生成関数を変える」で済ませず、入力ソースを `snap_companies` / `snap_agents` に差し替えて `valid_from` を実際に流し、直後に「なぜ版が要るか」の段落まで足しており、03回の結論との接続が取れている。I-3 / I-4 は結論を変えずに理由だけ差し替えるという指示どおりの直し方。
- 差し戻す理由は **N-1 の 1 件のみ**。m-5（Minor）の修正が、05回の `dim_member` 構築（同値の連続版を畳む・キーの入力は `min(valid_from)`）と食い違う SQL を新たに書き込んでしまった。コメントが「05回の変換まで済んだ行／一切変えない」と主張している分、読者が 05回と突き合わせたときの矛盾が目立つ。修正は CTE 1 つぶん、キー生成式を落として参照に留めるだけで済む。
- n-2（図のラベル）と n-3（`references.md` の追随）は Minor。N-1 と同じラウンドで片付けられる。
- `check_svg.py` は **0 errors, 0 warnings**。正典突合（テーブル名・列名・ID）、URL 突合、`<pre>` のエスケープ、節構成、`<title>`、`.table-wrap` はいずれも問題なし。
