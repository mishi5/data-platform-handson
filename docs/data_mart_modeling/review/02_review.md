# 02 ファクトの3型とファクトレス — レビュー

対象: `docs/data_mart_modeling/html/02_fact_types.html`（862 行）／ブリーフ `briefs/02.md`／報告 `reports/02_report.md`
正典: `canon/domain.md`（`dim_agency` 追加後の版）、`canon/style.md`、`canon/references.md`

---

## 1. ブリーフ準拠表

| 節 | 必須項目 | 判定 | 該当箇所 |
|---|---|---|---|
| §1 | 3型 + ファクトレスの比較表（粒度 / 行の増え方 / 更新の有無 / 日付キーの数 / 典型の問い） | ✅ | 「4つの型を1枚の表で」。加法性の行を追加している（加点） |
| §1 | CareerVoice の10ファクトを型に分類（domain.md §3） | ✅ | 「CareerVoice の10ファクトを型に分類する」。10本すべて登場・型/粒度/更新/日付キー数が正典と一致 |
| §2(a) | `fct_job_posting_daily` を作らず `posted_at`/`closed_at` で「4/15 時点の掲載中求人数」→ `closed_at` が後から埋まる問題 | ✅ | §2(a)。再掲載での上書き / 論理削除 / その日限りの派生値の3点 |
| §2(b) | `fct_application_pipeline` を UPDATE 運用 → ストリーミングバッファ / DML 制約（→ 09回へ送る） | ✅ | §2(b)。末尾で「09回」へ明示送付 |
| §2(c) | `rejected` と `withdrawn` を「終了」に丸めて歩留まりが読めなくなる | ✅ | §2(c)。`is_rejected` / `is_withdrawn` を別メジャーにする決定まで書いている |
| §3 | 累積スナップショットの「複数日付キー・ラグ計測・行の再訪」 | ✅ | 「3型の定義」表 + DT#77 節 |
| §3 | 定期スナップショットの半加法性 | ✅ | 「定期スナップショットの半加法性」 |
| §3 | ファクトレス2種（イベント記録型 / カバレッジ型） | ✅ | 「ファクトレス・ファクトの2種（DT#50）」表 |
| §3 | `fct_page_view` はイベント型として例示 | ✅ | 同節本文 |
| §3 | 「スカウト枠の付与」はカバレッジ型として例示 | ✅ | 同節末尾（`fct_contract_monthly` が役割を担う、と明示） |
| §5 | `fct_application_pipeline` を `selection_events` から PIVOT 的に組む dbt モデル（`MIN(IF(stage=...))`） | ✅ | §5 のモデル。P001 の7マイルストーンを正しく埋める（検算済み・下記 §3.1） |
| §5 | `-1` 日付キーの埋め方（`COALESCE(..., -1)`） | ✅ | `macros/date_key.sql` |
| §5 | `P001` の1行がどう埋まるかを表で | ✅ | 「`P001` の1行がどう埋まるか」7行の表。数値検算 OK |
| §5 | `fct_job_posting_daily` を `dim_date` との範囲結合で日次展開（`J001` の 4/1〜） | ✅ | §5 後半。`J001` の行の表つき。`days_since_posted` / `*_count_cum` 検算 OK |
| §6 | 「問い → 型」の表 | ⚠️ | 11行あるが**1行目が誤り**（Critical-1） |
| §7 | (a) スカウト枠は定期スナップショットか | ✅ | `<details>` に解答 |
| §7 | (b) `S002` は `fct_scout_funnel` でどの列がどう入るか | ✅ | 列 × 値 × 理由の表。正典の列名と完全一致 |
| §7 | (c) `is_unlocked` はメジャーかディメンションか | ✅ | 判断基準の表の行を適用した根拠つき |
| 図 | 累積スナップショットの1行が更新されていく様子（概念図型・時点6つ・ノード≤9・矢印は時間方向のみ・accent 1系統） | ✅ | `#dg-acc`。`check_svg.py` **0 errors, 0 warnings**（再実行で確認） |
| HTML | `<title>` 形式 / `p.meta` / 8節 / `&lt;` エスケープ / `.table-wrap` | ✅ | title・meta とも style.md の型どおり。h2 は 1〜8 + 参照文献。`<pre>` 内の生の `<`/`>` はゼロ。表10本すべて `.table-wrap` |
| 正典 | 本文のモデル名がすべて `domain.md` にある | ⚠️ | `stg_careervoice__{applications,job_postings,scouts,selection_events}` は命名規約どおりで問題なし。**`agency_key` / `dim_agency` が欠落**（Important-1） |
| 文体 | 1段落3文まで / 緩衝語なし / 一般論で終わらない | ✅ | 全 `<p>` を機械チェック。4文以上の段落はゼロ |
| 参照 | URL はすべて `references.md` にあるもの | ✅ | 8本すべて一致 |

---

## 2. 指摘一覧

### Critical

#### C-1. §6 の1行目「日別の応募数は？」→ `fct_selection_event` は答えられない

`selection_events.stage` の値集合は `document` / `first_interview` / `final_interview` / `offer` / `accepted` / `hired` / `rejected` / `withdrawn` の8値で、**`applied` は含まれない**（正典 §2、および本文 §2(c) が自ら「8値」と列挙している）。だから `fct_selection_event` には「応募した」という事象の行が1件も無く、`fct_selection_event` を日別に数えても出るのは選考イベント数であって応募数ではない。

本文自身がこの事実を前提に書いている点で内部矛盾になっている:
- §5 の PIVOT は `applied_date_key` だけ `selection_events` ではなく `applications.applied_at` から取っている
- `current_stage` の `ELSE 'applied'` は「選考イベントがまだ1件も無い」状態を表している

§1 の4型比較表でも「典型の問い = 「日別の応募数は？」／題材の例 = `fct_scout`, `fct_selection_event`」と並べており、同じ誤読を誘う。

**修正案**（どちらか）:
- (a) §6 の1行目を差し替える。問いを残すなら選択を変える:
  `「日別の応募数は？」／いつ何件起きたか` → `累積スナップショット（fct_application_pipeline）を applied_date_key で数える` ／ 理由 `1行 = 1応募なので、行を数えれば応募数になる。正典に「応募」単独のトランザクションファクトは無い（selection_events に applied ステージが無いため）`
- (b) 型のほうを残すなら問いを変える: `「日別のスカウト送信数は？」→ トランザクション（fct_scout）`、`「日別に一次面接が何件行われたか？」→ トランザクション（fct_selection_event）`

あわせて §1 の4型比較表の「典型の問い」も `「日別のスカウト送信数は？」` に直し、トランザクションの題材例から誤解を消す。

---

### Important

#### I-1. `fct_job_posting_daily` の `-1 AS agent_key` を `agency_key` に差し替える（正典更新への追従）

正典 §4 に `dim_agency`（`dim_agent` の縮約ディメンション, Type2, 自然キー `agency_id`）が追加され、`fct_job_posting_daily` の FK は `agency_key`（`-1` = 直接掲載）になった。本文は執筆時点の正典に無かったため `-1 AS agent_key` 固定で書かれており、現行正典に反する。該当は3か所。

1. §5 のモデル SELECT 節:

```
    -- 求人が持つのは agency_id までで、担当者（agent_id）は求人だけでは決まらない。
    -- 直接掲載も担当者未確定も -1（未知 = -1、DT#43）
    -1 AS agent_key,
```

**修正案**: `postings` CTE は既に `agency_id` を引いているので、そのまま縮約ディメンションに結ぶ。

```sql
    -- 担当者（agent_id）は求人だけでは決まらない。エージェンシー単位の
    -- 縮約ディメンション dim_agency に結ぶ。直接掲載（agency_id IS NULL）は -1
    COALESCE(agc.agency_key, -1) AS agency_key,
```

FROM 節に as-of 結合を1本足す（`dim_agency` は Type2）:

```sql
LEFT JOIN {{ ref('dim_agency') }} AS agc
    ON  agc.agency_id = pd.agency_id
    AND pd.full_date &gt;= DATE(agc.valid_from, 'Asia/Tokyo')
    AND pd.full_date &lt;  DATE(agc.valid_to,   'Asia/Tokyo')
```

2. モデル直後の2段落（「`agent_key` をここで `-1` に固定しているのは手抜きではない」「`agency_id` で結ぶと1求人 × 担当者数に行が増え…」）。論理そのものは正しく、**縮約ディメンションを導入する理由の説明として書き直すのが素直**。

**修正案（差し替え文案）**:
> `job_postings` が持つのは `agency_id`（会社としてのエージェンシー）までで、`dim_agent` の粒度である担当者は求人だけでは決まらない。担当者ディメンションに `agency_id` で結ぶと1求人 × 担当者数に行が増え、**粒度宣言（1行 = 1求人 × 1日）が壊れる**。だからここは `dim_agent` を `agency_id` 粒度へ畳んだ**縮約ディメンション `dim_agency`**（DWT ch.4）に結ぶ。直接掲載（`agency_id` が NULL）は `-1`。担当者別に見たい問いは `fct_scout` / `fct_placement` 側で答える。

3. §1 の10ファクト分類表・§3・§6 に `agent_key` の記述は無いため、この3か所だけで閉じる。なお `fct_application_pipeline` 側の `agent_key`（`applications.scout_id` → `scouts.sender_agent_id` で解決、無ければ `-1`）は**正典どおりなので変更不要**。

#### I-2. §5 の `fct_job_posting_daily` の実装が、§2(a) と §4 の主張を満たしていない

§2(a) の結論は「定期スナップショットを持てば、答えは `WHERE snapshot_date_key = 20260415` の**1パーティション読み**になり、**いつクエリを流しても同じ数字が返る**」。§4 は同じモデルについて `materialized='incremental'` + `insert_overwrite` + `partition_by={'field':'snapshot_date',...}` を示し「不変パーティションの積み上げ」と書く。

ところが §5 の実装は `{{ config(materialized='table') }}` のみで、

- `partition_by` が無い → `WHERE snapshot_date_key = 20260415` はフルスキャンになり「1パーティション読み」にならない
- 毎回 `job_postings` の**現在値**（`closed_at`、論理削除）から全期間を再展開する → §2(a) が「壊れている」と断じたソース再構成クエリと**同じ弱点**を持つ。再掲載で `closed_at` が NULL に戻れば、次回ビルドで過去日の行が変わる

つまりこの回の中心主張を、この回のコードが裏切っている。

**修正案**: §5 のモデル冒頭 config を §4 のものに揃え、`posting_days` を「この実行日のパーティションだけを作る」形にする（過去分の再展開をやめる）。最小の差分:

```sql
{{ config(
    materialized='incremental',
    incremental_strategy='insert_overwrite',
    partition_by={'field': 'snapshot_date', 'data_type': 'date', 'granularity': 'day'}
) }}
```

かつ `posting_days` の範囲結合に、増分時は当日（＋ルックバック）だけへ絞る述語を足す:

```sql
    INNER JOIN {{ ref('dim_date') }} AS d
        ON d.full_date BETWEEN p.posted_date
                           AND COALESCE(p.closed_date, CURRENT_DATE('Asia/Tokyo'))
    {% if is_incremental() %}
    WHERE d.full_date &gt;= DATE_SUB(CURRENT_DATE('Asia/Tokyo'), INTERVAL 3 DAY)
    {% endif %}
```

そのうえで1行添える: 「**過去のパーティションは二度と作り直さない。これが「いつ流しても同じ数字」の実体である**（ルックバック幅の設計は 09回）」。正典 §6 の「増分の単位: パーティション単位の `insert_overwrite`、ルックバック 3 日」とも揃う。

#### I-3. 掲載終了日の扱いが §2(a) と §5 で1日ずれている

- §2(a) の「壊れている」クエリ: `closed_at IS NULL OR DATE(closed_at) &gt; '2026-04-15'` → **終了日当日は掲載中に数えない**
- §5 の正解実装: `d.full_date BETWEEN p.posted_date AND COALESCE(p.closed_date, CURRENT_DATE(...))` → **終了日当日も `is_open = 1` で数える**

同じ「4/15 時点の掲載中求人数」を出す2つのクエリが、4/15 に閉じた求人について異なる答えを返す。§2(a) は「両者が食い違うこと」ではなく「片方が再現性を欠くこと」を論点にしている節なので、境界の食い違いは論点をぼかす。

**修正案**: どちらかに統一し、選んだ規約を1文で明示する。`closed_at` を「掲載が閉じた瞬間」と読むなら終了日当日は掲載中ではないので、§5 を半開区間に直すのが筋が通る:

```sql
    INNER JOIN {{ ref('dim_date') }} AS d
        ON  d.full_date &gt;= p.posted_date
        AND d.full_date &lt;  COALESCE(p.closed_date, DATE_ADD(CURRENT_DATE('Asia/Tokyo'), INTERVAL 1 DAY))
```

（`J001` は `closed_at` が NULL なので、本文の `J001` の表と `days_since_posted` の値は上記に直しても変わらない。検算済み。）

#### I-4. ディメンションキーが LEFT JOIN のまま NULL になりうる — 本文の「NULL の外部キーを作らない」に反する

§1 の判断表と §6 は「FK に NULL を入れない（DT#43）」を明示の決定として掲げ、§5 の `schema.yml` は `relationships` テストを張っている。ところが `fct_application_pipeline` の SELECT で `-1` に落としているのは `agent_key` だけで、`mem.member_key` / `co.company_key` / `jp.job_posting_key` / `jc.job_category_key` / `ch.channel_key` はすべて素の LEFT JOIN 結果である。`dim_member` の SCD2 区間が応募時刻をカバーしない（遅延到着や区間の穴）と `member_key` は NULL になり、`relationships` テストは NULL 行を無視するので**素通りする**。`fct_job_posting_daily` 側の `jp.job_posting_key` / `co.company_key` / `jc.job_category_key` も同じ。

**修正案**: 全ディメンションキーを同じ形で包み、規約であることを見せる。

```sql
    COALESCE(mem.member_key, -1) AS member_key,
    COALESCE(co.company_key,  -1) AS company_key,
    COALESCE(jp.job_posting_key,   -1) AS job_posting_key,
    COALESCE(jc.job_category_key,  -1) AS job_category_key,
    COALESCE(ch.channel_key,       -1) AS channel_key,
    COALESCE(ag.agent_key,         -1) AS agent_key,
```

`schema.yml` にも `member_key` の `not_null` を1本足すと、`-1` 方式の効用（`not_null` と `relationships` を両立できる）を主張している直後の記述と噛み合う。あわせて本文に1行: 「**未達だけでなく、ディメンション側に該当行が無い場合も `-1` に落とす**（DT#43 の「未知」）」。

#### I-5. `dim_audit` を `CROSS JOIN` で結ぶと、ファクトが丸ごと空になるか二重化する

2本のモデルとも `audit` CTE を `CROSS JOIN` している。

```sql
audit AS (
    SELECT audit_key FROM {{ ref('dim_audit') }}
    WHERE dbt_invocation_id = '{{ invocation_id }}'
)
...
FROM applications AS a
CROSS JOIN audit AS aud
```

`dim_audit` に当該 `invocation_id` の行がまだ無い場合（`dim_audit` が同一 run 内でファクトより後に走る、`--select` で部分実行する、初回実行など）**CROSS JOIN の結果は 0 行**になり、ファクトが黙って空のテーブルとしてビルドされる。逆に同一 `invocation_id` に行が2本あれば全ファクト行が2倍になり、粒度宣言が壊れる（`application_id` の `unique` テストが落ちて初めて気づく）。

**修正案**: スカラーサブクエリにして常に1値へ潰し、無ければ `-1` に落とす。

```sql
    COALESCE((
        SELECT MIN(audit_key) FROM {{ ref('dim_audit') }}
        WHERE dbt_invocation_id = '{{ invocation_id }}'
    ), -1) AS audit_key,
```

こうすれば `audit` CTE と `CROSS JOIN` が両モデルから消え、行数に一切影響しなくなる。監査ディメンションのロード順序という 10回の論点にも踏み込まずに済む（報告の「正典への変更提案 3」で執筆者自身が挙げている懸念に対する最小の回答でもある）。

#### I-6. DT#95 の aside に、原典が言っていない主張が混ざっている

```
Kimball の主張（DT#95）: ヘッダの次元性をすべて明細に降ろす。ヘッダの伝票番号は退化ディメンション
としてファクトに残し、それ専用のディメンション表は作らない。ヘッダ単位の金額（送料など）は明細に
按分するか、按分できないなら別ファクトにする。
```

DT#95 本文（WebFetch で確認）にあるのは前2文だけである。Bad Idea #1（ヘッダを大きなディメンションにする。「5 明細/伝票ならディメンションはファクトの 20% の大きさになる」）、Bad Idea #2（ヘッダを別ファクトにして明細から結合させる）、そして「ヘッダの次元性をすべて明細に降ろし、伝票番号は退化ディメンションにする」。**ヘッダ単位金額の按分は DT#95 に出てこない**。さらに「按分できないなら別ファクトにする」は、同じ tip の Bad Idea #2（ヘッダを別ファクト化する）と字面上ぶつかって読める。

**修正案**: 3文目を aside から外し、本文側に出典を分けて置く。

> `<div class="aside kimball">` は前2文で閉じる。3文目は aside の外に、こう書く:
> 「ヘッダ単位の金額（送料のような、明細に自然に割り当てられない額）の扱いは DT#95 の範囲外で、DWT ch.6 が明細への按分を勧める。按分できない額のためにヘッダ粒度のファクトを別に置く場合も、**明細ファクトがそこへ結合しに行かない**点で Bad Idea #2 とは別物である。」

この題材では該当する金額が無い（`applications` はヘッダ金額を持たない）ので、1文に削って落としてもよい。

---

### Minor

#### m-1. `-1 AS agent_key` / `COALESCE(..., -1)` がサロゲートキーの型を先取りしている

正典 §4 は「サロゲートキーは…INT64 か dbt_utils の STRING — **03回で判断を扱う。それ以外の回は `_key` と書くだけで型に踏み込まない**」と決めている。裸の `-1`（INT64 リテラル）はこの取り決めを踏み越えている。I-1 / I-4 の修正で `COALESCE(..., -1)` が増えるので、1行だけ注記を添えるのが安い: 「`-1` は INT64 キーを前提にした表記。STRING キーなら `'-1'`（型の判断は 03回）」。`date_key` は正典で INT64 と確定しているので対象外。

#### m-2. `fct_application_pipeline` に `partition_by` が無いのに「パーティション用の DATE 列」を選んでいる

```sql
    DATE(a.applied_at, 'Asia/Tokyo') AS applied_date,   -- パーティション用の DATE 列
```

正典は「`partition_by` はこの DATE 列に張る」と決めているが、config は `materialized='table'` のみ。コメントと config が食い違う。`config` に `partition_by={'field': 'applied_date', 'data_type': 'date', 'granularity': 'day'}` を足すか、コメントを「09回でパーティションを張る列」に直す。

#### m-3. `fct_application_pipeline` の SELECT に `member_profile_mini_key` が無い

正典 §4 の FK 列に `member_profile_mini_key`（応募時点）が含まれる。本文は直後の段落で「同じ形で足す。解決は 03回、時点の合わせ方は 05回」と断っており欠落の自覚はあるが、SQL に `-- member_profile_mini_key はここに同じ形で足す（03回 / 05回）` の1行コメントを置けば、正典との差が読み手に見える。

#### m-4. 「3型は並存しうる」の帰属

`<div class="aside kimball">` の「Kimball の主張（Fact Tables, 2008）」に「3型はどれかを選ぶものではなく、同じビジネスプロセスに対して並存しうる」を含めている。Fact Tables（2008）本文で確認できたのは3型の定義・密度・行の再訪・粒度は「1レコードが業務上何を表すかの定義」・単価と金額の加法性であり、「並存しうる」は DWT ch.4（在庫章の3型比較）側の主張。帰属を `（Fact Tables, 2008 / DWT ch.4）` に直す。他の3つの aside（DT#50 / DT#77 / DT#95 の前2文）は原文と一致していることを確認済み。

#### m-5. 掲載期間外に届いた応募・スカウトが累積カウントから落ちる

`daily_applications` / `daily_scouts` は `pd.full_date`（＝掲載中の日）でしか結合しないので、`closed_date` より後に届いた応募は `application_count_cum` に一生入らない。`J001` は `closed_at` が NULL なので本文の表は正しいが、閉じた求人では累計が過小になる。「累計は掲載期間内の分だけを数える」と1行で断るか、`daily_applications` 側を `MIN(pd.full_date)` 以降で丸める。

#### m-6. `P001` の表のヘッダが正典の列名と一致しない

`first_iv` / `final_iv` は表示上の短縮で、正典の列名は `first_interview_date_key` / `final_interview_date_key`。「一般論で終わらせず具体列名で語る」という style.md の方針からは、`<th>` に `first_interview` / `final_interview` と書いて `.table-wrap` の横スクロールに任せるほうがよい。

#### m-7. 「同一テーブルへの変更 DML は同時実行が制限される」は現在の BigQuery の挙動から少しずれる

BigQuery は現在、変更 DML をスナップショット分離で同時実行し、競合したものはキューに入れて再試行する（衝突しても即エラーではない）。§2(b) の結論（行単位 UPDATE 運用は破綻する）は変わらないので、表現を「大量の行単位 DML はキューイングと再試行のコストで詰まる」程度に緩めれば十分。

---

## 3. 検算結果（オーケストレータ指定分）

### 3.1 `fct_application_pipeline` の PIVOT は `P001` の7マイルストーンを埋めるか — **埋まる**

`selection_events` に P001 の行が6件（7/1 document, 7/8 first_interview, 7/15 final_interview, 7/20 offer, 7/22 accepted, 8/1 hired）、応募日 6/23 は `applications.applied_at` から取る。

- `MIN(IF(stage='X', occurred_at, NULL))` は該当ステージが無ければ全行 NULL → `MIN` は NULL を返す → `date_key()` が `-1` に落とす。**7マイルストーン + `closed` の8本すべて正しく埋まる。**
- `date_key` マクロ `COALESCE(CAST(FORMAT_DATE('%Y%m%d', DATE(ts,'Asia/Tokyo')) AS INT64), -1)`: BigQuery の `FORMAT_DATE(format, date)` の引数順で正しい。NULL 入力 → `DATE()` NULL → `FORMAT_DATE` NULL → `CAST` NULL → `-1`。**動く。**
- `closed_date_key = date_key(COALESCE(hired_at, rejected_at, withdrawn_at))` → 8/1 のみ `20260801`、それ以前は `-1`。**表と一致。**
- `current_stage` の `CASE`（hired → withdrawn → rejected → accepted → offer → final → first → document → ELSE 'applied'）は表の7時点すべてで表の値と一致。
- `days_applied_to_offer` = `DATE_DIFF('2026-07-20','2026-06-23')` = **27** ✅（本文と一致）
- `days_offer_to_hired` = `DATE_DIFF('2026-08-01','2026-07-20')` = **12** ✅（本文と一致）
- 構文: `CROSS JOIN` の後に `LEFT JOIN ... USING (application_id)` を置く形は、`application_id` が左側（`a`）にのみ存在するので BigQuery で通る。`USING` 後に `a.application_id` を修飾参照するのも BigQuery では合法。`scout_id` が NULL の応募は `scouts` に一致せず `agent_key` が `-1` になる（本文の記述どおり）。**構文エラーは無い。**

唯一の穴は I-5（`CROSS JOIN audit` の 0 行 / 二重化）と I-4（残り5本のキーが NULL になりうる）で、**PIVOT のロジック自体には誤りが無い**。

### 3.2 `fct_job_posting_daily` の日次展開は `J001` で1日1行になるか — **なる（境界1日ぶんの注意あり）**

`J001` は 4/1 掲載・`closed_at` NULL なので `d.full_date BETWEEN '2026-04-01' AND CURRENT_DATE('Asia/Tokyo')` に一致し、`dim_date` の日付行と1対1で**4/1 から今日まで1日1行**。`dim_date` の `-1` 行は `full_date` が NULL で `BETWEEN` が NULL 評価され INNER JOIN から落ちるので混ざらない（本文の記述は正しい）。

数値検算（すべて本文の表と一致）:

| `snapshot_date_key` | `days_since_posted` = `DATE_DIFF(d, 2026-04-01)` | `scout_count_cum` | `application_count_cum` |
|---|---|---|---|
| 20260401 | 0 ✅ | 0 ✅ | 0 ✅ |
| 20260415 | 14 ✅ | 0 ✅ | 0 ✅ |
| 20260620 | 80 ✅（4月29 + 5月31 + 6月20） | 1 ✅（`S001` 6/20 送信） | 0 ✅ |
| 20260623 | 83 ✅ | 1 ✅ | 1 ✅（`P001` 6/23 応募） |

累積の窓 `SUM(...) OVER (PARTITION BY pd.job_posting_id ORDER BY pd.snapshot_date_key)` は既定フレーム（`RANGE UNBOUNDED PRECEDING 〜 CURRENT ROW`）で走る。`audit` の `CROSS JOIN` が1行を返す限り (`job_posting_id`, `snapshot_date_key`) は一意なので `RANGE` でも重複加算は起きない — ただし I-5 の二重化が起きると、この累積は黙って2倍になる。

境界: I-3 のとおり終了日当日の扱いが §2(a) と食い違う。`J001` は無期限掲載なので**表の値は修正後も変わらない**。

### 3.3 `-1` の埋め方 — **一貫している。ただし対象が狭い**

日付キーは `date_key` マクロで全 8 本が `-1` に落ちる ✅。演習 (b) の「キーは `-1`、ラグは NULL、フラグは 0」の3分法も正典・DT#43 と整合 ✅。`dim_date` の `-1` 行（`full_date` = NULL, 表示名「未到達」）の前提も 03回の裁定と一致 ✅。抜けているのは**ディメンションキー側**で、これが I-4。

---

## 4. その他の確認（問題なし）

- `check_svg.py`: `0 errors, 0 warnings`（再実行して確認）。図はノード6個 + 説明で密度予算内、矢印は時間方向の5本のみ、accent は `cell-on` の1系統、ダーク3系統（`prefers-color-scheme` / `[data-theme=dark]` / `[data-theme=light]`）、marker id は `dg-acc-a` で前置済み。`accepted`（7/22）省略の注記も図中にある。
- 正典の列名: `fct_scout_funnel`（演習 b）、`fct_contract_monthly`（演習 a）、`dim_page_context`（演習 c）、`selection_events` / `applications` / `job_postings` / `scouts` のソース列は**すべて正典と一致**。正典に無い列・テーブルの持ち込みは無い（`dim_application` を作らなかったのは正しい判断）。
- サンプル値: `AG01` = エージェント（佐藤）／`A01` = キャリアブリッジ、`S002` は `AG01` → `M003`・`J002`・6/25 送信・未開封 — 正典 §5 と一致。
- 参照文献の URL 8本はすべて `references.md` 由来。DWT ch.4・Fact Tables・DT#50 #95 というブリーフ指定に、実際に使った DT#43 #77 を足した `p.meta` の形も style.md どおり。
- §8 は5項目、`dbt_logs_analysis` / `news_pipeline` への言及はこの節のみ、`raw_articles.content_status` の遷移（`pending → ok → summarized / failed / filtered`）も実際のコードと一致。「試せる種」も1行ある。
- §4 で未割当文献（FDE snapshotting / dbt BigQuery configs）を使った点は裁定済みのため指摘しない。`current_stage` の初期値 `applied` も正典採用済みのため指摘しない。

---

## 5. 総合判定

**REVISE**

- Critical: 1（C-1 §6 の「日別の応募数 → `fct_selection_event`」）
- Important: 6（I-1 `agency_key` 差し替え／I-2 §5 の materialization が §2(a)・§4 の主張を満たさない／I-3 終了日境界の1日ずれ／I-4 ディメンションキーの NULL FK／I-5 `CROSS JOIN dim_audit`／I-6 DT#95 aside の帰属）
- Minor: 7

原稿の骨格・検算・図・正典準拠はいずれも水準が高く、修正はすべて局所的。**最優先は I-1（正典追従）と C-1（誤った判断基準）**、次いで I-2（この回の主張とコードの整合）。
