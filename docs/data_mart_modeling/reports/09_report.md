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
| FDE（ssp.sh 解説） | 「reruns overwrite rather than append」／パーティションが状態の最小単位で丸ごと上書き／「one task → one table, one task instance → one partition」／ディメンションは完全スナップショットを実行ごとに追加（ストレージと引き換えに明快さ）／処理時刻ではなくイベント時刻で切るとバックフィルが並列化でき遅延到着を扱いやすい | §4、§4.1、演習(b) |
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

1. **references.md に dbt の2ページを追加**してほしい。
   - `https://docs.getdbt.com/docs/build/incremental-strategy`（アダプタ別の戦略と `incremental_predicates`）
   - `https://docs.getdbt.com/docs/build/incremental-microbatch`（`event_time` / `batch_size` / `lookback` / `begin`）
   本文では `microbatch` の `lookback`（既定 1）に触れているが、URL 規約（references.md にあるものだけ）に従い参照文献リストには `bigquery-configs` だけを載せた。10回も incremental に触れるなら共有しておきたい。
2. **`fct_scout` の物理設計を正典 §4 に明記**したい（`partition_by = sent_date`, `cluster_by = ['scout_sender_key']`）。07回と09回が同じ config を書くため、正典側に1行あると揺れない。正典には `fct_page_view` の「パーティション: `view_date`、クラスタ: `company_key`」だけがある。
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
