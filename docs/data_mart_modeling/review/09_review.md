# 09 増分・遅延到着・冪等性 — レビュー

対象: `docs/data_mart_modeling/html/09_incremental.html`
ブリーフ: `docs/data_mart_modeling/briefs/09.md` ／ 報告: `docs/data_mart_modeling/reports/09_report.md`

---

## 1. ブリーフ準拠表

| # | 必須項目 | 判定 | 該当箇所 |
|---|---|---|---|
| §1 | 増分3方式（`append` / `merge` / `insert_overwrite`）の表 | ✅ | L53–89。`append` を「`unique_key` 無しの `merge`」として扱う整理は裁定済みで可。`microbatch` の行を足しているのも可 |
| §1 | BigQuery での挙動（DML 制限・パーティション置換・コスト） | ✅ | L53–89。「BigQuery が実行する DML」「課金スキャン」列。静的 `insert_overwrite` の `WHEN NOT MATCHED BY SOURCE … THEN DELETE` は dbt docs と一致（下記 §2） |
| §1 | `fct_page_view`=insert_overwrite 日次 | ✅ | L96 |
| §1 | `fct_scout`=insert_overwrite | ✅ | L97 |
| §1 | `fct_application_pipeline`=merge（累積型） | ✅ | L98 |
| §1 | `fct_contract_monthly`=月パーティション置換 | ✅ | L99 |
| §2(a) | `> MAX(sent_at)` 境界で 6/20 に届いた 6/18 分が永久欠損 | ✅ | L107–116。`S003`（`AG02` → `M002`, 6/18 送信）で具体化。正典のサンプル値と一致 |
| §2(b) | 累積スナップショットを `append` にして `P001` が7行 | ⚠️ | L211–213。7行になること自体は正しいが、`SUM(is_hired)` の値が誤り（→ I3） |
| §2(c) | 遅延到着ディメンション（`C002` の 5/1 変更が 5/3 到着、5/1–5/2 のファクトが旧版キー） | ✅ | L215–219 |
| §2(d) | 冪等でない処理の再実行で二重計上 | ✅ | L221–223。`K001`（枠 200 → 合計 400）。検算一致 |
| §3 | ETL Toolkit の遅延到着ファクト（当時の版で SK 解決） | ✅ | L245–252 |
| §3 | 遅延到着ディメンション（仮キー → 後で更新） | ✅ | L253–262（遡及版挿入＋FK貼り替え／自然キーだけの仮行の2行に分割） |
| §3 | 監査ディメンションによる追跡 | ✅ | L231–241 の #6 行、L276–284 の対比表、L286–290 |
| §3 | サブシステム番号の対応 | ✅ | #2 CDC / #6 Audit Dimension Creation / #13 Fact Table Builders / #14 Surrogate Key Pipeline / #16 Late Arriving Data Handler / #24 Recovery and Restart — 原典 6/6 一致（WebFetch 照合済み） |
| §4 | FDE「パーティションを不変の単位にして丸ごと上書き」 | ✅ | L270–274 |
| §4 | FDE「タスクは純関数」 | ✅ | L270 |
| §4 | dbt の `insert_overwrite` + `partitions` がそれを実装する | ⚠️ | L276–284 の対比表「再実行」行で実質的に書かれているが、地の文での明示は無い（→ M6） |
| §4 | ルックバック窓の考え方（遅延の分布から決める。ここでは3日） | ✅ | L286–290。p99 を覆う最小日数、当日+過去3日=4パーティション。§4.1・§6.1・図と数値が一致 |
| §4 | FDE 要点の要約が原文どおりか | ❌ | L274。「処理時刻ではなくイベント時刻で」が引用元の記述と逆（→ I2） |
| §5(a) | `fct_scout` の `materialized='incremental'` / `insert_overwrite` / `partition_by` / 静的 `partitions` | ⚠️ | L296–373。config は dbt docs どおり。ただし `cluster_by` が正典と違う（→ I1） |
| §5(a) | ルックバック内は全パーティション置換で冪等 | ✅ | L322–331（config の `partitions` と同じ集合でソースも絞る）、L375–382 の静的/動的/`copy_partitions` 比較表 |
| §5(b) | `merge`（`unique_key='application_id'`）と対象を絞る CTE | ✅ | L386–460。`touched` CTE（`selection_events` ∪ `applications` のルックバック窓）＋ `incremental_predicates`（`DBT_INTERNAL_DEST.applied_date`）。窓不足で2行になる失敗も明示（L458） |
| §5(c) | 遅延到着ディメンション修復の `MERGE`（対象パーティションだけ） | ✅ | L478–506。`ON` 句に `t.submitted_date between …` を置いてターゲット側もプルーニング。更新は `company_key` / `audit_key` のみ |
| §5(d) | 同じ `--vars run_date` で2回流して比較する手順 | ✅ | L517–557。`COUNT(*)` / `SUM(scout_count)` / `BIT_XOR(FARM_FINGERPRINT(...))` を `EXCEPT DISTINCT` 双方向で突合。実際に比較可能（下記 §3） |
| §6 | 「ファクトの型 × 遅延の有無 × 行数 → 方式とルックバック」の表 | ⚠️ | L580–593。7行で網羅的。ただし「ファクトの型」の列にディメンションが例示されている（→ M4） |
| §7(a) | `fct_page_view` のルックバック日数と、決めるために測るもの | ✅ | L605–633。`dim_audit.loaded_at` との差の分位点＋`INFORMATION_SCHEMA.PARTITIONS`。列名は実在 |
| §7(b) | `fct_job_posting_daily` の増分単位は「日」か「求人」か | ✅ | L635–649。「日」＋累計列の定義注意 |
| §7(c) | `dim_member_daily` が1日欠けた時の as-of join の壊れ方と埋め方 | ⚠️ | L651–675。内容は妥当だが §5a への参照が食い違い（→ M3）、段落が4文（→ M2） |
| 図 | 概念図型・横軸 6/17〜6/21・上段 発生日／下段 到着日 | ✅ | L118–209 |
| 図 | 6/18 発生・6/20 到着を accent | ✅ | `S003` が `box-focal`、`lead-focal` の折れ線で 6/20 の到着ノードへ |
| 図 | `> MAX(date)` 境界と3日ルックバック窓を2本の縦線/帯、前者が取りこぼす様子 | ✅ | 帯を採用（report の判断9）。旧方式の帯は x=504–752（6/20 以降）、採用案の帯は x=120–624（6/17–6/20）で、6/18 の破線が後者だけを貫く。ブリーフの「縦線/帯」の後者 |
| 図 | ノード ≤9 | ✅ | ボックス5・矢印3 |
| 図 | `check_svg.py` 0 errors | ✅ | 再実行して `0 errors, 0 warnings` |
| HTML | `<title>` = `<タイトル> — データマート設計 09` | ✅ | L6 |
| HTML | `p.meta` | ⚠️ | L43。形式は正しいが、本文で使っている DT#43 と dbt microbatch が入っていない（→ M7） |
| HTML | 8節構成 | ✅ | 1–8 + 参照文献 |
| HTML | `&lt;` エスケープ | ✅ | `<pre>` 内に生の `<` 無しをスクリプトで確認 |
| HTML | `.table-wrap` | ✅ | `<table>` 7個すべてが `.table-wrap` 内 |
| 正典 | テーブル名・列名 | ⚠️ | 本文の `fct_*` / `dim_*` / `stg_careervoice__*` を機械抽出して照合。正典外は `fct_scout__fingerprint`（検証用一時表・裁定済みで可）と `mart_url_performance_incremental`（8節）のみ。列名も `dim_member_daily` の全列を含めて正典どおり |
| 正典 | `-1` 処理（DT#43） | ✅ | `coalesce(…, -1)` を全 FK に。`offer_date_key` / `hired_date_key` の未達も `-1` |
| 正典 | 固定判断「増分の単位はパーティション単位の `insert_overwrite`、ルックバック3日」 | ✅ | §1.2・§4.1・§5(a)・§6 で一貫 |

---

## 2. 外部照合の結果（WebFetch）

| 検証項目 | 結果 |
|---|---|
| dbt-bigquery の `incremental_strategy` は `merge` / `insert_overwrite` / `microbatch` の3つ、`append` は無い | **正しい**（bigquery-configs）。L50 の注記は妥当 |
| 静的 `partitions` が生成する SQL | **正しい**。docs の生成例は `merge … on FALSE / when not matched by source and {{partition_column}} in unnest(dbt_partitions_for_replacement) then delete / when not matched then insert`。L378 の記述と一致 |
| 動的置換と `_dbt_max_partition` | **正しい**。「一時表を作り、distinct なパーティションを検出」「`_dbt_max_partition` は BigQuery の SQL 変数」も docs どおり |
| `copy_partitions` は `partition_by` の内側・動的置換のみ | **正しい**。docs の原文 "This approach works only in combination with 'dynamic' partition replacement" / "the copy table API does not incur any costs for inserting the data"。L380 の「動的置換のみ」「挿入の課金が無い」は原文に対応 |
| `insert_overwrite` が `partition_by` を要求する | **正しい**。docs 明記 |
| `microbatch` の `lookback` 既定 1・dbt 1.9 以降・BigQuery では内部的に `insert_overwrite`・`partition_by` 必須 | **正しい**（incremental-microbatch）。L80–87、L290 と一致 |
| ETL サブシステム #2 #6 #13 #14 #16 #24 の名称 | **正しい**。Subsystems of ETL Revisited の一覧と 6/6 一致 |
| FDE（ssp.sh）の要点 | **一部不一致**。"Pure, idempotent tasks: … reruns overwrite rather than append" / "Immutable partitions: the partition (not the row) is the atomic unit of state" / "One task → one table, one task instance → one partition" は本文どおり。ただし **"No past dependencies; partition on processing time: keeps backfills parallelizable and cleanly handles late-arriving facts"** であり、本文 L274 の「処理時刻ではなくイベント時刻で…バックフィルを並列化」は逆（→ I2） |
| 手元の基盤（8節）の事実 | **正しい**。`mart_url_performance_incremental` は `unique_key=['url_path','date']`・`partition_by` が `date`(DATE)・境界 `WHERE DATE(request_timestamp) > (SELECT MAX(date) FROM {{ this }})`・`incremental_strategy` 未指定＝既定 `merge`。`news_pipeline` の `summaries` は `infra/bigquery.tf` にパーティション指定なし・`insert_rows_json` |

---

## 3. SQL / dbt の静的検証

読んだ結果、**構文で落ちる箇所は無い**。個別に確認した点:

- L296–373 `fct_scout`: `{% set %}` → `{{ config() }}` の順、`run_started_at.strftime` は dbt の Jinja コンテキストに実在。`partitions` の各要素が `date_sub(date '…', interval N day)`（DATE 型）で、`partition_by.data_type='date'` と型が合う。config の `partitions` とソースの `WHERE … IN (…)` が同じリストを `join(', ')` で展開しており、置換範囲とソース範囲が一致する（静的置換で最も壊れやすい点をおさえている）。
- ルックバックの `WHERE` は `date(s.sent_at, 'Asia/Tokyo') in (…)` で、比較の型は DATE。ターゲットのパーティション列 `sent_date` と一致する。`sent_date_key`（INT64）で絞っていない旨も L103 に明記されており、指示された検算どおり。
- L338–345 `member_snapshot`: `require_partition_filter=true` の `dim_member_daily` を `WHERE` 側で絞る形。JOIN の `ON` に置くと要件を満たさない場合があるため、この書き分けは正しい。
- L386–460 `fct_application_pipeline`: `incremental_predicates` の別名 `DBT_INTERNAL_DEST` は dbt の規約どおり。`touched` は `is_incremental()` の外で定義され初回実行では未参照だが、BigQuery は未参照 CTE を許容するのでエラーにはならない。
- L462–474 の計測クエリ: `group by p.application_id, p.applied_date` と `date_diff(max(e.event_date), p.applied_date, day)` は整合。`fct_selection_event.event_date` は正典 §4 の「`<role>_date` を持つ」からの導出で可。
- L478–506 の修復 `MERGE`: BigQuery の `MERGE INTO … AS t` は合法。`ON` 句にターゲットのパーティション述語を置いており（指示された検算項目）、ターゲット側のプルーニングが効く。`USING` 側は `reviews` × `dim_company` の as-of 結合で `review_id` ごとに最大1行、`WHEN MATCHED` のみでも `MERGE` は成立する。更新列は `company_key` / `audit_key` のみ。
- L520–557 の冪等性検証: 1回目 → 指紋表を `CREATE OR REPLACE` → 2回目 → `EXCEPT DISTINCT` 双方向、という順序で**実際に比較可能**。窓 `between '2026-06-17' and '2026-06-20'` は `run_date=2026-06-20` の置換対象4パーティションと一致する。`TO_JSON_STRING((SELECT AS STRUCT t.* EXCEPT (audit_key)))` は BigQuery の行ハッシュの定型で、相関参照も合法。`BIT_XOR` は順序非依存で、同一行の偶数回重複が打ち消される弱点は同じ行の `COUNT(*)` が拾う。
- L559–576 `schema.yml`: `data_tests:` キー・`dbt_utils.expression_is_true` の形とも妥当。`where` を使っていないので「`where` は各テストの `config:` に書く」規約には抵触しない。
- L664–674 の carry-forward `INSERT`: 列は正典の `dim_member_daily` の定義と完全一致。

---

## 4. 指摘一覧

### I1 (Important) — `fct_scout` の `cluster_by` が正典と違う

**箇所**: L309 `cluster_by = ['scout_sender_key'],`

正典 `canon/domain.md` §4 の `fct_scout` は「**パーティション: `sent_date`、クラスタ: `scout_sender_key`, `member_key`**（07/09 回で共通）」。実際 07 回（`html/07_star_vs_obt.html` L323, L356）と 10 回（L312）は `['scout_sender_key', 'member_key']` で書いている。09 だけ `member_key` が落ちており、シリーズ内で同じテーブルの物理設計が2種類存在する状態。

**修正案**:

```
    cluster_by = ['scout_sender_key', 'member_key'],
```

あわせて `reports/09_report.md` の「正典への変更提案 2」は、正典側に既に明記されたため「提案」ではなく「正典に従った」に書き換える（提案文の `cluster_by = ['scout_sender_key']` が今回の食い違いの元になっている）。

### I2 (Important) — FDE の要約が引用元と逆（処理時刻／イベント時刻）

**箇所**: L274「…行単位の更新をやめて丸ごと置換すること、処理時刻ではなく**イベント時刻**でパーティションを切ってバックフィルを並列化できる形にすること。」

参照文献に挙げた `https://www.ssp.sh/brain/functional-data-engineering/` の該当箇条書きは "**No past dependencies; partition on processing time**: keeps backfills parallelizable and cleanly handles late-arriving facts."。本文は、原文の理由節（バックフィルの並列化）をそのまま借りたうえで、主張の中身だけを反対に置き換えている。`reports/09_report.md` の「読んだ文献と引用した要点」にも同じ反転（「処理時刻ではなくイベント時刻で切ると…」）が記録されており、要約段階での取り違えと見られる。

なお、この題材で `sent_date`（イベント時刻）にパーティションを切る決定自体は妥当で、dbt microbatch の `event_time` もそちら側。問題は**それを FDE の主張として書いていること**。style.md の「原典／再解釈／この題材の決定の3段」に沿って分ける。

**修正案**（L274 を2文に分ける）:

> この主張のうち増分に効くのは2点。パーティションを不変の単位として扱うこと、行単位の更新をやめて丸ごと置換すること。FDE は「過去への依存を持たず、実行日（処理時刻）でパーティションを切る」ことでバックフィルを並列化できるとするが、CareerVoice では `run_date` を与えた実行が `sent_date`（イベント時刻）のパーティションを置換する形にして、遅延分をルックバック窓で吸収する（dbt の `microbatch` が `event_time` として持つ側）。

### I3 (Important) — `SUM(is_hired)` が 7 を返すという検算が合わない

**箇所**: L213「…状態が動いた日の実行ごとに1行増えて7行になる。粒度宣言「1行 = 1応募のパイプライン」が壊れ、`SUM(is_hired)` は 1 ではなく 7 を返す。」

追記で7行になるとき、各行は**その実行時点の状態**を写したもの。`is_hired` が 1 になるのは `hired_at`（8/1）が観測できた最後の行だけで、6/23・7/1・7/8・7/15・7/20・7/22 の6行は `is_hired = 0`。したがって `SUM(is_hired)` は 7 ではなく 1（＝たまたま正しい値）を返す。ルックバック3日で同じ状態が複数回書かれる想定にしても、値は「入社後に走った実行回数」であって 7 にはならない。

壊れているのは行数側なので、指標もそちらで示すのが正しい。

**修正案**:

> …状態が動いた日の実行ごとに1行増えて7行になる。粒度宣言「1行 = 1応募のパイプライン」が壊れ、`COUNT(*)` は応募数 1 ではなく 7 を返し、`AVG(days_applied_to_offer)` は同じ応募を7回数えた平均になる。`SUM(is_hired)` が 1 のままなのは、入社を観測できた最後の1行しか `is_hired = 1` にならないからで、「壊れていても合う指標がある」ことがこの失敗を見つけにくくしている。

### I4 (Important) — 原典が「メジャーの書き換えを許していない」という記述は原典の歪み

**箇所**: L266「原典が許しているのは「ファクトの外部キーを後から更新する」ことで、メジャーの書き換えではない。」

Kimball の遅延到着ハンドラ（#16）が扱うのはサロゲートキーの解決だが、原典はファクトのメジャー訂正そのものを禁じていない。誤りの訂正については「該当行を更新する／削除して再ロードする／相殺（負値）行を追加する」の3方式を提示しているのが原典の立場で、「外部キーの更新だけが許される」という制約は原典に無い。本文は原典の主張ではなく**この題材の設計判断**を原典の権限で語っており、style.md の3段（原典／再解釈／この題材の決定）を混ぜている。

**修正案**:

> 遅延到着ディメンションの修復で触るのは外部キーだけにする。原典はファクトの誤り訂正に更新・削除再ロード・相殺行の3方式を挙げるが、ここで直したいのは「ディメンションの版が後から来た」ことであってメジャーの誤りではない。この区別が §5(c) の `MERGE` を `company_key` と `audit_key` に限る理由になっている。

### M1 (Minor) — 参照文献に dbt の incremental-strategy / microbatch が無い

**箇所**: L688–698

本文は `microbatch` の `lookback` 既定 1（L86, L290）と `incremental_predicates`（L393–395）を根拠に使っているが、参照文献は `bigquery-configs` だけ。report の提案1のとおり `canon/references.md` には既に「dbt incremental strategy」「dbt microbatch」の2行があるので、URL 規約上も追加できる。

**修正案**: 参照文献に2行追加。

```html
<li>dbt, <em>Incremental strategies</em>（<code>incremental_predicates</code>） — <a href="https://docs.getdbt.com/docs/build/incremental-strategy">docs.getdbt.com</a></li>
<li>dbt, <em>Incremental microbatch</em>（<code>event_time</code> / <code>batch_size</code> / <code>lookback</code>） — <a href="https://docs.getdbt.com/docs/build/incremental-microbatch">docs.getdbt.com</a></li>
```

### M2 (Minor) — 4文の段落（style.md「1段落は3文まで」）

**箇所**: L656（演習(c) の「壊れ方」）。4文。本文中で唯一の違反。

**修正案**: 最後の1文（`require_partition_filter=true` のため…）を独立した段落にするか、`<ul>` の1項目に落とす。

### M3 (Minor) — 演習(c) の §5a 参照が食い違う

**箇所**: L656「`snapshot_date = view_date` で結ぶモデル（§5a の `member_snapshot` のような結合）」

§5(a) は `fct_scout` で、結合は `t.sent_date = d.snapshot_date`。`view_date` で結ぶのは §1.2 の `fct_page_view` 側であって §5a ではない。

**修正案**: 「`snapshot_date = <role>_date` で結ぶモデル（§5a の `member_snapshot` は `sent_date`、`fct_page_view` なら `view_date`）」。

### M4 (Minor) — §6 の表「ファクトの型」の例にディメンションが混じる

**箇所**: L587「定期スナップショット（日）… `fct_job_posting_daily`, `dim_member_daily`」

表の1列目が「ファクトの型」なので、`dim_member_daily`（ディメンションの日次スナップショット）は列見出しと合わない。判断としては正しい（05回の方式と同じ扱い）ので、括弧で注記するのが安い。

**修正案**: 「`fct_job_posting_daily`（同じ扱いで `dim_member_daily` も）」。

### M5 (Minor) — `member_profile_mini_key`（送信時点）を「その日の終わり時点」で解決している近似に触れていない

**箇所**: L338–345 / L351–353

正典の `dim_member_daily` は「1行 = 1会員 × 1日（**その日の終わり時点**）」。一方 `fct_scout.member_profile_mini_key` は正典で「送信時点」と定義されている。`sent_date = snapshot_date` で結ぶと、同じ日の送信後に属性が変わったケース（`M001` の 6/15 の `active`・`600_800` 化はまさにこの型）で送信時点と1日ぶんずれる。L364 直後の段落は `member_key` の as-of だけを説明していて、ミニディメンション側の近似に触れていない。

**修正案**: L364 の段落に1文追加。「`member_profile_mini_key` は `dim_member_daily`（その日の終わり時点）で解決するので、同日中の属性変化は当日ぶんが変化後の版に寄る。時点精度が要るなら 05回のミニディメンション履歴側に切り替える。」

### M6 (Minor) — ブリーフの「dbt の `insert_overwrite` + `partitions` がこれをそのまま実装する」が地の文に無い

**箇所**: §4（L268–290）

対比表の「再実行」行で実質的には書かれているが、FDE の主張と dbt の config を結ぶ一文が本文に無い。I2 の書き換えと同時に1文足すのが自然。

### M7 (Minor) — `p.meta` に DT#43 と microbatch が無い

**箇所**: L43

本文は演習(c)（L656）で DT#43 を根拠に使い、参照文献にも DT#43 を挙げている。`p.meta` の「Design Tip #164」に `#43` を足す。M1 を採るなら「再解釈: … dbt BigQuery configs（incremental strategies）」も microbatch を含む表現にする。

---

## 5. 総合判定

**REVISE**

- Critical: 0
- Important: 4（I1 正典の `cluster_by` 違反 / I2 FDE 要約の反転 / I3 `SUM(is_hired)` の検算不一致 / I4 原典の歪み）
- Minor: 7

ブリーフの必須項目・図の指定・8節構成・`check_svg` はすべて満たしており、SQL と dbt config は WebFetch で照合した限り BigQuery / dbt-bigquery のドキュメントどおりで、指示された検算項目（静的 `partitions` の config、DATE 列でのルックバック `WHERE`、`merge` の絞り込み CTE、修復 `MERGE` のターゲット側パーティション述語、冪等性検証の比較可能性、図のブリーフ準拠）はいずれも問題無し。残るのは、正典との物理設計の食い違い1件と、引用元・数値・原典の主張の扱い3件。I1〜I4 は差し替え文が短いので、修正コストは低い。
