# 08 コンフォームドとドリルアクロス — 再レビュー（修正ラウンド 1 後）

対象: `docs/data_mart_modeling/html/08_conformed.html`（`git show ae58454` 時点）
初回レビュー: `review/08_review.md`（Critical 2 / Important 3 / Minor 8）
執筆者の報告: `reports/08_report.md` 末尾「修正ラウンド 1」

判定の根拠はすべて HTML の現物と `git diff ae58454^ ae58454 -- html/08_conformed.html`、および実ファイル・公式ドキュメントの再確認による。報告の記述は根拠にしていない。

---

## 1. 初回指摘 13 件の判定

| ID | 重み | 指摘の要旨 | 判定 | 現物での確認 |
|---|---|---|---|---|
| C-1 | Critical | §5-4「`agg_company_entity` は MV 化した `agg_company_rating_daily` を参照できなくなる」は MV ネスト禁止の適用範囲の取り違え | **ADDRESSED** | 制約表の当該行の「影響」列が「ネスト禁止はここでは効かない — 参照側の `agg_company_entity` は `materialized='table'` であり MV ではない」に置換。結論の段が 2 段に分割され、前段が「MV は直接クエリでき…`{{ ref() }}` はそのまま通る」、後段が「MV 化を止めているのは定義 SQL の不変性」。§1 判断一覧表の MV 行も「条件を満たすが、定義が固まるまで通常のテーブル」＋根拠「定義 SQL は後から変更できない」に揃っている。ネスト禁止の原文 "You can't nest materialized views over other materialized views." は materialized-views-intro に存在することを WebFetch で再確認 |
| C-2 | Critical | §8 の `dbt_logs_analysis` の記述がリポジトリの事実と食い違う | **ADDRESSED** | §8 第 1・2 段が全面差し替え。実ファイルと突合して 5 点すべて一致: (1) `mart_url_performance.sql` は `GROUP BY url_path, date`、(2) `mart_error_analysis.sql` の `access_error_summary` は `GROUP BY date, hour, status_code` で `url_path` を捨てる、(3) `url_path` の導出は `stg_access_logs.sql` の `split(url, '?')[offset(0)]` 1 か所のみ、(4) `exposures.yml` の `error_monitoring_alert` は `ref('mart_error_analysis')` のみ・`url_performance_dashboard` は `ref('mart_url_performance_incremental')` のみ、(5) 3 本目の `weekly_performance_report` も `mart_url_performance_incremental` / `_v2` だけで、エラー系と URL 系を横断する exposure は存在しない。「試せる種」も `dim_url_path` 案が撤回され、`access_error_summary` に `url_path` を残す派生モデル案に変更。`news_pipeline` の段（`summaries` に日時列なし）は `news_pipeline/infra/bigquery.tf` で再確認 — `summaries` は `article_id`/`title`/`url`/`source`/`summary`/`tags`/`importance_score`/`relevance_score`/`scoring_version` の 9 列で TIMESTAMP なし、`published_at`/`collected_at` は `raw_articles` 側のみ |
| I-1 | Important | §7(c)「`P001` が `applications_30d` と `hires_90d` の両方に立つ」は窓が重ならず成立しない | **ADDRESSED** | 「✓ ただし固定窓なので両方には立たない。…`asof` が 7/23 以前なら `applications_30d` に、8/1〜10/30 なら `hires_90d` にしか入らない」に修正。§5-3 の定義で再検算: `applications_30d` は `applied_date >= asof - 30d` → `asof ∈ [6/23, 7/23]`、`hires_90d` は `hired_date >= asof - 90d` かつ 8/1 に入社済 → `asof ∈ [8/1, 10/30]`（8/1 + 90 日 = 10/30）。本文の日付と一致し、区間は交わらない |
| I-2 | Important | §5-2 の `group_map` は結合キーの型が違い `company_map` と差し替えられない | **ADDRESSED（ただし新規指摘 N-2 を伴う）** | `group_map` の出力が `(des.company_key, anc.company_key AS group_company_key)` に変更され、両方ともサロゲートキーになった。`INNER JOIN group_map AS g USING (company_key)` は解決する。`br_company_hierarchy` の祖先=`is_current`・子孫=全 SCD2 版・`depth = 0` の自己行は `html/06_bridges.html` の実装 SQL（383〜417 行）と一致し、`anc.is_current` が安全網である旨の 1 文も追加済み。ただし置き換え手順が `scout_monthly` を覆わない（N-2） |
| I-3 | Important | §7(a) の `apply_rate` は分子と分母の母集団が揃っていない | **ADDRESSED** | `application_monthly` に `INNER JOIN dim_channel` と `COUNTIF(ch.source_channel = 'scout_company') AS application_count_scout_company` を追加、`drilled` にも伝播、最終 SELECT が `SAFE_DIVIDE(d.application_count_scout_company, d.scout_count) AS apply_rate_scout_company` に改名。§7(a) の解答 SQL も同じ列に差し替え、定義文も「企業が送ったスカウト 1 通あたりの、`scout_company` チャネル応募数」に修正。列名 `source_channel` と値 `scout_company` は正典の `dim_channel`（自然キー `source_channel`）と `applications.source_channel` の値域に一致 |
| M-1 | Minor | §1「同じキー」行の「全ファクトが `company_key` を持つ」が不正確 | **ADDRESSED** | 「`fct_scout` / `fct_scout_funnel` を除く全ファクトが `dim_company` 由来の `company_key` を持つ。この 2 本は `dim_scout_sender`（`sender_id` が `company` なら `company_id`）経由」に修正。正典 §4 のファクト FK 一覧を全 10 本走査し、`company_key` を持たないのはこの 2 本だけであることを確認 |
| M-2 | Minor | §1「結ぶファクト」列の漏れ | **ADDRESSED** | `dim_member` 行に `fct_selection_event`、`dim_agent`/`dim_agency` 行に `fct_scout_funnel` を追記。正典の `member_key` 保持ファクト 6 本（`fct_scout`, `fct_scout_funnel`, `fct_page_view`, `fct_selection_event`, `fct_application_pipeline`, `fct_placement`）と過不足なく一致 |
| M-3 | Minor | `month_key` が DATE 型である説明が本文にない | **ADDRESSED** | §5-1 に「行ヘッダの `month_key` も `DATE_TRUNC` が返す DATE で、正典の `date_key`（INT64 `YYYYMMDD`）とは別物である（ブリーフの列名に合わせただけで、ディメンションのキーではない）」を追記 |
| M-4 | Minor | `review_count_total` の母集団が宣言されていない | **ADDRESSED** | `schema.yml` の `review_count_total` を「`fct_review` の粒度どおり submitted 全件で、審査中・却下も含む（published のみではない）」に、`avg_overall_score_90d` にも「母集団は `review_count_total` と同じ submitted 全件」を追記 |
| M-5 | Minor | §7(c) の「比率は下流で作る」と §7(b) の結論の関係が未説明 | **ADDRESSED** | 開封率・返信率のセルに「(b) と同じ条件で比率を持たせてもよいが、返信率は分母が『送信』か『開封』かで 2 通りあるため、分子分母を残して下流に選ばせる」を追記 |
| M-6 | Minor | `hires_90d` が `applied_date >= asof - 365d` で取りこぼす件が本文にない | **ADDRESSED** | `applications` CTE のコメントに「応募から入社まで 365 日を超えた案件は `hires_90d` から落ちる。許容できないなら `fct_placement`（`hired_date` がパーティション列）から取る」を追記 |
| M-7 | Minor | `company_key = -1` の扱いに言及がない | **ADDRESSED** | §5-1 に「`company_map` は `INNER JOIN` なので、`dim_company` に `-1`（未知）行が `is_current` で存在しないと、未知企業のファクト行が黙って消える。…`-1` 行は必ず現行版として置く（DT#43）」を 1 段追加 |
| M-8 | Minor | MV のパーティション制約の表現が公式より緩い | **ADDRESSED（ただし新規指摘 N-1 を伴う）** | 「ベーステーブルと**同じ列**に、時間パーティションなら同じ粒度で張る」に書き換え、`rating_date` が `fct_review.submitted_date` の別名なので条件を満たす、と対応づけた。要求どおりの方向の修正だが、添えられた英文引用が公式に存在せず、「必要がある」という強さも公式と食い違う（N-1） |

**集計: ADDRESSED 13 / NOT ADDRESSED 0**

### 図・体裁の再確認

- `python3 ~/.claude/skills/svg-diagram/scripts/check_svg.py docs/data_mart_modeling/html/08_conformed.html` → `0 errors, 1 warnings`（warning は「`<svg>` が見つからない」＝ブリーフの「図なし」指定どおり）。exit 0。
- `<title>コンフォームドとドリルアクロス — データマート設計 08</title>`、`p.meta` あり、h2 は 1〜8 ＋「参照文献」、表 12 個すべて `.table-wrap`、`<pre><code>` 6 ブロックに生の `<` / `>` なし、`<details>` 3 個（演習 a/b/c）。
- 修正で追加された `<p>` 11 個すべて 3 文以内。緩衝語なし。

---

## 2. 修正差分で新たに入った指摘

### Critical

#### N-1. §5-4 の英文引用「Materialized views must be partitioned on the same column as the base table with matching granularity」は公式ドキュメントに存在しない（かつ制約の強さを取り違えている）

該当: §5-4 制約表の最終行手前（`partition_by` の行）。

M-8 の修正で、この 1 文が英語の引用符付きで追加された。公式の該当箇所（materialized-views-create の Partitioned materialized views 節）を WebFetch と完全一致フレーズ検索の両方で確認した結果、実際の記述は次の 3 文である。

> "If the base table is partitioned, then you can partition a materialized view on the same partitioning column."
> "For time-based partitions, the granularity must match (hourly, daily, monthly, or yearly)."
> "You cannot partition a materialized view over a non-partitioned base table."

さらに同ページには次の文もある。

> "If you don't explicitly specify partitioning when you create the materialized view, then the materialized view is unpartitioned."

問題は 2 つある。

1. **引用が原文にない。** 引用符で囲んだ英文が公式ドキュメントのどのページにも存在しない。この回は Soul 1 / Soul 2 / DT#135 / ECM / Hightouch 2 の引用をすべて verbatim で揃えており、そこに 1 件だけ出典のない英文が混ざる。
2. **制約の強さが逆。** 公式は「パーティションを張る**なら**同じ列に」（`you can` / 張らなければ非パーティションの MV になる）であって、「張る**必要がある**」ではない。必須なのは (i) 張る場合は同じパーティション列であること、(ii) 時間パーティションなら粒度が一致すること、(iii) 非パーティションのベーステーブルの上に**パーティション MV は作れない**こと、の 3 点。本文の「MV の `partition_by` はベーステーブルと同じ列に、時間パーティションなら同じ粒度で張る必要がある」は (i)(ii) を混ぜて義務化しており、(iii) が落ちている。

なお `agg_company_rating_daily` の例自体は条件を満たすので、§5-4 の結論には影響しない。誤っているのは制約の記述と引用だけである。

**修正案**（引用を実在の 2 文に差し替え、義務と選択を分ける）

> MV のパーティションは任意だが、張るならベーステーブルと**同じパーティション列**でなければならない（"If the base table is partitioned, then you can partition a materialized view on the same partitioning column."）。時間パーティションでは粒度も一致が要る（"For time-based partitions, the granularity must match (hourly, daily, monthly, or yearly)."）。非パーティションのベーステーブルの上にパーティション MV は作れない。また "You can't nest materialized views over other materialized views."

（「影響」列は現状のままでよい。`rating_date` は `fct_review.submitted_date` の別名で、`fct_review` は DATE 列でパーティションされているので (i)(ii)(iii) すべてを満たす。）

### Important

#### N-2. §5-2 の置き換え手順が `scout_monthly` を覆わず、そのまま従うと粒度の混ざった `FULL OUTER JOIN` になる

該当: §5-2 の「§5-1 の各パスで `INNER JOIN company_map AS m USING (company_key)` を `INNER JOIN group_map AS g USING (company_key)` に、`m.current_company_key AS company_key` を `g.group_company_key AS company_key` に置き換えれば、行ヘッダがグループに変わる」。

I-2 の修正で手順が具体化されたのは正しい。ただし §5-1 の 3 パスのうち `scout_monthly` は `company_map` を使っていない。

```sql
scout_monthly AS (
    SELECT
        c.company_key,               -- ← company_map ではなく dim_company から直接
        ...
    FROM {{ ref('fct_scout') }} AS f
    INNER JOIN {{ ref('dim_scout_sender') }} AS s
        ON f.scout_sender_key = s.scout_sender_key
    INNER JOIN {{ ref('dim_company') }} AS c
        ON c.company_id = s.sender_id
        AND c.is_current
```

置き換え対象の文字列（`INNER JOIN company_map AS m USING (company_key)` / `m.current_company_key AS company_key`）がこの CTE には 1 つも現れないため、手順どおりに直すと `review_monthly` と `application_monthly` だけがグループ粒度になり、`scout_monthly` は企業粒度のまま残る。結果、`FULL OUTER JOIN USING (company_key, month_key)` の左右で行ヘッダのドメインが食い違い、`C003` のスカウトは `C001` のグループ行に合流せず別行として現れ、`C001` のグループ行の `scout_count` は `C001` 単体の値になる。**この回が §2(a) で「片方だけ版が違うと行が割れる／消える」と警告している症状そのもの**を、読者が手順に従うと再現してしまう。

**修正案**（`scout_monthly` の分だけ 1 行足す形で手順を閉じる）

> §5-1 の 3 パスすべてを畳む。`review_monthly` / `application_monthly` は `INNER JOIN company_map AS m USING (company_key)` を `INNER JOIN group_map AS g USING (company_key)` に、`m.current_company_key AS company_key` を `g.group_company_key AS company_key` に置き換える。`scout_monthly` は `company_map` を経由していないので、`dim_scout_sender` → `dim_company` で得た `c.company_key` に `INNER JOIN group_map AS g ON g.company_key = c.company_key` を足し、出力を `g.group_company_key AS company_key` にする（`group_map` の `company_key` は全 SCD2 版を含むので `is_current` 版の `c.company_key` も引ける）。3 パスのうち 1 本でも畳み忘れると、行ヘッダのドメインが揃わず §2(a) と同じ割れ方をする。

### Minor

#### N-3. §5-4 の「直接クエリできる」の引用が、参照文献に挙げていないページから来ている

「"You can query your materialized views directly, the same way you query a regular table or standard view."」は公式に実在するが、出典は **materialized-views-use** である（materialized-views-intro / -create には無い）。参照文献リストと `canon/references.md` の BQ MV 行は intro と create の 2 本だけなので、引用元が正典の URL リストの外にある。修正案: `references.md` の BQ MV 行に `https://cloud.google.com/bigquery/docs/materialized-views-use` を足す提案を report に書き、参照文献リストにも並記する。

#### N-4. §5-2 の出力行が互いに排他でないことに触れていない

`br_company_hierarchy` は `depth = 0` の自己行を含み、`C003` は「`C003` グループ」と「`C001` グループ」の両方の子孫として現れる。したがって `group_map` を挟んだ結果は `C001` 行と `C003` 行の両方を持ち、全行を `SUM` すると `C003` の数字が二重に入る。これはブリッジのロールアップとして正しい挙動だが、§2(b) で fan-out の二重計上を主題にしている回でこの性質が無言なのは片手落ちである。修正案: 「グループ行と単体行が同時に出る。全行の合計は取れない（`depth = 0` で自分自身も自グループの子孫だから）。レベルを選ぶなら `b.depth` を行ヘッダに足すか `is_root` で絞る」を 1 文足す。

#### N-5. `apply_rate_scout_company` の分子と分母が同じ月のコホートではない

母集団（チャネル）は揃ったが、`scout_count` は「その月に送信されたスカウト」、`application_count_scout_company` は「その月に応募された `scout_company` 応募」で、前月送信のスカウトからの応募が当月の分子に乗る。`S001`（6/20 送信）→ `P001`（6/23 応募）は同月に収まるが、月末送信では割れる。比率としては近似であり、それでよい旨か、コホート化するなら `fct_scout_funnel`（1 行 = 1 スカウトの送信→応募）を使う旨を 1 文添えると、§3 の「コンフォームドファクト＝計算式を揃える」と整合する。

#### N-6. §8 の `mart_error_analysis` の行ヘッダ列挙に `error_source` が抜けている

実物の `combined_errors` は `app_error_summary`（`GROUP BY date, hour, error_type`）と `access_error_summary`（`GROUP BY date, hour, status_code`）の `UNION ALL` で、出力の粒度は `date` × `hour` × `error_source` × `error_detail` である。本文は `date` × `hour` × `error_detail` としている。`error_detail` の値域が 2 系統で重ならないため実害は無いが、粒度宣言を主題にしたシリーズなので正確に書きたい。修正案: 「`date` × `hour` × `error_source` × `error_detail`」。

---

## 3. 再検証の記録

- `check_svg.py`: `0 errors, 1 warnings`（`<svg>` なし＝指定どおり）
- `dbt_logs_analysis/models/marts/mart_url_performance.sql` / `mart_error_analysis.sql` / `exposures.yml`、`models/staging/stg_access_logs.sql` を実読。§8 の 5 つの主張がすべて実物と一致
- `news_pipeline/infra/bigquery.tf` の `summaries` スキーマを実読。TIMESTAMP 列なし＝§8 の主張と一致
- `html/06_bridges.html` の `br_company_hierarchy` 実装 SQL を実読。祖先 `is_current` のみ・子孫全版・`depth = 0` 自己行を確認。§5-2 の 3 つの前提と一致
- BigQuery MV ドキュメント（materialized-views-intro / -create / -use）を WebFetch で再取得。ネスト禁止・定義 SQL 変更不可・直接クエリ可の 3 文は原文どおり。パーティション制約の 1 文のみ原文と不一致（N-1）
- `P001` の窓の再計算: `applications_30d` は `asof ∈ [6/23, 7/23]`、`hires_90d` は `asof ∈ [8/1, 10/30]`。本文と一致
- 正典 §4 のファクト FK 一覧を全 10 本走査。`company_key` 非保持は `fct_scout` / `fct_scout_funnel` の 2 本、`member_key` 保持は 6 本。§1 の 2 つの表と一致
- `dim_channel`（自然キー `source_channel`）と `applications.source_channel` の値域に `scout_company` があることを正典で確認。§5-1 の `dim_channel` 結合は正典内に収まる
- 本文の URL は Kimball 原典 4 本 ＋ ECM / Hightouch 2 / dbt BigQuery configurations / BQ MV intro・create。すべて `canon/references.md` 掲載か kimballgroup.com（引用文の出典としての materialized-views-use のみリスト外＝N-3）

---

## 4. 総合判定

**REVISE**

初回指摘 13 件はすべて ADDRESSED で、報告と実物の食い違いは無かった。C-1・C-2 の 2 つの Critical は根拠まで含めて正しく直っており、C-2 の差し替え後の記述は 5 点すべてリポジトリの実ファイルと一致する。I-1 の窓の算術、I-3 の母集団合わせ、M-1〜M-7 も現物で確認できた。

新規は Critical 1 / Important 1 / Minor 4。Critical の N-1 は M-8 の修正過程で入った出典のない英文引用で、制約の強さも公式と逆向き（`can` を `必要がある` にしている）。この回の価値が引用の忠実さに乗っている以上、1 件でも捏造引用が残ると全体の信頼が落ちる。Important の N-2 は I-2 の修正で手順が具体化された結果、3 パス中 1 本（`scout_monthly`）が手順から漏れていることが露見したもので、そのまま従うと本文が §2(a) で警告している粒度の割れを再現する。どちらも §5-2 / §5-4 の局所的な書き換えで閉じる。
