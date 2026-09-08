# 07 star か One Big Table か — レビュー

対象: `docs/data_mart_modeling/html/07_star_vs_obt.html`
ブリーフ: `docs/data_mart_modeling/briefs/07.md` ／ 報告: `docs/data_mart_modeling/reports/07_report.md`

---

## 1. ブリーフ準拠表

| # | 必須項目 | 判定 | 該当箇所 |
|---|---|---|---|
| §1 | 3つの形（star / snowflake / OBT）の比較表 | ✅ | L64–75（7 観点） |
| §1 | 観点: 結合数 | ⚠️ | L67。snowflake セルが「4 以上」と「1 段増える」で自己矛盾（→ I4） |
| §1 | 観点: 冗長 | ✅ | L68 |
| §1 | 観点: 更新時の整合 | ✅ | L69 |
| §1 | 観点: BI からの使いやすさ | ✅ | L70 |
| §1 | 観点: パーティション・クラスタの効き方 | ✅ | L71–72（2 行に分割） |
| §2(a) | OBT だけを正本にして `dim_company.name` の Type1 更新が全行書き換え（`fct_page_view` 数億行） | ⚠️ | L79–94。題材は合っているが SQL が Type1 の意味に反する（→ C1）、`obt_page_view` が正典外（→ I5） |
| §2(b) | OBT に `dim_member` の SCD2 属性を焼いた後で「現在値で見たい」→ 再生成 | ✅ | L96–100（`M001` の 6/15 変化・8/1 入社） |
| §2(c) | star を BI に渡して Looker Studio で fan-out | ✅ | L102–125（`M002` × `br_member_desired_job_category` の誤 SQL / `weighting_factor` 版） |
| §3 | Manifesto の「理解しやすさ・性能・拡張への耐性」 | ⚠️ | L129–131。引用は原文どおりだが「3 点に尽きる」が原典の列挙（対称性・標準技法・集約ナビゲーション）を落としている（→ I2） |
| §3 | DWT ch.1「正規化は DWH の敵」は行指向 DB の時代のもの、という前置き | ✅ | L133 |
| §3 | 技法 / 定義 / 使う条件の表 | ✅ | L135–144 |
| §4 | Fowler「性能のための技法は捨てる、意味のための技法は残す」を軸に | ❌ | L148–166。Fowler が本文・`p.meta`・参照文献のどこにも無く、dbt Discourse の別人の発言に差し替わっている（→ I1） |
| §4 | Fivetran の実測（BigQuery で OBT が 49% 速い） | ✅ | L168–175。WebFetch で原文照合済み（下記 §4 検証） |
| §4 | Hightouch 2「活用側から逆算」 | ✅ | L177–181（層構成）＋ L475（逆 ETL 行の理由列） |
| §4 | BQ 固有: ブロードキャスト結合 | ✅ | L188 |
| §4 | BQ 固有: プルーニングはファクト側の日付列にしか効かない | ✅ | L189 |
| §4 | BQ 固有: クラスタリングは高カーディナリティ列 | ✅ | L190 |
| §4 | BQ 固有: `ARRAY<STRUCT>` のネスト | ✅ | L191 |
| §5(a) | `fct_scout` の `partition_by` / `cluster_by` | ✅ | L288–315。dbt docs と照合済み（キー名・入れ子位置とも正しい） |
| §5(b) | `obt_scout_funnel` を marts 下流に `materialized='table'` で置く dbt モデル | ✅ | L317–381 |
| §5(c) | `require_partition_filter=true` と BI から `sent_date` で絞る前提 | ⚠️ | L383–428。設定は正しいが、同じ `schema.yml` の `relationships` テストが落ちることに触れていない（→ I7） |
| §5(d) | `INFORMATION_SCHEMA.PARTITIONS` / dry-run の使い方 | ⚠️ | L430–464。列名・擬似パーティション名は正しいが課金の記述が誤り（→ C3） |
| §6 | 「利用者 × 更新頻度 × 行数 → star / OBT 配布 / OBT のみ」の表 | ⚠️ | L466–481。行が排他でなく、読み方が §7(a)・§8 の適用と矛盾（→ I3） |
| §7(a) | `fct_page_view` を OBT 化すべきか・クラスタ列 | ⚠️ | L485–497。判断は妥当だが §6 表の行の引き当てが誤り（→ I3） |
| §7(b) | `agg_company_entity` は OBT か集約か（→ 08 回） | ✅ | L499–512 |
| §7(c) | `obt_scout_funnel` の member 属性は as-of か現在値か | ✅ | L514–533。as-of（送信時点）を既定と明記、L379 でも「等値結合でそのまま as-of」と書いている |
| 図 | 比較図型・左 star / 右 OBT・同じ日付で切る | ✅ | L197–282 |
| 図 | accent は「読む列数」と「読むパーティション」の差 | ⚠️ | 意図的な逸脱。逸脱自体は妥当と判定（下記 §3）。ただし数値の但し書きが無い（→ I6） |
| 図 | ノード ≤9・矢印 ≤6 | ✅ | ボックス 6・矢印 4 |
| 図 | `check_svg.py` 0 errors | ✅ | 再実行して `0 errors, 0 warnings` を確認 |
| HTML | `<title>` = `<タイトル> — データマート設計 07` | ✅ | L6 |
| HTML | `p.meta` | ⚠️ | L44。形式は正しいが「再解釈」に Fowler が無い（→ I1） |
| HTML | 8節構成 | ✅ | 1–8 + 参照文献 |
| HTML | `&lt;` エスケープ | ✅ | `<pre>` 内に生の `<` 無しをスクリプトで確認 |
| HTML | `.table-wrap` | ✅ | `<table>` 7 個すべてが `.table-wrap` の中 |

---

## 2. 外部照合の結果（WebFetch）

| 検証項目 | 結果 |
|---|---|
| Fivetran「49%」 | **原文どおり**。"the average improvement in query response time is 49%, with the denormalized table outperforming the star schema in every category" |
| Fivetran Redshift / Snowflake | **原文どおり**。"25%-30%" / "~25%"。「Snowflake では単純なクエリで star が勝つこともあった」も原文に対応する記述あり（"the star schema actually does appear to out-perform the OBT model in some of the simpler queries (namely 3, 4, and 7)"） |
| Fivetran ストレージ | **原文どおり**。60,250 MB（非正規化） vs `store_sales` 29,778 MB。本文が「ファクト単体は」と限定しているので誤りではない（→ M7） |
| Fivetran 結語 2 本 | **原文どおり** |
| dbt `partition_by` / `cluster_by` / `require_partition_filter` | **正しい**。`require_partition_filter` は `partition_by` の外側のトップレベル config。HTML の書き方（L320–329）はドキュメントの例と一致 |
| `INFORMATION_SCHEMA.PARTITIONS` の列名 | **正しい**。`table_name` / `partition_id` / `total_rows` / `total_logical_bytes` / `last_modified_time` は実在。`__NULL__` / `__UNPARTITIONED__` も正しい。データセット修飾必須も正しい |
| `INFORMATION_SCHEMA` の課金 | **本文が誤り**。オンデマンドでは最低 10 MB 課金され、しかもキャッシュされない（→ C3） |
| プルーニングが外れる書き方 | **原文どおり**。サブクエリ・`FORMAT_DATE`・`EXTRACT`・`ts + INTERVAL`・`OR` の 5 例すべてが公式ドキュメントの列挙と一致 |
| クラスタ選択の「10 GB」 | **原文どおり**。"Partitioning results in a small amount of data per partition (approximately less than 10 GB)" |
| Manifesto の 3 引用 | **原文どおり**。ただし「3 点に尽きる」は原典の列挙を落としている（→ I2） |
| `obt_scout_funnel` の as-of 明示 | **明示されている**。L379（等値結合でそのまま as-of・時点解決はファクトのビルド時）、L348–350（`_asof` サフィックス）、L393（`schema.yml` の description）、L518（演習の答え） |

---

## 3. 図の accent についての判定

**逸脱は妥当。採用してよい。**

ブリーフは「読む列数」と「読むパーティション」の差だけ accent と指定しているが、列指向の BigQuery で同じ集計（送信主体別の返信率）を star と OBT で走らせたとき、**読む列数もパーティション数も同じ**になる。ブリーフの文言どおりに描くと「OBT の方が読む列が少ない／パーティションが少ない」という存在しない差を図にすることになり、直後の §4 本文（L175「同じ集計をするなら OBT の方が読むバイトは多いことすらある」）と矛盾する。執筆者が accent を「実スキャン量」に移し、star 13 MB / OBT 21 MB と OBT 側を多く描いたのは、ブリーフの上位の意図（star と OBT で何が違うかを 10 秒で掴ませる）を満たしたうえで内容の正しさを守る判断であり、report L58 の理由づけも妥当。図下の 2 行の注記（L280–281）が「速いのは結合とシャッフルの段が消えるから」と補っているので、Fivetran の 49% と読者の中で衝突もしない。

ただし数値の扱いは直す必要がある（→ I6）。

---

## 4. 指摘一覧

### Critical

**C1. §2(a) の Type1 UPDATE に `AND is_current` が付いており、Type 1 の意味に反する**

`html/07_star_vs_obt.html` L83–86:

```sql
UPDATE marts.dim_company
SET name = 'ネクスト技研ホールディングス'
WHERE company_id = 'C002' AND is_current;
```

正典 `domain.md` L101 は `dim_company` を「**Type 6 相当**: `name` は Type1、他は Type2」と定めている。Type 1 属性は履歴を持たない＝その自然キーの**全 SCD2 版**を上書きするのが定義（DT#15 / DWT ch.5 の Type 6）。`AND is_current` を付けると 2026-05-01 以前の行に旧社名が残り、`name` が実質 Type 2 になってしまう。さらに正典 L138 では `C002` は 2026-05-01 に `employee_size_band` が変わって **2 行ある**ので、本文 L81 の「`is_current` 行 1 行の `UPDATE` で終わる」と SQL コメント `-- star: 1 行` はどちらも数が合わない。

修正案:

```sql
-- star: C002 の SCD2 版すべて（この時点で 2 行）
UPDATE marts.dim_company
SET name = 'ネクスト技研ホールディングス'
WHERE company_id = 'C002';
```

本文 L81 は「star なら `dim_company` の `C002` の行（現時点で 2 行）の `UPDATE` で終わる。Type1 属性は全 SCD2 版を揃えて上書きする（Type 6, DT#15）」に差し替える。数億行との対比は 2 行でも十分に立つ。

---

**C2. §8 の `mart_url_performance_incremental` に関する記述が事実と違う**

L539:

> ただし `partition_by` も `cluster_by` も無いため、`mart_url_performance_incremental` の増分境界 `> MAX(date)` を評価するたびに全表がスキャンされる。

`dbt_logs_analysis/models/marts/mart_url_performance_incremental.sql` L1–11 は実際には次の config を持つ:

```
materialized='incremental',
unique_key=['url_path', 'date'],
on_schema_change='sync_all_columns',
partition_by={'field': 'date', 'data_type': 'date'}
```

`partition_by` は**ある**（`cluster_by` は無い）。`partition_by` が無いのは `mart_url_performance`（v1）と `mart_url_performance_v2` の方で、`dbt_project.yml` にも marts 共通の `+partition_by` は無い。この回の内容を土台にした §8 の結論が丸ごと崩れている。

しかも本当の全表スキャン要因は、この回の §4 で列挙した内容そのもの:

1. 増分の `WHERE` は上流 `{{ ref('stg_access_logs') }}`（＝`logs_database.access` の view、パーティション無し）に掛かるので、下流のマートをいくらパーティション化しても上流は毎回フルスキャンされる。
2. `DATE(request_timestamp) > (SELECT MAX(date) FROM {{ this }})` は**サブクエリによる動的式**で、L195 で挙げたプルーニングが外れる形の 1 番目に一致する。仮に上流を日付でパーティション化しても、この書き方のままでは効かない。

修正案（L539 を差し替え）:

> `mart_url_performance_incremental` は `date` に `partition_by` を持つ（`cluster_by` は無い）。それでも増分実行のたびに上流 `stg_access_logs`（`logs_database.access` の view、パーティション無し）が全スキャンされる。増分境界 `DATE(request_timestamp) > (SELECT MAX(date) FROM {{ this }})` は §4 で挙げた「サブクエリによる動的式」そのもので、上流をパーティション化してもこの形のままではプルーニングが効かない。生テーブルを日付でパーティション化し、境界を一度変数に取って定数リテラルとして渡す形に書き換え、§5(d) の dry-run を書き換え前後で 2 本比べるのが、この回をそのまま試せる最小のチュートリアルになる。

---

**C3. §5(d)「このビュー自体のスキャンは課金されない」は誤り**

L446 の 3 文目。BigQuery のドキュメント（Introduction to INFORMATION_SCHEMA）は、オンデマンド課金のプロジェクトでは INFORMATION_SCHEMA ビューへのクエリが**処理バイトが 10 MB 未満でも最低 10 MB 分課金される**こと、および**結果がキャッシュされないため同じクエリでも毎回課金される**ことを明記している（ストレージ料金は掛からない、が課金されないのはそこだけ）。

修正案:

> `INFORMATION_SCHEMA.PARTITIONS` はデータセット修飾が必須で、日次パーティションの `partition_id` は `'20260620'` の形。`__NULL__` と `__UNPARTITIONED__` の擬似パーティションを除かないと平均が歪む。オンデマンド課金では 1 回あたり最低 10 MB が課金され、結果はキャッシュされないので回すたびに課金される。

---

### Important

**I1. Fowler が消えている（ブリーフ §4 の軸の出典）**

ブリーフ §4 は「Fowler『性能のための技法は捨てる、意味のための技法は残す』を軸に」と指定し、`canon/references.md` L56 も 07 回の再解釈に Fowler を割り当てている。HTML は Fowler・Chartio・Coalesce の語を 1 度も出さず、軸を「この回の側の整理」として提示し（L155）、根拠を dbt Discourse スレッドの Ernesto / levelworm / Josh に置き換えている（L150–153）。`p.meta`（L44）と参照文献（L545–553）にも Fowler が無い。

report L57 の判断（スレッド本文に Fowler の言及が無い）は調査としては正しいが、**講演は実在する**（Dave Fowler, Chartio, Coalesce 2020）。`canon/references.md` は URL を YouTube（https://www.youtube.com/watch?v=3OcS2TMXELU）に訂正済みで、スレッドは「関連議論」に格下げされている。

修正案:

1. §4 の軸（L155）を Fowler の講演の主張として書き直す。講演の主張は「クラウド DWH ではストレージが安く、非正規化した大きなテーブルを作り、その上にビューでマートを切る」。この回の層構成（star = 正本 / OBT = 配布物）を、Fowler のこの主張と Hightouch 2 の「star を中間層に置いてワイドテーブルをマテリアライズする」の 2 本で挟む形に組み直す。
2. 現在の `aside modern`（L150–153）は「関連議論: dbt Discourse スレッド」と見出しを付けて残す。Ernesto / levelworm / Josh の引用はそのまま使ってよい（実在の発言として正しく帰属している）。
3. `p.meta` の「再解釈:」の先頭に `Fowler (Coalesce 2020)` を足す。
4. 参照文献に `Dave Fowler (Chartio), Kimball in the context of the modern data warehouse — Coalesce 2020` と YouTube URL を追加する。

---

**I2. Manifesto の「主張は 3 点に尽きる」が原典の列挙を落としている**

L130 冒頭。Manifesto は強みとして (1) predictable framework、(2) symmetrical design（すべてのディメンションが対等な入口）、(3) graceful extensibility、(4) standard approaches（SCD・異種製品・ファクトレス）を列挙し、さらに集約ナビゲーションに触れている。「3 点に尽きる」は原典より狭い。しかも §3 の結論（L133「3 点のうち性能の根拠だけが失効した」）はこの列挙の上に立っているので、分母を誤ると論の形が変わる。

修正案: L130 の書き出しを「Manifesto（1997）が挙げる強みのうち、この回で使うのは 3 点。」にし、末尾に「同記事はほかに対称性（すべてのディメンションが対等な入口）と標準技法（SCD・異種製品・ファクトレス）、集約ナビゲーションも挙げるが、どれも意味の側の主張である。」を足す。そうすると L133 の「性能の根拠だけが失効した」がむしろ強くなる。

---

**I3. §6 の判断基準表が排他でなく、読み方が §7(a)・§8 の適用と矛盾する**

L481 は「上から順に当てはめ、最初に一致した行を採る」と宣言している。この読み方だと:

- §8（L538）は `mart_url_performance` を「最後から 2 行目（単発の分析・利用者 1〜2 名・1000 万行未満）」に当てているが、利用者は本人（SQL を書く）なので**1 行目「自分（SQL を書く）／問わない／問わない → star のまま」に先に一致する**。宣言した読み方に従うと §8 の結論（OBT で正しい）が出てこない。
- §7(a)（L489）は「§6 の表の 4 行目（BI ツール × Type1 が日次以上 × 1 億以上）」を引くが、その根拠は `dim_company.name` の社名変更であって**日次以上の更新ではない**。そして「Type1 が月数回 × 1 億以上」に当たる行が表に無い（3 行目は 1 億未満で切れている）。

原因は、1 行目が「star が既にある前提で OBT を配るか」の判断なのに対し、6 行目が「star を作るか」の判断で、2 つの問いが 1 つの表に混ざっていること。

修正案（いずれか）:

- (A) 行を「具体的 → 一般的」に並べ替える。「単発の分析・PoC」を 1 行目に上げ、「自分（SQL を書く）」を最後に落とす。同時に 1 行目の利用者を「自分（SQL を書く）／star が既にある」に限定する。
- (B) 更新頻度の列を「月数回以下 / 日次以上」の 2 値に整理し、行数の条件を 3 行目「1 億未満」・4 行目「1 億以上（更新頻度を問わず）」にして穴を塞ぐ。§7(a) の引き当ては 4 行目のままで通る。

(A) と (B) は両方入れられる。あわせて §8 と §7(a) の「N 行目」の記述を新しい行番号に合わせる。

---

**I4. §1 比較表の snowflake 結合数が同じセル内で矛盾**

L67: `4 以上（dim_scout_sender の agency_tier をエージェンシー表へ分離すると 1 段増える）`。star が 2 なので「1 段増える」なら 3。

修正案: `3（dim_scout_sender の agency_tier をエージェンシー表へ分離すると 1 段増える）`。

あわせて、正典が更新されて `dim_agency`（`dim_agent` の縮約ディメンション、DWT ch.4）が追加されている（`domain.md` L106）ので、「エージェンシー表へ分離」が正典の `dim_agency` と混同されないよう 1 文足す。`dim_agency` はファクトから**直接**結ぶ縮約ディメンションであって `dim_scout_sender` にぶら下がる雪片ではない、という区別を明示する。例:

> ※ 正典の `dim_agency` は `fct_job_posting_daily` / `fct_placement` からファクト直結で使う縮約ディメンションで、ここで言う雪片化（ディメンションからさらにディメンションを引く形）とは別物。

---

**I5. `obt_page_view` が正典外**

L89 の `UPDATE marts.obt_page_view` と、その列 `company_name` / `company_id`。正典は `obt_*` プレフィクスを採用したが、列挙されているのは `obt_scout_funnel` のみ（`domain.md` L86）。report L46–47 が採否を委ねているとおり、**採用されていない**。

修正案: 表名を残すなら、正典に無い仮定のテーブルであることを SQL の中で明示する。

```sql
-- OBT を正本にした場合: 全パーティションを触る
-- （marts.obt_page_view は正典に無い。fct_page_view を企業属性込みで
--   非正規化したと仮定した、この節だけの「やってはいけない設計」の例）
UPDATE marts.obt_page_view
SET company_name = 'ネクスト技研ホールディングス'
WHERE company_id = 'C002';   -- 全期間のパーティションが対象
```

代替案として、正典に実在する `obt_scout_funnel` の `sender_name`（`dim_scout_sender` 由来）で同じ論点を出すこともできる。ただし §2(a) の主眼が「数億行」なので、`fct_page_view` を使う現在の構成の方が良い。仮定であることの明示だけで足りる。

---

**I6. 図の数値が実測でないのに図中でそう見える**

L264 `13 MB スキャン` / L277 `21 MB スキャン` / L260・L273 `40 万行` / L274 `68 列中 4 列`。report L67 が「題材上の想定値で、実測ではない」と認めているが、HTML 側にその但し書きが無い。図は本文より強く読まれるので、読者はこの比（1.6 倍）を BigQuery の一般的な性質として持ち帰る。

修正案: `<desc>` だけでなく可視要素に入れる。既存の note 2 行（L280–281）の下に 3 行目を足すか、tag 行を書き換える。ノード数は増えない。

```
<text class="note" x="32" y="386">OBT が速いのは読むバイトが減るからではなく、結合とシャッフルの段が消えるから。数値は題材上の想定値で、自分の表の値は §5(d) の dry-run で取る。</text>
```

（1 行が長くなるなら、`viewBox` の高さを 400 → 420 にして 3 行目 `y="404"` を足す。）

accent の位置そのものは変更不要（上記 §3 の判定）。

---

**I7. `require_partition_filter=true` 下で落ちるテストの説明が不完全**

L419 は「`unique` のような全表スキャンが前提の dbt テストが失敗する」「上の `schema.yml` の `unique` / `not_null` は、そのままでは通らない」と書き、L421–426 で `unique` にだけ `where` を足している。しかし同じ `schema.yml`（L400–405）には `scout_sender_key` の `relationships` テストがあり、これは `where` が無ければ**確実に**落ちる（生成 SQL に `sent_date` の述語が入らない）。修正例に無いので、読者がそのまま写すと `dbt test` が落ちる。

一方 `not_null` の生成 SQL は `where sent_date is null` でパーティション列そのものへの述語なので、`unique` / `relationships` とは挙動が違う可能性がある。実行して確かめていない以上、「`not_null` は通らない」と断定しない方がよい。

修正案:

1. 本文を「`unique` と `relationships` は `where` が無いと落ちる」に限定する。
2. 修正例に `relationships` も入れる。あるいはモデル単位でまとめる形を示す:

```yaml
  - name: obt_scout_funnel
    config:
      # このモデルのテストは全て直近パーティションに限定する
      +where: "sent_date >= DATE_SUB(CURRENT_DATE('Asia/Tokyo'), INTERVAL 7 DAY)"
```

3. 「`not_null` はパーティション列自身への述語になるので挙動が違う。実際に `dbt test` を回して確認する」の 1 文を足す。

---

### Minor

**M1. 1 段落 3 文までの違反が 9 箇所**

`style.md`「1段落は3文まで」に対して、L81(4)、L100(4)、L125(4)、L133(5)、L175(4)、L315(4)、L379(4)、L419(6)、L464(4)。特に L419 は 6 文で、内容も「副作用が 2 つある」以降を分けるのが自然。段落を割るだけで直る。

**M2. §8 の aside が規約の「3〜5 行」を超えている**

L537–541 は 3 段落・レンダリング 9 行相当。`style.md`「その回の論点に関係するものだけ 3〜5 行」。C2 の書き直しと同時に、`dbt_logs_analysis`（partition_by はあるが上流が全スキャン）と `news_pipeline`（`summaries` の Type1 上書きと `raw_articles` 分離）の 2 点に絞って 5 行に収める。

**M3. 「2013 年以降に失効した」の年が根拠不明**

L133 末尾。2013 は DWT 3rd ed. の刊行年であって、列指向 DWH で性能の根拠が失効した年ではない。「列指向 DWH が標準になった時点で」など、年を出さない書き方にする。

**M4. §7(a) の `config` ブロックの対象が読み取れない**

L491–495。「OBT 化しない」と結論した直後に config が来るので、`fct_page_view` 本体の config なのか OBT の config なのか曖昧。先頭に `-- models/marts/fct_page_view.sql` を足す。

**M5. §7(a)「配布するなら `agg_company_rating_daily` のような集約」がページビューと無関係**

L489。`agg_company_rating_daily` はクチコミ評価の日次集約（`review_count`, `sum_score_*`）で、`fct_page_view` の配布物にはならない。「`agg_company_rating_daily` と同じ形の、企業 × 日粒度の閲覧集約」と書き換える（正典に該当テーブルが無いので新設は提案せず、形だけ借りる）。

**M6. `<caption style="...">` が骨格に無い**

L52。`style.md` の骨格 CSS に `caption` の定義が無く、インラインスタイルで補っている。シリーズで統一するなら `h3` にするか、骨格側に `caption` を足す提案を report に書く。

**M7. Fivetran のストレージ比較に star 側の合計を 1 語足すと親切**

L172「非正規化表は 60,250 MB、ファクト単体は 29,778 MB」は原文どおりで誤りではない。ただし star 全体は 4 ディメンションを足して 29,905 MB なので、「star 全体でも 29,905 MB」を括弧で足すと「約 2 倍」の根拠が閉じる。

---

## 5. 正典との照合（テーブル名の全数チェック）

本文に出るテーブル名を grep して `domain.md` と突き合わせた結果:

| テーブル名 | 正典 | 備考 |
|---|---|---|
| `dim_company` / `dim_member` / `dim_scout_sender` / `dim_job_posting` / `dim_date` / `dim_agent` / `dim_member_profile_mini` / `dim_page_context` | ✅ | |
| `fct_scout` / `fct_scout_funnel` / `fct_page_view` / `fct_review` / `fct_placement` | ✅ | |
| `br_member_desired_job_category` | ✅ | `weighting_factor` の使い方も DT#142 どおり |
| `agg_company_rating_daily` / `agg_company_entity` | ✅ | 用途は M5 参照 |
| `obt_scout_funnel` | ✅ | 正典に採用済み（`domain.md` L86） |
| `obt_page_view` | ❌ | 正典外（→ I5） |
| `int_scout_keyed` | ⚠️ | 正典の `int_<entity>_<verb>` 規約に沿う。中間モデルは正典に列挙が無いので違反ではない |
| `mart_url_performance` / `mart_url_performance_incremental` / `summaries` / `raw_articles` | ✅ | §8 の手元基盤。ただし C2 の事実誤認あり |

列名はすべて正典に一致（`sent_date` / `sent_date_key` / `audit_key` / `<role>_date` の正典更新にも追随できている）。`obt_scout_funnel` の別名（`member_birth_year_asof` 等）は OBT 内の別名として妥当で、report の `_asof` サフィックス規約化の提案も筋が通る。

正典の執筆後更新との矛盾は次の 1 点のみ:

- `dim_agency`（縮約ディメンション、`domain.md` L106）の追加により、§1 の「エージェンシー表へ分離＝雪片化」が正典の `dim_agency` と混同されうる（→ I4 に併記）。
- `dim_member_daily`（`domain.md` L99）は §2(b) / §7(c) の「現在値で見たい」に対する 05 回側の選択肢だが、07 回の必須内容ではないので欠落とはしない。

---

## 6. 総合判定

**REVISE**

- Critical 3（C1 Type1 UPDATE の意味違反 / C2 §8 の事実誤認 / C3 INFORMATION_SCHEMA 課金の誤り）
- Important 7（I1 Fowler 不在 / I2 Manifesto の圧縮 / I3 判断基準表の非排他 / I4 結合数の矛盾 / I5 `obt_page_view` 正典外 / I6 図の想定値の但し書き / I7 落ちるテストの説明不足）
- Minor 7

全体としては密度・題材への落とし込み・BigQuery 固有の記述の正確さが高く、外部照合した引用（Fivetran・Manifesto・BQ ドキュメント・dbt config）は 1 つを除いてすべて原文どおりだった。図の accent 逸脱も内容の正しさを優先した妥当な判断と認める。落ちているのは、原典の帰属（Fowler）と、手元の基盤・課金・Type1 の 3 つの事実確認である。
