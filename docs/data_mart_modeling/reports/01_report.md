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

---

# 修正ラウンド1（レビュー `review/01_review.md` への対応）

判定 REVISE / critical 2・important 5・minor 8。**全 15 件を修正した**。

## Critical

| ID | 修正内容 |
|---|---|
| **C1** | as-of join の比較を `e.event_date`（DATE）から `e.occurred_at`（TIMESTAMP）に変更（`dim_member` / `dim_company` / `dim_agent` の3箇所）。`e.event_date` は `event_date_key` の生成と `partition_by` 用に限定。§5 リードに「`valid_from` / `valid_to` も `occurred_at` も UTC の TIMESTAMP で統一し、JST は表示と日付キー算出にだけ使う。DATE に落とすと属性変化当日のイベントが境界の丸めで旧バージョンに当たる（05回）」の1段落を追加 |
| **C2** | `accepted_values` の `arguments:` 下に `quote: false` を追加。「既定の `quote: true` だと `not in ('1')` が生成され INT64 列で型エラーになる」というコメントを YAML 内に併記 |

## Important

| ID | 修正内容 |
|---|---|
| **I1** | 正典の追記（全ファクトが `audit_key` を持つ）に追随。SELECT の外部キー群末尾に `{{ audit_key() }} AS audit_key,` を追加し、「監査ディメンション（DT#164）。全ファクト共通。値の生成は10回で定義するマクロに委ねる」とコメント。`schema.yml` の `fct_selection_event.description` にも「`audit_key` は行の由来を指す外部キーであって粒度キーではない。全ファクト共通、DT#164、10回で扱う」の2行を追加。report の「正典への変更提案 2」は解消済みとして扱う |
| **I2** | 「company 列は10プロセス中9つに ✓」→「**10プロセス全てに ✓ が付く**」に訂正。あわせて「10行を貫く唯一のディメンションであり、上の『✓ が2つ以上ある列はコンフォームドでなければならない』を最も強く受けるのがここ」を1文追加し、conforming の最優先対象であることに結んだ |
| **I3** | 調整の裁定に従い、**正典に無いスコア値を作らず**主張を検証可能な形に書き直した。「`AVG` が壊れる」の根拠を「`overall_score` がクチコミ粒度の値なので4行に複製され、平均が行数＝遷移回数で重み付けされる」に限定し、`R002` を引き合いに出す誤った推論（別企業なので `C002` の平均に入らない）を削除。加えて「`R001` 単独では 3.5 のまま正しく見えるので気付けない」「件数の 1→4 と違いテストでも目視でも表面化しない」を追加し、レビューが指摘した「示したデータでは壊れない」点を主張の一部（沈黙する欠陥である）に転化した |
| **I4** | `applications` / `postings` の `INNER JOIN` を `LEFT JOIN` に変更（`scouts` は元から LEFT）。SQL の FROM 直前に「以下は全て多対一の LEFT JOIN。行を増やさず、減らしもしない」を追加。§5 リードを2段落に分け、「減る方も同じくらい危険で見落としやすい。`INNER JOIN` で落とすと粒度は宣言どおりのまま**母数だけが静かに欠ける**」「DT#43 の `-1` は落とさずに残すための仕掛けなので、`INNER JOIN` と `COALESCE(..., -1)` を同じ SQL に同居させてはならない」を明記。`equal_rowcount` のコメントも「結合で行が増えて（一対多）も減って（INNER JOIN）もいないか」に更新し、テストが両方向を守っていることを示した |
| **I5** | 裁定どおり `-1` の意味を「**エージェント関与なし**」に訂正（旧「-1 = 直接応募」は誤り）。`postings` CTE に `agency_id` を追加し、SELECT に2経路の解決を明記: ①スカウト経由は `scouts.sender_agent_id` で担当者が一意、②`source_channel = 'agent_referral'` は手がかりが `job_postings.agency_id` だけで agency 止まり。SELECT 直後に2段落を追加し、「`agent_referral` はこの実装では `agent_key = -1` に落ちる」「`dim_agent` を `agency_id` で結ぶと一対多になり粒度が壊れるので結ばない」「担当者の復元にはソース側の追加が要る。粒度の宣言が正しくてもディメンションの解決漏れは別の欠陥として残る——粒度テストは緑のまま、チャネル別ファネルだけが恒常的に歪む（03回）」と欠陥を明示した |

## Minor（8件すべて修正）

| ID | 修正内容 |
|---|---|
| **m1** | 4文以上の段落 10 箇所をすべて分割（§1 リード、§3 原子粒度、§3 DT#179、§4 Reis、§4 継ぎ目、§5 リード、§5 `P001`、§7問2 行数、§7問2 加法性、§7問3 落とし穴）。機械チェックで **4文以上の `<p>` は 0 件**。内容は削っていない |
| **m2** | `moderation_rounds` = 2 に定義を併記: 「投稿者に差し戻された往復を1として数えた回数であって、`screening` を通過した回数ではない」。遷移表（3遷移）は変えずブリーフ準拠を維持 |
| **m3** | 「1行 × 7 個の日付キー」→「**1行**（到達した7つのマイルストーンが日付キー列に埋まる。列としては未到達の `closed_date_key` を含め8本、未達は `-1`）」。行数の主張と列数の主張を分離 |
| **m4** | DWT 章番号を本文に3箇所追加: §1 リード「（DWT ch.2 の4ステップ）」、§3 4ステップ表のリード「Grain（2003）の定式化で、DWT 3rd ed. ch.2 が同じ順序を提示し、ch.3（小売）が実例で通す」、§2(c) 冒頭「累積スナップショットは DWT ch.4 が扱うファクト型」 |
| **m5** | `<code>“Atomic data has the most dimensionality…”</code>` を `<em>` に変更し、原文の末尾 `for that data source.` を補って全文引用に。直前の文に「Kimball の言い方では——」で接続し、出典 `（Grain, 2003）` を添えた |
| **m6** | バスマトリクスのリードを2段落に分け、1段落目に「1999年の原文は行を *first-level data mart* と呼んでおり、『ビジネスプロセス』は DWT 3rd ed.（2013）と DT#3 での言い直し。単一ソース1つ＝1行という中身は変わっていない」を追加 |
| **m7** | 演習1の設問から断定を削除。「パーティションスキャン量も同じだけ減る」→「行数は 1/10 以下になる——**性能を理由にこちらを選ぶべきか**」。解答の「判断は性能ではなく問いで決まる」との衝突を解消 |
| **m8** | 演習3の解答冒頭に前提を追加: 「まず4ステップの①。**バスマトリクスに行を足すとは、ソースを1つ増やすと宣言すること**。domain.md §2 に投票のソーステーブルは無いので、`review_votes`（`vote_id`, `review_id`, `member_id`, `voted_at`）相当が新たに要る」 |

## 修正後の機械チェック

| 項目 | 結果 |
|---|---|
| HTML タグ対応（`html.parser`） | unclosed 0 / mismatch 0 |
| `<p>` の文数 | 4文以上 **0件**（修正前 10件） |
| `<pre>` 内の裸の `<` | 0件 |
| `<pre>` 外のバッククォート | 0件（m8 追記時の Markdown 記法混入を `<code>` に修正済み） |
| SQL 内の `INNER JOIN` | 0件（本文中に2件あるのは「使ってはならない」説明のため） |
| SQL 内の as-of 比較 | `e.occurred_at &gt;=` 3件 / `e.event_date &gt;=` **0件** |
| `audit_key` | SELECT 1・`description` 2 の計3箇所 |
| `quote: false` | YAML 1 + 説明コメント 1 |
| domain.md 逸脱識別子 | `fct_review_vote` / `vote_count`（演習3・提案と明記）、`helpful_count` / `company_review_count`（反例）、`stg_careervoice__*`（命名規約どおり）のみ。**新規の逸脱なし** |
| 参照 URL | 9件、references.md 記載のもののみ（変更なし） |
| 図 | なし（`<svg` 0件）。`check_svg.py` は仕様どおり 0 errors / 1 warning（svg 無し） |

## 修正で残した判断（再レビュー時の論点）

- **`agent_referral` の agent 解決は実装しなかった**（I5）。裁定は「`source_channel = 'agent_referral'` と `job_postings.agency_id` の両方から解決」だったが、`dim_agent` の自然キーは `agent_id` であり `agency_id` で結ぶと1エージェンシー複数担当者の**一対多**になる。粒度を主題にした回で粒度を壊す JOIN は書けないため、**2経路を SQL コメントと本文で明示し、経路②は agency 止まりで担当者を特定できないという欠陥として残した**（`-1` の意味は裁定どおり「エージェント関与なし」に統一）。解決にはソース側（応募と担当エージェントの紐付け）の追加が要る旨を本文と下記の提案に書いた。
- **§2(a) の平均の例に仮想スコアを置かなかった**（I3）。レビューの修正案は2件目のクチコミに `overall_score` = 1.5 を仮定するものだったが、裁定「正典に無いスコア値を作らない」を優先し、複製による重み付けという**機構**の説明に切り替えた。数値検算は `review_count` 1→4 のみで完結する。

## 正典への変更提案（更新）

1. ~~`fct_selection_event` の `audit_key`~~ — **解消**（正典に「全ファクトが持つ」と追記済み。本文も追随した）。
2. **`dim_company` / `dim_agent` の SCD2 列名**（`valid_from` / `valid_to` / `is_current`）を §4 の命名規約に1行明記してほしい。C1 の修正で3ディメンションとも `occurred_at` との TIMESTAMP 比較に統一したので、**列の型が TIMESTAMP であることも併記**したい（DATE だと C1 と同じ型エラーが再発する）。
3. **パーティション用 DATE 列**（`fct_selection_event` の `event_date` など）の規約を §4 に1行。
4. **`review_votes`（ソース）と `fct_review_vote`**。演習3で必要になった。取り込むなら §2 のソースモデルにも追加が要る（本文のマトリクスには入れていない）。
5. **新規**: `applications` に担当エージェントを持たせるか、`agent_referral` の担当者を辿る経路を正典で決めてほしい（I5）。現状 `fct_selection_event` / `fct_application_pipeline` / `fct_placement` の `agent_key` が `agent_referral` 経路で `-1` に落ち、domain.md §1 の「スカウト送信主体別ファネル」「チャネル別歩留まり」が構造的に歪む。03回・06回が `dim_scout_sender` を扱う前に決着していると望ましい。

---

# 修正ラウンド2（正典 §4 の `dim_agency` 追加への追随）

正典が `dim_agency`（`agency_id`, SCD2, `dim_agent` の縮約/rollup ディメンション）を追加し、`fct_selection_event` / `fct_application_pipeline` が `agency_key` と `agent_key` の両方を持つと定めたため、ラウンド1で「欠陥」として残した I5 の論点は**設計として解決済み**になった。それに合わせて本文を修正した。

## 修正内容

| 箇所 | 修正内容 |
|---|---|
| §5 SELECT（外部キー） | `agent_key` 1本だった箇所を **`agency_key` + `agent_key` の2本**に変更。`agency_key` は「-1 = エージェント関与なし」、`agent_key` は「-1 = 担当者を特定できない（直接応募・企業スカウト・紹介経由）」とコメントで書き分けた |
| §5 SELECT（JOIN） | `dim_agency` への as-of join を `dim_agent` の直後に追加。`ON COALESCE(p.agency_id, da.agency_id) = dag.agency_id AND e.occurred_at >= dag.valid_from AND e.occurred_at < dag.valid_to`。正典の「`job_postings.agency_id` またはスカウト送信者の所属」を `COALESCE` で表現し、比較形式は `dim_agent` と同じ TIMESTAMP の as-of。多対一なので行数は変わらない（`equal_rowcount` を維持） |
| §5 SELECT（CTE） | `postings` CTE の `agency_id` のコメントを「agency 止まりで agent は特定できない」→「`agency_key` の解決に使う」に変更。`da` を参照するため `dim_agency` は `dim_agent` より後に置いている（BigQuery の JOIN は左から評価されるので有効） |
| §5 本文（旧「欠陥」2段落） | **削除し、3段落に差し替え。**(1) 解像度の違う2本の FK を並べる理由（`agent_key` はスカウト経由でしか決まらないが `agency_key` は紹介経由でも失われない）(2) `dim_agency` は `dim_agent` の縮約ディメンション（DWT ch.4）で属性が完全な部分集合＝コンフォームド、だから `agency_tier` で drill across できる (3) **「解像度が足りないときに粗い側のディメンションを別 FK として足すのが正解で、細かい側のディメンションを粗いキーで結ぶのは誤り。前者は行数を変えず、後者は変える」**——粒度の回の主題に接続した |
| §5 `schema.yml` | `fct_selection_event.description` に「エージェント関与は解像度の違う2本で持つ: `agency_key`（縮約ディメンション、紹介経由でも決まる）と `agent_key`（スカウト経由でのみ担当者まで決まる）」を追加。`columns:` に `agency_key` / `agent_key` を追加し、両方に `not_null` テスト（`COALESCE(..., -1)` が効いているか＝DT#43 の NULL 外部キー禁止のガード） |
| §3 バスマトリクス | **列は変更していない**（指示どおり）。読み取り箇条書きの先頭に1行追加: 「**agent 列は「agent / agency」の2解像度をまとめた表記。**担当者まで決まるファクトは `agent_key`、エージェンシー止まりのファクトは縮約ディメンション `dim_agency` の `agency_key` を持つ（両方持つファクトもある）。マトリクスの列は**コンフォームドな意味の単位**であって物理テーブル1本とは限らない」 |
| 正典への変更提案 | **提案5（`applications` に担当エージェントを持たせる件）を撤回**（下記の更新後リストを参照）。ラウンド1の「修正で残した判断」に書いた I5 の留保も、正典の解決により失効した |

## 更新後の「正典への変更提案」

ラウンド1で挙げた5件のうち、1（`audit_key`）・2（SCD2 の列名と型）・3（パーティション用 DATE 列）・5（`agent_referral` の担当者解決）は**すべて正典側で解消済み**。残るのは1件のみ。

1. **`review_votes`（ソース）と `fct_review_vote`** — 演習3で必要になった。取り込むなら domain.md §2 のソースモデルにも追加が要る（本文のバスマトリクスには入れておらず、演習内で「正典への追加提案」と明記している）。取り込まない判断でも支障はない。

## 修正後の機械チェック

| 項目 | 結果 |
|---|---|
| HTML タグ対応 | unclosed 0 / mismatch 0 |
| `<p>` の文数 | 4文以上 **0件** |
| `<pre>` 内の裸の `<` / `<pre>` 外のバッククォート | 0件 / 0件 |
| `check_svg.py` | 0 errors, 1 warnings（svg 無し＝ブリーフ指定どおり） |
| SQL の JOIN | 全て `LEFT JOIN`（7本）。`dim_agent` → `dim_agency` の順序を維持 |
| as-of 比較 | `e.occurred_at &gt;=` 4件（`dim_member` / `dim_company` / `dim_agent` / `dim_agency`）、DATE 比較 0件 |
| 「欠陥」の語 | 0件（旧 I5 の記述は完全に置換済み） |
| domain.md 逸脱識別子 | `fct_review_vote` / `vote_count`（演習3・提案と明記）、`helpful_count` / `company_review_count`（反例）、`stg_careervoice__*`（命名規約どおり）のみ。`dim_agency` / `agency_key` は正典に存在する |

---

# 修正ラウンド3（再レビュー `review/01_rereview.md` §2 への対応）

新規指摘 N1〜N6 を全て反映した。裁定どおり **SQL のロジックは変更していない**（変えたのは文言・コメント・`description`・参照文献のみ）。

## Important

| ID | 修正内容 |
|---|---|
| **N1** | 指摘は正しい。`COALESCE(p.agency_id, da.agency_id)` は、直接掲載求人（例: `J001`）へのエージェント紹介では両辺とも NULL になり `agency_key = -1` に落ちる。「エージェント関与なし」という言い切りは I5 と同型の誤りだった。**3箇所を裁定の文言に修正**: ①本文「求人がエージェント経由なら紹介経由でも失われない。逆に、直接掲載求人へのエージェント紹介はどちらの手がかりも無く `-1` に落ちる——解像度を1段落としても、関与の有無そのものを常に復元できるわけではない」②SQL コメント「`-1` = エージェンシーを特定できない（直接応募、企業スカウト、および直接掲載求人へのエージェント紹介）」③`schema.yml` の `agency_key.description` を同文言に。あわせて `fct_selection_event.description` の「紹介経由でも決まる」も「求人がエージェント経由なら紹介経由でも決まる」に限定した。「エージェント関与なし」の語は本文から **0件**になった |
| **N2** | 正典 §4 と突き合わせると `dim_agency` 固有の `contract_start_date` があり「完全な部分集合」は成立しない。裁定どおり「`agency_name` / `agency_tier` を `dim_agent` と**同一の名前・同一の値**で共有する（`dim_agency` 固有の `contract_start_date` は、エージェンシー粒度でしか意味を持たない属性）」＋「共有部分がコンフォームドである限り drill across は成立する」に書き換え、2段落に分割。なお §3 バスマトリクスに残る「完全な部分集合」は Kimball のコンフォームド定義の引用なので**そのまま**（1件） |

## Minor

| ID | 修正内容 |
|---|---|
| **N3** | 裁定 (a) を採用。参照文献に **Design Tip #164**（`https://www.kimballgroup.com/2014/03/design-tip-164-built-your-audit-dimension/`、references.md 記載、「（10回で扱う）」を添えた）を追加し、DWT の行を **ch.2–3 → ch.2–4** に変更。`p.meta` はブリーフ指定なので `ch.2–3` のまま触っていない |
| **N4** | 裁定どおり定義を「**審査担当者が判定を下した回数（03-11 の差し戻しと 03-12 の公開）**であって、`screening` を通過した回数ではない」に変更。示した3遷移から 2 が導けるようになった（遷移表は無変更＝ブリーフの「3遷移」を維持） |
| **N5** | `audit_key` のコメントを裁定の文言に拡張: 「`{{ audit_key() }}` は10回で定義するマクロ。それまでは `-1`（`dim_audit` の未知行）を置いても粒度の議論は変わらない」。コピーして `dbt compile` が落ちたときの回避策が読者の手元で完結する |
| **N6** | §2(a) の2つ目の `<li>` を「…重み付けが入る。」で切り、以降を直後の `<p>` に分離（「後者の厄介さは、`R001` 単独では平均が 3.5 のまま正しく見えることにある。**壊れていても気付けない。**件数の 1→4 と違い、この歪みはテストでも目視でも表面化しない。」）。指摘対象の `<li>` は 5文 → 3文 |

## 報告の訂正

- ラウンド2 の機械チェック表「SQL の JOIN｜全て `LEFT JOIN`（**7本**）」は誤り。実際は **10本**（`applications` / `postings` / `scouts` / `dim_member` / `dim_company` / `dim_agent` / `dim_agency` / `dim_job_posting` / `dim_job_category` / `dim_channel`）。機械カウントで再確認済み。

## 修正後の機械チェック

| 項目 | 結果 |
|---|---|
| HTML タグ対応 | unclosed 0 / mismatch 0 |
| `<p>` の文数 | 4文以上 **0件** |
| `<li>` の文数 | 指摘対象（§2(a)）は解消。残る4文以上の `<li>` は5件だが、いずれも再レビューが「元から」と明記した既存箇所（§3 の読み取り3点 + §8 の2項目）で、N6 の修正案の対象外。箇条書きの1項目を機械的に割ると §3 の「3点だけ挙げる」という枠組みが崩れるため据え置いた |
| `<pre>` 内の裸の `<` / `<pre>` 外のバッククォート | 0件 / 0件 |
| SQL の `LEFT JOIN` | **10本**（`INNER JOIN` 0本。本文中の `INNER JOIN` 2件は「使ってはならない」説明） |
| as-of 比較 | `e.occurred_at &gt;=` 4件、DATE 比較 0件 |
| 「エージェント関与なし」 | **0件**（N1 で全廃） |
| 参照 URL | 10件。全て references.md 記載のものであることを機械照合（未掲載 0件） |
| `check_svg.py` | 0 errors, 1 warnings（svg 無し＝ブリーフ指定どおり） |
| domain.md 逸脱識別子 | `fct_review_vote` / `vote_count`（演習3・正典への追加提案と明記）、`helpful_count` / `company_review_count`（「入れてはいけない列」の反例）、`stg_careervoice__*`（命名規約どおり）のみ |

## 正典への変更提案（最終）

ラウンド1〜2 で挙げたもののうち残っているのは1件のみ。

1. **`review_votes`（ソース）と `fct_review_vote`** — 演習3で必要になった。取り込むなら domain.md §2 のソースモデルにも追加が要る。本文のバスマトリクスには入れておらず、演習内で「正典への追加提案」と明記しているので、**取り込まない判断でも本文は成立する**。
