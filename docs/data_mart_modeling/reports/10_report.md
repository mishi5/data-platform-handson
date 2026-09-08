# 10 レイヤ・命名・契約・テスト・監査 — 執筆報告

- 出力: `docs/data_mart_modeling/html/10_layers_tests.html`
- 図: なし（ブリーフ指定どおり）。`check_svg.py` → `0 errors, 1 warnings`（warning は「`<svg>` が見つからない」＝図の無い回では正常）
- 本報告は初稿完成後にレート制限で書けなかったため、**修正ラウンド1の反映と同時に新規作成**した（§「修正ラウンド1」を参照）

## 完了した節

| 節 | 内容 | ブリーフの必須項目 |
|---|---|---|
| §1 この回が決めること | 決定一覧表（置き場 / 命名 / テストの種類 / 契約 / 改版 / 監査 / 設計完了）＋「層 × 役割 × マテリアライズ × テスト」8 行表 ＋ 命名規約 11 行表（`domain.md` §4 の転載） | ✓ staging / intermediate / marts(dim, fct, agg, br, obt) / snapshots を全て収録 |
| §2 どこで壊れるか | (a) `fct_scout_v2` をモデル名で切って `obt_scout_funnel` とダッシュボードが別版を見る (b) staging に `GROUP BY` が入って `fct_scout` の粒度が作れなくなる／型変換を marts に散らして `SAFE_CAST` と `CAST` がずれる (c) `review_moderation_events` の結合で `R001` が 2 行になり件数だけ 2 倍・平均は不変 (d) `audit_key` 不在でルックバック 3 日と衝突し、壊れた実行の行だけを消せない | ✓ 4 例すべて |
| §3 Kimball の原則 | ETL 34 サブシステムの 7 行表（#1 / #5 / #6 / #9 / #10 / #16 / #19）＋ DT#108 の 3 聴衆表とバスマトリクス先行・時間の 1/3 ＋ Data Quality の 3 スクリーン表・2 責務・3 択 ＋ 監査ディメンション（DT#164 の 2 分類） | ✓ |
| §4 現代の再解釈 | 34 サブシステム → dbt の実体 → 残る手作業の 8 行表 ／ dbt structure の staging 4 変換と結合・集約の禁止、intermediate の「DAG を狭めテーブルを広く」 ／ marts 命名で structure ガイドと dbt Kimball 記事が食い違う点 ／ contracts の強制範囲 ／ `versions:` と `deprecation_date` | ✓ |
| §5 実装 | (a) `fct_scout` の contract（10 列・型・`not_null`）＋ 粒度 `unique_combination_of_columns` ＋ `relationships`（`where` で `-1` 除外）＋ 加法性 `expression_is_true`（`fct_scout` と `fct_contract_monthly`）＋ `accepted_values`（`sender_type`）＋ 既定行の singular test (b) `dim_audit` モデルと `audit_key()` マクロ（`invocation_id` / `run_started_at` / `{% do ref() %}` による依存辺）(c) `versions:` / `latest_version` / `deprecation_date` / `ref('fct_scout', v=1)` / `alias` / `latest_version_pointer` (d) `dbt source freshness`（`loaded_at_field` の上書き・`filter`・`freshness: null`）(e) `exposures` 2 件と `dbt build -s +exposure:` | ✓ |
| §6 判断基準 | 「テストを置く層と種類」8 行表（必須 / 任意 / 置かない理由）＋「改版 vs 上書き」9 行表 | ✓ |
| §7 演習 | (a) `fct_application_pipeline` の 9 テスト × 捕まえる壊れ方 (b) `industry`／`sector` の間に中間分類を足す変更の 3 分岐表 (c) `int_review_member_link` の層・データセット・`dbt_project.yml`・保証すべき 5 項目 | ✓ 3 問すべて `<details>` に解答 |
| §8 手元の基盤 | `dbt_logs_analysis` の 3 モデル並立と `exposures.yml` の両版依存／`_incremental` のテスト 0 件／`sources.yml` の鮮度不在／`exposures.yml` は実装済み／`news_pipeline` の `scoring_version` と `collected_at`／種 1 行 | ✓ 6 行 |
| 参照文献 | canon の URL ＋ dbt docs 2 本（下記「正典への変更提案」参照） | ✓ |

## 読んだ文献と引用した要点

WebFetch で実際に取得（PDF は保存されたファイルを Read で直接読んだ）。

| 文献 | 引用した要点 |
|---|---|
| **Subsystems of ETL Revisited (2007)** | 34 サブシステムを 抽出(3) / クレンジングとコンフォーム(5) / デリバリ(13) / 管理(13) に分ける。§3 の表は #1 Data Profiling・#5 Error Event Tracking・#6 Audit Dimension Creation・#9 SCD Manager・#10 Surrogate Key Generator・#16 Late Arriving Data Handler・#19 Aggregate Builder の 7 つを CareerVoice の置き場所へ対応づけた。§4 で #22 Job Scheduler・#29 Lineage and Dependency が dbt に置き換わり、#1 だけが人間に残ることを書いた |
| **An Architecture for Data Quality (2007)** | 品質スクリーン＝ETL パイプライン内の診断フィルタ。成功時は副作用なし、失敗時の責務は 2 つ（エラー事象スキーマに 1 行落とす／停止・保留・タグ付け通過を選ぶ）。Jack Olson の 3 分類（列 / 構造 / 業務ルール、業務ルールには集約閾値も含む）を dbt のテスト種別へ対応づけた。3 択のうち推奨はタグ付け通過（停止は手動介入、保留は「いつ戻るか不明」で整合性が疑わしくなる）。error event fact の粒度＝1 スクリーンイベント、error event detail の粒度＝1 エラーに関わった 1 フィールド。least biased estimator と監査ディメンションの併用。監査ディメンションの粒度＝1 つの異なる監査条件（完璧な実行なら 1 行） |
| **DT#164 (2014)** | 監査ディメンションは「メタデータを通常のデータに格上げし、BI ツールの画面の第一階層に出す」。列を 2 群（環境変数＝ETL マスタ版・通貨換算版・配賦版／品質指標＝欠損・推定値・ありえない値）に単純化。「単純に始めよ、理想主義になるな、優雅さで賞を狙うな」を正典の `dim_audit` 5 列の根拠にした |
| **DT#108 (Bob Becker, 2008)** | 実装に飛びつく前のレビューと検証が最後の主要な設計活動。最低 3 聴衆（ソース開発者と DBA／モデル開発に関わらなかったコア業務ユーザー／広い利用者コミュニティ）。IT レビューは 3NF 志向なのでディメンショナルモデリングの教育を先に置く。**まずバスマトリクスをレビューし**、選んだ行がモデルにどう翻訳されるかを示してから各ディメンション・ファクトへ。広い層では時間の約 1/3 を「この設計で実際の問いにどう答えるか」の実演に充てる |
| **dbt structure (How we structure our dbt projects)** | staging が許すのは改名・型変換・単純な計算・条件による区分化の 4 つで、結合（計算の重複と分かりにくい関係）と集約（粒度を壊し下流の柔軟性を奪う）は禁止。1 ソーステーブル 1 モデル、`stg_[source]__[entity]`、view。intermediate は `int_[entity]s_[verb]`、`ephemeral` 既定または本番外スキーマの view、「DAG を狭めテーブルを広く」。marts は table / incremental、業務エンティティの平易な名前 |
| **dbt Kimball (Neo, 2023)** | AdventureWorks の受注で ビジネスプロセスの特定 → ファクトとディメンションの特定 → ディメンションの作成 → ファクトの作成 → 関係の文書化 の順に実装。テストは `product_key` / 自然キー / `sales_key` の `not_null` + `unique` と各 FK の `not_null` まで。**`relationships`・加法性・契約が無い**点を §4 で指摘し、この回で `relationships` を marts 必須に入れる根拠にした |
| **dbt model contracts** | `contract: enforced: true`、列ごとに `data_type` 必須、BigQuery では `not_null` のみ強制・`primary_key` / `foreign_key` は宣言のみ・`unique` / `check` は宣言不可。破壊的変更（列の削除、型の変更、既存制約の削除・変更）は版付きモデルでエラー・版無しで警告 |
| dbt model versions（参照文献に追加） | `versions:` / `v:` / `latest_version` / `deprecation_date`（dbt Core 1.6）／`include: all` + `exclude:` ／ファイル名 `<model>_v<v>.sql`（最新版は接尾辞無し可）／リレーション名 `<model>_v<v>` ／`ref('m', v=1)` ／`config: alias:` ／`latest_version_pointer`（dbt v1.12 以降） |
| dbt data tests / where / dbt-utils | `data_tests:` の下で引数は `arguments:`（dbt 1.10.5 以降。それ以前は直下）、config は `config:`。`where` はテスト対象を `(select * from … where …) dbt_subquery` に差し替える＝`to:` 側には効かない。`unique_combination_of_columns` / `expression_is_true` / `accepted_range` の引数名 |
| dbt sources / freshness | `config: freshness: {warn_after, error_after, filter}` ＋ `loaded_at_field`。**`filter` は `freshness:` の内側**。`freshness: null` で 1 テーブルだけ無効化。`config:` 配下への移動は 1.9 / 1.10 |
| dbt invocation_id / run_started_at | `invocation_id` は dbt コマンド 1 回ごとの UUID（BigQuery ジョブラベルにも入る）。`run_started_at` は UTC の Python `datetime` で `.strftime()` が使える |
| dbt BigQuery configs | `partition_by` の dict 形式、`require_partition_filter`、`cluster_by`、`insert_overwrite` |

## `check_svg` の結果

```
python3 ~/.claude/skills/svg-diagram/scripts/check_svg.py 10_layers_tests.html
WARN  10_layers_tests.html: <svg> が見つからない
0 errors, 1 warnings
```

図の無い回なので warning は解消できない（解消するには図を足すことになり、ブリーフ違反）。

## 正典への変更提案

1. **`references.md` の dbt structure の URL が 404**。`https://docs.getdbt.com/best-practices/how-we-structure/1-guide` は存在せず、実在するのは `…/how-we-structure/1-guide-overview`（配下は `2-staging` / `3-intermediate` / `4-marts` / `5-the-rest-of-the-project`）。本文では実在する方を使った。`references.md` の修正を提案する。
2. **`references.md` に dbt の 2 ページを追加したい**。§4・§5(c) は `https://docs.getdbt.com/docs/collaborate/govern/model-versions` に、§5(d) は `https://docs.getdbt.com/reference/resource-properties/freshness` に全面的に依拠している。参照文献には既に載せたが、正典側にも入れておくと以降の回でも引ける。あわせて `data_tests` / `where` / `invocation_id` / `run_started_at` / `dbt-utils` も候補。
3. **`domain.md` の `dim_audit` に `quality_flag` の値域を明記したい**。この回は `ok` / `estimated` / `suspect` の 3 値に固定した（Data Quality 白書の「タグを付けて通す」に対応）。03回は `ok` / `late_arriving_dimension` / `missing_natural_key` を使っており、値域が正典に無いために食い違った。
4. **`dim_audit.source_system` の値**を `'src_careervoice'`（`domain.md` §2 のデータセット名）に統一した。03回と同じ値になる。
5. **`fct_contract_monthly` のパーティション列名**。正典 §4 の規約「ファクトは主要な日付キーと並べて DATE 型の `<role>_date` を持つ」に従い `month_date` とした（§5(a) の `where`）。ファクト表の FK 欄は `month_date_key` しか書いていないので、DATE 列の名前を各ファクトについて明示しておくと以降の回で揺れない。

## 迷った判断とその理由

| 論点 | 判断 | 理由 |
|---|---|---|
| 契約は型を書かざるを得ないが、正典は「03回以外は型に踏み込まない」 | 03回の割当に従うと明記したうえで型を書いた（SCD2 キー = INT64 `FARM_FINGERPRINT`、Type0/1 キー = 自然キーの型、`date_key` = INT64） | `contract: enforced: true` は `data_type` が必須で、書かないと節が成立しない。踏み込みの根拠を 1 文で明示して最小化した |
| ブリーフ §5(a) の加法性の例 `scouts_remaining = scout_quota - scouts_sent` は `fct_scout` の列ではない | `fct_scout` には `scout_count = 1` を置き、`fct_contract_monthly` の追加ブロックとして正しい例も併記した | 正典の列を跨いだ式を `fct_scout` に書くと正典違反になる。半加法メジャーの内部整合がこの種のテストの代表例なので、両方載せた（レビュー M8） |
| `relationships` の `where: "member_key != -1"` | ブリーフどおり書いたうえで、代償（既定行が消えた事故を検知できなくなる）と対の singular test を足した | 正典は `dim_member` に `-1` の既定行を置く（03回）ので、除外しなくてもテストは通る。除外の意味は「実キーが解決できるか」への純化であり、穴が空く点を隠さない方が正本として使える |
| `require_partition_filter=true` 下のテスト | 各テストの `config: where:` に 90 日の窓を書く。`dbt_project.yml` の `data_tests:` 配下に `+where` を置く選択肢は「ファクトごとにパーティション列名が違う」ため採らない | `where` はテストの config なので `models:` 配下に書いても効かない。全期間の粒度保証は窓無しの同テストを別ジョブで回す、と代償を明記した |
| `dim_audit` を先にビルドさせる方法 | マクロ内で `{% do ref('dim_audit') %}` を呼び、依存辺だけ張る | `-- depends_on: {{ ref() }}` を `SELECT` リストの途中に差し込むと SQL が壊れる。`do` なら何も描画せず依存だけ登録できる。ただし `-s fct_scout` 単体実行では `dim_audit` がビルドされない（選択は広がらない）ので、その旨と `relationships` テストによる検知を aside に書いた |
| §7(b) で「`industry` の分類を1階層足す」を具体列名で書くか | 列名を作らず「`industry` と `sector` の間に中間分類を 1 本足す」と書いた | 正典に無い列名を作らない禁止事項に従った |
| `exposures` の `url:` | 書かない（任意項目） | 正典 `references.md` に無い URL を本文に出さないため。`url:` があると docs から飛べる旨はコメントで触れず、必須でないので省略した |

## 未達事項

- 図なしの回なので `check_svg.py` の warning 1 件は残る（仕様上解消不能）。
- §5(a) の YAML は 2 ブロックに分けて示しており、そのまま結合すると `member_key` などの `- name:` が重複する。差分の再掲であることをコメントで明示したが、完全な 1 ファイルとしては載せていない（長さの都合）。
- `fct_scout` の v1 / v2 の SQL 本体は v2 の抜粋のみ。v1 の全文は載せていない。

---

## 修正ラウンド1（`review/10_review.md` 対応）

判定 REVISE（Critical 2 / Important 3 / Minor 11）。**全 16 件を反映した。**

### Critical

| # | 指摘 | 対応 |
|---|---|---|
| C1 | §5(d) の `filter:` が `freshness:` の兄弟になっており、`page_views` の全件スキャン回避が効かない | `https://docs.getdbt.com/reference/resource-properties/freshness` を WebFetch して構文を確認（`config: freshness: {warn_after, error_after, filter}` ＋ `loaded_at_field` は `freshness` の兄弟）。YAML の `filter` を `freshness:` の内側へ移し、直後に「`filter` は `freshness` の内側のキーで `loaded_at_field` の兄弟ではない／ソース既定にも置けるが鮮度列名がテーブルごとに違うのでテーブル側に置く／テストの `where` を各テストの `config:` に書くのと同じ理由」の 1 段落を追加 |
| C2 | この回が `audit_key()` の正本なのに、03回 §5(e) の先行定義（引数が SQL 式・`quality_flag` の語彙・`source_system`・`loaded_at`）と非互換なまま何も断っていない | §5(b) の 1 段落目の直後に「03回 §5(e) は下書き。正本はこちらで変更点は 3 つ（引数を SQL 式から値に／`quality_flag` を `ok`/`estimated`/`suspect` の 3 値に固定／`loaded_at` を `CURRENT_TIMESTAMP()` から `run_started_at` に）」を 3 文で追加。あわせて `dim_audit.source_system` を `'careervoice'` → `'src_careervoice'` に修正（03回と一致）。`quality_flag` の値域は上記「正典への変更提案」3 に記載 |

### Important

| # | 指摘 | 対応 |
|---|---|---|
| I1 | §3 の aside「残る 27 はインフラ側」が原典の歪み。11 / 12 / 14 / 15 はこのシリーズがマート設計として扱った主題 | aside を全面差し替え。「選ばなかった 27 のうち 11（階層マネージャ）・12（特殊ディメンション）・14（SK パイプライン）・15（多値ブリッジ）は 03・05・06 回で既に扱った」「この回で残るのは 22・23・29・31 のような実行環境を規定する群」「dbt を採ると 22 と 29 は置き換わるが 1 は代われない」の 3 文に |
| I2 | §4「Neo の記事は 4 ステップ（…スキーマの選択…）」は原典に無い構成（実際は Part 1〜7） | 「AdventureWorks の受注を題材に、ビジネスプロセスの特定 → ファクトとディメンションの特定 → ディメンションの作成 → ファクトの作成 → 関係の文書化、という順で実装を追う」に差し替え。段落の残り（置かれているテスト、不在の 3 つ）は原典どおりなので変更なし |
| I3 | §7(a)「`P001` が 7 行に増える」は検算不一致。`selection_events.stage` に `applied` は無く 6 行 | 「6 行に増える（`selection_events` に `applied` は無く、書類〜入社の 6 イベント）」に修正 |

### Minor

| # | 指摘 | 対応 |
|---|---|---|
| M1 | `latest_version_pointer` の導入版を読者に外注していた | 「常に最新版を指すビューを自動生成する `latest_version_pointer`（dbt v1.12 以降）を使う」に修正（docs の該当箇所で確認） |
| M2 | 参照文献に model versions / source freshness が無い。dbt structure の URL が canon と食い違う | 参照文献に 2 本を追加。canon の URL 誤りは本報告の「正典への変更提案」1・2 に記載（`references.md` はこの回では触っていない） |
| M3 | 3 文を超える段落が 3 箇所（§4 aside modern / §7(b) 解答 / §7(c) 解答） | 3 箇所とも 2 段落に分割。全 `<p>` と `<li>` の文数を機械チェックし、4 文以上が 0 件であることを確認 |
| M4 | §2(c) の「（偶然一致する）」は誤り | `-- 3.5（分子も分母も 2 倍になるので変わらない）` に修正 |
| M5 | §5(a) 2 つ目の YAML が `member_key` の重複定義に見える | ブロック先頭に `# 上の columns: の該当エントリに data_tests: を足す（再掲は差分のみ）` を追加 |
| M6 | `dim_audit` がマクロを使わず同じ式を直書きしている結合の弱さが本文に無い | §5(b) 末尾の aside に「`dim_audit` 側は自己参照を避けるため直書き。式を変えるときは 2 箇所を同時に直す。この `relationships` テストはその取り違えも捕まえる」の 3 文を追加 |
| M7 | §6「制約を足す・外す＝破壊（1.6 以降）」は dbt の定義（既存制約の削除・変更）より広い | 表の行を 2 行に分割（「外す・変える＝破壊（1.6 以降）」／「足す＝dbt は検知しないが下流は壊れる」）。§4 の「制約の追加削除」も「既存制約の削除・変更」に修正 |
| M8 | ブリーフの加法性の例（`fct_contract_monthly` の `scouts_remaining`）が §5(a) に無い | §5(a) の YAML 末尾に `fct_contract_monthly` の `expression_is_true` ブロック（5 行 ＋ `where`）を追加。`fct_scout` に置けない理由は上記「迷った判断」に記載 |
| M9 | §3 の DT#108 の「」引用が原文 2 文の圧縮で、同節の他の引き方と不統一 | 「」を外し地の文に。「Bob Becker は、モデルが書けたと思った時点ではまだ終わっておらず、最後の主要な設計活動はディメンショナルモデルのレビューと検証だと位置づける。」 |
| M10 | §5(a) aside の `+where` が書ける場所を明示していない | 「`dbt_project.yml` の `data_tests:` 配下にパス単位で既定値を書けるが（`models:` 配下に書いても効かない）」に修正。末尾も「各テストの `config:` に書く」と明示 |
| M11 | `reports/10_report.md` が無い | 本ファイルを新規作成 |

### 修正後の再チェック

- `check_svg.py` → `0 errors, 1 warnings`（図なし）
- `<pre><code>` 内の未エスケープ `<` → 0 件
- 表 13 個 / `.table-wrap` 13 個（全て包まれている）
- h2 が「1.〜8. ＋ 参照文献」の 9 本
- `<p>` / `<li>` に 4 文以上のものは 0 件
- 本文の全 URL（11 本）は `kimballgroup.com` ＋ `references.md` 掲載の dbt docs ＋ 上記提案 2 の 2 本のみ
- 正典に無いテーブル名は `dim_product` / `fct_sales`（dbt Kimball 記事の引用と明示）、`fct_scout_v1` / `fct_scout_v2`（dbt が生成する物理リレーション名）、`snap_companies`（`snap_*` 規約の例示）のみ
