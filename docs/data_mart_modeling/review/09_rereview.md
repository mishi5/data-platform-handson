# 09 増分・遅延到着・冪等性 — 再レビュー（修正ラウンド1）

対象: `docs/data_mart_modeling/html/09_incremental.html`
初回レビュー: `review/09_review.md`（Important 4 / Minor 7）／執筆者の対応: `reports/09_report.md` 末尾「修正ラウンド1」
再レビュー担当: 初回レビューとは別人。報告は参照せず、HTML の該当箇所を直接見て判定した。
差分の確認: `git diff 2d6704d 7d05dd1 -- docs/data_mart_modeling/html/09_incremental.html`（この差分には修正ラウンド1以前の推敲も混ざるため、指摘対応のハンクだけを判定対象にした）

---

## 1. 初回指摘 11 件の判定

| # | 初回指摘 | 判定 | 現在の HTML（該当行） | 検証内容 |
|---|---|---|---|---|
| I1 | `fct_scout` の `cluster_by` が正典と違う | **ADDRESSED** | L315 `cluster_by = ['scout_sender_key', 'member_key'],` | `canon/domain.md` L124「パーティション: `sent_date`、クラスタ: `scout_sender_key`, `member_key`（07/09 回で共通）」と一致。07/10 回の記述とも揃った |
| I2 | FDE 要約の反転（処理時刻／イベント時刻） | **ADDRESSED** | L276–278 の段落 | 原典を WebFetch で再確認（"No past dependencies; partition on processing time" keeps backfills parallelizable and handles late-arriving facts cleanly）。本文は「FDE は…**処理時刻**でパーティションを切ることを挙げ、それでバックフィルが並列化でき遅延ファクトも素直に扱えるとする」＝原典どおり。続けて「CareerVoice はそこを採らず、`sent_date`（イベント時刻）のパーティションを置換し、遅延分はルックバック窓で吸収する」＝題材側の決定として分離済み。style.md の3段（原典／再解釈／この題材の決定）に適合 |
| I3 | `SUM(is_hired)` が 7 を返すという検算 | **ADDRESSED（ただし差し替え文に新たな検算ずれ → N1）** | L211–213 | 誤った `SUM(is_hired) = 7` は削除され、`COUNT(*) = 7`（正典 L153 の P001 は 6/23→7/1→7/8→7/15→7/20→7/22→8/1 の7遷移。追記なら7行で一致）と、`SUM(is_hired)` が 1 のままである理由の別段落に置き換わった。ただし同じ文に入った `AVG(days_applied_to_offer)` の記述が新たに合わない（N1） |
| I4 | 「原典が許しているのは外部キー更新だけ」という歪み | **ADDRESSED** | L266 | 断定を削除し、「原典はファクトの誤り訂正に『該当行の更新』『削除して再ロード』『相殺行の追加』の3方式を挙げるが、ここで直したいのは…メジャーの誤りではない」に書き換え。原典の主張と題材の判断が分離された。Kimball の遅延到着ディメンション技法そのものの言い換え（L253–262 の表）も原典と一致することを再確認（下記 §2） |
| M1 | 参照文献に dbt incremental-strategy / microbatch が無い | **ADDRESSED** | L708–709 | 2行追加。両 URL とも `canon/references.md` L71–72 に登録済みで URL 規約に適合 |
| M2 | 4文の段落（演習(c)） | **ADDRESSED** | L664 / L666 | `require_partition_filter=true` の1文を独立段落へ。全 `<p>`（`<pre>`・`<svg>` 除外）を機械走査して「。」4個以上の段落は0件 |
| M3 | 演習(c) の §5a 参照の食い違い | **ADDRESSED** | L664 | 「`snapshot_date = <role>_date` で結ぶモデル（§5(a) の `member_snapshot` は `sent_date`、`fct_page_view` なら `view_date`）」に修正。§5(a) の実装（L367–369 `t.sent_date = d.snapshot_date`）と整合 |
| M4 | §6 表「ファクトの型」にディメンションが混じる | **ADDRESSED** | L591 | 「`fct_job_posting_daily`（同じ扱いで `dim_member_daily` も）」 |
| M5 | ミニディメンションの「その日の終わり時点」近似に触れていない | **ADDRESSED** | L381 | 追加段落。`dim_member_daily` の定義（正典 L99「1行 = 1会員 × 1日（その日の終わり時点）」）と `fct_scout.member_profile_mini_key`（正典 L124「送信時点」）のずれを明示し、`M001` の 6/15 の `active`・`600_800` 化（正典 L140）を例に取っている。ID・列名とも正典どおり |
| M6 | FDE と dbt config を結ぶ地の文が無い | **ADDRESSED** | L280 | 「dbt の `insert_overwrite` に静的な `partitions` を渡す形は、この『1タスク実行 → 指定したパーティションを丸ごと置換』をそのまま実装する」。ブリーフ §4 の必須文が地の文に入った |
| M7 | `p.meta` に DT#43 と microbatch が無い | **ADDRESSED** | L43 | `Design Tip #43 #164` ／ 再解釈「dbt の増分戦略（BigQuery configs / incremental strategies / microbatch）」。DT#43 は本文 L262・L664 で、microbatch は L80–87・L290 で実際に使われている |

**合計: ADDRESSED 11 / NOT ADDRESSED 0**

---

## 2. 修正で入った箇所の検証

| 検証項目 | 結果 |
|---|---|
| FDE 要約が原文どおりか（ssp.sh を WebFetch） | **一致**。原文4点（"Pure, idempotent tasks: … reruns overwrite rather than append" / "Immutable partitions: the partition (not the row) is the atomic unit of state" / "No past dependencies; partition on processing time" / "One task → one table, one task instance → one partition"）のいずれも L272 の `aside modern`・L274・L276 の記述と対応。**「処理時刻でパーティション」が原典、イベント時刻採用が題材側の決定、という分離ができている**（L276–278 で「FDE は…とする」→「CareerVoice はそこを採らず」の順） |
| `cluster_by` | **正典どおり**（`['scout_sender_key', 'member_key']`）。`partition_by` は `{'field':'sent_date','data_type':'date','granularity':'day'}` で、ソース側 `WHERE date(s.sent_at,'Asia/Tokyo') in (…)` と型・列が一致したまま |
| `COUNT(*) = 7` の検算 | **一致**。正典 L153 の `P001` は応募→書類→一次→最終→内定→承諾→入社の7遷移。追記型なら7行、粒度宣言「1行 = 1応募」に対して `COUNT(*)` は 7 |
| `SUM(is_hired) = 1` の検算 | **一致**。`is_hired = 1` になるのは入社（8/1）を観測した最後の1行だけ。L213 の説明（壊れていても合う指標がある）は正しい |
| `AVG(days_applied_to_offer)` の検算 | **不一致**（→ N1）。未達マイルストーンは `-1`／NULL（正典 L168）なので、7行のうち `days_applied_to_offer` が非 NULL なのは内定以降の3行だけ。`AVG` は NULL を無視するため「7回数えた平均」にはならない |
| 原典（遅延到着ディメンション）の言い換え | **歪み無し**。Kimball の Late Arriving Dimension 技法ページを WebFetch: 「未解決の自然キーだけを持つプレースホルダ行を立て、後で Type1 上書き」「Type2 の遡及変更では新しい行を挿入し、関連ファクト行を restate する」。L253–262 の表2行（遡及版挿入＋外部キー貼り替え／自然キーだけの仮行→Type1 で埋める）と1対1で対応する |
| 原典（ファクト誤り訂正の3方式） | **歪みは確認できず、ただし出典アンカーが弱い**（→ N3）。更新／削除再ロード／相殺行の三択は Kimball の標準的な立場で、L266 は「原典は…3方式を挙げる」と正しくスコープを誤り訂正に限り、修復 `MERGE` を2列に絞る判断は題材側として書き分けている。ただしこの3方式は書籍（DWT ch.19–20 / ETL Toolkit）側の記述で kimballgroup.com に該当ページが無く、URL では裏取りできない |
| `check_svg.py` | `0 errors, 0 warnings`（再実行済み。図は修正ラウンドで触られていない） |
| 正典外のテーブル名・列名が増えていないか | 増えていない。`days_applied_to_offer` / `is_hired`（正典 L127）、`dim_member_daily` の全列（L99）、`dim_audit.loaded_at`（L113）、`fct_selection_event.event_date`（L126 の `<role>_date` 導出）はすべて正典内。正典外は初回同様 `fct_scout__fingerprint`（検証用一時表・裁定済み）のみ |

---

## 3. 新規指摘（修正差分の範囲）

### N1 (Important) — `AVG(days_applied_to_offer)` の「7回数えた平均」が合わない

**箇所**: L211「…`COUNT(*)` は応募数 1 ではなく 7 を返し、`AVG(days_applied_to_offer)` は同じ応募を7回数えた平均になる。」

I3 の差し替えで入った文。`days_applied_to_offer` は内定日が確定してはじめて値を持つ（正典 L168「未達マイルストーン = `date_key = -1`、`dim_date` の `-1` 行は `full_date` NULL」）。追記でできる7行のうち、この列が非 NULL なのは内定（7/20）・承諾（7/22）・入社（8/1）の3行だけで、6/23〜7/15 の4行は NULL。BigQuery の `AVG` は NULL を無視するため、

- `P001` 単独で見れば `AVG(days_applied_to_offer)` = 27（＝ 6/23→7/20）で**正しい値のまま**。`SUM(is_hired)` と同じ「壊れていても合う指標」側に入る
- 母集団で見たときの歪みは「`P001` が7回重み付けされる」ではなく **3回**

つまり I3 で直したのと同じ型の検算ずれが、差し替え文の後半に残っている。行数の壊れを示すなら `COUNT(*)` と、全行が非 NULL の `SUM(scout_count)` 相当の加法メジャー（この表なら `COUNT(DISTINCT application_id)` との乖離）で語るのが安全。

**修正案**（L211 の後半を差し替え）:

> …粒度宣言「1行 = 1応募のパイプライン」が壊れ、`COUNT(*)` は応募数 1 ではなく 7 を返す。`COUNT(*)` と `COUNT(DISTINCT application_id)` の乖離がそのまま二重計上の量になる。

そのうえで L213 の段落に `AVG` を「合ってしまう側」として足すなら:

> `SUM(is_hired)` が 1 のままなのは、入社を観測できた最後の1行しか `is_hired = 1` にならないからだ。`AVG(days_applied_to_offer)` も、内定前の4行が NULL で平均から外れるため `P001` 単独では正しい値を返す。壊れていても合う指標があることが、この失敗を見つけにくくしている。

### N2 (Minor) — `reports/09_report.md` の文献表に FDE の反転記述が残っている

**箇所**: `reports/09_report.md`「読んだ文献と引用した要点」の FDE 行 —「処理時刻ではなくイベント時刻で切るとバックフィルが並列化でき遅延到着を扱いやすい」。

HTML 本文（I2）は直ったが、report の引用記録は反転したまま。ここは後続回（10 回以降）で FDE を再引用するときの手元の一次記録になるので、修正ラウンド1の対応表と食い違ったまま残すと同じ取り違えが再発する。原文どおり「過去への依存を持たず処理時刻でパーティションを切る／題材はイベント時刻を選んだ」に直す。

### N3 (Minor) — ファクト誤り訂正「3方式」の出典アンカーが無い

**箇所**: L266「原典はファクトの誤り訂正に『該当行の更新』『削除して再ロード』『相殺行の追加』の3方式を挙げるが…」

主張自体は Kimball の立場と矛盾せず、スコープ（誤り訂正であって遅延到着ディメンション処理ではない）の切り方も正しい。ただし `p.meta` と §3.1 見出しの「DWT ch.19–20」以外にアンカーが無く、kimballgroup.com 側に対応ページが無いため読者が裏を取れない。`（DWT ch.19–20 のロード処理）` のように章参照を文中に添えるのが安い。

---

## 4. 総合判定

**REVISE**

- 初回指摘: ADDRESSED 11 / NOT ADDRESSED 0（Important 4・Minor 7 すべて HTML 上で解消）
- 新規 Critical: 0
- 新規 Important: 1（N1 — I3 の差し替え文に残った `AVG(days_applied_to_offer)` の検算ずれ）
- 新規 Minor: 2（N2 report の反転記述、N3 出典アンカー）

I1・I2・I4 は原典・正典に当たり直して確認し、いずれも正しく直っている。図は未変更で `check_svg.py` は `0 errors, 0 warnings`。残るのは N1 の1文だけで、L211 後半の差し替え（＋任意で L213 に1文追加）で解消する。修正後は再々レビュー不要と判断してよい範囲。
