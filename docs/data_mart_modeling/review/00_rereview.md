# 00 題材と簡易データモデル — 再レビュー（修正ラウンド1に対する検証）

対象: `docs/data_mart_modeling/html/00_domain.html`
初回レビュー: `review/00_review.md`（Critical 1 / Important 3 / Minor 8）
執筆者の対応報告: `reports/00_report.md`「修正ラウンド1」
再レビュー担当: 初回とは別。報告は参照するが判定の根拠にはせず、HTML の該当箇所を直接読んで判定した。
再レビュー日: 2026-09-08

検証に使った差分: `git diff fe39f65 f31ae7a -- html/00_domain.html`（30 insertions / 18 deletions）。以降の「修正差分の範囲」はこの diff を指す。

---

## 1. 初回指摘 12 件の判定

| ID | 指摘の要旨 | 判定 | HTML 上の確認内容 |
|---|---|---|---|
| Critical-1 | 「全テーブルが `updated_at`」「マスタ系は `deleted_at`」が正典 §2 の列一覧と矛盾 | **ADDRESSED** | §3 冒頭が2段落に書き換わっている。`updated_at` を持つ8表（`members`, `member_desired_job_categories`, `companies`, `agencies`, `agents`, `reviews`, `job_postings`, `contracts`）と持たない9表（`job_categories`, `industries`, `prefectures`, `review_moderation_events`, `scouts`, `applications`, `selection_events`, `placements`, `page_views`）を列挙。**正典 §2 の17テーブルを1件ずつ機械照合し、8/9 の振り分けは完全一致**（初回レビューが本文で「7/17」と書きつつ9件挙げていた数え誤りも、HTML 側は9で正しい）。`deleted_at` は `members` のみと明記。「OLTP としての設計意図」の削除の記述も「`members` の削除も `deleted_at` を立てるだけ」に限定された |
| Important-1 | Manifesto の強みは4つではなく5つ | **ADDRESSED** | Manifesto の `aside kimball` が「挙げるのは5つ」に訂正され、第5の強み（集約を管理するユーティリティ群）が追記。**原典を再取得して独立に確認**：First = predictable, standard framework／Second = withstands unexpected changes in user behavior／Third = gracefully extensible／Fourth = body of standard approaches（＝本文の「定型の対処法」）／Final = administrative utilities that manage and use aggregates。数・順序・4つ目の同定すべて正しい。「5つ目の集約は 04回・08回で扱う」の接続も正典 §4 の `agg_company_rating_daily`(04回) / `agg_company_entity`(08回) と整合 |
| Important-2 | ER 図の凡例「白は状態を上書き更新するテーブル」が §3 本文と矛盾 | **ADDRESSED** | 凡例テキストが `イベントが1行として記録されるテーブル（白は当事者・契約のマスタ）` に変更され、「上書き更新」という白側の定義が消えたので本文との正面衝突は解消。加えて図直下に `p.cap` が1本追加され「塗ったテーブルも `reviews.status` や `scouts.opened_at` のように後から列が更新される。追記と更新が混ざる点が 02回・05回の論点になる」と明示。図形・色分けは無変更（`box-focal` は `scouts` `applications` `selection_events` `reviews` の4つのまま）。※新 Minor-B を参照 |
| Important-3 | 図注「省略した外部キーが3本」が誤り（`job_postings.agency_id` 漏れ） | **ADDRESSED** | `p.cap` が「4本ある」に訂正され、`job_postings.agency_id` → `agencies`（`J002` が `A01` 経由であることの根拠）が追加。宙に浮いていた `agencies` も省略テーブルの列挙に「仲介会社そのもの（`agencies`）」として組み込まれた。ノードは9のまま、矢印12本も無変更 |
| Minor-1 | §6 転載1行目の `<strong>` 欠落 | **ADDRESSED** | `相当を<strong>ジャンク化した <code>dim_review_attributes</code></strong> に落とす` になっている |
| Minor-2 | Rule #5 の要約が見出しではなく従属節 | **ADDRESSED** | 「多対多はファクトテーブルで解決し、その外部キーを NULL にしてはならない」に訂正。**原典を再取得して確認**：Rule #5 の見出しは "Resolve many-to-many relationships in fact tables."、本文中に "These foreign key fields should never be null." — 訂正後の要約は見出し＋当該文の双方を含み正確。Rule #1 "Load detailed atomic data into dimensional structures." も一致 |
| Minor-3 | 3文超の段落（地の文2箇所） | **ADDRESSED** | 指摘された地の文2箇所を分割済み。§3「状態は列で持つ…」＝3文、後半を別段落（2文）へ。§6「1行目だけが…」＝3文、後半を別段落（2文）へ。さらに**据え置きでよいとされた `.aside` 5本にも `<br>` を入れて3文以内の塊に整理**しており、指摘以上に対応している（ch.18 3+1、Manifesto 2+2、DT#3 3+2、Reis 3+1、Techniques 3+1） |
| Minor-4 | §8 が `.aside` でなく `<p>` 3本・分量超過 | **ADDRESSED** | `<div class="aside">` 1つに集約。「Cloud Run のエンドポイントを分けた結果」の1文と `mart_error_analysis` の1文を削り、`<br>` 区切り3ブロック（2文＋2文＋1文）に圧縮。style.md の「3〜5行の aside」に収まる |
| Minor-5 | Reis の「町の地図」「セマンティックな衝突」の引用精度 | **ADDRESSED** | 「町の計画（Town Plan）」に訂正、鉤括弧付きの「セマンティックな衝突」は削除され「部門ごとに『顧客』の定義が食い違ったまま業務と IT が合意できない状態」に言い換え済み |
| Minor-6 | 「問いの半分は『ファネル』と『リードタイム』」 | **ADDRESSED** | 「§2 に挙げた5つの問いのうち2つが…」に訂正。§2 の箇条書きは5件、うち2件目がファネル・3件目がリードタイムで検算一致 |
| Minor-7 | 演習(b)「差し戻し回数」が正典の状態遷移に無い | **ADDRESSED** | 行見出しが「審査ラウンド数」に変更。理由欄も「`review_moderation_events` の行数を数えた加法メジャー。差し戻し（`screening` → `submitted`）を表現するなら正典の `status` 遷移に足す必要がある（01回で検討）」に書き換えられ、正典に無いことを明示したうえで送っている |
| Minor-8 | report の「正典への変更提案: なし」に追記すべき | **ADDRESSED** | `reports/00_report.md` の「正典への変更提案」が2件に更新（domain.md §2 前書きの主語明確化 / references.md の Hightouch 1 要点欄の訂正）。ただし**提案どまりで `canon/` 本体は未修正**（正典を勝手に変えないという運用どおりの状態。Critical-1 は本文側を正典に合わせて解消済みなので、ページ内の自己矛盾は残っていない） |

**集計: ADDRESSED 12 / NOT ADDRESSED 0。**

---

## 2. 正典 §2 の転載の機械照合（最新の `canon/domain.md` と）

`canon/domain.md` §2 の Markdown 表と HTML §3 の4表を、タグ・バッククォート・空白を除去したうえで **17テーブル × 3列（テーブル名 / 主キー / 列）を1セルずつ突合**した。

- **差分ゼロ。** 欠落テーブル 0、余剰テーブル 0、列名の不一致 0。
- 強調（`**不揃い階層**` / `<strong>不揃い階層</strong>`）も含めて一致。
- 列数の抜き取り確認: `members` 11列、`companies` 9列、`reviews` 17列（8軸スコア込み）、`scouts` 10列、`page_views` 10列 — いずれも正典どおり。
- 列挙値（`lt400`/`400_600`/… や `submitted`/`screening`/`published`/`rejected`、`ge1000` など）も1つも落ちていない。

ついでに他の転載表も同じ方法で照合した（いずれも差分ゼロ）:

| 転載元 | 規模 | 結果 |
|---|---|---|
| domain.md §1 サービス概要 | 5行 × 3列 | 一致 |
| domain.md §3 バスマトリクス | 10行 × 11列 | 一致（✓/✗/空欄の配置まで） |
| domain.md §6 固定判断 | 7行 × 4列（+「扱う回」列） | 一致（Minor-1 の強調復元を含む） |

Critical-1 の書き換えで新たに本文へ持ち込まれた列名（`opened_at` / `replied_at` / `reply_type`）も正典 `scouts` の列に実在する。**正典外のテーブル名・列名の混入はゼロ。**

---

## 3. `check_svg.py`

```
$ python3 ~/.claude/skills/svg-diagram/scripts/check_svg.py docs/data_mart_modeling/html/00_domain.html
0 errors, 0 warnings
```

修正は凡例テキストの差し替えのみで図形・座標・`viewBox` は無変更のため、密度予算（ノード9・矢印12・ゾーン3）とダーク3系統も初回判定のまま維持されている。HTML 体裁も再確認: `<table>` 12個すべて `.table-wrap` 済み、`<div>` 開閉 20/20、`<details>` 2/2、h2 は 1〜8 + 参照文献 の9個、`&lt;` エスケープ漏れなし（コードブロックは 00回では不要）。

---

## 4. 修正差分の範囲で見つけた新規指摘

新規 **Critical 0 / Important 0**。以下は Minor 3件。いずれも次回の修正で拾えば足り、単独では差し戻し理由にならない。

### Minor-A — 参照マスタ3表を「追記型」と呼んでいる（§3 第1段落）

> 残る9表（`job_categories`, `industries`, `prefectures`, `review_moderation_events`, `scouts`, `applications`, `selection_events`, `placements`, `page_views`）は追記型で更新列を持たない。

9表のうち `job_categories` / `industries` / `prefectures` はイベントログではなく参照マスタで、行が追記されるだけとは限らない（`job_categories.name` の改称、`industries` の統廃合はいずれも更新）。正典が言えるのは「`updated_at` を持たない」までで、「追記型」は正典に無い性質の付与にあたる。放置すると 09回（増分・遅延到着）で「参照マスタは追記のみだから差分取得できる」という誤った前提を誘発しうる。

**修正案**: 9表を2群に割る。
> 残る9表のうち、`review_moderation_events` `scouts` `applications` `selection_events` `placements` `page_views` は追記型のイベント表。`job_categories` `industries` `prefectures` は更新列を持たない参照マスタで、変更を差分では追えない（全件洗い替えになる）。

### Minor-B — 新しい凡例が `job_postings` を覆っていない（ER 図）

凡例は白を「当事者・契約のマスタ」と定義するが、白い5ノードのうち `job_postings` は当事者でも契約でもない（`contracts` が契約、`members`/`companies`/`agents` が当事者）。初回レビューの修正案は `白: 当事者・契約のマスタ（ディメンション候補）` で、この括弧書きが `job_postings` を回収する部分だったが、そこだけ落ちている。Important-2 の矛盾自体は解消しているので Minor に留める。

**修正案**: 凡例の白側を `白は当事者・求人・契約のマスタ（ディメンション候補）` にする。正典に `dim_job_posting` がある以上、「ディメンション候補」の一語で5ノードすべてが収まる。

### Minor-C — Rule #5 訂正後、「正面から衝突」の根拠が Rule #5 側で弱くなった（§6 末尾）

Minor-2 の訂正で Rule #5 は「多対多はファクトテーブルで解決し、その外部キーを NULL にしてはならない」になった。しかし `fct_review` は `member_key` を NULL にするのではなく**列ごと持たない**ので、Rule #5 との衝突は成立しにくい（衝突しているのは Rule #1 の原子性）。訂正が正確になった結果、文の論理が少しずれた。

**修正案**: Rule #5 を「衝突する原則」から外し、逃げ道を塞ぐ側の根拠として使う。
> 10 Rules の Rule #1「原子の詳細を入れよ」と正面から衝突する。`member_key` を NULL 可の外部キーとして残す逃げ道も Rule #5（外部キーを NULL にしてはならない）と DT#43 が塞ぐので、列ごと落とすか、隔離データセットに逃がすかの二択になる。

### 参考（指摘に至らなかった観察）

- 図直下の `p.cap` が2本連続する。`.cap` は `margin:-8px 0 20px` なので2本目の上マージンが負に効き、1本目との間隔が 12px に詰まる。読めるので体裁上の指摘には数えない。
- §3 第2段落「`scouts` の `opened_at` / `replied_at` / `reply_type` だけが例外で、更新列を持たないまま後から値が埋まる」は、直前の「追記型」に対する例外であることが明示されており自己矛盾ではない。Minor-A のとおり群分けすれば、この例外の位置づけもさらに明快になる。
- 未変更箇所（§1 の全11回一覧、§5 の対応表、§7 の演習本体）は今回の掘り起こし対象外とした。初回レビューで ✅ の項目が修正で壊れていないことだけを確認している（機械照合により全転載表の一致を再確認済み）。

---

## 5. 総合判定

**APPROVE**

- 初回指摘の対応: 12/12 ADDRESSED（NOT ADDRESSED 0）
- 新規 Critical: 0 / 新規 Important: 0 / 新規 Minor: 3
- `check_svg.py`: 0 errors, 0 warnings
- 正典 §2 転載: 17テーブル × 3列で差分ゼロ（§1 §3 §6 の転載も差分ゼロ）

Critical-1 の対応は最小限の言い換えで済ませず、`updated_at` の有無で17表を明示的に2群へ割ったうえで `scouts` の例外まで書いており、05回・09回が踏む地雷を先に除去できている。Important-1 / Minor-2 / Minor-5 の原典訂正は、こちらで原典を取り直しても正しい。Minor-3 は指摘範囲（地の文2箇所）を超えて `.aside` 5本まで整理されている。

残る Minor 3件はいずれも1〜2文の差し替えで閉じる。次の回の執筆と並行して処理してよく、この回の公開を止める理由にはならない。
