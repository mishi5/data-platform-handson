# 02 ファクトの3型とファクトレス — 執筆報告

- 出力: `docs/data_mart_modeling/html/02_fact_types.html`
- タイトル: ファクトの3型とファクトレス — データマート設計 02

## 完了した節

| 節 | 内容 | ブリーフ要求との対応 |
|---|---|---|
| 1. この回が決めること | 判断の一覧表 → 4型比較表（粒度 / 行の増え方 / 更新 / 日付キー数 / 加法性 / 典型の問い）→ CareerVoice の10ファクト分類表 | ✓ 必須内容すべて。日付キー数を型の判別軸として明示 |
| 2. どこで壊れるか | (a) `job_postings` から「4/15 時点の掲載中件数」を再構成する失敗（再掲載での `closed_at` 上書き・論理削除・その日限りの派生値） (b) `fct_application_pipeline` の UPDATE 運用（ストリーミングバッファ / DML 同時実行 / 非冪等 → 09回へ送る） (c) `rejected` と `withdrawn` の丸め | ✓ 3つとも |
| 3. Kimball の原則 | 3型の定義表（Fact Tables の原文要点）／半加法性／ファクトレス2種（`fct_page_view` = イベント型、契約×月×枠 = カバレッジ型）／ヘッダ明細 DT#95 ／ サマリー単独の危険 DT#77 | ✓ |
| 4. 現代の再解釈 | 割当なしのため「型は残り、実装だけ変わる」を主題に。FDE の snapshotting（不変パーティション）と dbt の `insert_overwrite` / `merge` の選択表 | 節構成の維持（style.md）。下記「迷った判断」参照 |
| 5. BigQuery + dbt での実装 | `date_key` マクロ／`fct_application_pipeline`（`MIN(IF(stage=...))` ピボット + `-1` + as-of 結合 + `audit_key`）／schema.yml のテスト／`P001` の1行の変遷表（7時点）／図／`fct_job_posting_daily`（`dim_date` 範囲結合 + 累積 window）／`J001` の行の表 | ✓ |
| 6. 判断基準 | 「状況（問いの形）→ 選択 → 理由」11行 | ✓ |
| 7. 演習 | (a) スカウト枠は定期スナップショットか (b) `S002` の `fct_scout_funnel` 1行 (c) `is_unlocked` はメジャーかディメンションか。各 `<details>` に解答 | ✓ 3問 |
| 8. 参考: 手元の基盤 | `mart_url_performance`（0件の日に行が立たない）／`_incremental` の MERGE は型としては集約／`raw_articles.content_status` は累積スナップショット未満（遷移時刻を持たない）／試せる種 | ✓ 5行・この節のみ |

## 読んだ文献と引用した要点

WebFetch で実読したもの:

| 文献 | 引用・利用した要点 |
|---|---|
| Fact Tables（2008） | トランザクション = 「測定値はその瞬間・その事象にとってのみ有効」／定期 = 「活動が無くても全報告エンティティの行が現れる強い保証」／累積 = 「プロセスの進行に伴い行が再訪され上書きされる」・行数は最小／粒度宣言は FK の列挙ではなく業務上の言明 |
| DT#50（ファクトレス） | 2種（イベント記録型 / カバレッジ型）。存在理由は「販促したのに売れなかった商品」型の**起きなかったこと**を答えるため。ダミー `1` 列の話は記事本文に無かったので、`view_count = 1` は正典側の決定として書き、DT#50 には帰属させていない |
| DT#95（ヘッダ/明細） | 反パターン2つ（ヘッダをディメンション化 → ファクトの約20%という異常比率／ヘッダを別ファクト化 → 大きいファクト同士の結合）。解は「ヘッダの次元性を全て明細に降ろし、伝票番号は退化ディメンション」 |
| DT#77（サマリー単独） | 「詳細は予測できない形に丸められるが、サマリーを構成要素へ魔法のように分解することはできない」。集約は原子データの補完であって置換ではない |
| ssp.sh / snapshotting（FDE） | パーティションを不変オブジェクトとして扱い、更新せず積む。再現性・冪等性・時系列の取りやすさ。代償は重複 |
| dbt BigQuery configs | `merge`（`unique_key` 必須）／`insert_overwrite`（`partition_by` 必須）／`partition_by` の dict 構文（`field` / `data_type` / `granularity`） |

読めなかったもの: Techniques PDF（2013）は WebFetch がバイナリのまま返し本文抽出できず。DWT ch.4 は書籍のため URL からは読めない。ch.4 の参照は「在庫章 = 定期スナップショット・半加法性・3型の比較」という範囲に留め、定義の引用は Fact Tables 記事から取った。

## check_svg の結果

```
python3 ~/.claude/skills/svg-diagram/scripts/check_svg.py docs/data_mart_modeling/html/02_fact_types.html
0 errors, 0 warnings
```

図は1枚（`#dg-acc`、概念図）。`P001` の1行が 6/23 → 8/1 の6時点で書き換わる様子を、行ラベル（6本の日付キー）× 6時点のセル格子で表現。accent は「その時点で埋まったセル」の1系統のみ、矢印は時間方向の5本のみ。ノード（時点）6個で密度予算内。

## 正典への変更提案

1. **`fct_job_posting_daily.agent_key` が解決できない**（最も重い）。バスマトリクスは求人掲載プロセスに agent 列で ✓ を置いているが、`job_postings` が持つのは `agency_id` まで。`dim_agent` は担当者（`agent_id`）粒度なので、`agency_id` で結ぶと 1求人 × 担当者数に行が増え粒度宣言が壊れる。本文では `-1`（未知、DT#43）に固定し、理由を明記して回避した。案:
   - (a) `dim_agent` にエージェンシー代表行（`agent_id` = NULL 相当）を持たせる
   - (b) バスマトリクスの「求人掲載」行から agent を外し、`dim_job_posting.is_agency_posting` で代替する
   - (c) `dim_agency` を別に立てる（雪片化しない方針とは衝突しない。`dim_agent` とは別のコンフォームド次元になる）
2. **`current_stage` の値集合**。`selection_events.stage` は8値だが、応募直後（選考イベントがまだ1件も無い）状態を表す値が無い。本文では `applied` を初期値として導入し、`accepted_values` テストにも 9値で書いた。正典の「ファクト」節に `current_stage` の値集合として追記したい。
3. **`audit_key` の取り方**。正典に「全ファクトは `audit_key` を持つ」とあるが、取得方法は未定義。本文では `dim_audit` から `dbt_invocation_id = '{{ invocation_id }}'` の行を `CROSS JOIN` する形にした（10回と整合させる必要あり。この実装は dim_audit がファクトより先にロードされることを暗黙に前提にしている）。
4. 執筆中に正典へ追記された「SCD2 の共通列」「`audit_key`」「パーティション用の DATE 列 `<role>_date`」は本文に反映済み（`applied_date` / `snapshot_date`、`DATE(valid_from, 'Asia/Tokyo')` での as-of 結合）。

## 迷った判断とその理由

- **§4（現代の再解釈）の扱い。** references.md の割当は「—」だが style.md は8節構成を「減らさない」と決めている。空にするより、references.md に載っている未割当文献のうちこの回の論点に直結する2本（FDE snapshotting / dbt BigQuery configs）だけを使って「型は残り、実装だけ変わる」を書いた。`p.meta` の「再解釈:」にも明記してある。他回と重複しうるので、07・09 の担当と衝突するなら削ってよい。
- **図の構図。** 当初は「6時点のカード内にセルを縦積み」にしたが、カード幅が 72–84px になり `check_svg.py` のテキストはみ出し検査（箱の内側 12px パディング）を通らない。行ラベルを箱の外（左）に出し、セル格子＋時点ノードに分離して解決した。
- **図から `accepted`（7/22）を省略。** ブリーフ指定の6時点（6/23 / 7/1 / 7/8 / 7/15 / 7/20 / 8/1）に合わせるため。省略した事実は図中の注記に書き、本文の変遷表では 7/22 を含む7時点を示した。
- **`dim_application` という架空名を本文から削除。** DT#95 の反パターン説明で使いたくなるが、正典に無い名前を出さない規約を優先し「応募ヘッダをそのままディメンション化すると」と言い換えた。
- **`fct_application_pipeline` の `agent_key`。** 求人の `agency_id` からではなく `applications.scout_id` → `scouts.sender_agent_id` → `dim_agent` で解決した（求人経由だと fan-out する）。スカウト経由でない応募は `-1`。
- **`view_count = 1` の帰属。** DT#50 の本文にダミーカウント列の記述が無かったため、Kimball の主張としてではなく正典側の決定として書いた。
- **(c) の演習の答え。** `is_unlocked` はメジャーに置いても率は出せるので「明確な誤り」ではない。判断基準の表の行（足して意味があるか／切り口か）を適用した根拠として書き、`is_hired` との対比を添えた。

## 未達事項

- Techniques PDF（2013）を実読できていない（WebFetch がバイナリを返す）。3型・ファクトレスの定義は Fact Tables 記事と Design Tip から取っており、Techniques の言い回しは引用していない。
- DWT ch.4 は書籍のため未読。章番号の参照のみで、章本文からの引用はしていない。
- 図は1枚のみ（ブリーフ指定どおり）。「定期スナップショットの密度 vs トランザクションの疎」を比較図にしたくなったが、§1 の比較表で足りるため描いていない。

---

## 修正ラウンド1（レビュー `review/02_review.md` への対応）

| ID | 対応 |
|---|---|
| C-1 | §6 の1行目を「日別のスカウト送信数は？→ トランザクション（`fct_scout`）」に差し替え、「日別の応募数は？→ 累積スナップショットを `applied_date_key` で数える（`selection_events` に `applied` が無いため応募単独のトランザクションファクトは正典に無い）」を新規行として追加。§1 の4型比較表の「典型の問い」も「日別のスカウト送信数は？」に修正 |
| I-1 | 正典追従。`fct_job_posting_daily` の `-1 AS agent_key` を `COALESCE(agc.agency_key, -1) AS agency_key` に差し替え、`dim_agency` への as-of 結合を追加。直後の2段落を「縮約ディメンションを使う理由」として書き直した。`fct_application_pipeline` にも `agency_key`（求人の `agency_id` → `dim_agency`）を追加し、`postings` CTE に `agency_id` を戻した（`agent_key` はスカウト経由の解決のまま） |
| I-2 | `fct_job_posting_daily` の config を `materialized='incremental'` + `insert_overwrite` + `partition_by={'field':'snapshot_date',...}` に変更し、`posting_days` に `{% if is_incremental() %}` のルックバック3日の述語を追加。「ルックバック窓より前のパーティションは二度と作り直さない」を本文に明記（09回へ送付） |
| I-2 派生 | レビュー案のまま増分化すると、累計メジャーの `SUM() OVER (ORDER BY snapshot_date_key)` が窓に過去行を持たず 0 から数え直しになる。`application_cum` / `scout_cum` CTE（`event_date <= full_date` で全履歴から集計）に置き換え、その理由を本文に1段落追加した |
| I-3 | `posting_days` の範囲結合を `BETWEEN` から半開区間 `[posted_date, closed_date)` に変更（`DATE_ADD(CURRENT_DATE, INTERVAL 1 DAY)` で無期限掲載を表現）。§2(a) のクエリと同じ規約であることを本文で明示。`J001` の表の値は不変 |
| I-4 | 両モデルの全ディメンションキーを `COALESCE(..., -1)` で包み、`schema.yml` に `member_key` の `not_null` を追加。「未達だけでなくディメンション側に該当行が無い場合も -1」「`relationships` は NULL 行を無視するので気づけない」を本文に1段落追加 |
| I-5 | `audit` CTE と `CROSS JOIN` を両モデルから削除し、`{{ audit_key() }} AS audit_key`（定義は 10回）の1行に置換。0行化・二重化のリスクが消えた |
| I-6 | DT#95 の aside を原典どおり前2文で閉じ、按分の話を aside の外の本文へ（この題材はヘッダ金額を持たないため1文に圧縮） |
| m-1 | 「`-1` は INT64 キー前提の表記。STRING キーなら `'-1'`（型の判断は 03回）」を本文に追記（正典 §4 の追記とも一致） |
| m-2 | `fct_application_pipeline` の config に `partition_by={'field':'applied_date',...}` を追加し、コメントと整合させた |
| m-3 | SQL に `-- member_profile_mini_key（応募時点）はここに同じ形で足す（03回 / 05回）` の1行を追加 |
| m-4 | 3型の aside の帰属を `（Fact Tables, 2008 / DWT ch.4）` に修正 |
| m-5 | 「累計は掲載期間内に届いた分だけを数える（掲載終了後の応募は入らない）」を本文に明記 |
| m-6 | `P001` の表のヘッダを `first_interview` / `final_interview` に戻した |
| m-7 | §2(b) の DML 表現を「競合するとキューイングと再試行に回る」に緩めた |

その他: 正典追加に伴い §3 の `fct_selection_event` のキー列挙に `agency_key` を足した。図は未変更（`check_svg.py` 再実行して `0 errors, 0 warnings`）。段落は全て3文以内、`<pre>` 内の生の `<`/`>` はゼロ、タグの対応検査も通過。

---

## 修正ラウンド2（再レビュー `review/02_rereview.md` §3 への対応）

| ID | 対応 |
|---|---|
| N-1 | 正典 §5 の `S003`（`AG02` → `M002`、`J001`、6/18 送信）に追従。`J001` の表に `20260618` の行（`days_since_posted` = 78、`scout_count_cum` = 1）を足し、`20260620` / `20260623` の `scout_count_cum` を 1 → **2** に修正。リード文も「`J001` 宛のスカウトは正典に2件ある。`S003` が 6/18 送信、`S001` が 6/20 送信、`P001` が 6/23 応募」に差し替えた。`0 → 0 → 1 → 2 → 2` の並びが「累計は `<=` で数える」の実例になる |
| N-2 | §2(a) の「答えは `WHERE snapshot_date = DATE '2026-04-15'` の1パーティション読み」に修正。§5 末尾も `<pre>` のクエリ例に起こして `WHERE snapshot_date = DATE '2026-04-15'` にし、「絞るのは `snapshot_date_key`（表示用の整数キー）ではなくパーティションを張った DATE 列 `snapshot_date`。プルーニングはパーティション列への述語にしか効かないので、`snapshot_date_key` で絞るとフルスキャンになる」を1段落追加 |
| n-1 | `macros/audit_key.sql` のスタブ（`COALESCE((SELECT MIN(audit_key) FROM dim_audit WHERE dbt_invocation_id = '{{ invocation_id }}'), -1)`、本設計は 10回）を `date_key` マクロの直後に追加。印刷されたモデルがそのまま compile できる状態になった |
| n-2 | §1 の判断表「型の選び方」セルに「ただし数えたい事象のトランザクションファクトが無い場合は例外（応募数は §6 の2行目）」を追記 |
| n-4 | §3 の「すべて `applications` 側から降りてきた次元」を「`applications` と、その求人・スカウトから降りてきた次元」に修正 |

### 未対応（理由あり）

- **n-3（`application_cum` と `scout_cum` を1つの CTE に畳む）: 意図的に見送り。** `posting_days` に `daily_applications` と `daily_scouts` を同時に `event_date <= full_date` で結ぶと、両者の行が直積になって `SUM(application_count)` がスカウト件数分、`SUM(scout_count)` が応募件数分だけ水増しされる（`J001` の 6/23 なら応募1 × スカウト2 で `application_count_cum` が 2 になる）。CTE を分けているのは視線移動より正しさの都合なので、そのままにした。
- **n-5（`valid_to` の番兵値と JST 変換の上限）: 05回へ送る。** 再レビュー自身が「この回では触れなくてよい」としており、SCD2 の番兵値の決定は 05回の論点。

図は今ラウンドも未変更。`check_svg.py` は `0 errors, 0 warnings`。段落は全て3文以内、`<pre>` 内の生の `<`/`>` はゼロ、表10本すべて `.table-wrap` 内。
