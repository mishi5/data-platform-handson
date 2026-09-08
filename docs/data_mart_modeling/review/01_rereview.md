# 01 粒度を宣言する — 再レビュー（修正ラウンド1・2 の検証）

対象: `docs/data_mart_modeling/html/01_grain.html`（665行、修正後）
前提: 初回レビュー `review/01_review.md`（critical=2 / important=5 / minor=8）、執筆者報告 `reports/01_report.md` の「修正ラウンド1」「修正ラウンド2」、正典 `canon/domain.md`（`dim_agency` 追加・`agency_key`+`agent_key`・全ファクト `audit_key`・`<role>_date`・`date_label` を含む更新版）

判定: **REVISE**（addressed=15 / not_addressed=0、新規 critical=0 / important=2 / minor=4）

---

## 1. 初回指摘 15 件の判定

報告は読んだが、判定は HTML 本体を直接読んで下している。

| # | 重み | 指摘 | 判定 | HTML 上の根拠 |
|---|---|---|---|---|
| C1 | Critical | as-of join が DATE と TIMESTAMP の比較で落ちる | **ADDRESSED** | SQL の as-of 比較は `e.occurred_at &gt;= X.valid_from AND e.occurred_at &lt; X.valid_to` が4本（`dim_member` / `dim_company` / `dim_agent` / `dim_agency`）。`e.event_date &gt;=` は **0件**。`e.event_date` は `event_date_key` の算出と `partition_by` にのみ使用。`occurred_at` は `DATE(occurred_at,'Asia/Tokyo')` に渡している以上 TIMESTAMP で、`valid_from`/`valid_to`（正典 §4 で TIMESTAMP）と型が合う。§5 に「as-of join の比較は DATE ではなく TIMESTAMP で行う…（作法は05回）」の段落も追加済み |
| C2 | Critical | `accepted_values` の `quote: false` 欠落で INT64 列が型エラー | **ADDRESSED** | `event_count` の `accepted_values` に `arguments: values: [1]` + `quote: false`。YAML コメントに「既定の `quote: true` だと `not in ('1')` が生成され型エラー」も併記。`arguments:` 直下に置く位置も正しい（`quote` は accepted_values の引数であって config ではない） |
| I1 | Important | 全ファクト `audit_key` の正典規定に未追随 | **ADDRESSED** | SELECT の FK 群末尾に `{{ audit_key() }} AS audit_key,`（コメントで DT#164・10回への forward pointer）。`schema.yml` の `fct_selection_event.description` にも「`audit_key` は行の由来を指す外部キーであって粒度キーではない」の2行。ファイル内の `audit_key` 出現は3箇所 |
| I2 | Important | 「company 列は10プロセス中9つ」は 10/10 | **ADDRESSED** | 「**`company` 列は10プロセス全てに ✓ が付く。**」に訂正。マトリクスの company 列を10行とも数え直して 10/10 を確認（`domain.md` §3 とも一致）。「✓ が2つ以上ある列はコンフォームドでなければならない」に結ぶ1文も追加されている |
| I3 | Important | §2(a) の「平均が壊れる」例が示したデータでは壊れない | **ADDRESSED** | 誤った `R002`（別企業）への言及を削除。主張を「`overall_score` は投稿粒度の値なので4行に複製され、`AVG` が行数＝遷移回数で重み付けされる」という機構の説明に限定し、「`R001` 単独では 3.5 のまま正しく見えるので気付けない／件数の 1→4 と違いテストでも目視でも表面化しない」を追加。正典外のスコア値を作らずに検証可能性を回復しており、初回レビューの修正案（仮想スコア 1.5 を置く）より筋がよい。検算: 4行 × 3.5 の `AVG` = 3.5（＝真値）で、示した数値と本文の主張は矛盾しない |
| I4 | Important | `INNER JOIN` が「行数を変えない」宣言と DT#43 に矛盾 | **ADDRESSED** | SQL 内の `INNER JOIN` は **0件**、`LEFT JOIN` 10本（`applications` / `postings` / `scouts` / `dim_member` / `dim_company` / `dim_agent` / `dim_agency` / `dim_job_posting` / `dim_job_category` / `dim_channel`）。FROM 直前に「以下は全て多対一の LEFT JOIN。行を増やさず、減らしもしない」。§5 リードに「母数だけが静かに欠ける」「`INNER JOIN` と `COALESCE(..., -1)` を同じ SQL に同居させてはならない」の2段落、`equal_rowcount` のコメントも「増えて（一対多）も減って（INNER JOIN）もいないか」に更新。本文中に残る `INNER JOIN` の語3件はすべて「使ってはならない」説明側 |
| I5 | Important | `agent_key` が `agent_referral` を取りこぼし、`-1` の意味づけが誤り | **ADDRESSED** | `-1 = 直接応募` の誤ったコメントは消え、`agent_key` は「-1 = 担当者を特定できない（直接応募・企業スカウト・紹介経由）」に。ラウンド2で正典追加の `dim_agency` に追随し、`agency_key` + `agent_key` の2本立てになった（正典 §4 の `fct_selection_event` の FK 定義と一致）。ただし新規の主張に過剰が残る → 下記 **N1** |
| m1 | Minor | 4文以上の段落が10箇所 | **ADDRESSED** | `<p>`（`p.meta` 含む）で句点4個以上のものは **0件**（機械計測）。内容の削除は見当たらない |
| m2 | Minor | `moderation_rounds = 2` が3遷移と噛み合わない | **ADDRESSED**（初回レビューが提示した remedy をそのまま適用。ただし残る算数のずれ → **N4**） | 「投稿者に差し戻された往復を1として数えた回数であって、`screening` を通過した回数ではない」を併記。遷移表は3件のままでブリーフ準拠を維持 |
| m3 | Minor | 「7個の日付キー」は正典では8本 | **ADDRESSED** | 「**1行**（到達した7つのマイルストーンが日付キー列に埋まる。列としては未到達の `closed_date_key` を含め8本、未達は `-1`）」。行数の主張と列数の主張が分離された。検算: `P001` の到達マイルストーンは 応募/書類/一次/最終/内定/承諾/入社 = 7、正典 §4 の日付キー列は 8、原子ファクト側は 6 行（`document`〜`hired`）で本文と一致 |
| m4 | Minor | DWT 章番号が本文に無い | **ADDRESSED** | §1「（DWT ch.2 の4ステップ）」、§2(c)「累積スナップショットは DWT ch.4 が扱うファクト型」、§3「DWT 3rd ed. ch.2 が同じ順序を提示し、ch.3（小売）が実例で通す」。§5 の縮約ディメンションにも「（DWT ch.4）」。ただし ch.4 は `p.meta` / 参照文献の `ch.2–3` に含まれない → **N3** |
| m5 | Minor | 原典引用が `<code>` に入っている・途中で切れている | **ADDRESSED** | `<em>“Atomic data has the most dimensionality and so it can be constrained and rolled up in every way possible for that data source.”</em>（Grain, 2003）` に変更。直前が「Kimball の言い方では——」で繋がっている |
| m6 | Minor | The Matrix の「行」は原文では first-level data mart | **ADDRESSED** | 「1999年の原文は行を *“all the first-level data marts that you could possibly build”* と呼んでおり、『ビジネスプロセス』は DWT 3rd ed.（2013）と DT#3 での言い直し。単一ソース1つ＝1行という中身は変わっていない」 |
| m7 | Minor | 演習1の設問に未検証の断定 | **ADDRESSED** | 「セッション粒度なら行数は 1/10 以下になる——**性能を理由にこちらを選ぶべきか**」。「パーティションスキャン量も同じだけ減る」の断定は消え、解答の「判断は性能ではなく問いで決まる」と衝突しなくなった |
| m8 | Minor | 演習3がソーステーブル不在に触れていない | **ADDRESSED** | 解答冒頭に「まず4ステップの①。**バスマトリクスに行を足すとはソースを1つ増やすと宣言すること**。domain.md §2 に投票のソーステーブルは無いので `review_votes`（`vote_id`, `review_id`, `member_id`, `voted_at`）相当が新たに要る」 |

**15/15 が ADDRESSED。** 執筆者の報告と実物の差分は見つからなかった（報告の「7本」だけは実物と食い違う → N4 に併記）。

### 修正後の機械チェック（再レビュー側で再実行）

| 項目 | 結果 |
|---|---|
| `check_svg.py` | `0 errors, 1 warnings`（warning は「`<svg>` が見つからない」＝ブリーフの「図なし」どおり） |
| HTML タグ対応（`html.parser`） | unclosed 0 / mismatch 0 |
| `<title>` | `粒度を宣言する — データマート設計 01` ✅ |
| `p.meta` | 1件 ✅ |
| 8節構成 | `1.`〜`8.` + `参照文献` = `<h2>` 9個 ✅ |
| `.table-wrap` | `<table>` 12 / `table-wrap` 13（CSS 定義1 + 12表すべて包まれている） |
| `<pre>` 内の裸の `<` | 0件（`&lt;` / `&gt;` のみ） |
| `<p>` の文数 | 4文以上 0件 |
| SQL の JOIN | `LEFT JOIN` 10本 / `INNER JOIN` 0件 |
| as-of 比較 | `e.occurred_at` 4本 / DATE 比較 0件 |
| `<code>` 識別子で `domain.md` に無いもの | `fct_review_vote` / `vote_count` / `review_votes` / `vote_id` / `voted_at`（演習3、正典への追加提案と明記）、`helpful_count` / `company_review_count`（反例）、dbt のテスト名・§8 の自基盤名のみ。**新規の正典逸脱なし**（`dim_agency` / `agency_key` は正典に存在） |

---

## 2. 新規指摘（修正差分の範囲）

### Important

#### N1. `agency_key` は「紹介経由でも失われない」わけではない（`-1` の意味づけが再び強すぎる）

**箇所**: §5 SELECT 直後の段落（「一方 `agency_key` は `job_postings.agency_id`（またはスカウト送信者の所属）から決まるので、紹介経由でも失われない。」）、SQL コメント（`-- エージェンシー。-1 = エージェント関与なし`）、`schema.yml` の `agency_key.description`（「-1 = エージェント関与なし。」）

SQL は `COALESCE(p.agency_id, da.agency_id) = dag.agency_id` で解決している。`source_channel = 'agent_referral'` の応募は `scouts` に行が無いので `da` は NULL、したがって `agency_key` は **求人側の `job_postings.agency_id` だけ**に依存する。`job_postings.agency_id` は nullable（＝エージェント経由求人のときだけ入る）なので、**エージェントが直接掲載求人（例: `J001` は `C001` の直接掲載）に紹介した応募は `agency_key = -1` に落ちる**。「紹介経由でも失われない」は成立しない。

これは I5 で指摘した「`-1 = 直接応募` という誤った意味づけ」と同型の問題が、`agent_key` から `agency_key` へ移っただけになっている。正典 §4 自身も `agency_key` を「`job_postings.agency_id` またはスカウト送信者の所属、**無ければ -1**」と定義しており、「エージェント関与なし」とは言っていない。SQL は正典どおりで正しく、誤っているのは本文・コメント・`description` の言い切りのほう。

**修正案**（SQL は変えない。3箇所の文言だけ）:

- 本文: 「一方 `agency_key` は `job_postings.agency_id`（またはスカウト送信者の所属）から決まるので、**求人がエージェント経由なら紹介経由でも失われない**。逆に、直接掲載求人へのエージェント紹介はどちらの手がかりも無く `-1` に落ちる——解像度を1段落としても、関与の有無そのものを常に復元できるわけではない。」
- SQL コメント / `description`: 「`-1` = エージェンシーを特定できない（直接応募、企業スカウト、および直接掲載求人へのエージェント紹介）」

#### N2. 「`dim_agency` の属性が `dim_agent` の完全な部分集合」は正典 §4 と一致しない

**箇所**: §5「`dim_agency` は `dim_agent` の**縮約（shrunken/rollup）ディメンション**（DWT ch.4）で、属性が `dim_agent` の完全な部分集合になっている——つまりコンフォームド。」

正典 §4 の列を突き合わせると一致しない。

| | 属性 |
|---|---|
| `dim_agent` | `agent_name`, `agency_id`, `agency_name`, `agency_tier`, `joined_date`, `left_date` |
| `dim_agency` | `agency_name`, `agency_tier`, `contract_start_date` |

`contract_start_date` は `dim_agency` にあって `dim_agent` に無い。したがって「完全な部分集合」ではない（Kimball の shrunken dimension は「行および／または**列の部分集合**」なので、この一文は定義そのものを外している）。drill across の結論（`agency_tier` で担当者別とエージェンシー別を並べられる）は共有属性 `agency_name` / `agency_tier` だけで成立するので、**主張は正しいが根拠の書き方が正典と食い違っている**状態。

**修正案**: 「属性が `dim_agent` の完全な部分集合」→「`agency_name` / `agency_tier` を `dim_agent` と**同一の名前・同一の値**で共有する（`dim_agency` 固有の `contract_start_date` はエージェンシー粒度でしか意味を持たない属性）。共有部分がコンフォームドである限り drill across は成立する」。「完全な部分集合」を落とせば、正典の列定義と矛盾せずに縮約ディメンションの説明が通る。

### Minor

#### N3. 引用の帳尻: DT#164 と DWT ch.4 が参照文献に無い

I1（`audit_key`）と m4（章番号）とラウンド2（縮約ディメンション）の修正で、本文に **DT#164 が2箇所**、**DWT ch.4 が2箇所**新たに登場した。しかし `参照文献` の一覧に DT#164 の項目は無く、DWT の項目は `ch.2–3` のまま。style.md の「参照文献＝この回で使ったものだけ」と自己チェックの「全 URL は references.md にあるものか」に照らすと、使ったのに載っていない状態になっている（DT#164 は `references.md` L47 に URL があり、回10 の担当として割り当てられている）。

**修正案**: どちらか。(a) 参照文献に DT#164（`https://www.kimballgroup.com/2014/03/design-tip-164-built-your-audit-dimension/`）を足し、DWT の行を `ch.2–4` にする。(b) 本文の DT#164 を「10回で扱う」への forward pointer と明示して DT 番号を出さない。`p.meta` はブリーフ指定（`DT#3 #77 #179`）なので触らなくてよい。

#### N4. `moderation_rounds = 2` は追記した定義でも 2 にならない

m2 の remedy（初回レビューが提示した文言）をそのまま入れたので **ADDRESSED 扱いにしたが、算数は依然合わない**。示した3遷移は `submitted→screening`（03-10）／`screening→submitted`（差し戻し, 03-11）／`submitted→published`（03-12）で、「投稿者に差し戻された往復」は **1回**、`screening` に入った回数も **1回**。どちらで数えても 2 にならない。

**修正案**: 遷移表を触らずに済む定義に寄せる。「`moderation_rounds` = 2 ＝ 審査担当者が判定を下した回数（03-11 の差し戻しと 03-12 の公開）」。これなら示した3遷移から 2 が導け、「`screening` を通過した回数ではない」という但し書きもそのまま生きる。

#### N5. `{{ audit_key() }}` は未定義マクロで、この SQL 単体ではコンパイルできない

I1 の修正で入った `{{ audit_key() }} AS audit_key,` は、コメントで「値の生成は10回で定義するマクロに委ねる」と断ってはいるが、この時点の読者がコピーすると `'audit_key' is undefined` で `dbt compile` が落ちる。初回レビューが提示した案そのままなので瑕疵とまでは言わないが、他の SQL がすべて実行可能な形で書かれている回なので浮く。

**修正案**: コメントを1語強めるだけで足りる。「`{{ audit_key() }}` は10回で定義するマクロ。それまでは `-1`（`dim_audit` の未知行）を置いても粒度の議論は変わらない」。

#### N6. `<li>` の文数（style.md の「1段落3文まで」の運用）

`<p>` は 4文以上ゼロだが、I3 の修正で §2(a) の2つ目の `<li>` が **5文**になった（`fct_review` の member 列を説明する `<li>` は元から6文）。初回レビューの m1 は `<p>` だけを数えていたので新規の規約違反とは言い切れないが、`<li>` を段落として扱うなら同じ基準が当たる。**修正案**: §2(a) の `<li>` は「重み付けが入る」までで一度切り、「しかも `R001` 単独では…」以降を直後の `<p>` に出す。

> なお報告 `reports/01_report.md` 修正ラウンド2 の機械チェック表「SQL の JOIN｜全て `LEFT JOIN`（7本）」は実物と合わない（実際は **10本**: `applications` / `postings` / `scouts` / `dim_member` / `dim_company` / `dim_agent` / `dim_agency` / `dim_job_posting` / `dim_job_category` / `dim_channel`）。HTML 側の欠陥ではないので指摘には数えないが、報告の数値は直しておきたい。

---

## 3. 新規に検証した箇所（問題なし・記録用）

- **`dim_agency` の as-of join の構文**: `LEFT JOIN {{ ref('dim_agency') }} AS dag ON COALESCE(p.agency_id, da.agency_id) = dag.agency_id AND e.occurred_at &gt;= dag.valid_from AND e.occurred_at &lt; dag.valid_to` は BigQuery で通る。先に結合済みの `da`（`dim_agent`）の列を後続 `LEFT JOIN` の `ON` で参照するのは標準 SQL の範囲内で、`dim_agent` → `dim_agency` の記述順も守られている。`da.agency_id` は正典 §4 の `dim_agent` の属性に実在する。
- **行数保存**: 追加された `dim_agency` は `agency_id` + 半開区間の as-of で最大1行しか当たらないため多対一。`equal_rowcount` の前提を壊していない。`COALESCE` が両方 NULL のときは NULL となり `= dag.agency_id` が偽 → `agency_key = -1`。DT#43 の作法どおり行は残る。
- **`fct_selection_event` の列構成と正典の一致**: 出力列は退化（`event_id`, `application_id`, `stage`）＋ `event_date_key` ＋ `member_key` / `company_key` / `job_posting_key` / `job_category_key` / `channel_key` / `agency_key` / `agent_key` ＋ `audit_key` ＋ `event_count` ＋ `event_date`。正典 §4 の FK・メジャー・退化の定義と過不足なく一致する。`partition_by` が DATE 列 `event_date` に張られているのも正典の新規約（`<role>_date`）どおり。
- **`quote: false` の効果**: `accepted_values` は `quote=True` のとき `where {{ column }} not in ('1')` を生成する。`event_count` は `1 AS event_count` の INT64 なので `quote: false` が必須で、修正は正しい。`arguments:` 直下（`values` と同階層）に置く位置も dbt 1.10.5 以降の仕様に合う。
- **数値の再検算**: §2(a) `SUM(review_count)` = 4 / 真値 1（4行 × `review_count`=1）✅。同表の `AVG(overall_score)` = 3.5 で「単独では正しく見える」も正しい ✅。§2(b) A/B/C 表は 6/20 送信 1・6/22 返信 0／0・1／1・1、6月送信 2・1・3 で `S001`+`S002` の定義から全セル一致 ✅。§2(c) `P001` = 累積1行 / 原子6行 / 到達マイルストーン7 / 日付キー列8 ✅。§7問2 `K001` の 2026-01〜09 = 9行 ✅。§3 company 列 10/10 ✅。`dim_review_attributes` 2×3×5=30、`dim_page_context` 3×3×4×2=72 ✅。
- **§3 バスマトリクス**: 10行 × 全列を `domain.md` §3 と再照合。ラウンド2の申告どおり**セルは1つも変わっておらず**、`✓(送信主体)` / `✗（下記参照）` の注記まで一致する。追加されたのは読み取り箇条書きの1項目のみ。

---

## 4. 総合判定

**REVISE**

- 初回の 15 件は **すべて実物で解消を確認**（addressed=15 / not_addressed=0）。C1・C2 はコードが実際に走る形に直っており、I3・I4 は主張と実装の矛盾が解けている。ラウンド2 の `dim_agency` 追随も正典 §4 の定義と一致していて、SQL としての欠陥は無い。
- 残るのは **新規 Important 2件（N1・N2）で、いずれも SQL ではなく本文の言い切り**。N1 は `-1` の意味を正典より強く書いてしまった点（I5 と同型の再発）、N2 は正典の列定義と照らすと成り立たない「完全な部分集合」。どちらも各1〜2文の書き換えで済み、設計判断の変更は不要。
- Minor 4件（N3 引用の帳尻、N4 `moderation_rounds` の算数、N5 未定義マクロの断り、N6 `<li>` の文数）はまとめて1パスで潰せる。
- 再々レビューは §5 の SELECT 直後の3段落（N1・N2）と 参照文献（N3）、§2(a) 末尾（N4・N6）を見れば足りる。
