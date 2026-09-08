# 06 多対多・不揃い階層・異種ディメンション — 執筆報告

- 出力: `docs/data_mart_modeling/html/06_bridges.html`
- 図: 1枚（比較図「ブリッジ vs ARRAY」、`#dg-brv`）
- `check_svg.py`: **0 errors, 0 warnings**

## 1. 完了した節

| 節 | 内容 | ブリーフ必須項目の充足 |
|---|---|---|
| 1 | 3つの問題と手段の表（多値 / 不揃い階層×2 / 異種）+ 「崩すコストをどこに払わせるか」の軸 | ✓ 4行の判断表（職種の階層を企業グループと分けて2行にした） |
| 2 | (a) 重みなし結合で `M002` のスカウトが 2倍 (b) `level3_name` NULL で `ENG-DATA`/`J001` が落ちる (c) 2本の FK で「送信主体別」が UNION | ✓ |
| 3 | 技法表 9行（多値ブリッジ / 重み / impact・weighted / 時間可変ブリッジ / 固定深さ / slightly ragged / 階層ブリッジ / pathstring / supertype-subtype）+ 原典引用 aside 2枚 + 題材への当てはめ | ✓ |
| 4 | BQ nested ガイドの要点、比較図、「何が変わり何が残るか」表 5行（結合コスト / 重み / グループキー / BI からの見え方 / 更新） | ✓ |
| 5 | (a) ブリッジ生成 + weighted report + `schema.yml` + 合計1の singular test (b) `WITH RECURSIVE` の階層ブリッジ + 「C001 グループのクチコミ数」 (c) `dim_scout_sender` の UNION (d) ARRAY 版 `dim_member` + `UNNEST` クエリ | ✓ |
| 6 | 判断基準 3表（多値 5行 / 階層 6行 / 異種 4行） | ✓ |
| 7 | (a) クチコミのタグ (b) `C003` の離脱と SCD (c) `fct_placement.agent_key = -1` — 各 `<details>` に解答例 | ✓ |
| 8 | `news_pipeline` の `summaries.tags`（REPEATED）＝ ARRAY 選択、`get_favorite_tag_counts` が impact report である指摘、`dbt_logs_analysis` の `url_path` を階層ブリッジにするチュートリアルの種 | ✓ |
| 参照文献 | 6件 | ✓ |

## 2. 読んだ文献と引用した要点

### Design Tip #142「Building Bridges」（Warren Thornthwaite）— WebFetch 済み
- ブリッジを **静的**（1ファクト行に紐づく値の集合が時間変化しない。救急外来の受診時診断）と **時間可変**（関係が測定対象のトランザクションと独立に存在し時間で変わる。顧客と口座）に分ける。
- 作り方は「値の組合せを重複排除して**グループ**を作る → グループに一意キーを振る → 行方向に展開する」。
- **この Design Tip は重み付け係数・impact/weighted・階層ブリッジには一切触れていない**（記事自身が「静的ブリッジの手順だけを扱う」と明記）。本文でもその旨を書き、重み付けの出典は DWT の口座-顧客ブリッジ側に振った。

### Kimball Dimensional Modeling Techniques（PDF, 2013）— pdftotext で全文抽出して該当節を読了
本文の `aside kimball` に原文引用。使った節:
- *Ragged/Variable Depth Hierarchies*: SQL の再帰拡張では「代替階層の差し替え・共有所有・時間変化」が扱えず、その全部がブリッジ表（あり得る全経路に1行）で解ける。
- *Alternative pathstring approach*: 経路を符号化した1列。ただし代替階層の差し替えと共有所有は表現できず、構造変更で全体の付け替えが要る。
- *Slightly Ragged/Variable Depth Hierarchies*: 深さの幅が小さいなら「複雑な機構を使うよりは」最大深さの位置属性に force-fit してよい。→ `dim_job_category` の平坦化の根拠。
- *Multivalued Dimensions and Bridge Tables*: グループディメンションキー経由でブリッジを繋ぐ。両端が Type2 なら有効/失効タイムスタンプが要り、クエリ側が特定時点に制約する。
- *Supertype and Subtype Schemas for Heterogeneous Products*: 共通属性の supertype と種別ごとの subtype（core / custom）。

### Google Cloud「ネストされた繰り返しフィールド」ガイド — WebFetch 済み
- 推奨は低〜中カーディナリティの 1対多で、一緒にクエリされるもの。理由は結合シャッフルの排除（"Denormalization localizes the data to individual slots"）。
- "Increases in storage costs are worth the performance gains of using denormalized data."
- **高カーディナリティの 1対多は避ける**、および **「すでに分析向けに最適化されたスタースキーマは、さらに非正規化してもそれほど得をしない」** と明記。この2点を根拠に、本文では「性能は選択理由にならない／決め手は BI からの見え方と更新頻度」と結論した。

### BigQuery `WITH RECURSIVE` の仕様 — 公式ドキュメントを WebFetch で確認
再帰項は CTE をちょうど1回参照、`UNION ALL` で接続、再帰項に集計/分析関数・`LIMIT` を置かない、反復上限 500。本文に反映（URL は正典に無いので引用リンクは張っていない）。

## 3. 正典への変更提案

1. **`M002` 宛のスカウトのサンプル ID が無い。** §2(a) の二重計上を語るには「希望職種2件の会員が受け取ったスカウト」が要るが、正典のスカウトは `S001`（→`M001`）と `S002`（→`M003`）だけ。本文では ID を作らず「2026-06 に `M002` 宛のスカウトが 10 件」と件数だけを仮定して書いた。**提案: `S003` = `AG02`(agent) → `M002`、`J001`、2026-06-18 送信 を追加**すると、06回の二重計上と、スカウト送信主体の agent 側の例が同じ会員で繋がる。
2. **`br_member_desired_job_category` の `member_key` をどの SCD2 版に張るかが未定義。** 正典は PK を (`member_key`, `job_category_key`) と定めるが、`dim_member` は SCD2 なので「現行版だけ」か「全版」かで、ファクトからの結合の書き方が変わる。本文では **全版に複製**する実装を採った（`fct_scout.member_key` と直結できるため）。理由と代償（「2026-06 時点の希望職種」に答えられない）は本文の aside に明記。**提案: 正典の備考に「`dim_member` の全 SCD2 版に展開する」と1行足す。**
3. **`br_company_hierarchy` の祖先側／子孫側で SCD2 版の扱いが非対称になる。** 本文の実装は祖先＝`is_current` のみ、子孫＝全版。これも正典に明記がないので暫定判断。演習(b) でこの非対称性が「時間変化する階層」の論点そのものになることを扱っている。
4. **`dim_member` の ARRAY 対案の列名。** ブリーフ指定の `desired_job_categories ARRAY<STRUCT<code STRING, priority INT64, weight FLOAT64>>` を本文で使ったが、正典の `dim_member` 属性一覧には無い。**対案（採用しない設計）としてのみ提示**しており、正典の `dim_member` は変更していない。
5. **`snap_members` という名前を1箇所で使った**（§5(d) の ARRAY 版 `dim_member` が参照する SCD2 本体）。正典の命名規約「dbt snapshot `snap_*`」の素直な具体化だが、テーブル名として列挙はされていない。
6. **演習(a) のタグ用ブリッジ表名を本文では出していない。** 「命名規約 `br_*` に従うブリッジを1本置く（表名は正典に追加が要る）」と書くに留めた。**提案: 将来 `br_review_tag` (`review_id`, `tag_key`, `weighting_factor`) と `dim_review_tag` を追加。**
7. **ブリーフの「DWT ch.6（supertype/subtype）」は 3rd ed. の章割と合っていない可能性がある。** 3rd ed. では ch.7 = Accounting（不揃い階層）、ch.8 = CRM（多値ブリッジ）は一致するが、supertype/subtype（heterogeneous products）は ch.10 Financial Services にある。`p.meta` はブリーフ指定どおり「DWT ch.6–8」としたうえで、本文中では supertype/subtype に章番号を振らず Techniques（技法一覧）に帰属させた。**正典側で章番号を確認されたい。**

## 4. 迷った判断とその理由

| 迷い | 決めたこと | 理由 |
|---|---|---|
| 図をどの節に置くか | §4（再解釈）の中、ARRAY ガイドの要点表の直後 | 図の主題が「ブリッジ表 vs ARRAY 内包」で、ARRAY を導入した直後でないと右パネルが読めない。§1 に置くと3つの問題のうち1つだけを図にする理由が説明できない |
| 図の accent をどちらのパネルに置くか | **両パネルの差分ノード**（左＝ブリッジ表、右＝ARRAY を内包した `dim_member`） | ブリーフの指定どおり。accent は「多値をどこに置くか」という1つの意味で1系統に収まる。旧 vs 新ではなく対等な2案なので、片側だけを accent にすると優劣を示唆してしまう |
| §5(c) のサロゲートキー生成 | `dbt_utils.generate_surrogate_key` を使い、「生成方式そのものは 03回の判断に従う」とコメント1行 | 正典は「03回以外は `_key` と書くだけで型に踏み込まない」。ただし `dim_scout_sender` の生成 SQL を出す以上、実行可能な形にするにはキー生成行が要る。踏み込みは最小1行に留めた |
| §5(c) に `-1` 行を入れるか | 入れない | ブリーフの必須内容は「`companies` と `agents` の UNION、`sender_type` + 固有属性は NULL 許容」まで。`-1` は演習(c) の主題なのでそちらに寄せた |
| 演習(c) の前提の扱い | 正典更新後の定義（`fct_placement.agent_key` は `applications.scout_id`→`scouts.sender_agent_id` で解決、無ければ `-1`）に合わせ、`-1` の意味を「直接応募」ではなく**「仲介した担当者を特定できない」**と読み替えて解答した | 執筆中に正典が更新され、`fct_job_posting_daily` が `agent_key` → `agency_key` に、`fct_placement` に `agency_key` と `dim_agency`（縮約ディメンション）が追加された。ブリーフの「`-1`（直接応募）」という但し書きは更新前の正典に基づくものと判断。新しい正典のほうが論点として強い（「`-1` 行を置くこと」と「`-1` が多い軸を主軸にしないこと」が別の判断であることを示せる）ので、そちらに寄せた |
| ブリッジと ARRAY のどちらを正典の第一選択にするか | ブリッジ | Google のガイド自身が「スタースキーマはすでに最適化済みで、さらなる非正規化の恩恵は小さい」と書いており、CareerVoice の規模では性能差が測定誤差。決め手は BI ツールが繰り返しフィールドを直接扱えないこと（セルフサービス性）と、ARRAY が部分更新できないこと |
| 職種の階層をブリッジにするか平坦化するか | 平坦化（正典の決定を踏襲） | Techniques の *Slightly Ragged* の条件（深さの幅が小さい）に正確に当てはまる。深さ 1〜3 で、レベル名が合意されている |

## 5. 未達事項・弱いところ

- **BI ツール側の挙動を一次情報で確認していない。** 「多くの BI ツールが繰り返しフィールドをディメンションとして直接扱えず、カスタムクエリで `UNNEST` するか、モデリング層で展開済みビューを定義する必要がある」と書いたが、正典の references.md に BI 側のドキュメントが無いため WebFetch していない。製品名（Looker Studio / Looker）を特定した断定は避け、一般化した記述にしてある。**正典に BI 側の文献を1本足すか、この記述を削るかの判断を仰ぎたい。**
- **DWT 3rd ed. 本体は WebFetch できない**（書籍）。章番号での参照は `p.meta` のみで、本文の技法定義は全て Techniques PDF（一次情報）に帰属させた。
- **`fct_review` にタグを持たせる演習(a) で、ブリッジの結合キーを `review_id`（退化ディメンション）としている。** 正典の `fct_review` は `review_id` を退化ディメンションとして持つのでこれで結べるが、サロゲートキーを介さない結合は 03回の方針次第で変わりうる。
- **§2(a) の「10件」は仮定値**（上記の変更提案1）。他の数値は全て正典のサンプル値から取っている。

---

## 修正ラウンド 1（レビュー `review/06_review.md` REVISE への対応）

| ID | 対応 |
|---|---|
| C-1 | `p.meta` を `DWT ch.7 ch.8 ch.10` に、参照文献の DWT 行を「ch.7（不揃い階層）/ ch.8（多値ディメンションとブリッジ）/ ch.10（heterogeneous products と口座-顧客ブリッジの weighting factor）」に修正。DT#142 の aside 末尾も「金融サービスの章」→「**DWT ch.10（Financial Services）**」に。本文の `ch.6` は 0 件になった |
| C-2 | §5(c) を版付きに全面改稿。入力を `snap_companies` / `snap_agents` に変え両ブランチに `valid_from` / `valid_to` を持たせ、キーを `FARM_FINGERPRINT(CONCAT(sender_type,'|',sender_id,'|',CAST(valid_from AS STRING)))` に（03回の割当と同形）。`is_current` も出力。直後に段落を1つ足し、「自然キーだけでハッシュすると全版が同一キーになり、`fct_scout` の結合が版の数だけ増殖して §2(a) と同じ二重計上が supertype 側で起きる」と明記。`agency_tier` が現在値である点も注記 |
| I-1 | §2(a) を正典の `S003`（`AG02`→`M002`, `J001`, 2026-06-18 送信）1 件で書き直し。検算表を 1 / **2** / 1 に、職種別を 0.5 / 0.5 に修正。「1,240 件」は規模の話へ橋渡しする別段落に分離。図の `fct_scout` ノード（左右とも）の sub を `S003 / member_key = M002` に、§4 の図の導入文も `S003` 参照に |
| I-2 | BI の断定を 3 箇所とも条件文化。§4 表「直接選べるかは BI ツールごとに違う。直接選べないツールでは…」／§5(d)「BI のセルフサービス画面が繰り返しフィールドを直接扱えないなら…」／§6 表「`UNNEST` を書かせられない」。製品挙動の断定は消し、`LookML 等` は例示のまま残した |
| I-3 | §7(a) の重みの理由を差し替え。「タグ別の平均が引っ張られる」（誤り）→「タグ別の件数を**合計して総クチコミ数と突き合わせる**とき／タグ展開後の全行をプールして 1 本の平均を出すときに要る。タグ 1 つの中での平均には掛けない（掛けると多タグのクチコミだけが不当に軽くなる）」 |
| I-4 | §6 階層表の共有所有行の理由を「再帰 CTE でも pathstring でも表現できない」→「クエリ時に親子表を辿るだけでは解けず（pathstring も同じ）、あり得る全経路を持つ表が要る。再帰 CTE は §5(b) と同じくその**生成手段**としては使える。経路が複数になるので重み付けも要る」に。§5(b) 直後の記述は指摘どおり無修正 |
| m-1 | 5 文以上の段落をゼロにした（`。` 分割の機械チェックで確認）。分割: §3 の当てはめ段落 / §5(a) の aside / §5(d) の「差は 3 点ある」（`<ol>` 化）/ DT#142 の aside / §7(b)(c) の 4 段落。4 文の段落は 12 残るが、いずれも列挙型で分けると論旨が切れるため保持 |
| m-2 | ragged 階層の引用を `…and enables all forms of hierarchy traversal to be accomplished with standard SQL rather than using special language extensions.` まで延長（§5(b) の動機に直結するため後者を採用）。訳の括弧書きも「標準 SQL のまま辿れる」を追加 |
| m-3 | §5(a) のブリッジ SQL 直後に 1 文追加: 「ここでは `member_key` がグループキーを兼ねる。会員ごとに希望職種のグループが 1 つしかないので、DT#142 の『組合せを重複排除してグループを作る』段は利得を生まない」 |
| m-4 | 「この上限が実質的な循環参照検出になる」という推論を、事実ベースの「循環を作ってしまった場合も、新しい行が出続けて 500 反復に達しエラーで落ちる。無限ループにはならない」に書き換え。正典への追加提案は下記 8 に記載 |
| m-5 | `member_versions` を「05回の SCD2 変換（snapshot → 版付きキーの付与）まで済んだ会員行」に直し、`FARM_FINGERPRINT(CONCAT(member_id,'|',CAST(dbt_valid_from AS STRING))) AS member_key` を明示（後続の `ON f.member_key = m.member_key` と噛み合う）。`IFNULL` のコメントの因果を「クエリ内では NULL 配列と空配列は別値なので、下流で取り違えないよう揃える」に修正 |
| m-6 | 図の右ゾーンラベルを `class="tag-accent"` → `class="tag"` に。両パネルのラベルが同格になり、accent は差分ノード（`box-focal` 2 つ）だけになった。`check_svg.py` 再実行で **0 errors, 0 warnings** |
| m-7 | §6 多値表の 3 行目（数十〜数百）の更新頻度を「高」→「問わない」に、理由列を「更新頻度ではなく**カーディナリティ**で落ちる」に。4 行目（更新頻度が高い→ブリッジ）との切り分けが立った |

### 追加の正典への変更提案（このラウンドで新規）

8. **`references.md` に BigQuery の再帰 CTE ドキュメントを追加したい**（`https://docs.cloud.google.com/bigquery/docs/reference/standard-sql/recursive-ctes`）。§5(b) の `WITH RECURSIVE` の制約（自己参照ちょうど 1 回 / `UNION ALL` / 再帰項に集計・分析関数と `LIMIT` 不可 / 反復上限 500）は WebFetch で確認済みだが、正典に無いため本文に URL を出せていない。
9. **`references.md` に BI 側の一次情報を 1 本追加したい**（Looker Studio の BigQuery コネクタ仕様、または LookML での `UNNEST` 展開）。I-2 の対応で断定を条件文に弱めたが、§4 の結論と §6 第 1 表の 1 行目を支える根拠なので、出典が付けば断定に戻したい。
10. **`snap_companies` / `snap_agents` を新たに使った**（C-2 の版付き supertype の入力。`snap_members` と同じく命名規約 `snap_*` の具体化）。

### 未達（このラウンドで解消していないもの）

- 4 文の段落が 12 残る（m-1 を完全には満たしていない。いずれも「A。B。C。D。」の列挙型で、分けると対応関係が読めなくなると判断した）。
- DWT 3rd ed. 本体は書籍のため WebFetch できていない。章番号は正典・ブリーフの裁定に従い、技法定義の帰属は引き続き Techniques PDF（一次情報）。

---

## 修正ラウンド 2（再レビュー `review/06_rereview.md` への対応）

| ID | 重み | 対応 |
|---|---|---|
| N-1 | Important | §5(d) の `member_versions` を、05回の変換を再現する形から**参照するだけ**の形に変更。`FARM_FINGERPRINT(CONCAT(member_id,'\|',CAST(dbt_valid_from AS STRING)))` によるキー再計算と `snap_members` 直読みを削除し、`SELECT member_key, member_id, valid_from, valid_to, is_current FROM {{ ref('dim_member') }}` に。コメントも「版の畳み込み・`deleted_at` 除外・`member_key` の生成は 05回で済んでいる。ここでは再現も再計算もしない」に書き換えた。オーケストレータ裁定に従い**モデル名を `dim_member_with_desired`（対案）**にして本体 `dim_member` と衝突させず、`UNNEST` クエリの `ref()` も同名に変更。さらに `<ol>` の直前に段落を 1 つ足し、「`M001` は `snap_members` では 3 版だが 05回の畳み込みを経て `dim_member` で 2 行になっており、この対案でも 2 行のまま。`fct_scout.member_key` との突き合わせが (a) と同じに保たれるのはこのためで、キーを作り直すとここが崩れる」と明記 |
| n-2 | Minor | 図の `fct_scout` ノード（左右とも）の `sub` を `S003 / member_key = M002` → `S003 / member_id = M002` に。`member_key` は `FARM_FINGERPRINT` の INT64 であって `M002` ではないため。右パネルの `member_id = M002` と表記が揃った。本文にも `member_key = M002` の残存は 0 件 |
| n-3 | Minor | 参照文献に 1 行追加: `Google Cloud, BigQuery 再帰 CTE（WITH RECURSIVE）— https://cloud.google.com/bigquery/docs/recursive-ctes（自己参照 1 回・UNION ALL・反復上限 500）`。`references.md` に `BQ recursive` が入った（提案 8 が採用された）ことへの追従。`p.meta` の「再解釈」は BQ nested のまま（再帰 CTE は再解釈ではなく実装の仕様確認のため） |

### 検証

| 項目 | 結果 |
|---|---|
| `check_svg.py` | **0 errors, 0 warnings** |
| SVG の well-formed | OK |
| `<pre><code>` 内の生 `<` | 0 件（9 ブロック） |
| 本文 URL 7 本 × `references.md` 突合 | 全件一致（kimballgroup.com 4 本 + decisionworks 1 本 + cloud.google.com 2 本） |
| `<p>` の 5 文以上 | 0 件 |
| `member_key = M002` の残存 | 0 件 |

### 正典への変更提案（このラウンドで新規）

11. **`dim_member_with_desired` を正典に載せるかどうか。** オーケストレータ裁定で命名は確定したが、`domain.md` §4 のディメンション表には無い。ARRAY 対案（＝採用しない設計）の説明用モデルなので、正典に載せず「06回の対案として本文にのみ登場する」扱いでよいと考えているが、判断は正典側に委ねる。

### 未達（このラウンドでも解消していないもの）

- 4 文の段落が 13 件残る（m-1 の parked 分。列挙型のため分割しない判断を維持）。
- 図の右パネルのノード名は `dim_member` のまま（§1 の判断表・§4 本文と揃えた概念表記）。物理モデル名が `dim_member_with_desired` に分かれるのは §5(d) の実装上の都合で、図で分けると「ARRAY 内包」という比較軸が読みにくくなるため変えていない。
- DWT 3rd ed. 本体は書籍のため WebFetch できていない（章番号は正典・ブリーフの裁定に従う）。
