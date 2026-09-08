# 04 加法性と派生指標 — 再レビュー（修正ラウンド1 の検証）

対象: `docs/data_mart_modeling/html/04_additivity.html`（`23f4e90` 時点）
初回レビュー: `review/04_review.md`（Critical 2 / Important 5 / Minor 7）／執筆者の報告: `reports/04_report.md`「修正ラウンド1」
差分の確認方法: `git diff a84df54 23f4e90 -- docs/data_mart_modeling/html/04_additivity.html`（438 行）を全行読み、HTML 側の該当箇所を直接確認した。報告の記述は照合対象であって根拠にしていない。

判定: **REVISE**（addressed=14 / not_addressed=0 / 新規 critical=0 / 新規 important=4）

---

## 1. 初回指摘 14 件の判定

| # | 指摘 | 判定 | HTML の該当箇所と根拠 |
|---|---|---|---|
| C1 | §7(b) の `QUALIFY` 評価順が逆 | **ADDRESSED** | §7(b) の `<pre>` 内コメントが「`QUALIFY` は `GROUP BY` / `HAVING` の後に評価される。同じ SELECT に `GROUP BY` を置くと `snapshot_date_key`（非グループ列）を `QUALIFY` で参照できないので、絞り込みを CTE に分ける」。GoogleSQL の評価順（… GROUP BY/集約 → HAVING → WINDOW → QUALIFY …）と一致 |
| C2 | MetricFlow YAML が legacy と latest の混成 | **ADDRESSED**（残件は N1） | 2ブロックとも `models: - name: X` → `semantic_model: {enabled, agg_time_dimension}` → モデル直下の `columns:`（`entity:` / `dimension:` / `granularity:`）→ モデル直下の `metrics:`、ratio はトップレベル `metrics:` に `numerator:` / `denominator:`。`docs.getdbt.com/docs/build/latest-metrics-spec` と `/docs/build/ratio` を WebFetch して1要素ずつ照合。初回レビューが挙げた6要素（コンテナ・時間軸・エンティティ・ディメンション・集約定義・ratio）は全て latest 側で統一されている。**`non_additive_dimension` の子キーだけが legacy のまま残っている（N1）** |
| I1 | `agg_company_rating_daily` に `rating_date` が無い | **ADDRESSED** | §5 の `config()` に `partition_by={'field': 'rating_date', 'data_type': 'date'}` と `cluster_by=['company_key']`、SELECT に `submitted_date AS rating_date`、`GROUP BY date_key, rating_date, company_key`、schema.yml に `rating_date`（`not_null`）。`canon/domain.md` §4 の `date_key`, `rating_date`(DATE, パーティション列), `company_key` と一致 |
| I2 | 企業グループ再集約が SCD2 キーで畳んでいる | **ADDRESSED**（残件は N5） | `JOIN dim_company AS anc ON b.ancestor_company_key = anc.company_key AND anc.is_current` を追加し、`SELECT anc.company_id AS group_company_id` / `GROUP BY group_company_id, d.year` に変更。`C002` の 5/1 の版分裂で年次が2行に割れる問題は解消。ブリッジ子孫側を全 SCD2 版に展開する前提と「足し上げの単位は企業という実体であって SCD2 の版ではない」を3段落で明記 |
| I3 | DWT 章番号 ch.4 → ch.2（3箇所） | **ADDRESSED**（残件は N4） | §1 h3「メジャーの3分類（DWT **ch.1–2**）」、§3 表「加法・半加法・非加法の分類（DWT **ch.2**）」、§5 h3「集約ファクト（DWT **ch.2** の aggregate fact table）」。§3 表の「定期スナップショット（DWT ch.4）」は据え置きで正しい。`p.meta` も「ch.1–2（加法・半加法・非加法）, ch.4（定期スナップショットと半加法残高）」に更新され、`canon/references.md` の「04 ｜ DWT ch.1–2（加法性）」と整合。**参照文献リストだけ「ch.1, ch.4」のまま（N4）** |
| I4 | `scout_quota` の分類と §2(b) の 600 が矛盾 | **ADDRESSED**（新規欠陥 N2 を伴う） | §1 表で `scout_quota`, `monthly_fee` を「加法（時間で足すと期間付与枠・期間売上）」の1行にまとめ、`scouts_remaining` を半加法の単独行に分離。§2(b) に「3列のうち2列は足してよい。`SUM(scouts_sent) = 160` …`SUM(scout_quota) = 600` …どちらも加法な**フロー**」「壊れているのは 440 だけ」を追加。レビューの推奨 a を採用 |
| I5 | メトリクス名 `scouts_sent` の衝突 | **ADDRESSED** | 2本目を `contract_scouts_sent`（label「契約枠の消化数」）にリネーム。プロジェクト内のメトリクス名は `scouts_sent` / `scouts_replied` / `reply_rate` / `scouts_remaining` / `contract_scouts_sent` の5つで重複なし。§4 に「メトリクス名はプロジェクト内で一意」の段落も追加 |
| M5-1 | 3文超の段落が7つ | **ADDRESSED** | 全 `<p>`（`<pre>` / `<svg>` 除外）を機械的に数え直した結果、`。` が4つ以上の段落は **0**。指摘された7段落はいずれも2段落に分割済み。`<li>` に1つだけ4文のものが残る（§7(c) の「送信主体別の率を平均しない。…」）が、規約の対象は段落なので指摘に数えない |
| M5-2 | `SAFE_DIVIDE` の説明が schema.yml と矛盾 | **ADDRESSED** | 「素の集計では発火しない（この表は 0 件の日に行を立てないので `review_count >= 1` が保証される）。効くのは後段で `dim_date` 側から 0 件月を `LEFT JOIN` で埋めたとき」に置換。同節の `accepted_range: min_value: 1` と整合 |
| M5-3 | §6 の「在籍フラグ」 | **ADDRESSED** | 「状態フラグ（`is_open`, `is_active`）」に変更 |
| M5-4 | DT#77 の引用が途中で切れている | **ADDRESSED** | "**While** you can roll up detailed data…" と "…must change **to accommodate new data**." に修正。2箇所とも原文どおり |
| M5-5 | パーティション列を使わないフィルタ | **ADDRESSED** | 月次再集約 `WHERE a.rating_date BETWEEN DATE '2026-03-01' AND DATE '2026-03-31'`、企業グループ `WHERE a.rating_date BETWEEN DATE '2026-01-01' AND DATE '2026-12-31'`、期末値・期中平均 `WHERE month_date BETWEEN DATE '2026-01-01' AND DATE '2026-03-01'`、§7(b) `WHERE f.snapshot_date BETWEEN DATE '2026-04-01' AND DATE '2026-04-30'`。指摘の2箇所を超えて4箇所に適用。`QUALIFY` の `ORDER BY` も `month_date` に統一 |
| M5-6 | §2(c) が正典サンプルと噛み合わない | **ADDRESSED**（新規欠陥 N3 を伴う） | `S003`（`AG02`→`M002`, 6/18）・`S001`（`C001`→`M001`, 6/20）・`S002`（`AG01`→`M003`, 6/25）に接地。`canon/domain.md` §5 のサンプル値と完全一致。表は 6/18 `M002` / 6/20 `M001` / 6/22 `M001` / 6/25 `M003` の4行 |
| M5-7 | 図の右パネル上段のハイフンが減算に読める | **ADDRESSED** | `sum 3.5 / 5.0 / 25.0` と `count 1 / 1 / 10` の2行に分割。左パネルも `avg 3.5 / 5.0 / 2.5` / `count は捨てる` で対称化。`check_svg.py` は **0 errors, 0 warnings**（自分でも実行） |

**14/14 が ADDRESSED。** ただし I4 / M5-6 の修正は新しい欠陥を持ち込んでおり（N2 / N3）、C2 / I2 / I3 には残件がある（N1 / N4 / N5）。

---

## 2. 再レビューの追加検証（依頼された項目）

### (1) MetricFlow YAML — 現行 spec との一貫性

`docs.getdbt.com/docs/build/latest-metrics-spec`・`/docs/build/ratio`・`/reference/metric-properties` を WebFetch して照合した。

| 要素 | 本文 | latest spec | 判定 |
|---|---|---|---|
| コンテナ | `models: - name: fct_scout_funnel` の下に `semantic_model:` | 同じ | ✅ |
| `columns:` の位置 | モデル直下（`semantic_model:` の兄弟） | 同じ（docs: "columns: Under model (sibling to semantic_model:)"） | ✅ |
| エンティティ | `columns[].entity: {type, name}` | 同じ | ✅ |
| 時間ディメンション | `columns[].granularity: day` + `dimension: {type: time}` | 同じ（`granularity` は列直下、`type_params` ではない） | ✅ |
| simple metric | モデル直下の `metrics:` に `type: simple` + `agg` + `expr` | 同じ（measures を置換） | ✅ |
| ratio metric | トップレベル `metrics:` に `numerator:` / `denominator:`（metric 名） | 同じ | ✅ |
| `non_additive_dimension` | simple metric 直下（`type_params` 配下ではない） | 同じ | ✅ |
| その子キー | `name` / **`window_choice`** | `name` / **`window_agg`** / `group_by` | ❌ → N1 |

メトリクス名の衝突: プロジェクト内5メトリクスに重複なし（I5 は解消）。legacy 記法の残骸は `window_choice` のみ。

### (2) 企業グループ再集約と `C002` の SCD2 版分裂

`GROUP BY group_company_id`（= `anc.company_id`）なので、`C002` が 2026-05-01 に `employee_size_band` を変えて2版に分裂しても年次は1行に畳まれる。子孫側は投稿時点の `company_key` で結ぶため、ブリッジを全 SCD2 版に展開する前提が本文に明記された。**この点は解消。** 残る曖昧さは N5 に記載。

### (3) `rating_date` でのパーティション絞り

`agg_company_rating_daily` は `partition_by` が `rating_date` で、これを参照するクエリ2本ともフィルタが `a.rating_date` の DATE リテラル比較。パーティションプルーニングが効く形。`fct_contract_monthly` は `month_date`、`fct_job_posting_daily` は `f.snapshot_date` で絞っており、`canon/domain.md` §4 の「`partition_by` は `<role>_date` に張る」と一貫。

### (4) §2(c) の 4 vs 3 の検算

表の4行の日次ユニークは 1 / 1 / 1 / 1 → 合計 **4**。実会員は `M001`（6/20, 6/22）・`M002`（6/18）・`M003`（6/25）の **3**。**算術は一致**。ただし窓の取り方が壊れている（N3）。

### (5) DWT 章番号

`p.meta` = ch.1–2 + ch.4、§1 h3 = ch.1–2、§3 分類行 = ch.2、§3 定期スナップショット行 = ch.4、§5 h3 = ch.2。`canon/references.md`（「04 ｜ DWT ch.1–2（加法性）; DT#77」）と整合。参照文献リストのみ未追随（N4）。

### (6) `check_svg.py`

```
$ python3 ~/.claude/skills/svg-diagram/scripts/check_svg.py docs/data_mart_modeling/html/04_additivity.html
0 errors, 0 warnings
```

HTML 骨格も再確認: `<title>加法性と派生指標 — データマート設計 04</title>`、`p.meta` あり、h2 は 1〜8 + 参照文献、`<table>` 7件すべて `.table-wrap` で包まれている、`<pre><code>` 内に生の `<` は無し。

---

## 3. 新規指摘（修正差分の範囲）

### Important

#### N1. `non_additive_dimension` の子キーが legacy のまま（C2 の残件）

該当: §4 の2本目の YAML と、その直前の段落。

```yaml
        non_additive_dimension:
          name: month_date
          window_choice: max      # 期間内の最終月の値だけを採る
```

`docs.getdbt.com/docs/build/latest-metrics-spec` の `type_params` 移行表では、latest spec の形は `non_additive_dimension: { name, window_agg, group_by }`。`window_choice` / `window_groupings` は measures 時代（legacy）の名前で、`docs/build/measures` 側にしか出てこない。ファイル冒頭に「dbt v1.12+ の spec」と書き、他の要素を全て latest に寄せた上でこの1キーだけ legacy というのは、C2 で指摘した「混成」がスケールを縮めて残っている状態。

本文の散文も同じ語を使っている:

> `non_additive_dimension` は「このメジャーはこの時間ディメンションでは集約するな」という指定で、`window_choice: max` が期末値、`min` が期首値にあたる。

修正案（YAML・散文とも）:

```yaml
        non_additive_dimension:
          name: month_date
          window_agg: max      # 期間内の最終月の値だけを採る
```

散文は「`window_agg: max` が期末値、`min` が期首値（legacy spec では `window_choice`）」とすると、旧 spec のプロジェクトを触る読者にも通じる。なお `dbt parse` での検証は執筆者も未実施（報告「未達事項」）なので、キー名は docs の移行表を根拠に直すのが確実。

#### N2. §1 の新しい但し書き「残高と同じ行に置かない」が正典と原典の両方に反する

該当: §1「CareerVoice のメジャー分類」表の、I4 で新設された行。

```html
<tr><td><code>scout_quota</code>, <code>monthly_fee</code></td><td><code>fct_contract_monthly</code></td>
  <td>加法（時間で足すと期間付与枠・期間売上）</td>
  <td>そのまま。<strong>残高（<code>scouts_remaining</code>）と同じ行に置かない</strong></td></tr>
```

`canon/domain.md` §4 の `fct_contract_monthly` は、メジャー欄が `scout_quota`, `scouts_sent`, `scouts_remaining`, `monthly_fee`, `is_active` で、**5つとも同じ行に載る定義**。この但し書きは正典の固定テーブル定義を否定している。しかも同じ記事の §2(b) の表が `scout_quota` / `scouts_sent` / `scouts_remaining` を1行に並べて見せており、記事内でも矛盾する。

原典側も逆。DWT ch.4 の在庫定期スナップショットは、加法な `quantity_sold` 系と半加法な `quantity_on_hand` を**同一行に共存させた上で「時間で足すな」を宣言する**のが定石で、それがこの回の §3「残高の扱い」行の前提になっている。加法／半加法の混在自体は禁止事項ではない（禁止なのは粒度の混在）。

修正案: この但し書きを落として「そのまま」だけにする。分類の違いを強調したいなら「同じ行に共存してよい。足す軸が違うので、**集計時に列ごとに扱いを変える**（`SUM(scout_quota)` は可、`SUM(scouts_remaining)` は不可）」に置き換える。

#### N3. §2(c) の「週」が週になっておらず、直後の HLL SQL の窓と食い違う

M5-6 の接地で日付が 6/18・6/20・6/22・6/25 になった結果、次の3つが噛み合わなくなった。

1. 本文は「6月**第4週**の正典サンプル」「**週**の実ユニーク数: 3」と書くが、2026-06-18(木) と 2026-06-25(木) は 8 日離れており、どの7日窓にも同時に入らない。ISO 週で切ると 6/15–6/21 に `M002`(6/18)・`M001`(6/20)、6/22–6/28 に `M001`(6/22)・`M003`(6/25) と分かれ、**どちらの週でも日次ユニークの合計と実ユニークは 2 vs 2 で一致してしまう**。つまり「週次に足すと壊れる」という §2(c) の主張を、示した数値が支えていない。
2. §5「ユニーク数はスケッチで持つ」の SQL は `WHERE sent_date BETWEEN DATE '2026-06-20' AND DATE '2026-06-26'` のまま。この窓は 6/18 を含まないので、同じデータに対して読者がこのクエリを回すと `weekly_unique_members` は 3 ではなく **2**（`M001`, `M003`）になる。§2(c) の「週の実ユニーク数 3」と直接矛盾する。
3. 報告の修正ラウンド1 は「HLL の窓も 6/18〜6/25 に合わせた」と書いているが、HTML は未変更（`git diff` の当該 `<pre>` に差分なし）。報告と実物が食い違う。

修正案（いずれか）:

- a. 窓を「6/18〜6/24 の7日」に取り、`S002`(6/25) を落として `M001`(6/20, 6/22)・`M002`(6/18) の3行で「日次合計 3 vs 実 2」にする。§5 の HLL も `BETWEEN DATE '2026-06-18' AND DATE '2026-06-24'` に揃える。
- b. 「週次」をやめて「6/18〜6/25 の期間（月次レポートの一部）」と言い換え、`SUM` = 4 / 実 = 3 を維持したまま §5 の HLL 窓を同じ期間に揃える。

どちらでも、§2(c) の窓と §5 の HLL の窓が**同一の日付範囲**になっていることが条件。

#### N6. `fct_contract_monthly` の primary entity が行を一意に識別しない

該当: §4 の2本目の YAML。

```yaml
models:
  - name: fct_contract_monthly
    description: "1行 = 1契約 × 1月"
    ...
    columns:
      - name: contract_id
        entity:
          type: primary
          name: contract
```

MetricFlow の `entity.type: primary` は「その列がテーブルの各行を一意に識別する」宣言。`fct_contract_monthly` の粒度は同じブロックの `description` が言うとおり **1契約 × 1月**なので、`contract_id` は月数ぶん重複する。この宣言のままだと、`contract` エンティティ経由の join で行が増幅する。

（この宣言自体は初稿の `primary_entity: contract` から引き継がれていて round 1 で新しく入ったものではないが、YAML ブロックを全面書き換えした範囲内なので挙げる。）

修正案: 一意になるのは `(contract_id, month_date)` なので、`contract_id` は `type: foreign`（`name: contract`）に落とし、primary は宣言しない（MetricFlow は primary 無しでも simple/ratio metric を作れる）。粒度を明示したいなら `semantic_model:` に `primary_entity: contract_month` を置き、モデル側で `contract_id || '-' || FORMAT_DATE('%Y%m', month_date)` の代理列を持つ。§1 の「1行 = 1契約 × 1月」という粒度宣言（01回）と YAML を一致させる、という一文を添えるとこの回の主題ともつながる。

### Minor

#### N4. 参照文献の DWT 章番号が `p.meta` と食い違う（I3 の残件）

参照文献リストの1行目が `The Data Warehouse Toolkit, 3rd ed.（2013）**ch.1, ch.4**` のまま。`p.meta` は「ch.1–2 …, ch.4 …」に直され、`canon/references.md` §「回ごとの割り当て」も「04 ｜ DWT ch.1–2（加法性）; DT#77」。リストも `ch.1–2, ch.4` にする。

#### N5. 月次再集約は依然 SCD2 版（`a.company_key`）で束ねている

I2 で企業グループ側に「足し上げの単位は企業という実体であって SCD2 の版ではない」と書いた直前の「月次へ再集約する」SQL が `GROUP BY d.year, d.month, a.company_key` のまま。`C002` を 2026年で月次に見ると 5/1 の属性変化で行が2本に割れるので、同じ落とし穴が同じ節に残っている（§2(a) の例は3月なので表面化しない）。企業グループ節の3段落を月次側にも1文で参照させるか、月次 SQL も `dim_company` の `is_current` 版へ `company_id` で結び直す形に揃えたい。

あわせて、企業グループ SQL の `AND anc.is_current` は `br_company_hierarchy` の**祖先側**の作り方が本文で未定義なため、前提次第で意味が変わる（祖先も全版に展開しているならファンアウト防止として必須、現行版だけなら no-op、時点対応でペアにしているなら古い子孫行が落ちる）。本文が子孫側の展開だけを宣言しているので、祖先側も1文で決めておくと SQL が一意に読める。

#### N7. 体裁の細かい傷（各1行）

- §7(b) の `WHERE f.snapshot_date BETWEEN DATE '2026-04-01' AND DATE '2026-04-30' ` に行末スペースが1つ残っている。
- §2(c) の「6月第4週」は、6/18 を含む時点で第3週にまたがる（N3 の修正で自然に解消する）。

---

## 4. 検算・正典照合の再確認（変更のなかった部分の追認）

初回レビューが検算した数値のうち、round 1 で変わったもの・変わらなかったものを再計算した。

| 数値 | 判定 |
|---|---|
| §2(a) 平均の平均 `11.0/3 = 3.67`、正しい平均 `33.5/12 = 2.79`、差 0.88 | 一致 |
| §2(b) `SUM(scout_quota)=600` / `SUM(scouts_sent)=160` / `SUM(scouts_remaining)=440`、上限 `200×3=600`、実在は 3月末 120 | 一致（`K001` = `C001` `premium` 枠 200/月 は正典どおり） |
| §2(c) 日次ユニーク合計 4 vs 実ユニーク 3 | 算術は一致（窓の取り方は N3） |
| §5 期中平均 `440/3 = 146.67` | 一致 |
| §7(b) 4月の `SUM(is_open) = 30` | 一致（`J001` は 2026-04-01 掲載、4月は30日） |
| §7(c) 12% / 24% の平均 18% vs 全体 `24/150 = 16%` | 一致 |

正典照合（`canon/domain.md` の更新分を含む）:

- `agg_company_rating_daily` の `rating_date`、`fct_placement` の `fee_amount = annual_income × fee_rate`（§6 の `SAFE_DIVIDE(SUM(fee_amount), SUM(annual_income))` に反映済み）、`S003`（`AG02`→`M002`, 6/18）は本文と一致。
- `dim_agency` / `dim_member_daily` は本文が触れていないため矛盾なし。
- `br_company_hierarchy` の列（`ancestor_company_key`, `descendant_company_key`, `depth`）、`dim_company` の `is_current`、`dim_scout_sender.sender_type`、`fct_review.submitted_date_key`、`fct_job_posting_daily.snapshot_date_key`、`fct_contract_monthly.month_date_key` はいずれも正典どおり。`<role>_date`（`rating_date` / `month_date` / `snapshot_date` / `sent_date`）は §4 の共通規約から導かれる形で使われている。
- 正典に無いテーブル名・列名の混入は無し（§8 の `mart_url_performance` 等は手元基盤の実物）。

---

## 総合判定

**REVISE**

- 初回指摘 14 件は **全て ADDRESSED**（not_addressed = 0）。C1 の評価順、C2 のコンテナ、I1 の `rating_date`、I2 の自然キー束ね、I3 の章番号、I5 のリネームはいずれも HTML 側で実物を確認した。
- 一方で、修正差分の中に **新規 Important 4件**:
  - N1: `non_additive_dimension` の子キーが legacy（`window_choice` → `window_agg`）。C2 の残り火
  - N2: §1 の「残高と同じ行に置かない」が正典の `fct_contract_monthly` 定義と DWT ch.4 の在庫スナップショットに反する
  - N3: §2(c) の「週」が7日窓になっておらず、§5 の HLL SQL（6/20–6/26）と数値が食い違う。報告の「HLL の窓も合わせた」は実物と不一致
  - N6: `contract_id` を primary entity と宣言しているが粒度は 1契約 × 1月
- 新規 Minor 3件（N4 参照文献の章番号、N5 月次再集約の SCD2 版束ね／ブリッジ祖先側の前提、N7 体裁）。
- 図は `check_svg.py` 0 errors, 0 warnings。HTML 骨格・エスケープ・`.table-wrap`・段落の3文制限は全て適合。

次ラウンドの修正対象は YAML 1キー（+ 散文1箇所）、§1 表の但し書き1セル、§2(c) と §5 の日付窓の統一、`entity.type` 1箇所、参照文献1行、月次 SQL への注記1文。
