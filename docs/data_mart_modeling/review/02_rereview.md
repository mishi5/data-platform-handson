# 02 ファクトの3型とファクトレス — 再レビュー（修正ラウンド1 の検証）

対象: `docs/data_mart_modeling/html/02_fact_types.html`（915 行、`debb2d4`）
初回レビュー: `review/02_review.md`（Critical 1 / Important 6 / Minor 7）
執筆者の報告: `reports/02_report.md` 末尾「修正ラウンド1」
正典: `canon/domain.md`（`dim_agency` / `audit_key` / `<role>_date` / `current_stage` 初期値 / `dim_member_daily` / `S003` 追加後の版）

検証方法: 報告は参照せず、`fe39f65..debb2d4` の実差分（+105 / −52 行）と現物の HTML を直接読んだ。新 SQL は BigQuery / dbt として静的に読み、`P001` の PIVOT と `J001` の日次展開を再検算した。

---

## 1. 初回指摘 14 件の判定

| ID | 指摘 | 判定 | 現物の該当箇所 |
|---|---|---|---|
| C-1 | §6 1行目「日別の応募数は？」→ `fct_selection_event` は答えられない | **ADDRESSED** | §6 1行目が「日別のスカウト送信数は？→ トランザクション（`fct_scout`）」に置換。直下に「日別の応募数は？→ 累積スナップショット（`fct_application_pipeline`）を `applied_date_key` で数える」を新規行として追加し、理由欄に「`selection_events.stage` に「応募」が無いため応募単独のトランザクションファクトは正典に存在しない」を明記。§1 の4型比較表「典型の問い」も「日別のスカウト送信数は？」に修正済み |
| I-1 | `fct_job_posting_daily` の `-1 AS agent_key` → `agency_key`（正典追従） | **ADDRESSED** | `COALESCE(agc.agency_key, -1) AS agency_key` + `LEFT JOIN dim_agency` の as-of 結合（`pd.full_date >= DATE(agc.valid_from,…) AND < DATE(agc.valid_to,…)`）。直後の2段落も「縮約ディメンションを使う理由」に書き直し（DWT ch.4 帰属つき）。加えて `fct_application_pipeline` にも `agency_key`（`jp_src.agency_id` → `dim_agency`）を追加し、`postings` CTE に `agency_id` を戻した。正典 §4 の `fct_application_pipeline` FK 一覧に `agency_key` がある以上これも正しい追従。§3 の `fct_selection_event` キー列挙にも `agency_key` を追加 |
| I-2 | §5 の materialization が §2(a)・§4 の主張を満たしていない | **ADDRESSED**（ただし新規 N-2 を生んだ） | config が `materialized='incremental'` + `incremental_strategy='insert_overwrite'` + `partition_by={'field':'snapshot_date','data_type':'date','granularity':'day'}` になり §4 の提示と一致。`posting_days` に `{% if is_incremental() %} WHERE d.full_date >= DATE_SUB(CURRENT_DATE('Asia/Tokyo'), INTERVAL 3 DAY) {% endif %}`。「ルックバック窓（3日）より前のパーティションは二度と作り直さない」を本文に明記 |
| I-3 | 掲載終了日の扱いが §2(a) と §5 で1日ずれる | **ADDRESSED** | `BETWEEN` を廃し `d.full_date >= p.posted_date AND d.full_date < COALESCE(p.closed_date, DATE_ADD(CURRENT_DATE('Asia/Tokyo'), INTERVAL 1 DAY))` に変更。「掲載期間は `[posted_date, closed_date)` の半開区間 … §2(a) の「壊れている」クエリ（`closed_at > '2026-04-15'`）と同じ規約に揃えてある」を追記。両者とも「4/15 に閉じた求人は 4/15 に数えない」で一致 |
| I-4 | ディメンションキーが LEFT JOIN のまま NULL になりうる | **ADDRESSED** | 両モデルの全ディメンションキーが `COALESCE(..., -1)`（pipeline: member / company / job_posting / job_category / channel / agency / agent、daily: job_posting / company / job_category / agency）。`schema.yml` に `member_key` の `not_null` を追加。「`relationships` テストは NULL 行を黙って無視するので気づけない」の1段落も追加 |
| I-5 | `dim_audit` の `CROSS JOIN` で 0 行化・二重化 | **ADDRESSED** | 両モデルから `audit` CTE と `CROSS JOIN audit` が消え、`{{ audit_key() }} AS audit_key` のスカラー展開に置換。行数に影響しない形になり、0行化・二重化のリスクは消えた（マクロ本体が未定義な点は n-1） |
| I-6 | DT#95 の aside に原典が言っていない主張（按分・別ファクト化） | **ADDRESSED** | aside は前2文で閉じ、3文目を削除。aside の外に「ヘッダ単位の金額 … の扱いは DT#95 の範囲外である。この題材では `applications` がヘッダ金額を持たないので問題にならない」を配置。「按分できないなら別ファクトにする」（Bad Idea #2 と衝突する記述）は消えている |
| m-1 | `-1` がサロゲートキーの型を先取り | **ADDRESSED** | 「`-1` は INT64 キーを前提にした表記で、STRING キーなら `'-1'` になる（キー型の判断は 03回）」を §5 に追記 |
| m-2 | `partition_by` が無いのに「パーティション用の DATE 列」 | **ADDRESSED** | `fct_application_pipeline` の config に `partition_by={'field':'applied_date',…}` を追加。コメントと config が一致 |
| m-3 | `member_profile_mini_key` が SELECT に無い | **ADDRESSED** | SELECT 内に `-- member_profile_mini_key（応募時点）はここに同じ形で足す（03回 / 05回）` を配置 |
| m-4 | 「3型は並存しうる」の帰属 | **ADDRESSED** | aside 見出しが `Kimball の主張（Fact Tables, 2008 / DWT ch.4）` に修正 |
| m-5 | 掲載期間外に届いた応募・スカウトが累積から落ちる | **ADDRESSED** | 「この累計は掲載期間内に届いた分だけを数える。掲載終了後に届いた応募は、その求人の行がもう立たないので入らない」を追記 |
| m-6 | `P001` の表のヘッダが正典の列名と不一致 | **ADDRESSED** | `first_iv` / `final_iv` → `first_interview` / `final_interview` |
| m-7 | 「同一テーブルへの変更 DML は同時実行が制限される」 | **ADDRESSED** | 「同一テーブルへの変更 DML は競合するとキューイングと再試行に回るので、件数が増えるほど詰まる」に緩和 |

**14 / 14 ADDRESSED。NOT ADDRESSED は無い。** 報告の記述と現物の差分は一致しており、報告に書かれていない改変（隠れた追加変更）も無い。

---

## 2. 修正で入った SQL の静的検証

### 2.1 `fct_application_pipeline`（変更部分）

- `partition_by={'field':'applied_date','data_type':'date','granularity':'day'}` + `materialized='table'`: dbt-bigquery で有効な組合せ。`applied_date` は `DATE(a.applied_at,'Asia/Tokyo')` で NULL にならないのでパーティション列として成立する ✅
- `COALESCE(agc.agency_key, -1) AS agency_key` と `LEFT JOIN dim_agency AS agc ON agc.agency_id = jp_src.agency_id AND a.applied_at >= agc.valid_from AND a.applied_at < agc.valid_to`: `jp_src` は `LEFT JOIN postings USING (job_posting_id)` の別名で `agency_id` を持つ ✅。TIMESTAMP 同士の比較 ✅。`agency_id` が NULL（直接掲載）なら等値が NULL → 不一致 → `-1` ✅
- 行の増減: `dim_agency` を1本足しても、`agency_id` × 時点が一意である限り fan-out しない（`dim_company` / `dim_agent` と同じ前提）。`P001` は `J001`（直接掲載）なので `agency_key = -1`、`S001` は `sender_agent_id` が NULL なので `agent_key = -1` → **PIVOT 後も 1 応募 = 1 行** ✅
- `{{ audit_key() }}` はスカラー式位置なので行数に影響しない ✅（本体は未定義 → n-1）
- `USING (application_id)` / `USING (job_posting_id)` / `USING (scout_id)` の後に `a.application_id` / `a.job_posting_id` / `a.scout_id` を修飾参照する形は BigQuery で合法 ✅

### 2.2 `fct_job_posting_daily`（変更部分）

- `{% if is_incremental() %} WHERE … {% endif %}` は `posting_days` CTE の `INNER JOIN … ON …` の直後にあり、生成される SQL は `FROM postings p INNER JOIN dim_date d ON … WHERE …` の正しい形になる ✅
- 半開区間: `d.full_date >= p.posted_date AND d.full_date < COALESCE(p.closed_date, DATE_ADD(CURRENT_DATE('Asia/Tokyo'), INTERVAL 1 DAY))`。無期限掲載は「明日の前日まで」＝今日まで行が立つ ✅。`dim_date` の `-1` 行は `full_date` が NULL → 比較が NULL → INNER JOIN から落ちる ✅（本文の記述も `BETWEEN` から「比較が NULL になり」に直っている）
- `application_cum` / `scout_cum`: `posting_days` × `daily_*` を `event_date <= pd.full_date` で結び、`GROUP BY pd.job_posting_id, pd.snapshot_date_key` で畳む。fan-out した行は必ず (`job_posting_id`, `snapshot_date_key`) に戻るので**粒度宣言は保たれる** ✅。`COALESCE(SUM(...), 0)` は「一致 0 件 → `SUM` が NULL」を 0 に落とす正しい形 ✅
- 増分実行でも累計が正しいこと: `daily_applications` / `daily_scouts` はソース全期間から作られ、窓の制限は `posting_days` 側にしか掛からない。したがって「直近4日分の行しか作らない」状態でも累計値は全履歴を反映する ✅ — 初回レビュー I-2 の素案（window 関数のまま増分化）が持っていた欠陥を、執筆者が自力で見つけて潰している（報告「I-2 派生」）。**この判断は正しい**
- `INNER JOIN application_cum USING (job_posting_id, snapshot_date_key)` を2連で書き、その後に `pd.` 修飾で参照する形も BigQuery で合法 ✅
- `insert_overwrite`（dynamic）は `partition_by` があれば `partitions` 未指定でも動く。出力に現れたパーティションだけを置換するので、ルックバック4日分だけが入れ替わる ✅

### 2.3 `P001` の PIVOT 再検算 — 表と一致

`selection_events` の 6 行（7/1 `document`, 7/8 `first_interview`, 7/15 `final_interview`, 7/20 `offer`, 7/22 `accepted`, 8/1 `hired`）＋ `applications.applied_at` = 6/23。

| 検算対象 | 計算 | 本文 | 判定 |
|---|---|---|---|
| `applied_date_key` | `applications` 由来 20260623 | 20260623 | ✅ |
| 未達マイルストーン | `MIN(IF(...))` が NULL → `date_key()` が `-1` | `-1` | ✅ |
| `closed_date_key` | `COALESCE(hired, rejected, withdrawn)` → 8/1 のみ 20260801 | 20260801 | ✅ |
| `current_stage` 7時点 | `applied`→`document`→`first_interview`→`final_interview`→`offer`→`accepted`→`hired` | 同じ | ✅ |
| `days_applied_to_offer` | `DATE_DIFF('2026-07-20','2026-06-23',DAY)` = 7 + 20 = **27** | 27 | ✅ |
| `days_offer_to_hired` | `DATE_DIFF('2026-08-01','2026-07-20',DAY)` = **12** | 12 | ✅ |
| 出力行数 | 1 応募 = 1 行（`M001` は 8/1 に SCD2 が切れるが応募時刻 6/23 は前版のみに一致、`dim_agency` / `dim_agent` は不一致で `-1`） | — | ✅ fan-out なし |

`accepted_values` に `applied` を含む 9 値を置いた点も、正典 §4 の「`current_stage` 初期値 `applied`」と一致 ✅。

### 2.4 `J001` の日次展開 再検算 — 行数は正しい / `scout_count_cum` が誤り

`J001` = 4/1 掲載・`closed_at` NULL。今日を 2026-09-08 とすると:

- 全再構築時の行数 = 4/1〜9/8 = 30 + 31 + 30 + 31 + 31 + 8 = **161 行**（1日1行）✅
- 増分実行時（ルックバック3日）= 9/5・9/6・9/7・9/8 の **4 行**のみを生成し、その4パーティションだけが置換される ✅
- `days_since_posted`: 20260401 → 0 ✅ / 20260415 → 14 ✅ / 20260620 → 29 + 31 + 20 = **80** ✅ / 20260623 → **83** ✅
- `application_count_cum`: `P001`（6/23、J001）のみ → 20260620 は 0 ✅ / 20260623 は 1 ✅
- `scout_count_cum`: **本文の値が誤り**（下記 N-1）。正典 §5 の `S003`（`AG02` → `M002`、**`J001`**、2026-06-18 送信）が `daily_scouts` に (J001, 2026-06-18, 1) として入るため、`event_date <= full_date` の累計は 20260620 で **2**、20260623 でも **2** になる

---

## 3. 新規指摘（修正差分の範囲）

### Important

#### N-1. `J001` の表の `scout_count_cum` が `S003` を数えていない（正典 `S003` 追加への未追従）

正典 §5 に `S003`（`AG02`(agent) → `M002`、**`J001`**、2026-06-18 送信、未開封）がある。新しい `scout_cum` CTE は

```sql
FROM posting_days AS pd
LEFT JOIN daily_scouts AS ds
    ON  ds.job_posting_id = pd.job_posting_id
    AND ds.event_date &lt;= pd.full_date
```

で「その日までの全履歴」を数えるので、`J001` の `scout_count_cum` は 6/18 以降 1、6/20 以降 2 になる。本文の表は 20260620 / 20260623 とも `1` のままで、**自分の SQL に正典データを通した結果と食い違う**。直前の段落「（`S001` は 6/20 送信、`P001` は 6/23 応募）」も `S003` を落としている。

`agency_key` と同じく、`S003` は執筆後に正典へ入ったサンプルなので追従漏れである（初回レビューもここは見落としている）。

**修正案**: 表の該当2セルを 2 に直し、リード文を差し替える。

| `snapshot_date_key` | `scout_count_cum` |
|---|---|
| 20260401 | 0 |
| 20260415 | 0 |
| 20260620 | **2** |
| 20260623 | **2** |

> `J001` の行はこうなる（`S003` は 6/18 送信、`S001` は 6/20 送信、`P001` は 6/23 応募。`J001` 宛のスカウトは正典に2件ある）。

`0 → 0 → 2 → 2` は「累計は当日分ではなく `<=` で数える」という直前の主張を数字で見せる例にもなるので、直すと本文が強くなる。`days_since_posted` と `application_count_cum` は変更不要（検算済み）。

#### N-2. パーティション列は `snapshot_date`（DATE）なのに、読者に見せるクエリは `snapshot_date_key`（INT64）で絞っている — I-2 が直そうとした「1パーティション読み」が依然成り立たない

I-2 の修正で `partition_by` は `snapshot_date`（DATE）に張られた。ところが本文の2か所は INT64 の退化キーで絞っている。

- §2(a): 「定期スナップショットを持てば、答えは `WHERE snapshot_date_key = 20260415` の1パーティション読みになり」
- §5 末尾: 「`SELECT SUM(is_open) FROM fct_job_posting_daily WHERE snapshot_date_key = 20260415` になる」

BigQuery は**パーティション列そのもの**への述語でしかプルーニングしない。`snapshot_date_key` は普通の INT64 列なので、この2つのクエリは今もフルスキャンする。初回レビュー I-2 の指摘（「`partition_by` が無い → 1パーティション読みにならない」）は config を直しただけでは閉じておらず、主張と実装のズレが本文側に残っている。§4 で「`partition_by` は `snapshot_date_key`（INT64）ではなく … DATE 列 `snapshot_date` に張る」と自ら書いている分、内部矛盾としても見えやすい。

**修正案**: 両方の述語を DATE 列に変える。

```sql
-- 4/15 時点の掲載中求人数（パーティション1枚だけを読む）
SELECT SUM(is_open)
FROM {{ ref('fct_job_posting_daily') }}
WHERE snapshot_date = '2026-04-15'
```

§2(a) の文も「答えは `WHERE snapshot_date = '2026-04-15'` の1パーティション読みになり」に直す。あわせて1文添えると、この回で `<role>_date` を持つ理由が完結する:

> 絞るのは `snapshot_date_key`（退化した表示用の整数キー）ではなく、パーティションを張った DATE 列 `snapshot_date` である。プルーニングはパーティション列への述語にしか効かない。

### Minor

- **n-1. `{{ audit_key() }}` の本体が無い。** 同じ §5 で `date_key` はマクロ定義を見せているのに、`audit_key` は「定義は 10回」とだけ書いて未定義のまま2モデルで呼んでいる。印刷されたモデルはそのままでは `dbt compile` に通らない。I-5 の実害（0行化・二重化）は消えているので Minor だが、`date_key` の直後に3行のスタブを置けば読者が動かせる: `{% macro audit_key() -%} COALESCE((SELECT MIN(audit_key) FROM {{ ref('dim_audit') }} WHERE dbt_invocation_id = '{{ invocation_id }}'), -1) {%- endmacro %}`（本設計は 10回、と1行添える）。
- **n-2. §6 の新2行が §1 の判断表と表面上ぶつかる。** §1 は「「いつ何件」＝トランザクション」と言い切り、§6 は「日別の応募数は？（＝いつ何件）」に累積スナップショットを割り当てている。理由欄で説明はついているが、§1 の該当セルに「（この題材では応募のトランザクションファクトが無いので §6 の2行目を見る）」相当の一言があると、判断表を単独で読んだ読者が取り違えない。
- **n-3. `posting_days` を3回スキャンしている。** `application_cum` / `scout_cum` / 本体で3回参照する。`daily_applications` と `daily_scouts` を1つの CTE にまとめて `FULL OUTER JOIN` する必要は無いが、`application_cum` と `scout_cum` は同じ結合キーなので1つの CTE に畳める（`SUM(da.application_count)` と `SUM(ds.scout_count)` を並べる形）。読み手の視線移動が減る。
- **n-4. §3 の「すべて `applications` 側から降りてきた次元」。** 追加した `agency_key` は正典 §4 では「`job_postings.agency_id` またはスカウト送信者の所属」由来と定義されており、`applications` の列から直接降りてくるわけではない。「`applications` とその求人・スカウトから降りてきた次元」程度に直すと正確になる。
- **n-5. `DATE(agc.valid_to, 'Asia/Tokyo')` の境界。** `dim_company` と同じ書き方をコピーしているだけなので新規の欠陥ではないが、現行行の `valid_to` を `9999-12-31 23:59:59 UTC` で作ると JST 変換が DATE の上限を超えて実行時エラーになる。05回で SCD2 の番兵値を決めるときに「`9999-12-31 00:00:00 UTC` を使う」と釘を刺しておくとよい（この回では触れなくてよい）。

### 新規の Critical

無し。

---

## 4. 図・体裁の再確認

```
$ python3 ~/.claude/skills/svg-diagram/scripts/check_svg.py docs/data_mart_modeling/html/02_fact_types.html
0 errors, 0 warnings
```

図（`#dg-acc`）は今ラウンドで未変更。差分に SVG は含まれていない。

- `h2` は 1〜8 + 参照文献 の 9 本 ✅（節の増減なし）
- `<table>` 10 本すべてが `.table-wrap` の中 ✅（`grep -c` の 11 は CSS 定義1行分）
- `<pre><code>` 内に生の `<` / `>` はゼロ ✅（新規追加した `&lt;=` / `&gt;=` / `&lt;` も正しくエスケープされている）
- 段落の文数: 追加された6段落を含め、4文以上の `<p>` はゼロ ✅。緩衝語（「でしょう」「かもしれません」「と言え」ほか）の出現ゼロ ✅
- 正典に無いテーブル名・列名の持ち込みは無し ✅（新規に登場したのは `dim_agency` / `agency_key` のみで、いずれも正典 §4 にある）

---

## 5. 総合判定

**REVISE**

- 初回指摘: addressed **14** / not addressed **0**
- 新規 Critical: **0**
- 新規 Important: **2**（N-1 `scout_count_cum` が `S003` を落としている／N-2 パーティション列と述語の不一致で「1パーティション読み」が成り立たない）
- 新規 Minor: 5

修正ラウンド1 の品質は高い。特に I-2 を機械的に適用せず、window 関数のままでは増分実行で累計が壊れることを自分で見抜いて `application_cum` / `scout_cum` に置き換えた判断は正しく、静的検証でも正しい結果を返す。残る2件はどちらも数語〜数行の局所修正で、どちらも「正典サンプル `S003` への追従」「主張とコードの一致」という初回レビューと同じ性質の漏れである。この2件が直れば APPROVE 相当。
