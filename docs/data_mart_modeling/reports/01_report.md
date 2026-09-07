# 01 ビジネスプロセスと粒度を宣言する — 執筆報告

- ファイル: `docs/data_mart_modeling/html/01_grain.html`
- タイトル: 粒度を宣言する — データマート設計 01
- 図: なし（ブリーフ指定どおり。バスマトリクスは表）

## 完了した節

| 節 | 内容 | ブリーフ要件の充足 |
|---|---|---|
| 1. この回が決めること | 1段落 + 判断6行の表（粒度の水準・宣言順序・複数粒度の混在・記録場所・プロセス単位・マトリクスの所在） | ✓ |
| 2. どこで壊れるか | (a) `fct_review` に投稿+審査を混ぜ `R001` の3遷移で `review_count` が 1→4 に膨らむ / (b) `fct_scout` と `fct_scout_funnel` の統合で送信日と返信日が衝突（3つの置き方すべてが壊れる表） / (c) `fct_selection_event` 無しで `P001` に答えられなくなる4つの問い（DT#77） | ✓ |
| 3. Kimball の原則 | 4ステップ表、原子粒度の原則、「原子で宣言し集約は後から」、DT#3、DT#179、**バスマトリクス完全版（10プロセス × 7ディメンション列）** + 読み取れる事実3点 | ✓ |
| 4. 現代の再解釈 | Reis の概念/論理/物理。粒度宣言が概念層と論理層の継ぎ目にあること。CareerVoice で semantic conflict が起きる語4つの表。「何が残り何が変わったか」の表 | ✓ |
| 5. BigQuery + dbt での実装 | `description` 第1文＝粒度宣言の規約（3文構成）、`schema.yml`（`fct_selection_event` / `fct_review` / `fct_job_posting_daily`）、`fct_selection_event` の SELECT 全文、入れてはいけないメジャー4例の表 | ✓ |
| 6. 判断基準 | 「答えたい問い → 1行の意味 → 表と型 → 畳むと失うもの」を domain.md §1 の5つの問いごとに + 共通ルール行 | ✓ |
| 7. 演習 | (a) `fct_page_view` の粒度 (b) `fct_contract_monthly` の粒度宣言と `K001` の行数 (c) バスマトリクスに「参考になった」投票プロセスを追加。全問 `<details>` で解答例 | ✓ |
| 8. 参考: 手元の基盤 | `mart_url_performance` の粒度テスト欠落と原子ファクト不在、`news_pipeline` の `summaries` / `raw_articles` の粒度分離。4行 | ✓ |
| 参照文献 | 9件（すべて references.md 記載 URL） | ✓ |

## 読んだ文献と引用した要点

WebFetch で実読したもの。

| 文献 | 引いた要点 |
|---|---|
| **Declaring the Grain** (2003) | “Declaring the grain means saying *exactly* what a fact table record represents.” / “If the grain isn’t clearly defined, the whole design rests on quicksand… rogue facts that introduce application errors sneak into the design.” / 粒度違反メジャーについて “Helpful facts… aren’t true to the grain. …dangerous because they invite the end user to make mistakes. Omit them from the design.” / 4ステップ（①ソース ②粒度・可能な限り原子 ③ディメンション ④粒度に忠実なメジャー）/ “Atomic data has the most dimensionality and so it can be constrained and rolled up in every way possible.” → §3 の4ステップ表・原子粒度節・§5 の「入れてはいけないメジャー」表の根拠 |
| **The Matrix** (1999) | 行 = first-level data mart（ビジネスプロセス）、列 = コンフォームドディメンション。“a column in the matrix is a map of where the dimension is required.” / 複数行に現れる列は conformed でなければならず、conformed とは「完全に同一か、一方が他方の完全な部分集合」/ マトリクスは “the invitation list to the conforming meeting” で stovepipe data marts を防ぐ → §3 バスマトリクス節のリード文と、company 列が10中9に付くという読み取り |
| **DT#3** | “all three organizations want the same core information, such as orders data.” 部門で切ると “you’ll duplicate data… multiple data flows into the marts invariably result in data inconsistencies.” 行は Marketing/Sales/Finance ではなくプロセス → §3 の DT#3 節（CareerVoice に「営業」「編集」行は無い） |
| **DT#77** | “Summary data naturally pre-supposes the typical business questions.” / **“you can’t magically explode summary data into its underlying components.”** / 集約は “performance-tuning complements to the atomic level, not replacements.” → §2(c) の引用枠、§6 の共通ルール行、演習1の解答の非対称性 |
| **DT#179** | Joy Mundy の7項目。この回で使ったのは “The dimensional model is the best specification for the DW/BI system.” / “Dimensional modeling is a group activity.”（4〜6週で 50〜60時間）/ “It’s all about the business.” → §3 の「粒度宣言が仕様書になる」節。**注意**: この DT には原子粒度・コンフォームドディメンション・4ステップの項目は無い（記憶で書くと混同しやすい）。本文でもその3つは DT#179 に帰属させていない |
| **Reis, Ch.14 The Levels of Data Modeling** | CDM/LDM/物理の3層。“At this stage, your goal is to capture the big picture: what fundamental concepts you’re modeling and how they relate to each other.” / 概念層を飛ばすと “semantic conflict—where IT and Business can’t agree on what a ‘Customer’ even means” / Larry Burns 引用 “The data model itself is not as important as the conversations the data model promotes.” → §4 全体 |
| **dbt-utils README / dbt docs (data-tests)** | 実装の裏取りのみで本文には URL を出していない。`data_tests:` が現行キー（`tests:` は旧称）、引数の `arguments:` 入れ子は **v1.10.5 以降**、それ以前は引数をテスト名直下に置く。本文にこの版差を注記した |

DWT 3rd ed. ch.2–3 は書籍のため URL のみ参照（章番号で引用）。

## check_svg の結果

**n/a**（この回は図なし）。`<svg` 要素は 0 件。代わりに以下を実行して確認した。

- `html.parser` によるタグ対応チェック: unclosed 0 / mismatch 0
- `<pre>` 内の裸の `<` : 0 件（`&lt;` / `&gt;` でエスケープ済み、6箇所）

## 正典への変更提案

1. **`dim_company` / `dim_agent` の SCD2 列名を明記してほしい。** domain.md §4 は `valid_from` / `valid_to` / `is_current` を `dim_member` の備考にしか書いていないが、`dim_company`（Type 6 相当）と `dim_agent`（Type 2）も同じ列が要る。§5 の `fct_selection_event` の as-of join では 3 ディメンションとも `valid_from` / `valid_to` で書いた。**「SCD2 のディメンションは一律 `<entity>_key`, `valid_from`, `valid_to`, `is_current` を持つ」を §4 の命名規約に1行足すことを提案。**（05回が本格的に扱う前に、01〜04 が同じ書き方をしている必要がある）

2. **`fct_selection_event` に `audit_key` が無い。** §4 のファクト表で、`fct_selection_event` と `fct_scout_funnel` / `fct_application_pipeline` / `fct_contract_monthly` / `fct_placement` / `fct_job_posting_daily` は `audit_key` を FK に持たない。一方 §4 の `dim_audit` 行には「**全ファクトに `audit_key`**」と書かれており矛盾する。10回（DT#164）で扱うはずなので、そこまでに統一しておきたい。本文では正典の FK 一覧に忠実に、`fct_selection_event` から `audit_key` を落とした。

3. **パーティション列の扱い。** `fct_selection_event` に `event_date`（DATE）を出力した。正典のメジャー/退化一覧には無い列だが、`partition_by` に DATE 列が要るため物理的に必要。`fct_page_view` の備考は「パーティション: `view_date`」と書いており同じ形なので、**「累積/トランザクションファクトはパーティション用の DATE 列 `<role>_date` を `<role>_date_key` と並べて持つ」を §4 に1行足すことを提案。**

4. **`fct_review_vote`（新規、演習3の答え）。** ブリーフ指定の演習でバスマトリクスに1行足させるため、`fct_review_vote`（トランザクション・ファクトレス、1行 = 1会員による1クチコミへの1投票、date ✓ / member ✓ / company ✓ / job_posting ✗ / agent ✗ / job_category ✓ / junk = `dim_page_context` 再利用）を**演習の中でだけ**提示した。本文の §3 バスマトリクスには入れていない。ソース側にも `review_votes` 相当のテーブルが無いので、正典に取り込むなら §2 のソースモデルにも追加が要る。**取り込まない判断でも構わない**（演習内では「正典への追加提案」と明記してある）。

## 迷った判断とその理由

| 迷った点 | 決めたこと | 理由 |
|---|---|---|
| §2(a) の「`R001` の 3 遷移」の中身 | `submitted`→`screening`(03-10) / `screening`→`submitted`(03-11, `low_quality` 差し戻し) / `submitted`→`published`(03-12) | 正典は `R001` を「03-10 投稿・03-12 公開」としか書かない。素直に読むと遷移は2つなので、ブリーフの「3遷移」を満たすには差し戻し1回を挟むしかない。`fct_review_moderation` のメジャーに `moderation_rounds` があるため複数ラウンドは正典が想定済みで、`reason_code` の `low_quality` も既存値。新しい列・値を作らずに済む唯一の構成 |
| §2(a) で平均の歪みを示すか | `R002` に `overall_score` の具体値を与えず、「遷移数の違いが重みの違いになる」と定性的に書いた | `R002` のスコアは正典に無い。数値例を作ると正典逸脱になるので、`review_count` の 1→4 だけを数値で示した（ブリーフが求めているのもそれ） |
| §5 の SQL をどこまで書くか | ディメンション結合まで含めて完成形で書き、as-of join は「05回」と注記 | 「BigQuery + dbt で実際に動く形」がルール。JOIN を省略すると動かない。ただし本節の主題は粒度なので、リード文で「粒度を決めているのは `FROM stg_careervoice__selection_events` の1行だけ、以降の JOIN は全て多対一で行数を変えない」と明示し、`equal_rowcount` テストでそれを守らせる構成にした |
| `fct_review` の粒度テストを `unique` にするか `unique_combination_of_columns` にするか | 後者（ブリーフ指定どおり）。理由を本文に書いた | 単一列なら `unique` で同じ結果だが、全ファクトでテストの種類を揃えておけば `schema.yml` を grep するだけで全ファクトの粒度キーが一覧できる。粒度キーの列数は設計変更で変わるので、そのたびにテスト種別を変えたくない |
| `data_tests:` か `tests:` か、`arguments:` 入れ子を使うか | `data_tests:` + `arguments:`（現行の推奨形）。版差を1行注記 | dbt 公式ドキュメントで `tests:` は旧称、`arguments:` 入れ子は v1.10.5 以降と確認した。読者が古い dbt を使う可能性があるので注記のみ添えた |
| §4 で Fowler / Fivetran OBT に触れるか | 触れない | references.md の割当では 01 の再解釈は Reis のみ。「集約を作る動機が変わった」という論点は Reis の枠内では言えないので、07回への forward pointer にとどめた |
| 演習3で新しいファクト名を出すこと | 出した（「正典への追加提案」と明記） | ブリーフが「バスマトリクスに1行足す」演習を必須にしているため、名前を付けずには答えられない。禁止事項（正典に無い名前を作らない）との衝突は、本文のマトリクスに入れず演習内に隔離し、report に提案として書くことで解消した |

## 未達事項

なし。ブリーフの必須内容（§2 の a/b/c、§3 のバスマトリクス完全版、§5 の3つの `schema.yml` と `fct_selection_event` の SELECT、§6 の判断基準表、§7 の3演習）はすべて本文に入っている。
