# 08 コンフォームドとドリルアクロス — レビュー

対象: `docs/data_mart_modeling/html/08_conformed.html` / ブリーフ `briefs/08.md` / 報告 `reports/08_report.md`

前提（オーケストレータ裁定済み・指摘対象外）: `agg_company_entity` への `dim_company`(`is_current`) 属性の平坦化と `audit_key` 非保持、`dim_scout_sender.sender_id` の意味、references への BQ MV URL 追加、`agg_member_entity` を「正典未登録の候補」として扱うこと、§2(a) を `fct_review` × `fct_application_pipeline` で書いた読み替え。

---

## 1. ブリーフ準拠表

| 節 | 必須項目 | 判定 | 該当箇所 |
|---|---|---|---|
| §1 | コンフォームドの定義 | ✅ | 「コンフォームドの 3 条件」導入段（Kimball の判定基準＝同じドメイン、部分集合可） |
| §1 | 「同じ意味・同じキー・同じ属性名」の3条件 | ✅ | 3 条件表（意味／キー／属性名 × 点検 × 破れる例） |
| §1 | CareerVoice での該当（`dim_date`, `dim_company`, `dim_member`, `dim_job_category`, `dim_agent`） | ✅ | 「CareerVoice のコンフォームドディメンション」表（`dim_agency` を `dim_agent` 行に併記）。ただし結ぶファクトの列挙に漏れあり（指摘 M-2） |
| §2(a) | SCD2 版がずれてドリルアクロスで行が消える | ✅ | §2(a)。`C002` の 2026-05-01 変化、`fct_review`（投稿時点）× `fct_application_pipeline`（応募時点）。`fct_scout` が `company_key` を持たない件も追記 |
| §2(b) | 直接 JOIN の fan-out（`C001` 3 × 5 = 15） | ✅ | §2(b) 本文＋3 行の対比表。検算一致（指摘なし） |
| §2(c) | 集約 20 本問題 / どれが正か分からない | ✅ | §2(c)「ずれる場所」表 4 行＋ `R002`・`R001` の具体例 |
| §3 | ドリルアクロス＝同粒度集約後の FULL OUTER JOIN（Soul 2） | ✅ | §3 技法表＋ Soul 2 aside（原文引用は全て verbatim 一致） |
| §3 | バスマトリクスの列がコンフォームドの正本 | ✅ | 「バスマトリクスの列が正本」段 |
| §3 | DT#135 とアジャイルの関係 | ✅ | DT#135 aside ＋ 逆側の警告の段（引用 verbatim 一致） |
| §3 | Soul 1 のドリルダウン＝属性を足すだけ | ✅ | Soul 1 aside（引用 verbatim 一致） |
| §4 | ECM を「事前に済ませたドリルアクロス＝エンティティ OBT」と位置づけ | ✅ | §4 ECM aside 2 段＋直後の段（引用 4 件すべて verbatim 一致） |
| §4 | 指標は時間窓付き（`_30d`/`_90d`）、正本は各ファクト | ✅ | §4 比較表「時間軸」「指標の正本」行 |
| §4 | Hightouch 2 | ✅ | Hightouch 2 aside（引用 3 件 verbatim 一致、3 層の名前も一致） |
| §5(a) | 3 ファクトを企業×月に集約し `FULL OUTER JOIN USING (company_key, month_key)` | ✅ | §5-1。`USING` 併合とチェーンの挙動を `bq` で実測確認済み |
| §5(b) | `agg_company_entity` の dbt モデル（窓付き集約＋現在値属性、`sum/count` から平均） | ✅ | §5-3＋`schema.yml` |
| §5(c) | BigQuery MV の選択肢と制約（結合・非加法の制限） | ⚠️ | §5-4。制約表の 5 行は公式ドキュメントどおりだが、結論を導く 1 行が誤り（指摘 C-1） |
| §6 | 「集約を持つ条件」表（クエリ頻度 × 元ファクト行数 × 再集約可能性） | ✅ | §6 前半表 6 行、3 列すべてが軸になっている |
| §6 | 「エンティティ表に指標を入れる条件」表 | ✅ | §6 後半表 7 行 |
| §7(a) | 「クチコミ平均↑ → 応募率↑」の SQL 骨格 | ⚠️ | §7(a)。SQL は BigQuery で実行確認済みだが指標の母集団が不整合（指摘 I-3） |
| §7(b) | `avg_overall_score_90d` と 04 回の原則の整合 | ✅ | §7(b)。条件表 3 行＋正本の所在 |
| §7(c) | `agg_member_entity` に何を持つか（匿名性の固定判断） | ⚠️ | §7(c)。可否表 7 行。うち 1 行が検算不一致（指摘 I-1） |
| §8 | 手元の基盤への言及（3〜5行） | ❌ | §8。リポジトリの事実と食い違う（指摘 C-2） |
| 図 | 「なし」の指定 | ✅ | SVG 0 個。`check_svg.py` = 0 errors（warning は「`<svg>` が見つからない」のみ） |
| HTML | `<title>` 形式 / `p.meta` / 8 節＋参照文献 / `&lt;` エスケープ / `.table-wrap` | ✅ | `<title>コンフォームドとドリルアクロス — データマート設計 08</title>`。h2 は 1〜8＋参照文献。`<pre>` 6 ブロックに生の `<`/`>` なし。表 12 個すべてに `.table-wrap` |
| 文体 | 1 段落 3 文以内 / 緩衝語なし / 一般論で終わらない | ✅ | 3 文超の `<p>` は 0。緩衝語（でしょう・かもしれません等）0 件 |
| 正典 | テーブル名・列名 | ✅ | 本文のテーブル名 27 種のうち正典外は `agg_member_entity`（裁定済み）、`dim_url_path` / `stg_access_logs`（§8 の手元基盤、正典対象外）のみ。列名も `dim_company` 属性・8 軸 `score_*`・`is_hired`/`is_active`/`is_open`・`<role>_date` すべて正典と一致 |

---

## 2. 指摘一覧

### Critical

#### C-1. §5-4「`agg_company_entity` は MV 化した `agg_company_rating_daily` を参照できなくなる」は事実誤認

該当: §5-4 制約表の最終行手前（「MV の `partition_by` は…MV の上に MV は作れない」行の「影響」列）と、その直後の段落。

> `agg_company_entity` は MV 化した `agg_company_rating_daily` を参照できなくなる
> 最後の行が実務上いちばん効く。`agg_company_rating_daily` を MV にすると `agg_company_entity` がそれを `ref` できなくなるため、この回では `agg_company_rating_daily` は通常のテーブル（09 回で増分）に置き、MV は「単一ファクトの集約を BI が直接叩く」ケースの選択肢として保留する。

公式ドキュメントで確認した事実は次の 2 つで、両者を混同している。

- 禁止されているのは **MV を MV の上に作ること**だけ: "You can't nest materialized views over other materialized views."（materialized-views-intro）
- MV は普通のテーブルと同じように **直接クエリできる**: "You can query your materialized views directly, the same way you query a regular table or standard view."（materialized-views-use）

`agg_company_entity` は §5-3 の `config` どおり `materialized='table'`（＝`CREATE TABLE AS SELECT`）であって MV ではない。したがって `agg_company_rating_daily` を MV 化しても `{{ ref('agg_company_rating_daily') }}` は問題なく参照できる。この節の結論（＝MV を保留する理由）が、成立しない制約の上に乗っている。しかもネスト禁止はこの設計では一切効かない — `agg_company_entity` は自己結合（`company_map`）・`CURRENT_TIMESTAMP()`・集約後の `SAFE_DIVIDE` の 3 つで**そもそも MV にできない**と §5-4 自身が別行で述べている。

**修正案**

1. 制約表の当該行の「影響」列を、実際に効く事実だけに直す:
   「`rating_date` は `fct_review` の `submitted_date` と同じ列なのでパーティション要件を満たす。ネスト禁止は `agg_company_entity` が MV でない（`materialized='table'`）以上ここでは効かない」
2. 結論の段落を、残る本物の理由で書き直す。候補は §5-4 に既にある「定義 SQL は後から変更できない」行:
   「MV 化を止めているのは定義 SQL の不変性である。`agg_company_rating_daily` の 8 軸の和はまだ動く余地があり、変更のたびに drop/create が要る。定義が固まり、09 回の `insert_overwrite` より自動維持が有利になった時点で MV に移す。参照側（`agg_company_entity`）は MV でもテーブルでも `ref` できるので、移行の障害にはならない」
3. §1 の判断一覧表「BigQuery マテリアライズド・ビュー」行の決定文（「`agg_company_rating_daily` は候補」）と、この結論の整合も取り直すこと。

#### C-2. §8 の `dbt_logs_analysis` に関する記述がリポジトリの事実と食い違う

該当: §8 第 1 段と「試せる種」の行。

> `dbt_logs_analysis` の `mart_url_performance` と `mart_error_analysis` は、どちらも `url_path` と日付を行ヘッダに持つ。…両者が `stg_access_logs` から独立に `url_path` を導出しているため、片方の正規化ルールだけが変わると「同じ名前で違うドメイン」になる
> 試せる種: `dim_url_path` を 1 本作って両マートから `ref` し、`mart_url_performance` と `mart_error_analysis` を `FULL OUTER JOIN USING (url_path, date)` で並べる analysis を書く。

実物（`dbt_logs_analysis/models/marts/mart_error_analysis.sql`）を読むと 3 点が違う。

- `mart_error_analysis` の出力列は `date`, `hour`, `error_source`, `error_detail`, `error_count`, `affected_users`, `affected_ips`, `cumulative_errors_today` の 8 列で、**`url_path` を持たない**。`access_errors` CTE では `url_path` を選んでいるが、`access_error_summary` が `GROUP BY date, hour, status_code` で落としている。したがって「どちらも `url_path` と日付を行ヘッダに持つ」は誤り。
- `url_path` は `stg_access_logs.sql` の `split(url, '?')[offset(0)] AS url_path` **1 か所でだけ**導出され、両マートはそれを継承している。「独立に導出している」も誤りで、むしろ「導出は 1 か所に閉じている＝コンフォームドの前提はできている」のが実態。
- 上記 2 点の帰結として、「試せる種」の `FULL OUTER JOIN USING (url_path, date)` は現状のモデルでは書けない。

**修正案**（この回の論点にはむしろ合う事実に差し替える）

> `dbt_logs_analysis` の `mart_url_performance` は `url_path` × `date`、`mart_error_analysis` は `date` × `hour` × `error_detail` を行ヘッダに持つ。共通する行ヘッダは `date` だけで、`mart_error_analysis` は `access_errors` CTE で読んだ `url_path` を `GROUP BY date, hour, status_code` で捨てている。この 2 本は URL でドリルアクロスできない — Soul 2 の「共通の行ヘッダが同じドメインを持つ」以前に、片方に列が無い。`url_path` の導出自体は `stg_access_logs` の `split(url, '?')[offset(0)]` 1 か所に閉じているので、条件は「揃える」ではなく「粒度を落とさない」側にある。
>
> 試せる種: `mart_error_analysis` の `access_error_summary` に `url_path` を残した `mart_error_analysis_by_url` を作り、`mart_url_performance` と `FULL OUTER JOIN USING (url_path, date)` で並べる analysis を書く。

（`news_pipeline` の段は正しい。`summaries` に TIMESTAMP 列は無く、`published_at` / `collected_at` は `raw_articles` 側にしかないことを `news_pipeline/infra/bigquery.tf` で確認した。）

### Important

#### I-1. §7(c)「`P001` が `applications_30d` と `hires_90d` の両方に立つ」は窓が重ならず成立しない

該当: §7(c) 解答例の表、「応募数（30 日）・入社（90 日）」行。

> ✓ `M001` の `P001`（6/23 応募・8/1 入社）が両方に立つ

`P001` は 2026-06-23 応募・2026-08-01 入社（正典 §5）。§5-3 の定義で検算すると:

- `applications_30d` に入る条件: `applied_date >= asof - 30d` → `asof ∈ [2026-06-23, 2026-07-23]`
- `hires_90d` に入る条件: `hired_date >= asof - 90d` かつ入社が既に起きている（`hired_date <= asof`）→ `asof ∈ [2026-08-01, 2026-10-30]`

2 つの区間は交わらない。同じ `asof` で両方に立つことはない。

**修正案**（否定するより、固定窓の性質を示す教材にできる）

> ✓ ただし固定窓なので両方には立たない。`asof` が 7/23 以前なら `applications_30d` に、8/1〜10/30 なら `hires_90d` に入る。応募から入社まで 39 日空く `P001` は、30 日窓と 90 日窓のどちらから見ても片方にしか現れない。窓幅の選択がそのままファネルの見え方を決める。

#### I-2. §5-2 の `group_map` は `company_map` と差し替えられない（結合キーの型が違う）

該当: §5-2 の SQL と直後の段。

`group_map` が返すのは `(group_company_id, member_company_id)` — どちらも**自然キー**である。一方 §5-1 の各パスは `INNER JOIN company_map USING (company_key)` でファクトの**サロゲートキー**と結んでいる。「`company_map` の代わりにこれを挟む」と書かれているが、`group_map` には `company_key` が無いため、`USING (company_key)` は解決できず、そのまま置き換えるとコンパイルが通らない。間に `dim_company` をもう 1 回挟んで `company_key → company_id` に落とす一段が省略されている。

**修正案**（子孫側を `company_key` のまま出せば、`company_map` と同じ形になって本当に差し替えられる）

```sql
group_map AS (
    -- 全 SCD2 版の company_key -> グループ親（is_current）の company_key
    SELECT DISTINCT
        des.company_key,
        anc.company_key AS group_company_key
    FROM {{ ref('br_company_hierarchy') }} AS b
    INNER JOIN {{ ref('dim_company') }} AS anc
        ON anc.company_key = b.ancestor_company_key
        AND anc.is_current
    INNER JOIN {{ ref('dim_company') }} AS des
        ON des.company_key = b.descendant_company_key
)
```

各パスの `m.current_company_key AS company_key` を `g.group_company_key AS company_key` に、`INNER JOIN company_map AS m USING (company_key)` を `INNER JOIN group_map AS g USING (company_key)` に置き換えれば行ヘッダがグループに変わる、と書けば手順が閉じる。なお 06 回の `br_company_hierarchy` は既に「祖先側 = `is_current` のみ / 子孫側 = 全 SCD2 版」で作られているので、`anc.is_current` は安全網としての再指定である旨を 1 文添えるとよい（`html/06_bridges.html` §5(b)）。

#### I-3. §7(a) の `apply_rate` は分子と分母の母集団が揃っていない

該当: §7(a) 解答例（および §5-1 最終 SELECT の `applications_per_scout`）。

分母 `scout_count` は `scout_monthly` で `s.sender_type = 'company'` に絞った**企業送信スカウトのみ**。分子 `application_count` は `fct_application_pipeline` の `COUNT(*)` で、`search` / `scout_agent` / `agent_referral` を含む**全チャネルの応募**である。エージェント経由の応募が増えるだけで「応募率」が上がる。この回自身が §3 で「コンフォームドファクト＝定義・単位・計算式を揃えること。揃えられないなら名前を変える」と書いているので、内部矛盾でもある。

**修正案**（`fct_application_pipeline` は `channel_key` を持つので 1 行で揃う）

```sql
application_monthly AS (
    SELECT
        m.current_company_key AS company_key,
        DATE_TRUNC(f.applied_date, MONTH) AS month_key,
        COUNT(*) AS application_count,
        COUNTIF(ch.source_channel = 'scout_company') AS application_count_scout_company,
        SUM(f.is_hired) AS hired_count
    FROM {{ ref('fct_application_pipeline') }} AS f
    INNER JOIN company_map AS m USING (company_key)
    INNER JOIN {{ ref('dim_channel') }} AS ch ON ch.channel_key = f.channel_key
    WHERE f.applied_date BETWEEN DATE '2026-01-01' AND DATE '2026-08-31'
    GROUP BY 1, 2
)
```

そのうえで `SAFE_DIVIDE(application_count_scout_company, scout_count)` を `apply_rate` とする。全チャネルの応募を分子に残すなら名前を `applications_all_per_company_scout` に変え、母集団が違うことを 1 文で明記する。§5-1 の列名 `applications_per_scout` も同じ扱いにすること。

### Minor

#### M-1. §1「同じキー」行の「全ファクトが `dim_company` 由来の `company_key` を持つ」が不正確

正典の FK 一覧では `fct_scout` に加えて `fct_scout_funnel` も `company_key` を持たない（`scout_sender_key` 経由）。修正案: 「`fct_scout` / `fct_scout_funnel` を除く全ファクトが `dim_company` 由来の `company_key` を持ち、この 2 本は `dim_scout_sender` 経由で企業に戻す」。

#### M-2. §1 の「結ぶファクト」列に漏れがある

- `dim_member` 行: `fct_selection_event`（正典 FK に `member_key` あり）が抜けている。
- `dim_agent` / `dim_agency` 行: `fct_scout_funnel`（`scout_sender_key` 経由）が抜けている。

修正案: 両行に追記する。この表は「どのプロセスを横に並べられるか」の可否表として読まれるので、抜けは §3 の「バスマトリクスは制約表として読む」と直接ぶつかる。

#### M-3. `month_key` が DATE 型であることが本文に書かれていない

正典は「日付キーは `date_key` INT64 `YYYYMMDD`」で、`_key` は INT64 という前提が 01〜07 回で通っている。§5-1 の `month_key` は `DATE_TRUNC(..., MONTH)` の DATE だが、その旨の説明が本文に無い（report にはある）。修正案: 「フィルタは DATE 型のパーティション列に掛ける」の段に「行ヘッダの `month_key` も `DATE_TRUNC` の DATE で、`date_key`（INT64 `YYYYMMDD`）とは別物である。ブリーフの列名に合わせているが正典のディメンションキーではない」を 1 文足す。

#### M-4. `review_count_total` の母集団が宣言されていない

§2(c) が「ずれる場所」の筆頭に「母集団（`published` のみ / `submitted` 全件）」を挙げているのに、§5-3 と `schema.yml` の `review_count_total` は「全期間のクチコミ件数」としか書いていない。上流の `agg_company_rating_daily` は `fct_review`（粒度＝投稿された 1 クチコミ）由来なので `submitted` 全件だが、これは本文から読み取れない。修正案: `schema.yml` の description を「全期間の**投稿**クチコミ件数（`fct_review` の粒度どおり `submitted` 全件。却下・審査中を含む）。加法」に変える。同じ理由で `avg_overall_score_90d` の description にも母集団を書く。

#### M-5. §7(c) の「比率は下流で作る」と §7(b) の結論の関係が説明されていない

§7(b) は「終端テーブルなら `sum/count` から作った平均を持ってよい」と結論する一方、§7(c) の開封率・返信率は「`SUM(is_opened)` と件数を別列で持ち、比率は下流で作る」としている。どちらも §6 の表を適用した結果のはずだが、判断が分かれた理由が書かれていない。修正案: (c) の当該セルに「(b) と同じ条件で比率を持たせてもよいが、開封・返信は分母が『送信』か『開封』かで 2 通りあるため、`agg_member_entity` では分子分母を残して下流に選ばせる」のように、適用した行と分岐の理由を 1 文で足す。

#### M-6. `hires_90d` が `applied_date >= asof - 365d` で取りこぼす件が本文にない

§5-3 `applications` CTE のコメントはプルーニングの意図しか書いていない。応募から入社まで 365 日を超えた案件は `hires_90d` から落ちる。修正案: コメントを「…`applied_date` 側にも広めの下限を置く。応募から入社まで 365 日を超えた案件は落ちる。許容できないなら `hired_date` を第 2 パーティション相当のクラスタ列にするか、`fct_placement`（`hired_date` がパーティション列）から取る」に変える。

#### M-7. `company_key = -1` の扱いに言及がない

§5-1 / §5-3 の各パスは `INNER JOIN company_map USING (company_key)` である。`dim_company` の `-1`（未知）行が `is_current` を立てていなければ、未知企業のファクト行は静かに落ちる。この回のテーマがまさに「行が消える」ことなので、1 文の補足がほしい。修正案: §5-1 の読み方の要点に「`-1`（未知）行も `dim_company` に `is_current` で存在させる。`company_map` は `INNER JOIN` なので、無ければ未知企業の行が黙って消える（DT#43）」を足す。

#### M-8. MV のパーティション制約の表現が公式より緩い

§5-4 の「MV の `partition_by` はベーステーブルのパーティションと粒度を合わせる必要がある」は、公式では列そのものの一致まで求めている: "Materialized views must be partitioned on the same column as the base table with matching granularity"（materialized-views-create）。修正案: 「MV の `partition_by` は**ベーステーブルと同じ列**に、時間パーティションなら同じ粒度で張る必要がある」。この例の `rating_date` は `fct_review.submitted_date` の別名なので条件を満たす、と続けると要件と充足が対応する。

---

## 3. 検証したこと（記録）

- **`FULL OUTER JOIN USING` の 3 段チェーン**: `bq query` で実測。キー列は 1 列に併合され、どの CTE にしかない行もキーが埋まる（`k = 1,2,3,4` が全て出る）。§5-1 の記述は正しい。
- **`company_map` による版ずれの解決**: `C002` の旧版キー（3 月のクチコミ）と新版キー（6 月の応募）を含むダミーで §5-1 を実行。`C002` は 2 行に割れず、3 月行に両方が乗った。SCD2 の版ずれは解消されている。
- **`agg_company_entity` の平均**: `SAFE_DIVIDE(sum_overall_score_90d, review_count_90d)` で、日次平均の平均になっていない。0 件時は `SAFE_DIVIDE(NULL, NULL) = NULL` を実測確認。04 回の原則との整合は §7(b) の説明で成立している。
- **DATE 列での絞り込み**: §5-1 の 3 パスは `submitted_date` / `sent_date` / `applied_date`、§5-3 は `snapshot_date` / `sent_date` / `applied_date` / `month_date` と、すべて DATE 型のパーティション列。`rating` CTE だけ無フィルタだが、全期間の `review_count_total` を作る以上これは正しい。
- **§7(a) の SQL**: `LAG(...) OVER w` ＋名前付き `WINDOW` 句を `bq query` で実行、動作を確認。
- **fan-out の検算**: 3 × 5 = 15。`SUM(review_count)` は 3 → 15（5 倍）、`SUM(scout_count)` は 5 → 15（3 倍）。本文の数値と一致。
- **`C001` の 4 月クチコミ**: `R002`（`M002` → `C001`、2026-04-02 投稿、却下）のみ。`published` のみ = 0 / `submitted` 全件 = 1 は正典どおり。`R001` の 3/10 投稿・3/12 公開も一致。
- **`agg_company_entity` の 7 指標**: `review_count_total`, `avg_overall_score_90d`, `open_postings`, `scouts_sent_30d`, `applications_30d`, `hires_90d`, `mrr` — 正典と過不足なく一致。§4 の「正典の 7 指標に固定」も正しい。
- **原典の引用**（すべて WebFetch で原文照合、verbatim 一致）:
  - Soul 1: "adding a row header" / "Row headers and grouping columns are the same thing" / "drilling down has nothing to do with descending a predetermined hierarchy"
  - Soul 2: "separate requests to the target fact tables followed by a simple sort/merge on the identical row headers returned from each request" / "All fact tables in a drill-across query must use conformed dimensions" / "Two dimensions are conformed if the fields that you use as common row headers have the same domain" / "too low or too high, or both"。部分集合可（brand が product の部分集合）の記述も原文にあり、「縮約ディメンションが使える」への接続は歪めていない。
  - DT#135: "the development crank starts turning faster and faster" / "identify a subset of attributes that have significance across the enterprise" / "inconsistent categorizations and labels" / "slightly different"
  - ECM: "A BI application must never issue SQL that joins two fact tables together across the fact table's foreign keys" / "simple queries (without having to use `JOIN`, `UNION ALL`, or subqueries)" / "every row is an instance of an entity" / "column overload" / "exercise restraint and limit the number of metrics"。`visits_7d` / `visits_28d` / `visits_90d` も原文の例。
  - Hightouch 2: "To get the best of both worlds…materialize Wide Tables out of it" / "25-50% faster in Redshift, Snowflake and BigQuery than Star Schema and joins" / "there is no one-size-fits-all model"。staging / core / consumption の 3 層も原文どおり。
- **BigQuery MV の制約**（materialized-views-create / -intro / -use を WebFetch）: `RIGHT`/`FULL OUTER JOIN`・自己結合の不可、`LEFT OUTER JOIN` と `UNION ALL` のプレビュー、"Aggregates in the materialized view query must be outputs. Computing, filtering, or joining based on an aggregated value is not supported."、対応集約関数（`SUM`/`COUNT`/`COUNTIF`/`AVG`/`MIN`/`MAX`/`APPROX_COUNT_DISTINCT`/`HLL_COUNT.INIT` を含む）、非決定的関数・UDF・ウィンドウ関数の不可、"You can't nest materialized views over other materialized views."、"You can't update the query for a materialized view after you create it." — **表の 6 行のうち 5 行は公式どおり**。誤っているのは C-1 の 1 か所（ネスト禁止の適用範囲）のみ。
- **dbt の MV 設定キー**: `materialized='materialized_view'`, `on_configuration_change`, `enable_refresh`, `refresh_interval_minutes`, `partition_by`, `cluster_by` はすべて dbt-bigquery の正式な config（BigQuery configurations）。「MV の SQL は変更不可、`--full-refresh` で drop/create」も dbt 側の記述と一致。
- **`check_svg.py`**: `0 errors, 1 warnings`（warning は「`<svg>` が見つからない」＝図なし指定どおり）。
- **手元の基盤**: `mart_error_analysis.sql` / `stg_access_logs.sql` / `news_pipeline/infra/bigquery.tf` を実読（C-2 の根拠）。

---

## 4. 総合判定

**REVISE**

Critical 2 / Important 3 / Minor 8。

原典・再解釈記事の引用は 15 件すべて原文と verbatim 一致で、要約にも歪みはない。ドリルアクロスの SQL は版ずれの解消まで含めて実測で正しく、fan-out・母集団・7 指標の検算もすべて一致した。修正が要るのは (1) §5-4 で MV ネスト禁止の適用範囲を取り違え、それを節の結論の根拠にしている点、(2) §8 の手元基盤の記述がリポジトリの実物と食い違う点、の 2 つが中心である。どちらも局所的な書き換えで直る。
