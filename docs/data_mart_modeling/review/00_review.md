# 00 題材と簡易データモデル — レビュー

対象: `docs/data_mart_modeling/html/00_domain.html` / ブリーフ `briefs/00.md` / 報告 `reports/00_report.md`
レビュー日: 2026-09-08

---

## 1. ブリーフ準拠表

| # | ブリーフの必須項目 | 判定 | 該当箇所 |
|---|---|---|---|
| 0 | ファイル名 `html/00_domain.html` | ✅ | — |
| 0 | `<title>` = `題材と簡易データモデル — データマート設計 00` | ✅ | L6 |
| 0 | `p.meta` に DWT ch.1 / ch.18 / 10 Rules / Manifesto / 再解釈 Reis・Hightouch 1 | ✅ | L45 |
| 0 | 冒頭1段落で DMBOK シリーズ（総論）との違いを宣言 | ✅ | L47（3文） |
| 1 | 節1「このシリーズが扱うこと」＝位置づけ | ✅ | L49–51 |
| 1 | 全11回の一覧表（`canon/plan.md` そのまま） | ✅ | L53–72。plan.md の4列（#/タイトル/中心の判断/図）を全行一致で転載（差分ゼロを機械照合で確認） |
| 2 | 節2「題材: CareerVoice」＝サービス概要表（domain.md §1） | ✅ | L83–95。5行とも文字列一致 |
| 2 | 分析側が答えたい問い | ✅ | L97–105。5項目とも一致 |
| 3 | 節3 ＝ domain.md §2 の表を**列を省略せず**転載 | ✅ | L113–164。**17テーブル × 3列を1セルずつ機械照合し、差分ゼロ**（会員・企業8表 / クチコミ2表 / 求人・スカウト・応募5表 / 契約・閲覧2表。`members` の11列、`reviews` の8軸スコア＋17列、`page_views` の10列を含め欠落なし） |
| 3 | OLTP としての設計意図（正規化・状態列・論理削除）を短く | ⚠️ | L275–279。3点とも触れているが、`updated_at` / `deleted_at` の記述が正典の列一覧と矛盾 → **Critical-1** |
| 4 | 節4 ＝ domain.md §3 のプロセス一覧 | ✅ | L296–320。10行 × 11列を機械照合し差分ゼロ |
| 4 | 「部門ではなくプロセス」（DT#3）を原則として置く | ✅ | L288（本文）+ L290–292（`aside kimball`） |
| 5 | 節5 ＝ Reis の階層 × DWT 4ステップの対応表 | ✅ | L332–343 |
| 5 | 各回がどの段階に属するかを表で | ✅ | L347–365 |
| 6 | 節6 ＝ domain.md §6 の表を転載し「扱う回」を示す | ✅ | L372–385。7行とも一致（強調1箇所の欠落のみ → Minor-1） |
| 7 | 演習(a) 担当システムのプロセス5つ・部門名チェック、解答例は CareerVoice | ✅ | L391–410 |
| 7 | 演習(b) `reviews.status` の遷移を列挙しファクト/ディメンションに分類 | ✅ | L412–435 |
| 7 | `<details><summary>解答例</summary>` で同回内に解答 | ✅ | 2問とも |
| 8 | 節8 ＝ `dbt_logs_analysis`（データソース起点）vs `news_pipeline`（プロセス起点）の対比 | ✅ | L437–443。内容は指定どおり。ただし体裁が `.aside` でなく分量超過 → Minor-4 |
| 図 | OLTP 簡易 ER 図（アーキテクチャ図型・ノード ≤9） | ✅ | L168–271。ノード9個（`members` `companies` `reviews` `job_postings` `scouts` `applications` `selection_events` `contracts` `agents`）＝ブリーフ指定と完全一致 |
| 図 | 矢印は FK の向き（子→親）だけ | ✅ | 12本すべて子→親。座標を追って全12本の始点・終点テーブルを検証済み（誤った向き・誤った接続先なし） |
| 図 | `page_views` と参照マスタは省いて注記に落とす | ✅ | L273 の `p.cap`。ただし省略 FK の本数が誤り → **Important-3** |
| 図 | ゾーンは3つまで | ✅ | 会員側 / 企業側 / エージェント側 の3。ただし凡例の色の意味が本文と矛盾 → **Important-2** |
| 図 | `check_svg.py` が 0 errors | ✅ | 再実行して `0 errors, 0 warnings` を確認 |
| 必須 | 全11回の一覧表 | ✅ | §1 |
| 必須 | domain.md §2 の全テーブル表（列を落とさない） | ✅ | §3 |
| 必須 | バスマトリクス（domain.md §3）を予告として | ✅ | §4「バスマトリクス（予告）」+「読み方と作り方は 01回で扱う」 |
| 構成 | 00回特例の8節 + 参照文献 | ✅ | h2 が 1〜8 + 参照文献 の9個 |
| 体裁 | 全表が `.table-wrap` | ✅ | `<table>` 12個 / `.table-wrap` 12個 |
| 体裁 | `&lt;` エスケープ漏れ | ✅ | 該当なし（SQL/YAML コードブロックはゼロ。00回では妥当） |
| 体裁 | 前後の回へのリンクを張らない | ✅ | 回番号参照のみ |
| 文献 | 全 URL が references.md 由来 | ✅ | 参照文献9本すべて references.md に存在 |

---

## 2. 指摘一覧

### Critical-1 — 「全テーブルが `updated_at`」「マスタ系は `deleted_at`」が正典の列一覧と矛盾（L111, L279）

本文:

> L111: 全テーブルが <code>updated_at</code> を持ち、マスタ系は論理削除 <code>deleted_at</code> を持つ。**列は以下が全てで、以降の回もこれ以外を持ち出さない。**
> L279: 削除は <code>deleted_at</code> による論理削除で、行は消えない。

直後に転載している domain.md §2 の列一覧に照らすと、どちらも成り立たない。

- `updated_at` を**持たない**テーブル（7/17）: `job_categories`, `industries`, `prefectures`, `review_moderation_events`, `scouts`, `applications`, `selection_events`, `placements`, `page_views`
- `deleted_at` を持つのは `members` **のみ**。マスタ系の `companies` / `agencies` / `agents` / `job_categories` / `industries` / `prefectures` はいずれも持たない

同じ段落が「列は以下が全て」と宣言しているため、ページ内で自己矛盾している。しかもこの記述は 05回（SCD / CDC）や 09回（増分・遅延到着）の前提として引き継がれ、`stg_careervoice__scouts` に `updated_at` を仮定した増分境界や、`companies` の `deleted_at IS NULL` フィルタといった、正典上あり得ないコードを誘発する。

**修正案（本文を正典に合わせる）**:

> OLTP は BigQuery の `src_careervoice` データセットに Datastream（CDC）で複製されている前提。更新される行を持つテーブル（`members` `companies` `agencies` `agents` `reviews` `job_postings` `contracts` `member_desired_job_categories`）は `updated_at` を持ち、論理削除 `deleted_at` を持つのは `members` だけである。`scouts` `applications` `selection_events` `placements` `page_views` は追記型で更新列を持たない（`scouts` の `opened_at` / `replied_at` だけが例外的に後から埋まる）。**列は以下が全てで、以降の回もこれ以外を持ち出さない。**

L279 も同様に「削除は `members` の `deleted_at` による論理削除で、行は消えない」に限定する。

なお `canon/domain.md` §2 の前書き（L28「`updated_at` / 論理削除 `deleted_at` を持つ」）は主語が曖昧で、この誤読を招く書き方になっている。正典側を「更新列は表のとおり。`deleted_at` は `members` のみ」と明確化する提案を report の「正典への変更提案」に書くのが望ましい（本文を直さず正典を変える場合も、どちらか一方に揃える必要がある）。

---

### Important-1 — Manifesto が挙げる次元モデルの強みは「4つ」ではなく5つ（L282–285）

本文:

> Manifesto が次元モデルの強みとして挙げるのは4つ — 予測可能な枠組み、対称性…、優雅な拡張性…、そして…**定型の対処法が揃っていること**。

原文（https://www.kimballgroup.com/1997/08/a-dimensional-modeling-manifesto/ を取得して確認）は "A second strength… A third strength… A fourth strength… **A final strength** of the dimensional model is the growing body of administrative utilities and software processes that manage and use aggregates." と、集約（アグリゲート）管理のユーティリティ群を第5の強みとして明記している。列挙数の断定が原典と食い違う。

**修正案**:

> Manifesto が次元モデルの強みとして挙げるのは5つ — 予測可能な枠組み、対称性（どのディメンションからでも等しく入れる）、優雅な拡張性（行や列を足すだけで既存クエリを壊さない）、緩やかに変化するディメンションやファクトレスファクトのような**定型の対処法が揃っていること**、そして集約テーブルを管理するユーティリティ群。このシリーズが扱うのは4つ目の「定型」の中身で、5つ目の集約は 04回・08回で触れる。

（「4つ目の『定型』」という後続の参照はそのまま生きる。集約を 04/08回に接続すると `agg_company_rating_daily` / `agg_company_entity` の伏線にもなる。）

---

### Important-2 — ER 図の凡例「白は状態を上書き更新するテーブル」が §3 本文と矛盾（L495 付近の凡例 / L277）

凡例は accent 塗り＝「イベント行が積まれるテーブル」、白＝「状態を上書き更新するテーブル」と二分している。accent は `scouts` `applications` `selection_events` `reviews` の4つ。

しかし §3 本文（L277）はこう書いている:

> `reviews.status`、`job_postings.status`、`contracts.status`、`scouts.opened_at`/`replied_at` はいずれも行を上書きして遷移する。

accent の4つのうち `reviews` と `scouts` が、白側の定義（上書き更新する）に真正面から該当する。図と本文が同じページで逆のことを言っている状態で、しかも報告書（迷った判断2）はこの色分けを「02回の定期スナップショットが必要になる理由へ繋がる」伏線として位置づけているため、誤読の影響が後続回に及ぶ。

**修正案**（凡例の文言だけで直る。図形の変更は不要）:

> accent: <strong>イベントが1行として記録されるテーブル（ファクト候補）</strong> ／ 白: 当事者・契約のマスタ（ディメンション候補）
> 注記に1行追加: 「accent のテーブルも `reviews.status` や `scouts.opened_at` のように後から列が更新される。追記と更新が混ざる点が 02回・05回の論点になる。」

---

### Important-3 — 図注「図に出していない外部キーが3本ある」が誤り（L273）

`p.cap` は省略した FK を3本（`members.current_company_id` → `companies`、`companies.parent_company_id` 自己参照、`agents.agency_id` → `agencies`）と数えているが、`job_postings.agency_id` → `agencies`（正典 §2 で `nullable=エージェント経由求人`）が漏れている。`agents.agency_id` を数に入れている以上、判定基準は「描いたテーブルが持つ FK」であり、同じ基準なら 4本になる。

加えて `agencies` は、続く「図からは省いた」テーブル列挙（`job_categories`, `industries`, `prefectures`, `member_desired_job_categories`, `review_moderation_events`, `placements`, `page_views`）にも入っておらず、矢印の説明中に一度出るだけで宙に浮いている。`J002` が `A01` 経由という正典サンプルの根拠が `job_postings.agency_id` である以上、落としたままにするのは惜しい。

**修正案**:

> 図に出していない外部キーが4本ある。`members.current_company_id` → `companies`、`companies.parent_company_id` → `companies`（自己参照、`C003` の親が `C001`）、`agents.agency_id` → `agencies`、`job_postings.agency_id` → `agencies`（`J002` が `A01` 経由であることの根拠）。仲介会社そのもの（`agencies`）、参照マスタ（`job_categories`, `industries`, `prefectures`）、多値の `member_desired_job_categories`、審査ログの `review_moderation_events`、成果報酬の `placements`、イベントログの `page_views` も図からは省いた。

---

### Minor-1 — §6 の転載で強調が1箇所落ちている（L374）

正典 §6 の1行目は「…相当を**ジャンク化した `dim_review_attributes`**に落とす」と太字。HTML では `<strong>` が無い。他6行・他3表（§1 §2 §3）は強調も含めて完全一致しているので、ここだけ揃っていない。

**修正案**: `相当を<strong>ジャンク化した <code>dim_review_attributes</code></strong> に落とす`

---

### Minor-2 — 10 Rules Rule #5 の要約が見出しではなく従属節（L387）

本文:

> 10 Rules の Rule #1 は「原子の詳細を入れよ」、Rule #5 は「外部キーを NULL にするな」と言うが…

原文を取得して確認したところ、Rule #5 の見出しは **"Resolve many-to-many relationships in fact tables"** で、"These foreign key fields should never be null." はその説明中の一文。引用として誤りではないが、ルールの主旨を取り違えた印象になる（NULL 外部キーの正典根拠は §6 の表が挙げる DT#43 の方）。Rule #1 の要約は正確。

**修正案**:

> 10 Rules の Rule #1 は「原子の詳細を入れよ」、Rule #5 は「M:M はファクトテーブルで解決し、その外部キーを NULL にしてはならない」と言うが…

---

### Minor-3 — 3文超の段落（style.md「1段落は3文まで」違反）

| 箇所 | 文数 | 冒頭 |
|---|---|---|
| L277（§3） | 5 | 「状態は列で持つ。…」 |
| L387（§6） | 5 | 「1行目だけが Kimball の原則と正面から衝突する。…」 |
| L290–292（DT#3 aside） | 5 | 「『データマートは部門で定義される』は…」 |
| L86–88（ch.18 aside） | 4 | 「設計に入る前に…」 |
| L281–285（Manifesto aside） | 4 | 「ER モデリングは…」 |
| L326–328（Reis aside） | 4 | 「概念モデル（CDM）は…」 |
| L345（Techniques aside） | 4 | 「4つの決定は…」 |

引用枠（`.aside`）は原典要約という性格上ある程度は許容範囲だが、地の文の2箇所（L277 / L387）は分割すべき。L277 は Critical-1 の書き直しと同時に、「状態は列で持つ」＋「削除は論理削除」＋「だから今しか分からない」の3文に整理できる。

---

### Minor-4 — §8 が `.aside` ではなく本文段落3本、分量も超過（L437–443）

style.md は「8節 … 3〜5行の aside」と規定。現状は `<p>` 3本・実測で本文幅10行前後。内容（`dbt_logs_analysis` = データソース起点 / `news_pipeline` = プロセス起点 / チュートリアルの種）はブリーフどおりなので、体裁のみの指摘。

**修正案**: 3段落を `<div class="aside">` 1つに収め、2段落目の「設計意図というより、Cloud Run のエンドポイントを `/collect` と `/notify` に分けた結果としてそうなった。」を削るか、太字の結論文（「アプリの処理境界がプロセス境界と一致していると…」）に吸収して4〜5行に圧縮する。

---

### Minor-5 — Reis の「町の地図」と「セマンティックな衝突」の引用精度（L326–328）

原文（Practical Data Modeling ch.14）を取得して確認した範囲では、概念モデルの比喩は **"Town Plan"**（都市計画。データモデラー John Giles の用語を Reis が引く形）であり、「地図」ではない。また `「セマンティックな衝突」` を鉤括弧で Reis の言葉として置いているが、原文で確認できるのは「部門ごとに『顧客』の定義が非互換になる」という記述で、この訳語が逐語引用かは確認できなかった。CDM を「最も価値のある成果物」とする位置づけ、CDM = 名詞（エンティティ）+ 動詞（関係）+ スコープの可視化、LDM = 属性・PK・FK、PDM = 技術選定、はいずれも原文どおりで正確。

**修正案**: 「業務側と共有する『町の計画（Town Plan）』」に改め、鉤括弧の「セマンティックな衝突」は括弧を外して「部門ごとに『顧客』の定義が食い違う状態」と言い換える。

---

### Minor-6 — 「問いの半分は『ファネル』と『リードタイム』」（L322）

§2 に挙げた問いは5件で、ファネルとリードタイムは2件。「半分」は言い過ぎ。

**修正案**: 「§2 に挙げた5つの問いのうち2つが『ファネル』と『リードタイム』なので、トランザクションファクトだけでは答えられない。」

---

### Minor-7 — 演習(b)「差し戻し回数」が正典の状態遷移に存在しない（L423）

`reviews.status` の4値（`submitted` / `screening` / `published` / `rejected`）には差し戻し（`screening` → `submitted`）が無く、演習(b) の解答表が列挙した遷移3本にも含まれていない。メジャー名 `moderation_rounds` は正典どおりなので、ラベルだけの問題。

**修正案**: 行の見出しを「審査ラウンド数」に変え、理由欄を「`review_moderation_events` の行数を数えた加法メジャー。差し戻しを表現するなら `screening` → `submitted` の遷移を正典に足す必要がある（01回で検討）」とする。

---

### Minor-8 — report の「正典への変更提案: なし」に1件追記すべき

`canon/references.md` は Hightouch Part 1 の要点を「Kimball → Inmon → OBT の整理」としているが、実際の Part 1 は raw → staging → reporting models の3層のみを扱い、Kimball / Wide table の比較は明示的に Part 2 以降へ繰り越されている（記事末尾 "In the next article in the series… This involves explaining Kimball's ideas… Wide tables…"）。本文（L318 の `aside modern`）は実際の記事を読んで3層で書いており**正しい**が、正典の要点欄が誤っているため、以降の回（07回が Hightouch 2 を引く）で混乱が起きる。

**修正案**: report の「正典への変更提案」に「references.md の Hightouch 1 の要点欄を『raw / staging / reporting の3層。raw を直接レポート層に使わない。Kimball vs OBT の比較は Part 2 以降』に修正」を追加する。

---

## 3. 個別観点の所見（指摘に至らなかったもの）

- **正典準拠（テーブル名・列名・ID）**: 本文の `<code>` 全 91 種を機械抽出して canon（domain.md + plan.md）と突合。正典外の識別子は、(a) `members.current_company_id` のようなドット表記（構成要素はいずれも正典に存在）、(b) `stg_careervoice__reviews`（正典の命名規約 `stg_careervoice__<table>` に適合）、(c) §8 の実基盤名（`dbt_logs_analysis` / `mart_url_performance` / `news_pipeline` / `raw_articles` / `summaries` / `favorites` / `/collect` / `/notify`）だけ。style.md が §8 に限って許す範囲に収まっている。**正典外テーブルの捏造はゼロ。**
- **サンプル値**: `M001`（6/15 属性変化 → 6/20 `S001` 受信 → 6/23 応募）、`C002` の `employee_size_band` 変化（2026-05-01, `50_299` → `300_999`）、`R001`（03-10 投稿 / 03-12 公開）、`R002`（`M002` → `C001`, `defamation` 却下）、`C003` の親が `C001` — すべて canon §5 と一致。
- **検算**: バスマトリクス「10行のうち3行が累積スナップショット、2行が定期スナップショット」→ 累積3（`fct_review_moderation` / `fct_scout_funnel` / `fct_application_pipeline`）、定期2（`fct_job_posting_daily` / `fct_contract_monthly`）、トランザクション5。一致。`dim_review_attributes` の 2×3×5 = 30行も正典どおり。
- **Kimball 原典との整合**: 10 Rules #1 / #7 / #10、DT#3、DT#43、DT#77、Manifesto の ER モデル評価と「エンドユーザーに届く前に次元モデルへ」、Techniques の4ステップ順序・「粒度はディメンション/ファクトより先」・「拘束力のある契約」・「異なる粒度を混ぜない」— 原典を WebFetch して確認し、いずれも正確。歪みは Important-1 と Minor-2 の2件のみ。
- **SQL / dbt**: コード例ゼロ。00回の性格上これは妥当で、report の判断に同意する（`partition_by` / `cluster_by` は §5 の表で語として出るだけ）。
- **図**: `check_svg.py` 再実行で `0 errors, 0 warnings`。ノード9・矢印12・ゾーン3・accent 1系統は密度予算内。矢印12本の座標を全て追い、始点（子）・終点（親）の対応に誤りが無いことを確認した（`scouts` → `agents` / `members` / `companies` / `job_postings`、`applications` → `members` / `scouts` / `job_postings`、`selection_events` → `applications`、`reviews` → `members` / `companies`、`contracts` → `companies`、`job_postings` → `companies`）。ダーク3系統（`prefers-color-scheme` + `[data-theme]` 両方向）も規約どおり。
- **正典 §4 の追記分**（SCD2 列名の統一 / 全ファクトに `audit_key` / パーティション用 `<role>_date`、および今回さらに加わった `dim_date.date_label` と STRING キーの `'-1'`）は 00回の §6 に不要。本文が §4 に踏み込んでいない点は正しい判断で、report の記述にも同意する。
- **文体**: 緩衝語（「〜でしょう」「かもしれない」「と思われる」等）の検出ゼロ。一般論で終わる節も無く、各節が具体 ID または具体テーブルで着地している。§8 は「直せ」と書かず「この回の基準ならどう判断されるか」に留めており、style.md の指定どおり。

---

## 4. 総合判定

**REVISE**

- Critical: 1（§3 の `updated_at` / `deleted_at` が正典の列一覧と矛盾）
- Important: 3（Manifesto の強み5つを4つと断定 / ER 図凡例が本文と矛盾 / 省略 FK の本数が誤り）
- Minor: 8

ブリーフの必須項目（全11回一覧・domain.md §2 の全列転載・バスマトリクス予告・9ノード ER 図・8節構成）はすべて満たしており、特に §2 の17テーブル × 3列は1文字も落とさずに転載されている。転載精度と原典の読み込みの質は高い。修正はいずれも局所的な文言差し替えで、構成の作り直しは不要。
