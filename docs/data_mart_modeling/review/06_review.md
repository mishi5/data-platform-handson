# 06 多対多・不揃い階層・異種ディメンション — レビュー

対象: `docs/data_mart_modeling/html/06_bridges.html`（673 行）／ブリーフ `briefs/06.md`／報告 `reports/06_report.md`
正典: `canon/domain.md`（`S003` 追加後の版）、`canon/style.md`、`canon/references.md`（06 = DWT ch.7, 8, 10; DT#142 / BQ nested）
判定: **REVISE**（critical=2 / important=4 / minor=7）

前提（オーケストレータ裁定済み。指摘対象にしない）:
- `S003`（`AG02`→`M002`, `J001`, 2026-06-18 送信、未開封）は正典 §5 に採用済み
- `br_member_desired_job_category` の「`dim_member` の全 SCD2 版に展開」は正典に明記済み
- supertype/subtype の章は **DWT ch.10** と訂正済み（ブリーフ・references.md とも更新済み）
- `br_review_tag` は正典に入れない（演習内の将来提案のままでよい）
- `snap_members` は命名規約の具体化として可

---

## 1. ブリーフ準拠表

| 節 | 必須項目 | 判定 | 該当箇所 |
|---|---|---|---|
| §1 | 3 つの問題と手段の表（多値 / 不揃い階層 / 異種） | ✅ | L50–59。4 行（階層を企業グループと職種に分割）。「手段 A / 手段 B / この回の決定」の 3 列が全行に揃う |
| §1 | 多値 → ブリッジ + `weighting_factor` / `ARRAY` | ✅ | L54 |
| §1 | 不揃い階層（企業グループ、職種）→ 階層ブリッジ / 固定深さ平坦化 | ✅ | L55–56 |
| §1 | 異種 → supertype / 2 本の FK + `-1` | ✅ | L57 |
| §2(a) | 重みなしで `M002`（希望 2 件）のスカウトが 2 倍 | ⚠️ | L66–83。論理・検算とも正しいが、正典の `S003` を使わず「10 件」という架空の件数だけで書いている（**Important-1**） |
| §2(b) | `level3` 固定で `ENG-DATA`（level2 終端）が NULL で落ちる | ✅ | L85–95。`GROUP BY` / `WHERE` / BI フィルタの 3 通りの壊れ方 + `J001` の消失。DT#43 と `leaf_level` への接続あり |
| §2(c) | 2 本の FK でどちらかが常に `-1`、BI で「送信主体別」が UNION | ✅ | L97–105。`S001`/`S002` の割当も正典どおり。`COUNT(DISTINCT sender_agent_key)` が +1 になる指摘は加点 |
| §3 | ブリッジの重み（合計 = 1） | ✅ | L112（技法表）。ただし出典が「金融サービスの章」止まりで章番号が無い（**Critical-1** に含む） |
| §3 | impact report / weighted report の使い分け | ✅ | L113。「両方作る・同じ画面に混ぜない」まで書けている |
| §3 | 階層ブリッジ（祖先-子孫 + `depth`） | ✅ | L117。Techniques PDF の原文と照合済み（"a row for every possible path"）。使う条件 4 つ（不定深さ・代替階層・共有所有・時間変化）も原文どおり |
| §3 | supertype/subtype（共通属性を supertype、固有を subtype 表） | ✅ | L119 + L128 の引用。引用は Techniques PDF と**逐語一致**（`pdftotext` で全文突合） |
| §4 | `desired_job_categories ARRAY<STRUCT<code, priority, weight>>` の選択肢 | ✅ | L54 / L156–178（図）/ L515–533 |
| §4 | `UNNEST` のコスト | ✅ | L238（「同一テーブル内の展開でシャッフルが起きない」） |
| §4 | BI（Looker Studio / Looker）からの見え方 | ⚠️ | L241 / L550 / L559。主張は妥当だが一次情報が無いまま断定している（**Important-2**） |
| §4 | Google の公式ガイドの位置づけ | ✅ | L221–232。3 引用すべて原文と一致（WebFetch で確認）。「star schema は既に最適化済みなので更なる非正規化の得は小さい」→「性能は選択理由にならない」への接続が正しい |
| §5(a) | `weighting_factor = 1 / COUNT(*) OVER (PARTITION BY member_id)` | ✅ | L293。`SAFE_DIVIDE(1.0, …)` は等価かつ 0 除算に安全。BigQuery で分析関数をスカラー関数の引数に置くのは有効 |
| §5(a) | weighted report の SQL | ✅ | L322–334。impact と weighted を 1 クエリで並べる形。`sent_date`（DATE 列）での期間絞り込みも正典どおり |
| §5(b) | `br_company_hierarchy` を `WITH RECURSIVE` で（`C001`→`C003` depth 1、自己 depth 0） | ✅ | L343–411。`WITH RECURSIVE` の位置・`UNION ALL`・自己参照 1 回・非再帰 CTE の同居はすべて BigQuery 仕様に適合（公式ドキュメントで確認）。depth 0 の自己行あり |
| §5(b) | 「`C001` グループのクチコミ数」の結合 | ✅ | L414–425。木構造なので `C001` 自身 + `C003` が各 1 回。共有所有で崩れる旨の但し書きも正しい |
| §5(c) | `dim_scout_sender` の生成（`companies` × `agents` の UNION、`sender_type` + 固有属性 NULL 許容） | ⚠️ | L431–479。UNION の列数（5）・順序・型はすべて整合。ただしサロゲートキーが版を含まず SCD2 が成立しない（**Critical-2**） |
| §5(d) | `ARRAY` 版 `dim_member` と `UNNEST` クエリ | ⚠️ | L484–548。`ARRAY_AGG(STRUCT(...) ORDER BY priority)`・型付き空配列リテラル・`CROSS JOIN UNNEST` はすべて BigQuery で有効。`member_key` の生成が抜けている（**Minor-5**） |
| §6 | 多値: 個数の分布 × BI の `UNNEST` 可否 × 更新頻度 | ✅ | L556–568（5 行） |
| §6 | 階層: 深さの分布 × 問いの形 | ⚠️ | L571–583（6 行）。共有所有の行の理由が §5(b) と矛盾（**Important-4**） |
| §6 | 異種: 共通属性の割合 | ✅ | L586–595（4 行）。「2 本の FK は採らない」を明示行にしているのは加点 |
| §7(a) | `reviews` にタグが付いたら `fct_review` にどう持つか | ⚠️ | L601–620。表名を出さず「正典に追加が要る」に留めたのは裁定どおり。重みを持つ理由の説明が誤り（**Important-3**） |
| §7(b) | `C003` 離脱時の `br_company_hierarchy`（SCD の観点） | ✅ | L622–645。「階層が Type 1 として振る舞う」→ 時間可変ブリッジ / 全件再生成 / 両方の 3 択表。§5(b) の実装の性質を正直に自己批判している |
| §7(c) | `dim_agent` の `-1` 行か `dim_scout_sender` 統一か | ✅ | L647–658。ブリーフの「`-1`（直接応募）」を正典（`fct_placement` は「1 行 = 1 入社（エージェント経由）」）に合わせて「担当者を特定できない」と読み替えたのは**正しい訂正**。`dim_agency` を主軸にする補足も正典に整合 |
| 図 | 比較図（左=ブリッジ 3 ノード / 右=`dim_member` に ARRAY 内包）、差分だけ accent、ノード ≤9 | ⚠️ | `#dg-brv`。`check_svg.py` **0 errors, 0 warnings**（再実行で確認）。ノード 7、斜めコネクタゼロ、`M002`・weight 0.5・`priority` まで入っている。ゾーンラベルの accent が右だけ非対称（**Minor-6**） |
| HTML | `<title>` 形式 / `p.meta` / 8 節 / `&lt;` エスケープ / `.table-wrap` | ⚠️ | `<title>` はブリーフ指定と一致。h2 は 1〜8 + 参照文献。`<pre>` 内の生 `<` はゼロ（機械チェック）。表 9 本すべて `.table-wrap`。`p.meta` の章番号が誤り（**Critical-1**） |
| 正典 | 本文のテーブル名・列名・ID がすべて `domain.md` にある | ✅ | `<code>` の全トークンを機械抽出して突合。逸脱ゼロ。`stg_careervoice__*` / `br_*` / `snap_members` は命名規約どおり |
| 参照 | URL はすべて `references.md` にあるもの | ✅ | 6 本すべて一致（機械チェック） |
| 文体 | 1 段落 3 文まで / 緩衝語なし / 一般論で終わらない | ⚠️ | 緩衝語ゼロ。一般論で終わる節ゼロ。ただし 4 文以上の段落が 43 中 20（**Minor-1**） |

---

## 2. 指摘一覧

### Critical

#### C-1. `p.meta` と参照文献の DWT 章番号が誤り（`ch.6–8` → `ch.7, 8, 10`）

`references.md` の割当は **06 = DWT ch.7, 8, 10**、ブリーフも「ch.7（不揃い階層）, ch.8（多値・ブリッジ）, ch.10（heterogeneous products = supertype/subtype）」と明記している。HTML は L44（`p.meta`）と L664（参照文献）で **`ch.6–8`** と書いており、

1. ch.6（Order Management）はこの回の 3 技法のいずれとも関係が無い
2. supertype/subtype と、重み付け係数・impact/weighted の出典である **ch.10（Financial Services）が落ちている**

報告 §3-7 は「ブリーフの `ch.6` は 3rd ed. の章割と合っていない可能性がある／正典側で確認されたい」と正しく疑義を挙げているが、その裁定（ch.10 が正）はブリーフ・references.md に反映済みなので、HTML 側を追従させる。

なお本文 L132 の aside は重み付けの出典を「DWT の口座-顧客ブリッジ（**金融サービスの章**）」と書いており、章番号を伏せたまま ch.10 を指している。ここも番号を出せば `p.meta` と本文が噛み合う。

**修正案**:

L44:
```html
<p class="meta">データマート設計 06 ／ 参照: DWT ch.7 ch.8 ch.10, Design Tip #142, Kimball Dimensional Modeling Techniques ／ 再解釈: BigQuery ネスト・繰り返し列</p>
```

L664:
```html
<li><em>The Data Warehouse Toolkit, 3rd ed.</em> (Kimball &amp; Ross, 2013) ch.7（不揃い階層）, ch.8（多値ディメンションとブリッジ）, ch.10（heterogeneous products と口座-顧客ブリッジの weighting factor） — <a href="…">kimballgroup.com</a></li>
```

L132 の末尾:

> 重み付け係数と impact / weighted の対比は DWT **ch.10（Financial Services）**の口座-顧客ブリッジ側の議論。

#### C-2. `dim_scout_sender` のサロゲートキーに版が入っておらず、SCD2 が成立しない

L473:

```sql
{{ dbt_utils.generate_surrogate_key(['sender_type', 'sender_id']) }} AS scout_sender_key,
```

正典（`domain.md` §4 ディメンション表）は `dim_scout_sender` を **SCD 2** と定めており、直後の L481 も「`valid_from` / `valid_to` / `is_current` の付与（正典では `dim_scout_sender` は SCD2）は 05回の方式に従う」と書いている。ところがキーの入力が自然キー（`sender_type`, `sender_id`）だけなので、**同じ送信主体の全版が同一の `scout_sender_key` を持つ**。結果は

- `dim_scout_sender` の `scout_sender_key` が一意にならない（`unique` テストが落ちる）
- `fct_scout` を結合すると 1 スカウトが版の数だけ増殖する（この回が §2(a) で戒めているのと同じ二重計上が、supertype 側で起きる）

さらに 03回（`03_dimensions.html` L189）は「**ハッシュがサロゲートキーになるのは、ハッシュの入力に版を識別する要素（`valid_from`）が入るときだけ**——これがこの回の中心的な結論である」と書き、L375 の表で `dim_scout_sender` を名指しで「SCD2 → `FARM_FINGERPRINT(自然キー + '|' + valid_from)`」に割り当てている。05回（`05_scd.html` L348）も `generate_surrogate_key(['v.company_id', 'v.valid_from'])` と版を含めている。06 だけが版を落としており、シリーズ内で矛盾する。

報告 §4 は「踏み込みは最小 1 行に留めた」としているが、問題は関数の選択ではなく**入力に版が無いこと**なので、1 行の書き換えで解消する。

**修正案**（L471–479 のうちキー生成行）:

```sql
SELECT
    -- SCD2 なので版を識別する valid_from をハッシュ入力に入れる（03回の結論）。
    -- 生成方式（FARM_FINGERPRINT / generate_surrogate_key）は 03回の判断に従う
    FARM_FINGERPRINT(CONCAT(sender_type, '|', sender_id, '|', CAST(valid_from AS STRING))) AS scout_sender_key,
    sender_type,
    …
```

`unioned` に `valid_from` がまだ無いなら、L481 の「`valid_from`/`valid_to`/`is_current` の付与は 05回の方式に従う」を SQL の外の注記のままにせず、`unioned` の後段に 05回の as-of 版展開が入る前提であることを 1 文足す。最小の代替案として、キー生成行をこの SQL から外し「版付きのキー生成は 05回の形に従う」と注記だけにしてもよい（この回の主題は supertype の UNION なので、キーを出さなくてもブリーフの必須内容は満たす）。

---

### Important

#### I-1. §2(a) が正典の `S003` を使わず「10 件」という架空の件数で書かれている

L68:

> 2026-06 に `M002` 宛のスカウトが 10 件送られたとする（`fct_scout` に 10 行）。

執筆時点では `M002` 宛のスカウトが正典に無く、報告 §3-1 でその追加を提案していた。提案は採用され、正典 §5 に **`S003` = `AG02`(agent) → `M002`、`J001`、2026-06-18 送信、未開封** が入った。style.md の「一般論で終わらせない。必ず題材の具体テーブル・具体 ID で語る」に照らして、件数だけの仮定を具体 ID に置き換える。`S003` は 6/18 送信なので §5(a) の `WHERE f.sent_date BETWEEN DATE '2026-06-01' AND DATE '2026-06-30'` の窓にそのまま入る。

**修正案**（L68 と L81）:

L68:
```html
<p>正典の <code>S003</code>（<code>AG02</code> → <code>M002</code>、<code>J001</code>、2026-06-18 送信）は <code>fct_scout</code> の 1 行である。<code>M002</code> の希望職種は <code>ENG-BE</code> と <code>ENG-DATA</code> の 2 件なので、<code>br_member_desired_job_category</code> には <code>M002</code> の行が 2 本ある。この 1 行にブリッジを重みなしで結合すると 2 行になる。</p>
```

L70–79 の表は「1 件」を単位に読み替える（`SUM(scout_count)` = 1 / ブリッジ結合 = **2** / 重み付き = 1）。そのうえで L81 を、規模の話へ橋渡しする段落に分ける:

```html
<p>職種別に割ると、重み付きは <code>ENG-BE</code> 0.5 / <code>ENG-DATA</code> 0.5 で合計 1。重みなしは 1 / 1 で合計 2。</p>
<p>壊れるのは数字そのものではなく、<strong>「明細を足すと総数になる」という読み手の前提</strong>である。<code>S003</code> と同型のスカウトが 6 月に 1,240 件あれば、上段の「6 月のスカウト送信数 1,240 件」に対して下段の職種別内訳の合計が 1,240 を超える。</p>
```

（併せて、L150 の図の導入文と SVG の `member_key = M002` に `S003` を添えると §2 →§4 の視線が繋がる。SVG 側は `fct_scout` ボックスの `sub` を `S003 / member_key = M002` にするだけで済み、`check_svg.py` にも影響しない。必須ではない。）

#### I-2. BI ツールの繰り返しフィールドの挙動を、一次情報無しに断定している（3 箇所）

該当:

1. L241「繰り返しフィールドは**多くの BI ツールがディメンションとして直接扱えない**。カスタムクエリで `UNNEST` して平坦化するか、モデリング層（LookML 等）で展開済みビューを定義する**必要がある**」
2. L550「この `UNNEST` を BI ツールのセルフサービス画面から**書かせることはできない**」
3. L559「セルフサービス BI が直結する（`UNNEST` 不可）」

`references.md` の 06 の割当は BQ nested（Google Cloud）だけで、BI 製品側の一次情報は正典に無い。報告 §5 も「WebFetch していない」「正典に BI 側の文献を 1 本足すか、この記述を削るかの判断を仰ぎたい」と自己申告している。この主張は §4 の結論（「性能は決め手にならない。決め手は BI からの見え方」）と §6 の第 1 表の 1 行目を支える**中心的な根拠**なので、断定のまま残すと記事の結論が無出典の前提の上に立つ。

**修正案**（出典を足せない前提での書き換え。断定を条件文に変える）:

L241 の第 3 列:
```html
繰り返しフィールドを「ディメンションとして直接選べるか」は BI ツールごとに違う。直接選べないツールでは、カスタムクエリで <code>UNNEST</code> して平坦化するか、モデリング層（LookML 等）で展開済みビューを先に定義することになる
```

L550 の 3 点目:
```html
<strong>3.</strong> この <code>UNNEST</code> を誰が書くかが変わる。BI のセルフサービス画面が繰り返しフィールドを直接扱えないなら、カスタムクエリかモデリング層のどちらかで、誰かが先に平坦化しておく必要がある。
```

L559 の第 2 列:
```html
セルフサービス BI が直結する（<code>UNNEST</code> を書かせられない）
```

そのうえで報告に「BI 側の一次情報（Looker Studio の BigQuery コネクタ仕様 / LookML の `UNNEST` 展開）を `references.md` に追加したい」と変更提案を 1 件足す。追加が通れば L241 を断定に戻してよい。

#### I-3. §7(a) の「重みを持つ理由」が誤り（タグ別の平均では多タグのクチコミは平均を強く引っ張らない）

L615:

> ただし `weighting_factor` の列自体は作っておく。「タグ別の平均 `overall_score`」を出す時に、重みなしだとタグを多く付けたクチコミが平均を強く引っ張るため。

**タグ別**の平均は、タグごとのグループ内で 1 クチコミが 1 観測として現れる。3 タグ付いたクチコミも「残業少なめ」グループには 1 回しか現れないので、そのグループの平均を余分に引っ張ることはない。むしろここで `weighting_factor`（= 1/タグ数）を掛けると、多タグのクチコミだけを不当に軽くした加重平均になり、答えが変わる。

重みが要るのは**タグをまたいで足す/均す**とき、すなわち (i) 全タグの件数を合計して総クチコミ数と一致させたいとき、(ii) タグ展開後の全行をプールして 1 つの平均を出すとき（3 タグのクチコミが 3 回入る）である。

**修正案**（L615 の第 3・4 文を差し替え）:

```html
<p><strong>重みは持つが、既定の見せ方は impact。</strong>「残業少なめのタグが付いたクチコミは何件か」が主な問いで、合計が総クチコミ数と一致する必要はない。</p>
<p>ただし <code>weighting_factor</code> の列自体は作っておく。タグ別の件数を<strong>合計して総クチコミ数と突き合わせる</strong>ときと、タグ展開後の全行をプールして 1 本の平均を出すときに、重みが無いと 3 タグのクチコミが 3 回数えられるため。タグ 1 つの中での平均には重みを掛けない（掛けると多タグのクチコミだけが不当に軽くなる）。</p>
```

#### I-4. §6 の「共有所有は再帰 CTE でも表現できない」が §5(b) の実装と矛盾し、原典の主張の範囲も超えている

L577:

> 共有所有（1 社が複数の親を持つ）｜任意｜**ブリッジ一択**｜**再帰 CTE でも pathstring でも表現できない**。加えて重み付けが要る

Techniques PDF の原文は "With SQL extensions, alternative ragged hierarchies cannot be substituted at query time, shared ownership structures are not supported, and time varying ragged hierarchies are not supported." であり、否定されているのは **クエリ時に SQL 拡張（`CONNECT BY` 等）だけで階層を辿ること**。一方この記事の §5(b) は再帰 CTE を **ブリッジを生成する ETL の手段**として使っており、`parent_company_id` が多値になっても同じ再帰 CTE は全経路を列挙できる（それが「あり得る全経路に 1 行」そのものである）。つまり「再帰 CTE でも表現できない」は原典の射程を広げた誤りで、記事の自分の SQL とも噛み合わない。

結論（ブリッジ一択）は正しいので、理由だけを直す。

**修正案**（L577 の第 4 列）:

```html
クエリ時に親子表を辿るだけでは解けず（pathstring も同じ）、あり得る全経路を持つ表が要る。再帰 CTE は §5(b) と同じくその<strong>生成手段</strong>としては使える。加えて経路が複数になるので重み付けが要る
```

（§5(b) 直後の L427「共有所有（1 社が 2 つの親を持つ）を許した瞬間にこれは崩れ、多値ブリッジと同じ重み付けが必要になる」は正しいので、そちらは触らない。）

---

### Minor

#### m-1. 4 文以上の段落が 43 中 20（style.md「1 段落は 3 文まで」）

機械チェック（`。` で分割）。最長は L550 の 8 文、次いで L132 の aside 7 文、L303 の aside と L657 が 6 文。地の文で 4 文超のもの（L46, L61, L81, L120, L150, L232, L322, L412, L550, L615, L624, L628, L648, L650, L654, L657, L667, L670）を優先して割る。特に L550 は「差は 3 点ある」の直後に 3 点を 1 段落へ詰め込んでいるので、`<ol>` にするのが素直。

#### m-2. Techniques PDF の引用が原文の途中で切れているのに「.」で閉じている

L126:

> “All these objections can be overcome … This bridge table contains a row for every possible path in the ragged hierarchy.”

原文は `…in the ragged hierarchy and enables all forms of hierarchy traversal to be accomplished with standard SQL rather than using special language extensions.` と続く。**修正案**: `…for every possible path in the ragged hierarchy…”` と省略記号で閉じるか、`…and enables all forms of hierarchy traversal to be accomplished with standard SQL` まで引く（後者は「標準 SQL で辿れる」という、この回の §5(b) の動機そのものなので引く価値がある）。他の 3 引用（supertype、multivalued、time-varying）は `pdftotext` での全文突合で**逐語一致**を確認済み。

#### m-3. §5(a) のブリッジに「グループディメンションキー」が無いことの説明が抜けている

L111 の技法表と L130 の引用は「ファクトからディメンションへ、**グループキー経由で**ブリッジを挟む」と Kimball の定義を書いているのに、§5(a) の実装（L281–307）は `member_key` で直接結んでおり、グループキーが登場しない。正典の PK が (`member_key`, `job_category_key`) なのでこれで正しいが、読者は定義との差に引っかかる。L307 直後（aside の前）に 1 文:

> ここでは `member_key` がグループキーを兼ねる。会員ごとに希望職種のグループが 1 つしかないので、DT#142 の「組合せを重複排除してグループを作る」段は利得を生まない。

#### m-4. BigQuery `WITH RECURSIVE` の仕様（反復上限 500 など）に出典が無い

L412 の記述（自己参照ちょうど 1 回 / `UNION ALL` / 再帰項に集計・分析関数・`LIMIT` 不可 / 反復上限 500）は公式ドキュメントと照合して**すべて正しい**（`https://docs.cloud.google.com/bigquery/docs/recursive-ctes` で確認: "For BigQuery, the iteration limit is 500 iterations."）。ただし `references.md` に BigQuery のクエリ構文ドキュメントが無いため、本文に URL を出せない状態になっている。報告 §2 は「URL は正典に無いので引用リンクは張っていない」と書いているが、§3「正典への変更提案」には挙げていない。**修正案**: 報告の変更提案に「`references.md` に BigQuery `Work with recursive CTEs` を追加したい」を 1 件足す。本文は現状のままでよい。

なお「反復上限が実質的な循環参照検出になる」はドキュメントが明示している事実ではなく推論（循環があれば新しい行が出続けて 500 に達しエラー）なので、「循環があれば 500 回に達してエラーで止まる。無限ループにはならない」という書き方に寄せると安全。

#### m-5. §5(d) の ARRAY 版 `dim_member` が `member_key` を作っていないのに、直後のクエリが `m.member_key` で結合している

L516–520 は `member_versions AS (SELECT * FROM {{ ref('snap_members') }})` で、L522 の `SELECT m.*` にそのまま流している。`snap_members` は dbt snapshot なので出てくるのは `dbt_valid_from` / `dbt_valid_to` であり、`member_key` は 05回の変換を経て初めて生まれる。一方 L541 のクエリは `ON f.member_key = m.member_key`。**修正案**: L518 のコメントを「`dim_member` の既存本体（05回の SCD2 変換後。`member_key` / `valid_from` / `valid_to` はそこで付く）」に直すか、CTE 名を `member_versions` のまま `{{ ref('dim_member') }}` の本体 SQL を指す旨の注記にする。

併せて L525 のコメント「NULL 配列を読み戻すと空配列になる**ので**、型付き空配列で明示的に揃える」は因果が逆向き。読み戻すと空になるなら `IFNULL` は不要で、実際の理由は「クエリ内では NULL 配列と空配列が別値なので、下流で取り違えないよう揃える」。1 語直すだけで済む。

#### m-6. 図のゾーンラベルの accent が右側だけ非対称

L194 は `class="tag"`（BRIDGE）、L198 は `class="tag-accent"`（ARRAY IN DIM）。ブリーフの指定は「差分（ブリッジ表の存在 / ARRAY 内包）だけ accent」、報告 §4 も「両パネルの差分ノードに accent」と書いており、実際に差分ノード（`br_member_desired_job_category` と `dim_member`）は両方 `box-focal` で揃っている。ラベルだけ右が強調されていると「右が新方式／推奨」に読める。この回の結論はブリッジ採用なので誤読の向きが逆になる。**修正案**: L198 を `class="tag"` に揃える（`tag-accent` クラス定義は残しても未使用で問題ない）。修正後に `check_svg.py` を再実行（現状は 0 errors, 0 warnings）。

#### m-7. §6 の多値表で 3 行目と 4 行目の切り分けが弱い

L565（数十〜数百・更新頻度「高」→ 別ファクト表）と L568（個数が可変で頻繁に変わる・「高」→ ブリッジ）は、読者から見ると「更新頻度が高い」で同じ条件に見える。3 行目の決め手はカーディナリティなので、更新頻度の欄を「問わない」にするか、理由列に「個数ではなくカーディナリティで落ちる」と書くと表として切れる。

---

## 3. 検算・静的検証の記録

| 検証項目 | 結果 |
|---|---|
| `weighting_factor = 1/2`、10 件 × 2 職種 | 重み付き 5 / 5 = 10、重みなし 10 / 10 = 20。本文の表・地の文とも一致 ✅（ただし I-1） |
| `SAFE_DIVIDE(1.0, COUNT(*) OVER (PARTITION BY member_id))` | BigQuery で有効（分析関数をスカラー関数の引数に置ける）。0 除算も安全 ✅ |
| ブリッジを全 SCD2 版に展開した場合の weighted report | `fct_scout.member_key`（送信時点の版）↔ ブリッジの `member_key` が 1 対 N（N = 希望数）で、重み合計 1。総送信数と一致 ✅ |
| `unique_combination_of_columns: [member_key, job_category_key]` | 版ごとに希望職種が 1 回ずつなので一意 ✅ |
| `HAVING ABS(total_weight - 1.0) > 1e-9` | BigQuery は `HAVING` で SELECT 別名を参照できる ✅ |
| `dbt_utils.accepted_range` の引数名（`min_value`/`max_value`） | 正しい ✅ |
| `WITH RECURSIVE` のキーワード位置 | `WITH RECURSIVE` は WITH 句全体に掛かる。非再帰 CTE（`base`, `flags`）の同居も可 ✅ |
| 再帰項の形 | `paths` を 1 回だけ参照、`UNION ALL` で基底項と接続、集計・分析関数・`LIMIT` 無し、再帰参照が INNER JOIN の左側 ✅ |
| 終了条件 | 新しい行が出なくなれば停止。循環時は 500 反復でエラー ✅（公式ドキュメントで確認） |
| `flags` の相関サブクエリ `NOT EXISTS (…)` を SELECT リストに置く | BigQuery で有効 ✅ |
| `br_company_hierarchy` の depth 0 自己行 | `SELECT company_id AS ancestor…, company_id AS descendant…, 0 AS depth FROM base` で全社ぶん生成 ✅ |
| 「`C001` グループのクチコミ数」の重複 | 祖先を `is_current` に絞り、木構造なので子孫→祖先の経路は 1 本。`C001` 自身 + `C003` が各 1 回 ✅ |
| `dim_scout_sender` の UNION の列数・順序・型 | 5 列 × 2 ブランチ。`sender_type`/`sender_id`/`sender_name`/`company_industry`/`agency_tier` がすべて STRING で一致。無い側は `CAST(NULL AS STRING)` ✅ |
| 参照している列がソースに実在するか | `companies.name`, `industries.name`, `agents.name`, `agents.agency_id`, `agencies.tier` すべて `domain.md` §2 にある ✅ |
| `ARRAY_AGG(STRUCT(job_category_code AS code, priority, weight) ORDER BY priority)` | 有効。STRUCT のフィールド名が宣言型 `ARRAY<STRUCT<code STRING, priority INT64, weight FLOAT64>>` と一致 ✅ |
| `ARRAY<STRUCT<…>>[]` の型付き空配列リテラル | BigQuery で有効 ✅ |
| `CROSS JOIN UNNEST(m.desired_job_categories) AS d` と空配列の挙動 | 空配列の行は落ちる。`LEFT JOIN UNNEST` で残る。本文の記述どおり ✅ |
| Techniques PDF の引用 4 本 | `pdftotext` で全文抽出して突合。supertype / multivalued / time-varying は**逐語一致**。ragged の 1 本のみ文中で切れている（m-2） |
| DT#142 の要約（静的/時間可変、グループ化の手順、重み付けに触れていない） | WebFetch で確認。著者 Warren Thornthwaite、"There is no time variance in this bridge table because it captures the set of values that were in effect when the transaction occurred."、"The second kind of many-to-many relationship exists independent of the transactions being measured."、グループの重複排除＋一意キー付与の記述あり、重み付け・impact report・階層ブリッジへの言及なし。**本文の要約はすべて正しい** ✅ |
| BQ nested ガイドの引用 3 本 | WebFetch で確認。"Denormalization localizes the data to individual slots, so that execution can be done in parallel."、"Increases in storage costs are worth the performance gains of using denormalized data."、"star schemas are typically optimized schemas for analytics, and as a result, performance might not be significantly different if you attempt to denormalize further."、"(so long as the relationship isn't high cardinality)" すべて一致 ✅ |
| §8 の `get_favorite_tag_counts` の記述 | `news_pipeline/collector/bq_client.py` L371–382 を確認。`, UNNEST(s.tags) AS tag` + `COUNT(DISTINCT f.article_id)` で impact report。本文の指摘は正確 ✅ |
| `check_svg.py` | **0 errors, 0 warnings**（再実行） |
| `<pre>` 内の生 `<` | ゼロ（機械チェック、9 ブロック） |
| 本文の全 URL（6 本） | すべて `references.md` に存在（機械チェック） |
| 本文の全 `<code>` トークン | `domain.md` に無いテーブル名・列名・ID はゼロ（機械チェック） |

---

## 4. 総合判定

**REVISE**（critical=2 / important=4 / minor=7）

内容の質は高い。特に、(1) Techniques PDF と DT#142 を実際に読み、DT#142 が重み付けに触れていないことまで把握して出典を切り分けている点、(2) §5(b) の実装が「階層を Type 1 として扱っている」ことを演習(b)で自己批判している点、(3) ブリーフの「`-1`（直接応募）」を正典に照らして訂正した §7(c)、(4) §5(d) の ARRAY 対案が (a) と同じ問いに同じ答えを返す形で書かれている点は、いずれもこのシリーズの水準を満たしている。SQL は全 9 ブロックが BigQuery で構文的に通り、論理も（C-2 を除いて）正しい。

差し戻す理由は 2 点に集約される。章番号（C-1）は正典・ブリーフとの単純な不整合で、修正は 3 行。サロゲートキー（C-2）は 03回の中心的な結論との矛盾で、放置すると `dim_scout_sender` の一意性が崩れ、この回自身が §2(a) で戒めている二重計上を supertype 側で再現する。Important 4 件のうち I-1（`S003`）と I-2（BI の断定）は執筆者が報告で自ら挙げていた未決事項で、裁定は済んでいる。I-3 と I-4 は本文の論理そのものの誤りなので、結論を変えずに理由だけ差し替える。
