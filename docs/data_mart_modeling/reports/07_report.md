# 07 star か One Big Table か — 執筆レポート

ファイル: `docs/data_mart_modeling/html/07_star_vs_obt.html`

## 完了した節

| 節 | 内容 | ブリーフ要件との対応 |
|---|---|---|
| 1. この回が決めること | 「star = 正本 / OBT = 配布物」の固定判断表 + star / snowflake / OBT の 7 観点比較表（結合数・冗長・更新時の整合・BI からの使いやすさ・パーティション・クラスタ・粒度宣言） | §1 必須内容 + 中心の判断 |
| 2. どこで壊れるか | (a) `dim_company.name` の Type1 上書きが `fct_page_view` 数億行の書き換えになる（`C002` 社名変更）(b) `M001` の 6/15 属性変化を as-of で焼いた後に「現在値で見たい」が来て全期間再生成 (c) `M002`（希望職種 2 件）で `br_member_desired_job_category` の fan-out。誤 SQL と `weighting_factor` 版を並記 | §2 (a)(b)(c) |
| 3. Kimball の原則 | Manifesto の 3 利点（理解しやすさ / 性能 / 拡張への耐性）。DWT ch.1 の「正規化は DWH の敵」が行指向 RDBMS の物理特性に由来するという前置きを明記し、「3 点のうち性能の根拠だけが失効した」と整理。技法 / 定義 / 使う条件の表 | §3 |
| 4. 現代の再解釈 | 「性能のための技法は捨てる / 意味のための技法は残す」の軸表 → Fivetran 実測 → Hightouch 2 の 3 層 → BigQuery 固有 4 点（ブロードキャスト結合・プルーニング・クラスタリング・`ARRAY<STRUCT>`）+ プルーニングが外れる書き方の列挙。図をここに配置 | §4 + BigQuery 固有 |
| 5. BigQuery + dbt での実装 | (a) `fct_scout` の `partition_by`/`cluster_by` (b) `obt_scout_funnel` の全文 (c) `require_partition_filter=true` + `schema.yml` + 通る/落ちる SQL + `unique` テストが落ちる副作用と `where` 設定 (d) `INFORMATION_SCHEMA.PARTITIONS` と `bq --dry_run` 2 本比較 | §5 (a)(b)(c)(d) |
| 6. 判断基準 | 利用者 × 更新頻度 × 行数 → star のまま / star + OBT 配布 / OBT 配布 / OBT のみ / 集約配布 の 7 行。上から当てはめる読み方を明記 | §6 |
| 7. 演習 | (a) `fct_page_view` の OBT 化可否 + クラスタ列 (b) `agg_company_entity` は OBT か集約か (c) `obt_scout_funnel` の member 属性は as-of か現在値か | §7 (a)(b)(c) |
| 8. 参考: 手元の基盤 | `mart_url_performance`（star なしの OBT ＝この回の基準では正しい判断）、パーティション無しゆえ `> MAX(date)` が全表スキャン、`summaries` の Type1 上書きと `raw_articles` 分離 | style.md の参考ボックス規約（3〜5 行） |
| 参照文献 | この回で実際に読んだ 7 件のみ | — |

## 読んだ文献と引用した要点

いずれも WebFetch で実際に取得した。

1. **Manifesto（1997）** — "End users cannot understand or remember an ER model. End users cannot navigate an ER model." / "predictable, standard framework" / "evaluate arbitrary n-way joins to a fact table in a single pass" / 拡張への耐性 4 種（新ファクト・新ディメンション・新属性・粒度変更）。→ §3 で 3 利点として引用し、「性能の根拠だけが失効」の論を組んだ。
2. **dbt Discourse スレッド #225** — Ernesto の失効した前提 3 点（"Databases are slow and expensive" / "SQL language is limited" / "You can never join fact tables"）、levelworm の "Columnar database welcomes wide table and hate a lot of joins."、Josh の残るもの（"if you are slicing a bunch of facts by, say, customer, it needs to be the same, common list" / "when we add new data it doesn't break existing reports"）。→ §4 の軸の根拠。
3. **Fivetran, Star Schema vs. OBT（2022）** — TPC-DS scale 100（`store_sales`, `date_dim`, `store`, `household_demographics`, `customer_address`）。BigQuery で "the average improvement in query response time is 49%, with the denormalized table outperforming the star schema in every category"。Redshift 25〜30%、Snowflake 約 25%（単純クエリでは star が勝つことも）。ストレージ 60,250 MB vs 29,778 MB。"OBT is good for small teams and small projects that are focused on tracking a specific item" / "The star schema promotes better ELT / ETL code conceptualization and organization"。→ §4 と §6 最終行。
4. **Hightouch, Modelling Part 2** — "To get the best of both worlds, we can still utilize Kimball's Star Schema as an intermediate step after the staging layer, then materialize Wide Tables out of it." / "cloud data warehouses are different now. Storage, for instance, does not cost as much" / 立ち上げ段階のチームには複合構成を勧めない。→ §4 の層構成。
5. **BigQuery パーティション分割テーブル**（+ 同ドキュメント群の「パーティション分割テーブルのクエリ」） — 時間単位列パーティション（DATE/TIMESTAMP/DATETIME、hour/day/month/year、境界は UTC）、"filter the partitioning column using a constant expression, rather than a dynamic expression"、プルーニングが外れる形（サブクエリによる動的値、`FORMAT_DATE` / `EXTRACT(MONTH FROM ts)`、`ts + INTERVAL 1 DAY > CURRENT_TIMESTAMP()` のような算術、`OR` 連結）、クラスタリングを選ぶ条件 "Partitioning results in a small amount of data per partition (approximately less than 10 GB)" と高カーディナリティ。→ §4 の表と本文。
6. **dbt BigQuery configurations** — `require_partition_filter` と `partition_expiration_days` が `partition_by` の外側のトップレベル config であること、`partition_by` の `field`/`data_type`/`granularity`、`cluster_by` のリスト形。→ §5 の config が正しい位置になるよう確認。
7. **DWT 3rd ed. ch.1** — 「正規化は DWH の敵」の文脈（書籍。URL は正典のもの）。

## check_svg の結果

```
$ python3 ~/.claude/skills/svg-diagram/scripts/check_svg.py 07_star_vs_obt.html
0 errors, 0 warnings
```

図は 1 枚のみ（比較図型・`#dg-obt`・viewBox 800×400）。ノード 6・矢印 4・ゾーン 2・accent 1 系統（＝「実際にスキャンされるバイト量」の focal ボックスとそこへ入る矢印）で密度予算内。XML としてもパース可能なことを別途確認した。

## 正典への変更提案

1. **`obt_*` プレフィクスの追加**（要対応）
   `canon/domain.md` §4 の命名規約は marts を `dim_*` / `fct_*` / `agg_*` / `br_*` としており、`obt_*` が無い。ブリーフ 07 は `obt_scout_funnel` を必須内容として指定しているため本文では使ったが、規約側にも `obt_*`（star の下流に置く配布用非正規化テーブル）を足すべき。
2. **`obt_scout_funnel` をファクト表に追記**
   粒度: 1 行 = 1 スカウトの送信→開封→返信→応募（`fct_scout_funnel` と同粒度）。構成: `fct_scout_funnel` + `dim_scout_sender` + `dim_member`(as-of) + `dim_job_posting` + `dim_date`。パーティション `sent_date`、クラスタ `scout_sender_key`, `member_key`、`require_partition_filter=true`。
3. **`obt_page_view` の扱い**（採否は要判断）
   §2(a) の「Type1 上書きが全行書き換えになる」を実行可能な `UPDATE` 文で示すために、`fct_page_view` を企業属性込みで非正規化した表として `marts.obt_page_view` を 1 度だけ使った（コメントで正体を明示）。**これは「やってはいけない設計」の例示専用**なので、正典に足すのが適切かは判断が要る。足さない方針なら、§2(a) の 2 本目の SQL を疑似コードに落とす必要がある。
4. **OBT の列名（別名）について**
   `member_birth_year_asof` / `sender_company_industry` / `job_title` などは OBT 内でのみ使う別名で、正典のディメンション列に 1:1 対応する。OBT を正典に足すなら「as-of の列には `_asof` サフィックスを付ける」を規約化すると、§7(c) で扱った「時点の違う 2 系統が混ざる」事故を名前で防げる。
5. **中間モデル名 `int_scout_keyed`**
   §5(a) の `fct_scout` の FROM 句に使った。正典の `int_<entity>_<verb>` 規約に従っているが、中間モデルは正典に列挙が無い。列挙するなら追加候補。
6. **`INFORMATION_SCHEMA` のデータセット修飾**
   §5(d) で `marts.INFORMATION_SCHEMA.PARTITIONS` と書いた。正典は materialize 先スキーマとして `marts` を定めているが、BigQuery プロジェクト名は定義されていないので、プロジェクト修飾は省いた。プロジェクト名を正典に足すかは要判断。

## 迷った判断とその理由

- **「Fowler」の帰属**: `canon/references.md` は Dave Fowler の Coalesce 2020 講演を dbt Discourse スレッド #225 に紐づけているが、**このスレッドに Fowler・Chartio・Coalesce への言及は無い**（2 度異なるプロンプトで取得して確認）。存在しない発言を Fowler に帰属させるのは主張の歪曲なので、本文ではスレッドの実在の発言者（Ernesto / levelworm / Josh）を名指しして引用し、「性能のための技法は捨てる / 意味のための技法は残す」という軸は**この回の側の整理として明示**した。`p.meta` と参照文献も「dbt Discourse」表記にしてある。references.md の略記「Fowler」と URL の対応は見直しが要る。
- **図の accent をどこに置くか**: ブリーフは「読む列数」と「読むパーティション」の差を accent と指定している。実際に BigQuery で検算的に考えると、同じ集計（送信主体別の返信率）では **star と OBT で読む列数もパーティション数も同じ**で、差はバイト単価（OBT 側は `sender_name` が STRING で行ごとに複製される）と結合の段数に出る。図をブリーフ文言どおり「OBT の方がスキャンが少ない」と描くと誤りになるので、accent は両パネルの「実スキャン量」ボックスに置き、star 13 MB / OBT 21 MB と**OBT の方が多い**数字を出した。図の下 2 行の注記で「列指向ではスキャン量は読む列で決まる／OBT が速いのは結合とシャッフルの段が消えるから」と明示している。Fivetran の 49% が応答時間の話でバイト数の話ではないことと整合する。
- **`require_partition_filter` をどちらに掛けるか**: ブリーフ §5(c) の指定どおり OBT 側に掛け、star 側（`fct_scout` / `fct_scout_funnel`）には掛けない方針にした。正本は全期間のバックフィルと整合テストの対象になるため。副作用として `unique` / `not_null` テストが全表スキャンで落ちることを本文に書き、テストの `where` 設定で直近 7 日に限定する回避を示した。
- **`fct_scout` の materialization**: ブリーフの config 例に `materialized` の指定が無いため `table` にし、`insert_overwrite` による増分は 09 回に送った（正典の固定判断「増分の単位」も 09 回扱い）。
- **snowflake の例示**: 正典が `dim_agent` への agency 平坦化を固定判断としており、さらに今回の正典更新で `dim_agency`（縮約ディメンション）が追加されたため、`dim_agent` を雪片化の例に使うと縮約ディメンションと混同される。§1 の比較表では `dim_scout_sender` の `agency_tier` を分離した場合として書いた。
- **演習 (b) の答え**: `agg_company_entity` は粒度が 1 行 = 1 企業で「ファクト粒度の OBT」ではないため、「OBT でも集約でもなくディメンション粒度の集約」と答えた。正典の固定判断「集約は `avg_*` を持たず `sum_*` + `count`」と `agg_company_entity.avg_overall_score_90d` の矛盾は、窓固定の指標としての例外と位置づけ、08 回に送った。

## 未達事項

- BigQuery の「1 テーブルあたり最大パーティション数」を本文に入れようとしたが、公式ドキュメントの当該記述を確認できなかったため**書かなかった**（記憶で数値を出すのは避けた）。日次パーティションの上限が題材の規模で問題になる箇所は無いので、内容上の欠落は無い。
- 図中の 13 MB / 21 MB、40 万行、68 列は**題材上の想定値**で、実測ではない。列指向で OBT の方がスキャンバイトが増えうるという定性的な事実は正しいが、比率は行の構成に依存する。本文の §5(d) で「dry-run で 2 本を比べるのが OBT を作る前に必ずやる作業」として、読者が自分の数字を取る手順に落としてある。
- `ARRAY<STRUCT>` は §4 の表で 1 行触れるにとどめ、詳細を 06 回に送った（正典の割当でも BQ nested は 06 回）。参照文献に BQ nested の URL は載せていない。

---

## 修正ラウンド 1（レビュー `review/07_review.md` への対応）

### Critical

- **C1**: §2(a) の Type1 `UPDATE` から `AND is_current` を外し「`C002` の SCD2 版すべて（現時点で 2 行）」に修正。本文も「Type1 属性は `is_current` で絞らず全版を揃えて上書きする（Type 6, DT#15）」と `C002` が 2 行ある理由を書き足し、`-- star: 1 行` のコメントも実数に合わせた。
- **C2**: `dbt_logs_analysis/models/marts/mart_url_performance_incremental.sql` を実際に読み、`partition_by={'field':'date','data_type':'date'}` が**ある**こと（`cluster_by` は無い）を確認。§8 を「上流 `stg_access_logs`（`logs_database.access` の view・パーティション無し）が全スキャンされる」「増分境界 `DATE(request_timestamp) > (SELECT MAX(date) FROM {{ this }})` は §4 の『サブクエリによる動的式』そのもの」に差し替えた。
- **C3**: §5(d) の「このビュー自体のスキャンは課金されない」を削除し、「オンデマンド課金では 1 回あたり最低 10 MB が課金され、結果がキャッシュされないので回すたびに課金される」に置き換えた。

### Important

- **I1**: 裁定に従い Fowler を復帰。`p.meta` の「再解釈:」先頭に `Fowler (Coalesce 2020)` を追加、§4 の軸ボックスを Dave Fowler（Chartio）の Coalesce 2020 講演の主張（クラウド DWH ではストレージが安く、結合可能な列を全て結合した大きな非正規化テーブルを作り、その上にビューでマートを切る）として書き直し、dbt Discourse スレッドは「関連議論」の `aside` に降格。参照文献に YouTube URL 付きで Fowler を追加し、Discourse は「関連議論:」として残した。あわせて「BigQuery ではビューは実行のたびに下のテーブルをスキャンするので、OBT は `materialized='table'` で置く」の 1 段落を足し、C3 と整合させた。
- **I2**: §3 の「主張は 3 点に尽きる」を「この回で使うのは 3 点」に変え、原典が挙げる対称性・標準技法（SCD・異種製品・ファクトレス）・集約ナビゲーションを 1 文で補い、「そのどれもが意味の側の主張」と続けた。
- **I3**: §6 の表を (A)+(B) の両方で作り直した。`#` 列を追加、行を具体的→一般的に並べ替え（1 行目「単発の分析・PoC・star をまだ持っていない」、8 行目「自分・star が既にある」）、更新頻度を「月数回以下 / 日次以上 / 問わない」に整理、4 行目を「1 億以上（更新頻度を問わず）」にして穴を塞いだ。読み方の段落に「1 行目と 8 行目では問いが違う」を明記。§7(a) の引き当ては 4 行目のまま通り、§8 は 1 行目に修正した。
- **I4**: snowflake の結合数を「4 以上」→「3」に修正。表の直後に「正典の `dim_agency` はファクト直結の縮約ディメンション（DWT ch.4）で、ここで言う雪片化とは別物」の注記を追加。
- **I5**: `marts.obt_page_view` の SQL に「正典に無い。`fct_page_view` を企業属性込みで非正規化したと仮定した、この節だけの『やってはいけない設計』の例」というコメントを入れた。
- **I6**: 図の注記に 3 行目「数値は題材上の想定値（実測ではない）。自分の表の実値は §5(d) の dry-run で取る。」を追加し、`viewBox` を 400 → 424、背景 `rect` も 424 に。`<desc>` からも断定的な数値を外し「数値は題材上の想定値」を追記。accent の位置は変更していない。
- **I7**: 本文を「`unique` と `relationships` が落ちる」に限定。修正例をテスト単位からモデル単位の `config: +where:` に変え、「`not_null` はパーティション列自身への述語になるので挙動が違う可能性がある。実際に `dbt test` を回して確かめる」の 1 段落を追加した。

### Minor

- **M1**: 4 文以上の段落を 9 箇所分割（§2a・§2b・§2c・§3・§4×2・§5a・§5b・§5c・§5d・§7a×2）。残る 4 文の段落は §7(c) の `(1)…(2)…` 列挙 1 箇所のみで、これは列挙なのでそのままにした。
- **M2**: §8 を 4 段落・要点 2 つ（`dbt_logs_analysis` の上流全スキャン / `news_pipeline` の Type1 上書き）に絞った。C2 の書き直しで内容が増えたため厳密な「3〜5 行」よりわずかに長いが、`mart_url_performance` v1 の記述を 1 行に圧縮して短縮した。
- **M3**: 「2013 年以降に失効した」→「列指向 DWH が標準になった時点で失効した」に変更（年を出さない書き方）。
- **M4**: §7(a) の `config` ブロック先頭に `-- models/marts/fct_page_view.sql（OBT ではなくファクト本体の config）` を追加。
- **M5**: 「`agg_company_rating_daily` のような集約」→「`agg_company_rating_daily` と同じ形の『企業 × 日粒度の閲覧集約』」に変更し、正典に無いので追加が要る旨を明記（新設は提案していない）。
- **M6**: `<caption style="...">` を `<h3>この回で固定する判断</h3>` に置き換え、インラインスタイルを消した。骨格 CSS への `caption` 追加提案は不要になった。
- **M7**: 「ファクト <code>store_sales</code> 単体は 29,778 MB（4 つのディメンションを足した star 全体でも 29,905 MB）」に書き換え、「約 2 倍」の根拠を閉じた。

### 検証

- `python3 ~/.claude/skills/svg-diagram/scripts/check_svg.py 07_star_vs_obt.html` → `0 errors, 0 warnings`
- HTML タグの入れ子balance・`<h2>` 8 節 + 参照文献・URL 一覧（`canon/references.md` 内のみ、YouTube を追加）・テーブル名の正典照合を再実行。正典外は `obt_page_view`（I5 で仮定と明示）と `int_scout_keyed`（`int_<entity>_<verb>` 規約に沿う）の 2 件のみ。
- 正典の執筆後更新（`dim_agency` / `dim_member_daily` / `obt_*` プレフィクス採用 / 全ファクト `audit_key` / `<role>_date`）との矛盾は解消済み。§5(a) の `fct_scout` config は `sent_date`（DATE）にパーティション・`audit_key` を SELECT に含む形で、更新後の正典と一致する。
- 変更提案のうち「`obt_*` プレフィクス」「`obt_scout_funnel`」は正典に採用済みのため、上の「正典への変更提案」1・2 は解決済み。残るのは 3（`obt_page_view` の採否）・4（`_asof` サフィックス規約）・5（`int_scout_keyed`）・6（プロジェクト修飾）。
