# 03 ディメンションの設計 — 再レビュー（修正ラウンド1 の検証）

対象: `docs/data_mart_modeling/html/03_dimensions.html`
参照: `review/03_review.md`（Critical 1 / Important 5 / Minor 11）、`reports/03_report.md`「修正ラウンド1」、`canon/domain.md`（最新）、`canon/style.md`、`briefs/03.md`
再レビュー日: 2026-09-08 ／ 担当: 初回レビューとは別。**報告の対応表は根拠にせず、HTML と原典を直接読んで判定した。**

判定の材料: `git diff fe39f65..HEAD -- html/03_dimensions.html`（+138 / −76）で修正差分を機械抽出し、17 件の指摘それぞれについて HTML の該当行を確認。原典は SK(1998) を再取得、Techniques は PDF を `pdftotext -layout` で再取得して該当ページを確認。dbt の `where` config は公式ドキュメントを取得して確認。

---

## 1. 初回指摘 17 件の判定

| ID | 指摘の要旨 | 判定 | 確認した根拠（HTML の行 / 検証内容） |
|---|---|---|---|
| **Critical-1** | dbt モデル3本が末尾セミコロンで実行できない | **ADDRESSED** | 全 `;` を機械抽出。残っているのは 124 / 129 / 136（§2(c) の壊れた例）と 326（ロールプレイング）の4箇所のみで、いずれもモデルではない。`dim_review_attributes`(362) / `dim_member_profile_mini`(393) / `dim_member`(464) の末尾 `;` は消えている。324 行に `-- 分析クエリ（モデルではない）。` が入り、使い分けも明示された |
| **Important-1** | 正典の `dim_agency`（SCD2）が SK の結論から欠落 | **ADDRESSED** | `dim_agency` は 6 箇所に出現。§1 決定表(56)・§1 技法一覧の SK 行(68)・§1 `-1` 行の列挙(75)・§3 SK 表の第4行(171)・§5 判断表 SCD2 行(416) の**5 箇所すべてで 5 本に統一**。§1 冒頭(48) も「SCD2 の 5 ディメンションだけ」。`-1` の列挙では `dim_agency`（`fct_job_posting_daily.agency_key` = 直接掲載）と `dim_agent`（`fct_application_pipeline` / `fct_placement` の `agent_key` = スカウト経由でない）が書き分けられており、正典 §4 の記述と一致。§5 判断表に縮約ディメンションの行(417)も追加済み |
| **Important-2** | 正典の `dim_member_daily` を無視して「ミニを採る」と結論 | **ADDRESSED** | §4 比較表3行目(242)が「ECM / FDE の日次スナップショット（正典 `dim_member_daily`、05回）」になり、`require_partition_filter=true` でスキャンが1日分 ≒ 300 万行に閉じることを明記。結論(247)が「正典はどちらか一方を選ばず両方を置く」に変更され、整合条件（`dim_member_daily.member_profile_mini_key` がミニ側と一致）も追加。§7 問3 の結び(660) も `dim_member_daily` に接続。schema.yml にも該当テストを追加（ただし**そのテストが動かない → 新 Critical-1**） |
| **Important-3** | SK(1998) の理由を「7つ」と書き、結合性能を落としている | **ADDRESSED** | SK(1998) を再取得して原典と1行ずつ突合した。原典の構成は「本番系が踏む」6項目（パージ済みキー再利用／誤った再利用／キー空間の再圧縮／記述の上書き＝SCD／キー書式の一般化／買収による統合）＋未知値の符号化＋4バイト整数＋結合性能で、**HTML の 9 行表は順序まで原典どおり**。aside(159) の「計9つ」も、結合性能の原文引用（"The final reason I can think of… is one that I strongly suspect but have never proven. Replacing big, ugly natural keys… is bound to improve join performance."）の訳も正確。§4(224) の「§3 の表の9つの理由」も追随している |
| **Important-4** | §2(c) の `LEFT JOIN` 例が注釈と本文を同時に満たさない | **ADDRESSED** | クエリが3本に分割された(115–136)。2本目は `WHERE` 無しの `COUNT(*)` vs `COUNT(d.date_key)` で確かにずれ、3本目の `WHERE d.year = 2026` は `LEFT JOIN` を実質 `INNER JOIN` に戻す。自己矛盾は解消。直後の段落(138)も3文＋2文に分割済み（文言に1点だけ不正確さが残る → 新 Minor-b） |
| **Important-5** | §2(a) の「正典の形では全部消える」が §7 問3 と矛盾 | **ADDRESSED** | (96)「(i) が消え、(ii)(iii) が桁で軽くなる」に訂正。(98) で「正典の `dim_member` は SCD2 のままで `M001` は 8/1 に版が増える／会員数は `member_id` で数える／as-of 結合も残る（05回）」を明記。§5(c) 末尾(395)も「15 行への参照と `dim_member` 側の 2 行への as-of 結合に縮む」に変更され、05回への前振りが復活している |
| **Minor-1** | 4文以上の段落が19箇所 | **ADDRESSED** | `<pre>` を除いた `<p>` 70 本を機械カウント。**4文以上は 0**。DT#100 の8文 aside は3ブロック(183–186)、ミニの手順は `<ol>`(196–200) に分割されている |
| **Minor-2** | Techniques の NULL FK 引用が p.5 → p.4 | **ADDRESSED** | (176) `（Techniques, p.4）`。PDF の目次・本文とも p.4 で一致 |
| **Minor-3** | DT#100 の `BETWEEN` 二重ヒットの説明が逆 | **ADDRESSED** | (185)「ある行の `valid_to` と次の行の `valid_from` が一致すると、その境界の瞬間に `BETWEEN` が2行を返す」。原典（理由3）の向きと一致 |
| **Minor-4** | 原文 "employee" を「会員」に置換したまま引用 | **ADDRESSED** | (168)「従業員の版が増えるにつれ複数のサロゲートキーがその従業員に結び付きうるが、耐久キーは決して変わらない」＋地の文で「CareerVoice では `member_id` / `company_id` / `agency_id` が耐久キー」。引用と適用が分離された |
| **Minor-5** | `p.meta` に DT#164 が無い | **ADDRESSED** | (44) `Design Tip #5 #43 #46 #83 #100 #127 #164` |
| **Minor-6** | ロールプレイングで `hired` が別名と出力列を兼ねる | **ADDRESSED** | (317–327) テーブル別名 `applied_d` / `hired_d`、出力列 `applications` / `still_open` / `hired_count`。§2(c) 末尾(140)と §5(329) の恒等式も `hired_count` に統一 |
| **Minor-7** | §2(b) の `applied_date` 前提と `applied_at` 例示の食い違い | **ADDRESSED** | (106) 表内が `EXTRACT(YEAR FROM applied_date)` / `DATE_SUB(applied_date, INTERVAL 3 MONTH)` に統一。`DATE_SUB` の型エラーは解消 |
| **Minor-8** | 正典に無い規模を断定形で置いている | **ADDRESSED**（ただし正典側が動いたため文言が陳腐化 → **新 Important-1**） | (89) に「以下、規模は会員 300 万人・`fct_page_view` 日次 2,000 万行を仮定する（正典はデータ量を定めていない）」を追加。数値自体は現行正典 §5 の想定規模と一致 |
| **Minor-9** | ミニの行数が 15 / 16 で揺れる | **ADDRESSED** | (73) で「組合せ 15 通り。実装は `-1` の既定行を足して 16 行。以降『15 行』は組合せ数を指す」と最初に規約化。以降の 15 / 16 の出現（58, 96, 202, 241, 386, 395, 475, 531, 641, 647）はすべてこの規約の下で読める。schema.yml の description と singular test のコメントも「組合せ 15 通り ＋ -1 の既定行 = 16 行」に統一 |
| **Minor-10** | ミニを「Type 4 / 5」と併記 | **ADDRESSED** | (172)「ミニディメンション（Type 4, DT#127）」＋「本体にも現在のミニキーを Type1 で埋めると Type 5 だが、正典は採らない（時点解決の経路が2本になる）」。§1(73) の Type 4 と食い違わない |
| **Minor-11** | 「DT#100 の要件は満たす」が理由9を落としている | **ADDRESSED** | (191)「DT#100 の中心の要件（単一列・整数・ETL 時に対応付けを解決）は満たす。残る理由9…はハッシュの入力が自然キーである以上まともに当たるが、ソースが `src_careervoice` 単一である限り効かない——2つ目のソースが来たら、上の表の6行目と一緒に ✓ に変わる」 |

**ADDRESSED 17 / NOT ADDRESSED 0。** 報告の対応表に、実物と食い違う記載は無かった。

---

## 2. 修正で新たに入った箇所の検証

| 検証項目 | 結果 |
|---|---|
| SK の結論が 5 ディメンションで一貫しているか | ✅ 5 箇所すべて `dim_member` / `dim_company` / `dim_agent` / `dim_agency` / `dim_scout_sender`。「4 本」の残存 0。§6 判断基準表・§7 にも矛盾する記述なし |
| SK(1998) の理由の表が原文どおりか（原典を再取得） | ✅ 9 行の順序・内容とも原典どおり。留保つきの結合性能の引用も原文に一致。判定（1–3,5,6,8 が ✗ / 4 が ✓ / 7,9 が △）に原典の歪みなし |
| `dim_agency` の縮約行の出典（Techniques p.10） | ✅ PDF の目次「Shrunken Rollup Dimensions … 10」、本文も同ページ。"They are also necessary for business processes that naturally capture data at a higher level of granularity" が `fct_job_posting_daily`（担当者が特定できない）への適用を支える。正典 §4 の「`dim_agent` の縮約（shrunken/rollup）ディメンション（DWT ch.4）」とも整合 |
| `dim_member_daily` の位置づけが正典と矛盾しないか | ⚠️ 概ね整合（正典 §4 に `member_profile_mini_key` を含む列があり、整合条件の主張は成立）。ただし正典の備考は「FDE 方式の代替（05回）」＝**選択肢**として置いており、「どちらか一方を選ばず両方を置く」はやや強い → 新 Minor-d。また `require_partition_filter=true` の扱いが schema.yml で破綻 → 新 Critical-1 |
| `relationships` テストの `where:` 記法 | ⚠️ HTML に `relationships` への `where:` は**無い**。`where:` は `dim_date.full_date` の `not_null` にだけ付いており、`- not_null:` → `config:` → `where: "date_key <> -1"` は dbt 公式ドキュメント（`reference/resource-configs/where`「generic テストでは `config:` の下にネストする」）どおりで**正しい**。問題は逆に、`dim_member_daily` の2テストに `where:` が**必要なのに無い**こと → 新 Critical-1 |
| §2(c) の3クエリ | ✅ 1本目は `INNER JOIN` で未入社行が落ちる、2本目は `WHERE` 無しなので `COUNT(*)` ≠ `COUNT(d.date_key)` が実際に成立、3本目は `WHERE d.year = 2026` が NULL 行を落として内部結合に戻る。3本とも BigQuery で構文的に通る。文言に1点の不正確さ → 新 Minor-b |
| `dim_date` 生成 SQL の検算 | ✅ 両ブランチとも 10 列・同順・型一致（`date_key` INT64 / `full_date` DATE / `date_label` STRING / `year`〜`iso_week` INT64 / `day_of_week` STRING / `is_holiday_jp` BOOL / `fiscal_year` INT64）。祝日リストは 2026 年 18 件（`09-22` の国民の休日を含む）。`GENERATE_DATE_ARRAY(2020-01-01, 2030-12-31)` は 4,018 行で本文に行数の断定なし |
| ジャンク生成 SQL の検算 | ✅ 2 × 3 × 5 = 30、コメントも「30 行（＝組合せ数）」。`dim_page_context` の 3 × 3 × 4 × 2 = 72 も一致 |
| ミニ生成 SQL の検算 | ✅ 5 × 3 = 15、`UNION ALL` の既定行で 16。両ブランチとも 3 列・型一致（INT64 / STRING / STRING）。singular test の `<> 16` と一致し、`accepted_values` に `'不明'` も入っている |
| `dim_member` の既定行 | ✅ 両ブランチ 12 列・型一致（`member_key` INT64、`member_id` `'-1'` STRING、`registered_date` DATE、`valid_*` TIMESTAMP、`is_current` BOOL） |
| dbt モデルの末尾セミコロン | ✅ 0（`dim_date` / `dim_review_attributes` / `dim_member_profile_mini` / `dim_member` / `dim_audit` / `fct_scout` 抜粋のすべて） |
| `check_svg.py` | ✅ `0 errors, 1 warnings`（warning は `<svg>` が見つからない＝ブリーフ「図: なし」どおり） |
| HTML 体裁（差分の範囲） | ✅ `<h2>` 9本（1〜8 ＋ 参照文献）、表 12 個すべて `.table-wrap` 包み、追加された `<pre>` 内の `<` `>` はエスケープ済み（`where: "date_key &lt;&gt; -1"`、`HAVING COUNT(*) &lt;&gt; 16`）、`<title>` / `p.meta` 規約どおり |

---

## 3. 新規指摘（修正差分の範囲）

### 新 Critical-1 — 追加された `dim_member_daily` のテスト2本は `require_partition_filter=true` により必ずエラーになる

**該当:** §5 の schema.yml（HTML 514–525 行）。Important-2 の対応で追加された箇所。

```yaml
  - name: dim_member_daily
    columns:
      - name: member_profile_mini_key
        tests:
          - not_null
          - relationships:
              to: ref('dim_member_profile_mini')
              field: member_profile_mini_key
```

正典 §4 の `dim_member_daily` は `partition_by=snapshot_date` かつ **`require_partition_filter=true`**。BigQuery はこの設定のテーブルに対し、パーティション列の述語を含まないクエリを `Cannot query over table '…' without a filter that can be used for partition elimination` で拒否する（Google Cloud「パーティション分割テーブルの管理」）。dbt の generic テストは `select … from {{ model }} where <条件>` を素で発行するため、`snapshot_date` の述語が入らず**2本とも実行時エラーになる**（テストが「落ちる」のではなく「走らない」）。約 11 億行/年のテーブルなので、仮に制約が無くてもフルスキャンのコストが毎回かかる。

しかも本文は「`relationships` テストが参照整合性の実装であり、`-1` 行を作り忘れた瞬間にこれが落ちる」と締めており、**動かないテストがこの回の結論の例示になっている**のが痛い。同じ HTML 内の `dim_date.full_date` では `config: where:` を正しく使っているので、書き方の知識ではなく `require_partition_filter` の見落としである。

**修正案:** 2本とも `where` を付ける（`where` は generic テストでは `config:` 配下、公式ドキュメントどおり）。

```yaml
  - name: dim_member_daily
    columns:
      - name: member_profile_mini_key
        tests:
          - not_null:
              config:
                where: "snapshot_date = current_date('Asia/Tokyo')"
          - relationships:
              to: ref('dim_member_profile_mini')
              field: member_profile_mini_key
              config:
                where: "snapshot_date = current_date('Asia/Tokyo')"
```

コメントも1行足すと、この回の論点（`-1` 行 × テスト）とパーティション設計が繋がる。例: `# require_partition_filter=true なので、テストにも snapshot_date の述語が要る（1日分だけ検査する）`。「全期間を検査したいなら日付をループさせるのではなく、`dim_member_daily` を作る側のモデルで整合を担保する」という一言まで書ければ 05回・09回に接続する。

### 新 Important-1 — 「正典はデータ量を定めていない」が現行の正典と食い違う

**該当:** §2(a) 冒頭（HTML 89 行）。Minor-8 の対応で追加された文。

> 以下、規模は**会員 300 万人・`fct_page_view` 日次 2,000 万行を仮定する**（正典はデータ量を定めていない）。

`canon/domain.md` §5 末尾には既に**想定規模**が入っている（「会員 300 万、企業 5 万、エージェント 2 千、クチコミ累計 500 万、`page_views` 日次 2,000 万行、スカウト日次 10 万件、応募日次 5 千件」）。数値は一致しているので判断の中身に影響は無いが、**正典の状態についての記述が誤り**であり、後続の回が「規模は各回で仮定してよい」と読むと不整合の元になる。報告の「追加の正典への変更提案 10」も同様に陳腐化している（提案8・9 と併せて既に正典へ反映済み）。

**修正案:** 「以下、規模は正典 §5 の想定規模（会員 300 万人・`page_views` 日次 2,000 万行）を使う。断定ではなく前提で、この分岐は行数で決まるので題材が変われば結論も変わる。」に置き換える。報告の提案8〜10 は「反映済み」に更新する。

### 新 Minor-a — §5 判断表で `dim_agency` が2行に重複して現れる

SCD2 行(416)の対象に `dim_agency` が入り、直下の縮約行(417)の対象も `dim_agency` 単独。キーの作り方は同一（`agency_id + '|' + valid_from`）なので、読者には「6本目のディメンションがある」と読めてしまう。**修正案:** 縮約行の対象を「同上（`dim_agency`）」とし、行の主眼が「なぜ `dim_agent` と別に置くか」であることを明示する。ついでに正典 §4 は結び先を `fct_job_posting_daily` と **`fct_placement` の主軸**の2つ挙げているので、後者も足すと §1 の `-1` 行の書き分けと揃う。

### 新 Minor-b — 「3本目は…1本目と同じ結果に戻る」は厳密には成り立たない

§2(c) の段落(138)。1本目は `WHERE` が無く全年を返し、3本目は 2026 年だけを返す。同じなのは**結合の挙動**（`LEFT JOIN` が実質 `INNER JOIN` になる）であって結果集合ではない。コード側のコメント(134)は「`INNER JOIN` と同じ結果に戻る」と正しく書いており、地の文だけがずれている。**修正案:** 「3本目は絞り込みを1つ足しただけで `INNER JOIN` と同じ挙動に戻る（1本目を 2026 年で絞ったものと一致する）」。

### 新 Minor-c — 本文で `FDE` を名指ししているが `p.meta` にも参照文献にも無い

§4 比較表(242)の「**ECM / FDE の日次スナップショット**」。`FDE`（Beauchemin, *Functional Data Engineering*）は `canon/references.md` に URL 付きで載っているが、この回の `p.meta`（再解釈: dbt Kimball, ECM）にも参照文献 13 本にも入っていない。`style.md` の自己チェック「原典参照が `p.meta` と各節にある」から外れる。**修正案:** `p.meta` の再解釈欄に `FDE (Beauchemin 2018)` を足して参照文献に `https://www.ssp.sh/brain/snapshotting/` を1行加えるか、この回では触れない範囲なので単に「ECM の日次スナップショット」に戻す。正典 §4 の備考が「FDE 方式の代替」と書いている以上、前者のほうが後続の回と揃う。

### 新 Minor-d — 「正典はどちらか一方を選ばず両方を置く」は正典の書き方より一歩強い

§4(247)。正典 §4 の `dim_member_daily` の備考は「**FDE 方式の代替**（05回）」で、ミニと併存させる設計だとは書いていない（表に両方が載っているのは事実）。この回で「両方を置く」と確定させると、05回で「SCD2 vs 日次スナップショット」を比較する余地を先に潰す。**修正案:** 「正典は両方を定義しており、どちらを主経路にするかは 05回で決める。日次 2,000 万行の `fct_page_view` に毎日結合するのはミニの側で、`dim_member_daily` は会員断面の時系列分析用。」程度に留める。整合条件（`member_profile_mini_key` の一致）の指摘はそのまま活かせる。

---

## 4. 総合判定

**REVISE**

- 初回指摘: **ADDRESSED 17 / NOT ADDRESSED 0**（Critical 1・Important 5・Minor 11 のすべてが実物で確認できた。報告と実物の食い違いは無し）
- 新規: **Critical 1 / Important 1 / Minor 4**（すべて修正差分の中で生じたもの。未変更箇所の掘り起こしはしていない）

修正の質は高い。特に SK(1998) は原典を数え直したうえで9行表に再構成され、順序・留保・原文引用まで原典と一致する。§2(c) の3分割と §2(a) の「(i) は消えるが (ii)(iii) は残る」への訂正は、05回の as-of join への伏線を正しく復元している。`dim_agency` は5箇所すべてで抜けなく反映されている。

残るのは 2 点だけ。(a) Important-2 の対応で足した `dim_member_daily` のテストが、正典の `require_partition_filter=true` を見落として実行不能になっている（新 Critical-1）。(b) Minor-8 の対応で足した「正典はデータ量を定めていない」が、その後の正典更新で偽になった（新 Important-1）。どちらも数行の修正で済む。Minor 4 件は体裁・言い回しの範囲。
