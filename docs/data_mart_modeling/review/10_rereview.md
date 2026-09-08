# 10 レイヤ・命名・契約・テスト・監査 — 再レビュー（修正ラウンド1）

対象: `docs/data_mart_modeling/html/10_layers_tests.html`
初回レビュー: `docs/data_mart_modeling/review/10_review.md`（Critical 2 / Important 3 / Minor 11 = 16 件）
執筆者報告: `docs/data_mart_modeling/reports/10_report.md`（新規作成）
レビュアー: 初回とは別人。報告は鵜呑みにせず、HTML の該当箇所と原典を直接確認した。

修正の範囲は `git diff f1740e6 ae58454 -- html/10_layers_tests.html`（40 insertions / 18 deletions）で特定した。判定はこの差分と現在の HTML 実物に対して行っている。

---

## 1. 初回指摘 16 件の判定

| # | 重み | 指摘 | 判定 | 確認した根拠 |
|---|---|---|---|---|
| C1 | Critical | `filter:` が `freshness:` の兄弟になっており全件スキャン回避が効かない | **ADDRESSED** | L596–600。`filter` が `warn_after` / `error_after` と同じ階層（`freshness:` の内側）へ移動。`loaded_at_field` は `freshness` の兄弟のまま。dbt docs `reference/resource-properties/freshness` を WebFetch し、`config: { freshness: {warn_after, error_after, filter}, loaded_at_field }` の入れ子であることを確認。L613 に「`filter` は `freshness:` ブロックの**内側**のキーで、`loaded_at_field` の兄弟ではない」を明示した段落も追加済み |
| C2 | Critical | `audit_key()` が 03回の同名マクロと非互換なのに正本宣言が無い | **ADDRESSED** | L461。「03回 §5(e) はこのマクロの下書き…**正本はこちらで**、変更点は 3 つ（引数を SQL 式から値に／`quality_flag` を 3 値に固定／`loaded_at` を `CURRENT_TIMESTAMP()` から `run_started_at` に）」を 3 文で追加。あわせて L478 の `source_system` を `'careervoice'` → `'src_careervoice'` に修正し、03回 L569 および `domain.md` L113 と一致した |
| I1 | Important | §3 aside「残る 27 は…インフラ側」が原典の歪み | **ADDRESSED** | L185。aside を全面差し替え。Subsystems of ETL Revisited を WebFetch して番号と名前を照合 — 11 Hierarchy Manager / 12 Special Dimensions Manager / 14 Surrogate Key Pipeline / 15 Multi-Valued Bridge Table Builder / 22 Job Scheduler / 23 Backup System / 29 Lineage and Dependency / 31 Paralleling and Pipelining、**8 件すべて原典どおり**。「11/12/14/15 は 03・05・06 回で扱った」への転換で歪みは解消 |
| I2 | Important | §4「4 ステップ（…スキーマの選択…）」が原典に無い構成 | **ADDRESSED** | L283。dbt Kimball 記事を WebFetch。実際の構成は Part 1 Setup / 2 Identify the business process / 3 Identify the fact and dimension tables / 4 Create the dimension tables / 5 Create the fact table / 6 Document the dimensional model relationships / 7 Consume。修正後の「ビジネスプロセスの特定 → ファクトとディメンションの特定 → ディメンションの作成 → ファクトの作成 → 関係の文書化」は Part 2–6 と一対一で対応する。「スキーマの選択」「4 ステップ」の語は消えている |
| I3 | Important | §7(a)「`P001` が 7 行に増える」が検算不一致 | **ADDRESSED** | L704。「6 行に増える（`selection_events` に `applied` は無く、書類〜入社の 6 イベント）」に修正。検算: `domain.md` L153 の `P001` は 06-23 応募 → 07-01 書類 → 07-08 一次 → 07-15 最終 → 07-20 内定 → 07-22 承諾 → 08-01 入社。`selection_events.stage`（`domain.md` L57）は `document`/`first_interview`/`final_interview`/`offer`/`accepted`/`hired`/`rejected`/`withdrawn` の 8 値で `applied` を含まないため、イベントは書類・一次・最終・内定・承諾・入社の **6 件**。本文と一致 |
| M1 | Minor | `latest_version_pointer` の導入版を読者に外注 | **ADDRESSED** | L568。「常に最新版を指すビューを自動生成する `latest_version_pointer`（dbt v1.12 以降）」に修正。dbt model versions ドキュメントを WebFetch し「(Applies to dbt v1.12 and later)」を確認 |
| M2 | Minor | 参照文献に model versions / freshness が無い。structure の URL が canon と食い違う | **ADDRESSED** | L792–793 に 2 本を追加。structure URL は `…/1-guide-overview` で、更新後の `references.md` L77 と一致。canon への訂正提案は report の「正典への変更提案」1・2 に記載され、実際に `references.md` へ反映済み（→ ただし freshness の URL 表記に軽微なずれ。N2） |
| M3 | Minor | 3 文超の段落が 3 箇所 | **ADDRESSED** | §4 aside modern（L276–277）・§7(b) 解答（L723–724）・§7(c) 解答（L742–743）とも 2 段落に分割。全 `<p>` / `<li>`（`<pre>` 除外）の「。」数を機械カウントし、**4 文以上は 0 件** |
| M4 | Minor | §2(c)「（偶然一致する）」は誤り | **ADDRESSED** | L135 が `-- 3.5（分子も分母も 2 倍になるので変わらない）` に。直後の「平均が正しく見えるので気づかない」と噛み合う |
| M5 | Minor | 2 つ目の YAML が `member_key` の重複定義に見える | **ADDRESSED** | L390 に `# 上の columns: の該当エントリに data_tests: を足す（再掲は差分のみ）` を追加 |
| M6 | Minor | `dim_audit` の直書きとマクロの結合の弱さが本文に無い | **ADDRESSED** | L523。aside に「`dim_audit` 側は自己参照を避けるためマクロを呼ばず同じ式を直書きしている。式を変えるときは 2 箇所を同時に直す。この `relationships` テストはその取り違えも捕まえる。」の 3 文を追加 |
| M7 | Minor | 「制約を足す・外す＝破壊（1.6 以降）」が dbt の定義より広い | **ADDRESSED** | L684–685 で 2 行に分割（「外す・変える＝破壊（1.6 以降）」／「足す＝**検知されない**（dbt の破壊的変更の定義は『既存制約の削除・変更』）」）。§4 本文 L290 も「制約の追加削除」→「既存制約の削除・変更」に修正 |
| M8 | Minor | ブリーフの加法性例（`fct_contract_monthly`）が §5(a) に無い | **ADDRESSED** | L418–427 に `fct_contract_monthly` の `dbt_utils.expression_is_true: scouts_remaining = scout_quota - scouts_sent` を追加。`domain.md` L128 のメジャー 3 列と一致し、半加法メジャーの内部整合という位置づけも正しい |
| M9 | Minor | DT#108 の「」引用が原文 2 文の圧縮 | **ADDRESSED** | L190。鉤括弧を外して地の文「Bob Becker は、モデルが書けたと思った時点ではまだ終わっておらず、最後の主要な設計活動はディメンショナルモデルのレビューと検証だと位置づける。」に。同節 L206 の締めの書き方と一貫 |
| M10 | Minor | `+where` が書ける場所を明示していない | **ADDRESSED** | L452。「`+where` は `dbt_project.yml` の **`data_tests:` 配下**にパス単位で既定値を書けるが（`models:` 配下に書いても効かない）」＋末尾「正典では各テストの `config:` に書く」に修正。`where` はテストの config なので記述は正しい |
| M11 | Minor | `reports/10_report.md` が無い | **ADDRESSED** | `reports/10_report.md` を新規作成（節ごとの完了表・読んだ文献・正典への変更提案 5 件・迷った判断 7 件・未達事項・修正ラウンド1 の対応表）。他 10 本の report と同じ構成 |

**集計: ADDRESSED 16 / NOT ADDRESSED 0**

報告の記述と HTML の実物に食い違いは無かった。報告が「対応した」と書いた 16 件はすべて差分として実在する。

---

## 2. 修正で新たに入った箇所の検証

| 検証項目 | 方法 | 結果 |
|---|---|---|
| `freshness:` 内の `filter:` の位置 | dbt docs `reference/resource-properties/freshness` を WebFetch | ✅ `filter` は `freshness:` の内側、`loaded_at_field` は `freshness` の兄弟。HTML の YAML・本文の説明とも docs と一致 |
| `freshness` / `loaded_at_field` の `config:` 配下移行（1.9 / 1.10） | dbt docs `source-configs` / `freshness` を WebFetch | ✅ `freshness` は「Applies to dbt v1.9 and later」で確認。`loaded_at_field` 側の版番号は当該ページに明記が無いが、docs の例はすべて `config:` 配下で、初回レビューでも確認済み。害は無い |
| `audit_key()` の正本宣言と `dim_audit` の整合 | HTML L461–482・03回 L557–573・`domain.md` L113 を突き合わせ | ✅ `quality_flag` = `ok`/`estimated`/`suspect` の 3 値（`UNNEST(['ok','estimated','suspect'])` と本文が一致）／`source_system` = `'src_careervoice'`（03回・domain.md と一致）／`loaded_at` = `run_started_at`（`TIMESTAMP '{{ run_started_at.strftime(...) }}'`）／`FARM_FINGERPRINT` = INT64 で契約の `data_type: int64`（L354）と整合。マクロ側 `farm_fingerprint(concat('{{ invocation_id }}','|','{{ quality_flag }}'))` と `dim_audit` 側の式が同一 |
| 正本宣言の記述が 03回の実物と合っているか | 03回 HTML を直接確認 | ✅ 03回は `audit_key(quality_flag_expr)`（SQL 式）／`['ok','late_arriving_dimension','missing_natural_key']`／`CURRENT_TIMESTAMP()`。宣言が挙げる「変更点 3 つ」はこの 3 点と正確に対応。`source_system` は 03回も `'src_careervoice'` なので変更点に挙げていないのが正しい |
| ETL サブシステム番号の列挙 | Subsystems of ETL Revisited を WebFetch し 34 件全部を取得 | ✅ 11 Hierarchy Manager / 12 Special Dimensions Manager / 14 Surrogate Key Pipeline / 15 Multi-Valued Bridge Table Builder / 22 Job Scheduler / 23 Backup System / 29 Lineage and Dependency / 31 Paralleling and Pipelining。**8 件とも番号・名称が原典どおり** |
| dbt Kimball 記事の実装順 | 記事を WebFetch し Part 見出しを取得 | ✅ Part 2–6 と一対一。「スキーマの選択」に相当する段が存在しないことも確認 |
| `P001` 6 行の検算 | `domain.md` L57（stage 値域）・L153（P001 のイベント列）から手計算 | ✅ 6 行。02回の記述とも数が合う |
| `latest_version_pointer` の導入版 | dbt model versions を WebFetch | ✅ 「(Applies to dbt v1.12 and later)」。本文の「dbt v1.12 以降」と一致 |
| `+where` が `data_tests:` 配下にあること | HTML L452 | ✅ 「`dbt_project.yml` の `data_tests:` 配下…（`models:` 配下に書いても効かない）」。`where` がテストの config である以上、記述は正しい |
| `check_svg.py` | `python3 ~/.claude/skills/svg-diagram/scripts/check_svg.py docs/data_mart_modeling/html/10_layers_tests.html` | ✅ `0 errors, 1 warnings`（warning は「`<svg>` が見つからない」。ブリーフが「図なし」なので正常。図を足すとブリーフ違反になるため解消不能） |
| HTML / 体裁の再チェック | 機械カウント | ✅ `<table>` 13 個 / `.table-wrap` 13 個（残り 1 件は CSS 定義）／`h2` 9 本（1〜8 ＋ 参照文献）／`<pre><code>` 内の未エスケープ `<` 0 件／`<p>`・`<li>` に 4 文以上 0 件／`<title>` 形式どおり |
| 追加 YAML の BigQuery 妥当性 | 静的読解 | ✅ `date_sub(current_date(), interval 12 month)` は BigQuery で有効（`DATE_SUB` は MONTH を取る）。`dbt_utils.expression_is_true` の `arguments:` / `config:` の位置も 1.10.5 以降の書式で他ブロックと一貫 |

---

## 3. 新規指摘

### Critical

なし。

### Important

なし。

### Minor（差分の範囲。いずれも次回まとめてで可）

- **N1. `fct_contract_monthly` の `month_date` が正典の列一覧に無い（L427）**
  M8 の追加ブロックの `where` が `month_date` を使う。`domain.md` L128 の FK 欄は `month_date_key` しか挙げていない。`domain.md` §4 の「ファクトは主要な日付キーと並べて DATE 型の `<role>_date` を持つ」から導出はできるので誤りではなく、report の「正典への変更提案」5 で明示的に申告している。正典側にファクトごとの DATE 列名を書けば以降の回で揺れない。
- **N2. 参照文献の freshness URL が `references.md` の表記と一致しない（L793）**
  HTML は `https://docs.getdbt.com/reference/resource-properties/freshness`、更新後の `references.md` L75 は `https://docs.getdbt.com/docs/build/sources#declaring-source-freshness`。どちらも実在する公式ページで、`filter` の入れ子を確認できるのは前者。どちらかに寄せる（正典側を `resource-properties/freshness` に変えるのが実質的）。
- **N3. §3 aside「この回で残るのは 22・23・29・31 のような…」の残余（L185）**
  選ばなかった 27 には 13 Fact Table Builders / 17 Dimension Manager / 18 Fact Table Provider / 4・7・8（クレンジング・重複排除・コンフォーム）のような「実行環境ではない」ものも残る。文は「〜のような」で例示に留めており原典の歪みではなくなったので Important ではないが、初回レビューの修正案がそのまま残した弱点でもある。1 句「13・17・18 は 02・08 回のファクト／ディメンションの作り方そのもの」を足せば閉じる。
- **N4.（未変更箇所の参考）§7(a) の `relationships` 行が `member_profile_mini_key` を落としている（L707）**
  日付キー 8 本 ＋ 列挙 7 本 = 15 で、同じ表の最終行が言う「16 本の FK」と 1 本ずれる。`domain.md` L127 の FK は 16 本（`member_profile_mini_key` を含む）。I3 で直した行の隣だが今回の差分には含まれないため参考扱い。

---

## 4. 総合判定

**APPROVE**

- 初回指摘 16 件: ADDRESSED 16 / NOT ADDRESSED 0
- 新規 Critical: 0 ／ 新規 Important: 0 ／ 新規 Minor: 4（うち 1 件は未変更箇所の参考）

C1 は dbt docs の実物で `filter` の入れ子を確認し、YAML と本文の両方が正しくなっている。C2 は 03回・`domain.md`・この回の 3 者が `quality_flag` 3 値・`source_system='src_careervoice'`・`loaded_at=run_started_at`・INT64 で完全に揃い、正本宣言の「変更点 3 つ」も 03回の実物と一字一句対応する。I1・I2 は原典を再取得して照合し、番号・名称・実装順とも原典どおりであることを確認した。I3 は `domain.md` の stage 値域と `P001` のイベント列から独立に検算して 6 行で一致する。Minor 11 件も全て差分として実在し、機械チェック（3 文超 0 件、`.table-wrap` 13/13、エスケープ漏れ 0 件、`check_svg.py` 0 errors）も通っている。残る 4 件はいずれも正典側の表記調整か 1 句の追記で、この回の公開を止める性質のものではない。
