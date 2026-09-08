# 09 増分・遅延到着・冪等性 — 執筆報告

- ファイル: `docs/data_mart_modeling/html/09_incremental.html`
- タイトル: `増分・遅延到着・冪等性 — データマート設計 09`

## 完了した節

| 節 | 内容 | ブリーフ対応 |
|---|---|---|
| 1 | 増分3方式の表（BigQuery の DML・冪等性・課金・使う条件）＋ microbatch の行／CareerVoice のファクト割当表（`fct_page_view` / `fct_scout` / `fct_application_pipeline` / `fct_contract_monthly`） | §1 完了 |
| 2 | 壊れ方4つ: (a) `> MAX(sent_at)` の境界と S003 の永久欠損（図）(b) `P001` が7行 (c) `C002` の規模変更が 5/3 到着 (d) `fct_contract_monthly` の二重計上 | §2 完了 |
| 3 | ETL サブシステム表（#2 #6 #13 #14 #16 #24）／DWT ch.19–20 の遅延到着ファクト・遅延到着ディメンション・仮行 | §3 完了 |
| 4 | FDE（純関数・不変パーティション・1タスク実行=1パーティション・イベント時刻でのパーティション）／原典との対比表／ルックバック窓の決め方 | §4 完了 |
| 5 | (a) `fct_scout` の静的 `partitions` モデル＋静的/動的/`copy_partitions` の比較表 (b) `fct_application_pipeline` の `merge` ＋ `touched` CTE ＋ `incremental_predicates`（窓の下限を測るクエリ付き） (c) `repair_late_company_key` マクロ（対象パーティション限定の `MERGE`） (d) 指紋クエリによる冪等性検証＋`schema.yml` | §5 完了 |
| 6 | 「ファクトの型 × 遅延 × 行数 → 方式とルックバック」7行の表＋ルックバック決定の3手順 | §6 完了 |
| 7 | (a) `fct_page_view` のルックバック測定 (b) `fct_job_posting_daily` の増分単位 (c) `dim_member_daily` の欠損と as-of join | §7 完了 |
| 8 | `mart_url_performance_incremental` の `> MAX(date)` 境界／`summaries` のストリーミング挿入／チュートリアルの種 | 4行 |
| 図 | 遅延到着とルックバック（概念図・ノード5・矢印3・accent 1系統） | §図 完了 |

## 読んだ文献と引用した要点

| 文献 | 実際に取った要点 | 使った箇所 |
|---|---|---|
| Kimball, *Subsystems of ETL Revisited*（2007） | サブシステム番号と名称: #2 Change Data Capture, #6 Audit Dimension Creation, #13 Fact Table Builders（transaction / periodic snapshot / accumulating snapshot の3種を作る）, #14 Surrogate Key Pipeline, #16 Late Arriving Data Handler, #24 Recovery and Restart | §3 の表 |
| DWT ch.19–20（書籍。URL は書誌のみ） | 遅延到着ファクト = イベント時点で有効だった版のサロゲートキーを割り当てる／遅延到着ディメンション = 遡及版を挿入し、その区間のファクトの外部キーを貼り替える／ディメンション行が無い場合は自然キーだけの仮行 | §3.1 |
| FDE（ssp.sh 解説） | 「reruns overwrite rather than append」／パーティションが状態の最小単位で丸ごと上書き（行ではない）／「one task → one table, one task instance → one partition」／ディメンションは完全スナップショットを実行ごとに追加（ストレージと引き換えに明快さ）／**「No past dependencies; partition on processing time」＝過去への依存を持たず処理時刻でパーティションを切ることでバックフィルが並列化でき遅延ファクトを素直に扱える**（この題材はそこを採らず、イベント時刻 `sent_date` のパーティションを置換しルックバック窓で遅延を吸収する側を選んだ。両者を混同しないこと） | §4、§4.1、演習(b) |
| dbt, BigQuery configurations | `incremental_strategy` は `merge` / `insert_overwrite` / `microbatch`。`partition_by` の辞書キー（field / data_type / granularity / range / copy_partitions）。静的 `partitions`（列挙した集合を置換）と動的（一時表から distinct パーティションを検出、`_dbt_max_partition` が使える）の違い。`copy_partitions=true` は動的置換のみ・copy API で挿入課金なし。`require_partition_filter`, `on_schema_change` | §1.1、§5(a) の比較表 |
| dbt, incremental strategies / microbatch（URL は本文に出していない。下の提案1参照） | `microbatch` の config は `event_time` / `batch_size` / `begin` / `lookback`（既定 1）/ `concurrent_batches`。BigQuery では内部的に `insert_overwrite`。`incremental_predicates` は `DBT_INTERNAL_DEST` / `DBT_INTERNAL_SOURCE` 別名を使う | §1.1、§4.1、§5(b) |
| dbt-adapters のソース（`dbt_bigquery_validate_get_incremental_strategy`） | BigQuery で有効な戦略名は `'merge', 'insert_overwrite', 'microbatch'` のみ（`append` は無い） | §1.1 の注記 |

原典に無い「引用」（カギ括弧の創作文）は作っていない。Kimball の主張は表の「原典の処理」列に要約として置き、地の文で断定的な引用形にしていない。

## check_svg の結果

```
python3 ~/.claude/skills/svg-diagram/scripts/check_svg.py html/09_incremental.html
0 errors, 0 warnings
```

図の密度: ノード5（S003 チップ / S001 チップ / 6/20 到着 / 旧方式の帯 / 採用案の帯）、矢印3、accent 1系統（遅れて届いた行 → その行を拾う窓、という1つの筋）。

## 正典への変更提案

1. ~~references.md に dbt の incremental-strategy / microbatch を追加してほしい~~ → **採用済み**（references.md 71–72 行）。修正ラウンド1で参照文献に2行を追加した。
2. ~~`fct_scout` の物理設計を正典 §4 に明記したい~~ → **正典に明記済み**（domain.md 124 行: パーティション `sent_date`、クラスタ `scout_sender_key`, `member_key`）。初稿の `cluster_by = ['scout_sender_key']` は正典違反で、修正ラウンド1で正典に従った。
3. **`fct_selection_event.event_date` / `fct_application_pipeline.applied_date` を使用した**。正典 §4 の「ファクトは日付キーと並べて DATE 型の `<role>_date` を持つ」からの機械的な導出だが、明示は無い。
4. **検証用スクラッチ表 `marts.fct_scout__fingerprint`** は正典外の名前。モデルではなく冪等性検証の一時表なので正典に入れる必要はないと判断したが、レビューで名前規約の対象と見なすなら `tmp_` などの接頭辞規約が要る。

## 迷った判断とその理由

1. **ブリーフの `partitions = dbt.partition_range(...)` は実在しないマクロ**。dbt docs の静的パーティション置換パターン（Jinja でリストを組み立てて `partitions=` に渡し、同じリストでモデルの `WHERE` を書く）に置き換えた。ブリーフの「または」以下（`{% if is_incremental() %} WHERE sent_date >= DATE_SUB(...)`）は動的置換の形なので、両方を §5(a) の比較表で並べ、静的を既定にした。静的を選んだ理由は、遅延到着だけでなく**行が消える訂正**（クチコミ削除・スカウト取消）でもパーティションが正しく空になるため。
2. **`append` は dbt-bigquery の有効な戦略名ではない**。ブリーフは3方式の表を求めているので、行は残しつつ「`unique_key` 無しの `merge`（一致条件が常に偽の MERGE ＝ INSERT のみ）」として書いた。架空の config 名を書かないための処理。
3. **修復 `MERGE`（§5c）を書いた上で、`insert_overwrite` のファクトなら再ビルドの方が安いと明記**した。ブリーフの必須項目なので実装は載せたが、CareerVoice の `reviews` は CDC で `submitted_at` を保持しており該当パーティションを流し直せる。MERGE を選ぶ条件（大きい表・貼り替えが多数パーティションに散る）を書き添えた。
4. **`MERGE` の `UPDATE SET` 左辺を非修飾にした**（`company_key = ...`）。BigQuery のドキュメント例が非修飾で、別名修飾の可搬性が低いため。ターゲット側のパーティション条件は `ON` 句に置き（`t.submitted_date BETWEEN ...`）、オーケストレータの指示どおりターゲットのプルーニングを効かせた。
5. **冪等性の指紋から `audit_key` を除外**した（`SELECT AS STRUCT t.* EXCEPT (audit_key)`）。`audit_key` は実行ごとに変わるので、除外しないと検証は常に不一致になる。「同じ入力なら同じ出力」の対象はメジャーとキーであって実行の記録ではない、という一文を添えた。
6. **`fct_page_view` だけ動的置換 + `copy_partitions`**にした。`copy_partitions` は動的置換専用（dbt docs）なので静的 `partitions` と両立しない。最大表では挿入課金の回避が優先、という理由を §1.2 と比較表に書いた。
7. **`member_profile_mini_key` の時点解決に `dim_member_daily` を使い、`member_key` は `dim_member` の as-of join**にした。ミニディメンションは SCD2 ではないので有効期間を持たず、日次スナップショット側にしか「その日の版」が無いため。`dim_member_daily` は `require_partition_filter=true` なので、結合条件ではなく CTE の `WHERE` でパーティションを絞る形にした（実装上の落とし穴なのでコメントを残した）。
8. **図は縦線2本ではなく、日付軸に沿った2本の帯**にした。`> MAX(date)` の境界とルックバック窓を縦線で描くと 6/20 の位置で重なって読めなくなる。カバレッジ帯にすると「6/18 の行がどちらの範囲に入るか」が x 座標だけで読める。ブリーフの「2本の縦線/帯」の後者を採った。
9. **`incremental_predicates` の窓を 180 日にし、その根拠を測るクエリを添えた**。数字そのものより「最長パイプライン以上でなければ同じ `application_id` が2行になる」という失敗が要点なので、実測クエリを本文に置いた。

## 未達事項

- なし。ブリーフの §1〜§7・図・8節すべてを埋めた。
- 注意点として、`microbatch` の config 詳細（`lookback` 既定 1・BigQuery が内部で `insert_overwrite` を使う）は dbt の microbatch ページを読んで書いたが、URL 規約のため参照文献に出していない（提案1）。


---

## 修正ラウンド1（レビュー `review/09_review.md` への対応）

| 指摘 | 対応 | 箇所 |
|---|---|---|
| I1 `cluster_by` が正典と違う | `cluster_by = ['scout_sender_key', 'member_key']` に修正（正典 domain.md 124 行・07/10 回と一致）。report の提案2も「正典に従った」に書き換え | §5(a) の config |
| I2 FDE 要約の反転 | ssp.sh を再取得して原文（"No past dependencies; partition on processing time": keeps backfills parallelizable and cleanly handles late-arriving facts）を確認。§4 を3段に分割し、「FDE は処理時刻でパーティションを切る」と原典側を正しく書いたうえで、この題材はイベント時刻（`sent_date`）を選び窓で遅延を吸収する、と決定側を分けた | §4 の3段落 |
| I3 `SUM(is_hired)` の検算 | `COUNT(*)` が 1 ではなく 7、`AVG(days_applied_to_offer)` が7回数えた平均、と行数側の指標に差し替え。`SUM(is_hired)` が 1 のままである理由（入社を観測した最後の1行だけが 1）を別段落で説明し、「壊れていても合う指標がある」ことを失敗の見つけにくさとして書いた | §2(b) |
| I4 原典の歪み | 「原典が許しているのは…ではない」を削除。原典は誤り訂正に更新／削除再ロード／相殺行の3方式を挙げること、直したいのはメジャーの誤りではなくディメンションの版であること、それが `MERGE` を2列に限る理由であること、の3段に書き直した | §3.1 の末尾 |
| M1 参照文献に dbt の2ページが無い | `incremental-strategy` と `incremental-microbatch` を参照文献に追加（references.md に追加済みのため URL 規約に適合） | 参照文献 |
| M2 4文の段落 | 演習(c) の「壊れ方」を2段落に分割（`require_partition_filter` の1文を独立） | §7(c) |
| M3 §5a 参照の食い違い | 「`snapshot_date = &lt;role&gt;_date` で結ぶモデル（§5(a) の `member_snapshot` は `sent_date`、`fct_page_view` なら `view_date`）」に修正 | §7(c) |
| M4 表にディメンションが混じる | 「`fct_job_posting_daily`（同じ扱いで `dim_member_daily` も）」に修正 | §6 の表 |
| M5 ミニディメンションの近似 | 「`member_profile_mini_key` は `dim_member_daily`（その日の終わり時点）で解決するので同日中の変化は変化後の版に寄る。`M001` の 6/15 がこの型で、時点精度が要るなら 05回の履歴側」の段落を追加 | §5(a) の直後 |
| M6 FDE と dbt config を結ぶ地の文 | 「`insert_overwrite` に静的な `partitions` を渡す形は『1タスク実行 → 指定したパーティションを丸ごと置換』をそのまま実装する」を段落として追加 | §4 |
| M7 `p.meta` | `Design Tip #43 #164` に修正し、再解釈側を「dbt の増分戦略（BigQuery configs / incremental strategies / microbatch）」に変更 | L43 |

- 図は触っていないが `check_svg.py` を再実行: `0 errors, 0 warnings`。
- 1段落3文の上限を全 `<p>` について再スキャンし、超過ゼロを確認。`<pre>` 内の生 `<` ゼロ・タグ平衡も再確認。


---

## 修正ラウンド2（再レビュー `review/09_rereview.md` への対応）

| 指摘 | 対応 | 箇所 |
|---|---|---|
| N1 (Important) `AVG(days_applied_to_offer)` の検算ずれ | 「7回数えた平均」を削除し、行数の壊れは `COUNT(*)` と `COUNT(DISTINCT application_id)` の乖離で語る形に差し替え。`AVG(days_applied_to_offer)` は内定前の4行が NULL で平均から外れるため `P001` 単独では正しい値を返す、と「壊れていても合う指標」側（`SUM(is_hired)` と同じ段落）へ移した。差し替えで第1段落が4文になったため段落を割り直し、3文上限を維持した | §2(b) の2段落 |
| N2 (Minor) report の FDE 反転記述 | 「読んだ文献と引用した要点」の FDE 行を原文どおり「No past dependencies; partition on processing time（過去への依存を持たず処理時刻で切る）」に訂正し、イベント時刻採用はこの題材の決定である旨を併記（後続回が同じ取り違えをしないための注記） | 09_report.md の文献表 |
| N3 (Minor) 誤り訂正3方式の出典アンカー | 「（DWT ch.19–20 のロード処理）」を文中に追加。局所修正なので併せて反映した | §3.1 末尾 |

- 図は未変更。`check_svg.py` 再実行: `0 errors, 0 warnings`。
- 全 `<p>` の3文上限を再スキャンし超過ゼロ、`<pre>` 内の生 `<` ゼロ、タグ平衡も再確認。
