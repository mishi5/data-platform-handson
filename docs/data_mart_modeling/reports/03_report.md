# 03 ディメンションの設計 — 執筆報告

- 出力: `docs/data_mart_modeling/html/03_dimensions.html`
- 図: なし（ブリーフ指定どおり）。`check_svg.py` は n/a

## 完了した節

| 節 | 内容 | ブリーフの必須項目 |
|---|---|---|
| §1 この回が決めること | 決定一覧表（SK の要否 / Type0-1 のキー / 速い属性の置き場 / NULL FK）＋ 技法の一覧表（技法 / 定義 / CareerVoice での適用先） | ✓ サロゲートキー・自然キー・退化・ロールプレイング・ジャンク・ミニ・監査・`-1` 行を全て収録 |
| §2 どこで壊れるか | (a) `annual_income_band` を `dim_member` の Type2 にした場合の3つの壊れ方（行数・`COUNT(DISTINCT member_key)` の二重計上・ETL の範囲結合）(b) `dim_date` 無しで年度/営業日/クロス集計/未達が壊れる表 (c) `hired_date_key` NULL で INNER JOIN が行を落とし LEFT JOIN が `COUNT` をずらす実例 SQL | ✓ 3例すべて |
| §3 Kimball の原則 | 技法 / 定義 / 使う条件 の表（8技法）＋ SK(1998) の7理由を CareerVoice で1つずつ成否判定した表 ＋ DT#100 ＋ ミニディメンションの設計と DT#127 の但し書き | ✓ |
| §4 現代の再解釈 | dbt Kimball（3方式・`generate_surrogate_key`・「何が変わり何が残らないか」）／ ECM（ディメンションに指標／日次スナップショットとミニの行数比較表） | ✓ ECM の「ディメンションに指標を持たせてよい」を §4 に配置 |
| §5 実装 | (a) `dim_date`（`GENERATE_DATE_ARRAY` + `-1` 行 UNION ALL）(b) `dim_review_attributes` の `CROSS JOIN` (c) `dim_member_profile_mini` (d) 3案比較表（型/衝突/可読性/結合コスト + 既定行 + 落とし穴）と判断表、`dim_member` の SCD2 キー実装 (e) `dim_audit` + `invocation_id` マクロ。加えて schema.yml と singular test、ロールプレイングのクエリ | ✓ |
| §6 判断基準 | 「変化速度 × カーディナリティ → 置き場所」の8行表 ＋ 属性/メジャー/退化のタイブレーク表 ＋ DT#83 による `dim_scout_sender` への注意 | ✓ |
| §7 演習 | (a) `template_id` の退化 vs ディメンション (b) `is_unlocked` のジャンク vs メジャー (c) `M001` の 6/15 と 8/1 の変化が `dim_member` / `dim_member_profile_mini` に何を起こすか（時系列表付き） | ✓ 3問すべて `<details>` に解答 |
| §8 手元の基盤 | `mart_url_performance_incremental` の複合自然キー（この回の基準では正しい）／ `dim_date` 不在＝§2(b) の形／ `news_pipeline` の監査列不在／試せる種 | ✓ 4行 |
| 参照文献 | canon の URL のみ 13 本 | ✓ |

## 読んだ文献と引用した要点

WebFetch で実際に取得（PDF は `pdftotext` / Read で本文を確認）。

| 文献 | 引用した要点 |
|---|---|
| **SK, Surrogate Keys (1998)** | サロゲートキーの7理由: ソースキーの再利用 / キー空間の再圧縮・再割当 / Type2 / 未知値の符号化 / キー書式の変更 / 複数ソース統合 / 4バイト整数の容量削減。**§3 でこの7つを CareerVoice + BigQuery で1つずつ成否判定し、Type2 だけが残ることを示した**（これがこの回の中心の判断の根拠） |
| **DT#100 Keep Your Keys Simple** | 「SCD2 のキーを固定キー＋日付範囲にするのは明確に間違い」。9つの理由のうち (1) 複合フィールド結合の性能、(3) 日付範囲の隙間と `BETWEEN` の二重ヒット、(6) 「単純なサロゲートキーを使えばこの反論は消える。ディメンション行とファクト行の正しい対応が ETL 時に解決されるから」を引用。**「単一列の整数」が要件で「連番」は要件ではない**という読み方を §3 に明記 |
| **DT#5 Surrogate Keys For The Time Dimension** | 「時間ディメンションのキーはアプリケーション上の意味を持ってはならない。ただの整数で、計算に使えない」。`xmas99` / `1qtr99` のようなスマートキーへの批判。`Time_Type`(Normal / Not_Applicable / Hasnt_Happened_Yet / Corrupted) の4分類。**2013年 Techniques の「YYYYMMDD にしてよい」と正面から食い違うため、§5(a) で立場の変遷として書いた**（正典の `date_key` INT64 YYYYMMDD は 2013 年版に従う。DT#5 の「絞り込みは属性で、スマートキーで行わない」は今も生きている） |
| **DT#43 Nulls In The Dimensional Model** | NULL 外部キーが最悪（RI 違反・データが消える）／ NULL メジャーは残してよい（集計関数が正しく扱う）／ NULL 属性は記述文字列で置換。**§2(c) と §5(a) の `-1` 行、および「数値属性は NULL のままにする」判断の根拠** |
| **DT#46 Another Look At Degenerate Dimensions** | DD の定義。「ディメンション表がファクト表とほぼ同じ速度で伸びていたら、見落とした退化ディメンションが潜んでいる」。**§3 の表と §7 問1 の判定条件に使用** |
| **DT#83 Abstract Generic Dimensions** | 汎用ディメンションの3つの問題（意味のずれ・ラベルの曖昧化・表の肥大）。「抽象化は業務ユーザーにとっての明快さを減じ、必然的により大きな表を生む」。ロールプレイングとは別物。**§6 で `dim_scout_sender`（supertype）がこの警告の射程に入ることを明記し、判断根拠（送信主体が排他的に1つ）を書いた** |
| **DT#127 Creating and Managing Mini-Dimensions** | 「サロゲートキー列を持つ新しい表を作り、本体ディメンションの列の `SELECT DISTINCT` で埋めるだけ」。Type 5 アウトリガー。**但し書き「顧客属性がファクトイベントを伴わずに変化しうる場合、変化の完全な履歴を捉えないかもしれない」を §3 と §7 問3 に引用**（`M001` の 6/15 の変化が 6/20 の `S001` があって初めて記録に残る、という具体化） |
| **Kimball Dimensional Modeling Techniques (2013)** | 各技法の定義を原文で確認。特に (i) 日付ディメンションの YYYYMMDD 例外と「絞り込み・グループ化はスマートキーではなく属性で」、(ii) ジャンクは「直積である必要はなく実際に出現する組合せだけでよい」、(iii) NULL FK 禁止と既定行、(iv) ロールプレイングは「別のビュー」を参照すべき、(v) Type 4/5、(vi) 監査ディメンション |
| **dbt Kimball (Neo, 2023)** | 3方式（ハッシュ / 連番 / 連結）。`generate_surrogate_key` は「おそらく最も簡単な方法」で「ファクト表の SK 生成でディメンション表との結合を行う手間が省ける」。**記事のコードが `generate_surrogate_key(['stg_product.productid'])`＝自然キー1列のハッシュである点を §4 で指摘し、「ハッシュがサロゲートキーになるのは入力に版（`valid_from`）が入るときだけ」という結論に接続した** |
| **ECM (Beauchemin, 2023)** | 「Ralph Kimball の弟子」を自称しつつ「Kimball ならディメンション表に多くの指標を持ち込むことに眉をひそめるが、エンティティ中心のアプローチはむしろそうすることを推奨する」。時間窓付き指標（`7d_visits` 等）。日次フルスナップショット。**§4 で指標は `agg_company_entity` に隔離する折衷を示し、日次スナップショット vs ミニディメンションを行数で比較した** |
| dbt-utils `generate_surrogate_key` ソース | NULL は既定のプレースホルダに `coalesce` され、`-` 区切りで連結してハッシュ。BigQuery では `TO_HEX(MD5(...))` の STRING。**§5(d) の比較表の「落とし穴」行の根拠**（`-` 区切りによる境界の曖昧さ、`surrogate_key_treat_nulls_as_empty_strings` の後方互換フラグ） |

## check_svg の結果

n/a（この回に図は無い。ブリーフ「図: なし（技法一覧・置き場所は表）」に従い、SVG を1つも置いていない）。
代わりに HTML の構造検証を行った: タグ対応 0 エラー / 未閉タグ 0 / `<pre><code>` 11 ブロックすべてで `<` `>` がエスケープ済み / 12 個の表すべてが `.table-wrap` に包まれている / 本文にマークダウンのバッククォート残りが 0 / 本文の全 URL 13 本が `canon/references.md` に存在。

## 正典への変更提案

いずれも本文では正典の範囲に収まる形で書いてある（勝手な逸脱はしていない）が、明示化を提案する。

1. **`dim_date` に `date_label`（表示用文字列）を追加**。domain.md §6 は「`-1` 行（`full_date` = NULL, 表示名 `未到達`）」と表示名の存在を要求しているが、§4 の `dim_date` 属性一覧に表示名の列が無い。DT#43 / Techniques の「NULL 属性は記述文字列で置換」を満たすには文字列列が必要なので、`date_label`（通常行は `YYYY-MM-DD`、`-1` 行は `未到達`）を追加した。§4 の属性一覧への追記を提案する。
2. **`-1` は「値の約束」であって「型の約束」ではない、と §4 に明記**。`dim_job_posting.job_posting_key` は自然キー `job_posting_id`（STRING）なので、`scouts.job_posting_id` が NULL のスカウトが指す既定行は `'-1'`（STRING）になる。本文では「`-1` は値の約束。STRING キーのディメンションでは `'-1'`」と書いた。ここを揃えるために全ディメンションをハッシュ INT64 にするのは、この回の結論（SK は SCD2 だけ）と矛盾するので採らなかった。
3. **`fct_application_pipeline` の `dim_date` 参照は 7 ではなく 8**。ブリーフ 03 §1 は「`dim_date` の 7 役割」と書くが、domain.md §4 の FK 列は `applied` / `document` / `first_interview` / `final_interview` / `offer` / `accepted` / `hired` / `closed` の 8 本。本文は正典に合わせ「8 本の FK（7 マイルストーン ＋ `closed_date_key`）」と両方が読める形で書いた。ブリーフ側の数字の訂正を提案する。
4. **`dim_member_profile_mini` に `-1` の既定行が要る**。`fct_page_view.member_key` は `-1`（匿名）を取りうるので、同じ行の `member_profile_mini_key` も既定行を指す必要がある。domain.md は「5 × 3 = 15行」としか書いていないので、`-1` 行を含めて **16 行**であることを §4 の備考に足すことを提案する（本文はそう書いている）。
5. **`dim_date` の特殊行を将来 `-2` に分ける可能性**。DT#5 は `Not_Applicable` と `Hasnt_Happened_Yet` を分けていた。CareerVoice の未達は今のところ全て「まだ起きていない」なので `-1` 一本で足りるが、「応募せずに終わったスカウトの `applied_date_key`」のように「該当しない」を区別したくなったら `-2` が要る。本文にはその旨を注記した（正典は変更していない）。
6. **snapshot / staging モデル名**: `snap_members`、`stg_careervoice__scouts` を使用。どちらも domain.md §4 の命名規約（`snap_*` / `stg_careervoice__<table>`）に従っているが、個別名は正典に列挙されていない。列挙が必要なら §4 に追加を提案する。
7. **演習1のディメンション化候補にテーブル名を与えていない**。`scouts.template_id` をディメンション化する場合の名前（`dim_scout_template` 相当）は正典に無いため、本文では「テンプレート用のディメンションを新設する。ただし正典に無いのでバスマトリクスへの列追加が先」と名前を出さずに書いた。

## 迷った判断とその理由

1. **DT#5 と 2013 年 Techniques の食い違いをどう扱うか**。DT#5（2000年）は「時間ディメンションのキーはアプリケーション上の意味を持ってはならない」と明言し、正典の `date_key` INT64 `YYYYMMDD` はこれに反する。一方 Techniques（2013）は「パーティショニングを容易にするため、日付ディメンションの主キーは YYYYMMDD を表す整数のようにより意味のあるものにしてよい」と明示的に例外を認めている。**隠さず「立場が変わった」と書き、DT#5 の禁止の主旨（絞り込みは属性で行い、スマートキーで計算しない）は今も生きている、と両立させた**。正典が DT#5 を引きながら YYYYMMDD を採るのは 2013 年版に従っているためで、矛盾ではない。
2. **ジャンクを直積で作るか `SELECT DISTINCT` で作るか**。Techniques は「実際に出現する組合せだけでよい」と言い、ブリーフは `CROSS JOIN`（直積）を指定している。両立させるため、**直積を採る理由（30/72 行と小さく、キーが最初から全部確定するので増分ロードで FK 解決が失敗しない）と、切り替えの目安（直積が数千行を超えたら `SELECT DISTINCT`。属性 10 個 × 各 5 値なら 977 万行）を明記した**。
3. **ジャンク・ミニのキーをハッシュにするか連番にするか**。この回の結論は「Type0/1 は自然キーをそのまま `_key`」だが、ジャンク・ミニの自然キーは複合（組合せ）で1列にできない。`ROW_NUMBER()` は再実行で値が変わりうる（冪等でない）ので採らず、**「組合せが自然キーの場合は決定的ハッシュ」を判断表の第4行として独立させた**。同時に「自然キーのハッシュはサロゲートキーではなく自然キーの符号化にすぎない」という §4 の主張と衝突しないよう、ここでは「1列にできないから符号化する」という別の理由であることを明示した。
4. **`dim_member` の既定行を書くか**。`fct_page_view.member_key` が `-1`（匿名）を取るので必要。ただし SCD2 の `valid_from` / `valid_to` / `is_current` にも値が要る。`TIMESTAMP '1900-01-01'` 〜 `'9999-12-31'`・`is_current = TRUE` とした（どの時点の as-of join でも既定行が1行だけ引ける）。
5. **`is_unlocked`（演習2）の反論をどこまで書くか**。BigQuery では `fct_page_view` に `is_unlocked BOOL` を直接持つ方が結合なしで絞れるので、Kimball の答え（属性はディメンションへ）を無条件に採ると現代環境では説得力を欠く。**反論を明示的に立てたうえで、(1) 72 行はブロードキャストで結合コストがほぼゼロ、(2) 2値属性は選択率 50% でクラスタリングが効かない、(3) 二重保持は更新経路が2つになる、の3点で退けた**。配布用の非正規化は 07 回（OBT）に送った。
6. **§4 で ECM をどこまで採るか**。ブリーフは「ディメンションに指標を持たせてよいと拡張する点を §4 で」とだけ指定している。ECM の指標は `agg_company_entity`（08回）に隔離されるので、この回では「なぜディメンション本体に置かないか」（窓付き平均は再集約できず、ディメンションで絞ってファクトを足すという基本操作が壊れる。04回の原則）を1段落で示すに留めた。
7. **`dim_member_profile_mini` に並び順の列を足すか**。`annual_income_band` は `lt400` < `400_600` < ... の順序を持つが、文字列としては並ばない。実務では `income_band_order` のような列を足すが、正典に無い列を増やすのを避けて本文では足していない。必要なら提案として扱う。

## 未達事項

- **DWT 3rd ed. 本体（ch.3 / ch.6）は原典 PDF を参照できていない。** 書籍の目次ページ（kimballgroup.com）以外に本文の入手経路が無いため、章の内容は同じ内容を要約した公式 PDF *Kimball Dimensional Modeling Techniques*(2013) と各 Design Tip で代替した。引用は全て Techniques / Design Tips / SK 記事の原文からで、DWT の本文を記憶で引いた箇所は無い。`p.meta` と §3 の技法表では出典を Techniques と明記している。
- 図は無し（ブリーフ指定）。`check_svg.py` は実行していない（対象ファイルに SVG が無いため）。
- `-1` 行を持つべきディメンションの一覧は §1 の技法表に列挙したが、ファクトごとの「どの FK が `-1` を取りうるか」の網羅表は密度の都合で入れていない（02 回・06 回と重複するため）。

---

## 修正ラウンド1（レビュー `review/03_review.md` への対応）

| ID | 対応 |
|---|---|
| Critical-1 | `dim_review_attributes` / `dim_member_profile_mini` / `dim_member` の3モデルの末尾セミコロンを削除（`create or replace table … as ( … )` の内側で文が終わり BigQuery が構文エラーになるため）。§5 のロールプレイングクエリ先頭に `-- 分析クエリ（モデルではない）` を追記して、セミコロン有無の使い分けを明示 |
| Important-1 | SK の結論を SCD2 の **5 本**（`dim_member` / `dim_company` / `dim_agent` / **`dim_agency`** / `dim_scout_sender`）へ統一。§1「この回の決定」表・§1 技法一覧のサロゲートキー行・§3 SK 表の SCD 行・§5 判断表の4箇所を修正。§1 の `-1` 行の列挙に `dim_agency`（`fct_job_posting_daily.agency_key` = 直接掲載）を追加し、`dim_agent` 側を「`fct_application_pipeline` / `fct_placement` の `agent_key` = スカウト経由でない」に書き分け。§5 判断表に縮約ディメンションの行（`dim_agency` は `dim_agent` の shrunken rollup, Techniques p.10 / DWT ch.4。同じ SK 規則で作る）を1行追加 |
| Important-2 | §4 の3手法比較表の3行目を「ECM / FDE の日次スナップショット（正典 `dim_member_daily`、05回）」に改め、行数欄に `partition_by=snapshot_date` ＋ `require_partition_filter=true` で1クエリのスキャンが1日分（≒300 万行）に閉じることを明記。結論を排他形（「ミニを採る」）から併存形（「正典はどちらか一方を選ばず両方を置く」＋整合条件は `dim_member_daily.member_profile_mini_key` がミニ側と一致すること）へ変更。§5 の schema.yml に `dim_member_daily.member_profile_mini_key` の `relationships` テストを追加。§7 問3 の結びも「ミニでは足りない → `dim_member_daily` かファクトレスファクト表（05回）」に修正 |
| Important-3 | SK(1998) を再取得して数え直し、`aside kimball` を「本番系がキーを踏む6通り ＋ 未知値の符号化 ＋ 4バイト整数の容量削減 ＋ 結合性能 の計9つ」に訂正。結合性能の理由（「私が思いつく最後の理由は、強く疑ってはいるが証明したことのないものだ」）を原文引用で追加。成否判定の表を7行→**9行**に拡張し、9行目「結合性能」を **△ 測ってから決める** と判定。§4 の「§3 の表の7理由」も「9つの理由」に修正 |
| Important-4 | §2(c) の壊れた SQL を **3本**に分割（1: INNER JOIN が行を落とす／2: LEFT JOIN で `COUNT(*)` と `COUNT(d.date_key)` がずれる（`WHERE` なし）／3: 絞り込みを1つ足すと1本目に戻る）。直後の段落も3文＋2文に書き直し、`WHERE` 付きクエリで「a と b がずれる」と主張していた自己矛盾を解消 |
| Important-5 | §2(a) の締めを「(i) が消え、(ii)(iii) が桁で軽くなる」に訂正し、「正典の `dim_member` は SCD2 のままなので `M001` は 8/1 に版が増え、会員数は `member_id` で数える必要が残り、as-of 結合も残る（05回）」を段落追加。§5(c) の「§2(a) の 3,000 万行への範囲結合と比べてほしい」も「15 行への参照と `dim_member` 側 2 行への as-of 結合に縮む」に修正 |
| Minor-1 | 4文以上の段落 19 箇所を全て 3 文以内に分割（DT#100 の8文 aside を「原典の主張」と「この題材への当てはめ」の3ブロックに、§4 の7文/6文、§3 のミニ手順（`<ol>` 化）、§1・§5(b)・§6・§7 問2/問3 など）。機械カウントで残 0 |
| Minor-2 | `（Techniques, p.5）` → `（Techniques, p.4）`（目次・本文とも p.4 であることを `pdftotext` で確認） |
| Minor-3 | 「開始日と次の行の終了日が一致すると」→「ある行の `valid_to` と次の行の `valid_from` が一致すると、その境界の瞬間に `BETWEEN` が2行を返す」に訂正（DT#100 理由3 の原文を `pdftotext` で確認） |
| Minor-4 | 耐久キーの引用を原文どおり「従業員の版が増えるにつれ複数のサロゲートキーがその従業員に結び付きうるが、耐久キーは決して変わらない」に戻し、「CareerVoice では `member_id` / `company_id` / `agency_id` が耐久キーにあたる」を地の文で接続 |
| Minor-5 | `p.meta` の Design Tip 列に `#164` を追加 |
| Minor-6 | ロールプレイングのクエリで別名衝突を解消（テーブル別名 `applied_d` / `hired_d`、出力列 `applications` / `still_open` / `hired_count`）。§2(c)・§5 の恒等式の記述も `hired_count` に統一 |
| Minor-7 | §2(b) の表内の式を `applied_at`（TIMESTAMP）→ `applied_date`（DATE）に統一。`DATE_SUB` は DATE 専用なので型エラーになる例示を排除 |
| Minor-8 | §2(a) の初出に「以下、規模は会員 300 万人・`fct_page_view` 日次 2,000 万行を仮定する（正典はデータ量を定めていない）」を追加（下の提案8も参照） |
| Minor-9 | 「15 行」を**組合せ数**の意味に統一。§1 技法一覧で「組合せ 15 通り。実装は `-1` の既定行を足して 16 行。以降『15 行』は組合せ数を指す」と最初に断り、§1 決定表・§3・§4 比較表・§5(c) の SQL コメント・§7 問3 の表現を揃えた。schema.yml の description と singular test のコメントも「組合せ 15 通り ＋ -1 の既定行」に統一 |
| Minor-10 | §3 の技法表を「ミニディメンション（**Type 4**, DT#127）」に修正し、「本体にも現在のミニキーを Type1 で埋めると Type 5 だが、正典は採らない（時点解決の経路が2本になる）」を1行で併記 |
| Minor-11 | 「DT#100 の要件は満たす」→「DT#100 の中心の要件（単一列・整数・ETL 時に対応付けを解決）は満たす。残る理由9（自然キーの中身への依存）はハッシュの入力が自然キーである以上まともに当たるが、ソースが `src_careervoice` 単一である限り効かない——2つ目のソースが来たら表の6行目と一緒に ✓ に変わる」に修正 |

### 追加の正典への変更提案（ラウンド1で判明）

8. **`domain.md` §4 の散文が表と食い違っている。** 散文は「SCD2 のディメンション（`dim_member` / `dim_company` / `dim_agent` / `dim_scout_sender`）は一律に…」と4本を挙げるが、同 §4 の表は `dim_agency` を SCD **2** としている。本文は表（5本）に従った。散文側に `dim_agency` を追加する訂正を提案する。
9. **`dim_member_profile_mini` は「組合せ 15 通り ＋ `-1` の既定行 = 16 行」。** `fct_page_view.member_key` が `-1`（匿名）を取る以上、同じ行の `member_profile_mini_key` にも既定行が要る。§4 の備考に明記を提案する（ラウンド0 の提案4 の再提出）。
10. **データ量の前提を正典に置く。** 会員 300 万人・`fct_page_view` 日次 2,000 万行という規模は本文（§2(a)・§4・§7 問2）の判断を左右するが正典に記述が無い。本文では「仮定する」と条件形にしたが、`domain.md` §5 に規模の前提行を1行足すと、後続の回が別の数字を使う事故を防げる。

### 検証（修正後に実行）

- `python3 ~/.claude/skills/svg-diagram/scripts/check_svg.py html/03_dimensions.html` → **`0 errors, 1 warnings`**（warning は「`<svg>` が見つからない」＝ブリーフ「図: なし」どおり）
- タグ対応 0 エラー / 未閉タグ 0 / `<pre><code>` 内の生の山括弧 0 / バッククォート残り 0
- `<h2>` 9本（1〜8 ＋ 参照文献）／ 表 12 個すべて `.table-wrap` 包み ／ SVG 0 個
- 4文以上の `<p>` = **0**（`<pre>` 除外・機械カウント）
- モデル SQL ブロックの末尾セミコロン = 0（機械チェック）
- 本文の `dim_*` / `fct_*` / `stg_*` / `snap_*` を `canon/domain.md` と再突合 → 非収録は `snap_members` / `stg_careervoice__scouts`（命名規約適合）と `stg_product`（dbt 記事の引用内）の3件のみ
- 本文の URL 13 本すべて `canon/references.md` に存在

---

## 修正ラウンド2（再レビュー `review/03_rereview.md` への対応）

再レビューは初回 17 件を **ADDRESSED 17 / NOT ADDRESSED 0** と判定。以下は修正差分の中で新たに生じた 6 件への対応。

| ID | 対応 |
|---|---|
| 新 Critical-1 | ラウンド1で追加した `dim_member_daily` のテストが、正典 §4 の `require_partition_filter=true` の下では実行自体を拒否される（`Cannot query over table … without a filter that can be used for partition elimination`）ことを見落としていた。**各テストの `config:` に `where: "snapshot_date >= DATE_SUB(CURRENT_DATE('Asia/Tokyo'), INTERVAL 3 DAY)"` を付けた**（dbt 公式ドキュメント `reference/resource-configs/where` を WebFetch で確認。generic テストでは `where` を `config:` 配下にネストする）。あわせて (a) モデル側 `config` の `+where` は generic test に伝播しないため必ず各テストに書くこと、(b) 直近3日だけを検査するこの形を **10 回で規約化**すること、をコメントで明記。テスト対象も `not_null` / `relationships` に加えて正典の自然キー `(snapshot_date, member_id)` の `dbt_utils.unique_combination_of_columns` を追加した（3本とも同じ `where`）。さらに締めの段落に「テストは物理設計に従属する。直近3日だけの検査は全期間を諦めたのではなく、全期間の整合は `dim_member_daily` を作る側のモデルで担保する分担だ（09回・10回）」を追加し、この回の「`-1` 行はテストの前提条件」という結論とパーティション設計を接続した |
| 新 Important-1 | §2(a) 冒頭の「（正典はデータ量を定めていない）」を削除。`canon/domain.md` §5 末尾に想定規模（会員 300 万、`page_views` 日次 2,000 万行 ほか）が追加されているため、「以下、規模は**正典 §5 の想定規模**（会員 300 万人、`page_views` 日次 2,000 万行）を使う。断定ではなく前提で、この回の判断のいくつかはこの桁に乗っている」に置き換えた。列名も `fct_page_view` → 正典 §5 の表記に合わせて `page_views` にした |
| 新 Minor-a | §5 判断表で `dim_agency` が SCD2 行と縮約行の2箇所に対象として並び「6本目がある」と読めた点を修正。縮約行の対象欄を「同上（<code>dim_agency</code>）。この行の主眼は『なぜ `dim_agent` と別に置くか』」に変更し、結び先に正典どおり `fct_placement` の主軸も追加した |
| 新 Minor-b | §2(c) の「3本目は絞り込みを1つ足しただけで**1本目と同じ結果に戻る**」を「**`INNER JOIN` と同じ挙動に戻る**（1本目を 2026 年で絞ったものと一致する）」に訂正。1本目は全年・3本目は 2026 年のみで結果集合は一致しないため |
| 新 Minor-c | 本文で名指ししていた FDE を `p.meta` の再解釈欄（`FDE / スナップショット (Beauchemin 2018)`）と参照文献（`https://www.ssp.sh/brain/snapshotting/`、`canon/references.md` 収録の URL）に追加。正典 §4 の `dim_member_daily` の備考が「FDE 方式の代替」である以上、削るより載せるほうが後続の回と揃うため |
| 新 Minor-d | §4 の「**正典はどちらか一方を選ばず両方を置く**」を「**正典は両方を定義しており、どちらを主経路にするかは 05回で決める**」に緩めた。正典 §4 の備考は「FDE 方式の代替（05回）」であり、この回で確定させると 05回の比較の余地を潰すため。整合条件（`dim_member_daily.member_profile_mini_key` がミニ側と一致）はそのまま残した |

### 正典への変更提案の更新

- ラウンド1 の提案 8（§4 散文の SCD2 が4本）・9（ミニは組合せ 15 通り ＋ 既定行 = 16 行）・10（想定規模を §5 に）は、**いずれも正典に反映済み**であることを確認した（§4 散文・§4 備考・§5 末尾）。未処理の提案は残っていない。

### 検証（ラウンド2 修正後に実行）

- `python3 ~/.claude/skills/svg-diagram/scripts/check_svg.py html/03_dimensions.html` → **`0 errors, 1 warnings`**（warning は `<svg>` 不在＝ブリーフ「図: なし」どおり）
- タグ対応 0 エラー / 未閉タグ 0 / `<pre><code>` 内の生の山括弧 0（`snapshot_date &gt;= …` の 3 箇所を含めエスケープ済み）/ バッククォート残り 0
- 4文以上の `<p>` = 0（`<pre>` 除外・機械カウント）
- `<h2>` 9本 ／ 表 12 個すべて `.table-wrap` 包み ／ SVG 0 個
- モデル SQL ブロックの末尾セミコロン = 0
- 本文の URL 14 本すべて `canon/references.md` に存在（FDE の追加分を含む）
- 本文の `dim_*` / `fct_*` / `stg_*` / `snap_*` を `canon/domain.md` と再突合 → 非収録は `snap_members` / `stg_careervoice__scouts`（命名規約適合）と `stg_product`（dbt 記事の引用内）の3件のみ
- 「正典はデータ量を定めていない」の残存 = 0
