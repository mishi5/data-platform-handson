# 01 粒度を宣言する — レビュー

対象: `docs/data_mart_modeling/html/01_grain.html`（590行）／ブリーフ `briefs/01.md`／報告 `reports/01_report.md`
判定: **REVISE**（critical=2 / important=5 / minor=8）

---

## 1. ブリーフ準拠表

| # | ブリーフの必須項目 | 判定 | 該当箇所 |
|---|---|---|---|
| 1 | ファイル `html/01_grain.html` | ✅ | — |
| 2 | タイトル `粒度を宣言する — データマート設計 01` | ✅ | `<title>` L6 / `<h1>` L42 |
| 3 | `p.meta` = DWT ch.2–3; Grain; Matrix; DT#3 #77 #179 ／ 再解釈 Reis | ✅ | L44 |
| 4 | 中心の判断（1行の意味を一文で宣言／宣言→ディメンション→ファクトの順序／混在は二重計上） | ✅ | §1 リード文 + 判断表6行（L46–66） |
| 5 | §2(a) `fct_review` に投稿と審査を混ぜ、`R001` の**3遷移**で `review_count` が膨らむ | ✅（内容に難あり → I3） | L70–89。4行 → `SUM(review_count)`=4 |
| 6 | §2(b) `fct_scout` と `fct_scout_funnel` を1表にして送信日／返信日が衝突 | ✅ | L91–108。A/B/C の3案すべてが壊れる表 |
| 7 | §2(c) `fct_selection_event` を作らず `fct_application_pipeline` だけ → 答えられない問い（DT#77） | ✅ | L110–136。4問 + DT#77 引用枠 |
| 8 | §3 4ステップ | ✅ | L140–156 |
| 9 | §3 原子粒度の原則 | ✅ | L158–163 |
| 10 | §3 「粒度は最も原子的な水準で宣言し、集約は後から」 | ✅ | L162 |
| 11 | §3 バスマトリクス（プロセス × コンフォームドディメンション） | ✅ | L172–199 |
| 12 | §3 domain.md §3 の**完全版**（10プロセス × 全列） | ✅ | 10行すべて、各セルが domain.md §3 と一致（機械照合済み） |
| 13 | §5 dbt で粒度を**テストとして固定** | ✅ | L245–298 |
| 14 | §5 `fct_job_posting_daily` = `snapshot_date_key` + `job_posting_id` | ✅ | L288–297 |
| 15 | §5 `fct_review` = `review_id` | ✅ | L277–286 |
| 16 | §5 `description` に粒度宣言の一文を書く規約 | ✅ | L245–248（3文構成）+ L303 の CI 案 |
| 17 | §5 `fct_selection_event` の SELECT（`selection_events` → 1行=1遷移） | ✅（SQL に欠陥 → C1/I1/I4/I5） | L307–415 |
| 18 | §6 「答えたい問い → 必要な粒度 → 表の型」を domain.md §1 の問いごとに | ✅ | L432–479。§1 の5問すべて + 共通ルール行 |
| 19 | §7(a) `fct_page_view` の粒度はセッションかページ表示か | ✅ | L483–509 |
| 20 | §7(b) `fct_contract_monthly` の粒度宣言一文 + `K001` の 2026-01〜09 の行数 | ✅ | L511–541。9行（検算一致） |
| 21 | §7(c) バスマトリクスに「参考になった」投票プロセスを1行追加 | ✅ | L543–570 |
| 22 | §8 参考ボックス 3〜5行 | ✅ | L572–577（4項目） |
| 23 | 図: **なし**（バスマトリクスは表） | ✅ | `<svg` 0件。`check_svg.py` → 0 errors / 1 warning（"svg が見つからない"＝仕様どおり） |

**ブリーフの必須内容に欠落なし。** 問題は中身の正確性（下記）に集中している。

### 機械チェックの結果

| 項目 | 結果 |
|---|---|
| `check_svg.py` | `0 errors, 1 warnings`（warning は「svg が見つからない」＝図なし指定どおり） |
| 8節構成 | ✅ `1.`〜`8.` + `参照文献` |
| `<title>` 形式 | ✅ `粒度を宣言する — データマート設計 01` |
| `p.meta` | ✅ 1件 |
| `<pre>` 内の裸の `<` | 0件（`&lt;`/`&gt;` 各3、SCD2 の比較演算子のみ） |
| `.table-wrap` | `<table>` 12個 / `table-wrap` 13（CSS 定義1 + 12個すべて包まれている） |
| CSS 変数・骨格 | style.md のテンプレートと完全一致 |
| domain.md に無いテーブル/列名 | `fct_review_vote` / `vote_count`（演習3、正典への提案と明記）、`helpful_count` / `company_review_count`（「入れてはいけない列」の反例）、`stg_careervoice__{applications,job_postings,scouts,selection_events}`（命名規約どおり）。**逸脱なし** |
| 参照 URL | 9件すべて references.md 記載のもの |
| 緩衝語（「でしょう」「かもしれ」「と思われ」等） | 0件 |

---

## 2. 指摘一覧

### Critical

#### C1. as-of join が BigQuery で構文エラーになる（DATE と TIMESTAMP の比較）

**箇所**: §5 `fct_selection_event` の SELECT、`dim_member` / `dim_company` / `dim_agent` の3つの JOIN（L396–411）

```sql
LEFT JOIN {{ ref('dim_member') }} AS dm
    ON a.member_id = dm.member_id
   AND e.event_date >= dm.valid_from
   AND e.event_date <  dm.valid_to
```

`e.event_date` は CTE で `DATE(occurred_at, 'Asia/Tokyo')` として作った **DATE**、`valid_from` / `valid_to` は domain.md §4 で **TIMESTAMP** と固定されている。BigQuery は DATE を TIMESTAMP に暗黙変換（coercion）しないため、`No matching signature for operator >= for argument types: DATE, TIMESTAMP` でコンパイルが落ちる。3箇所とも同じ。style.md の「SQL は BigQuery で実行可能な形」に反する。

加えて意味論でも誤る。仮に `TIMESTAMP(e.event_date)` を噛ませても UTC 深夜＝JST 09:00 になり、**属性変化が起きた当日のイベントが9時間ずれて旧バージョンに当たる**。この回の題材（`M001` が 6/15 に変化 → 6/20 に `S001`）は5回の核なので、01 の時点で誤った形を刷り込みたくない。

**修正案**: 比較に使うのは日付ではなくイベントの TIMESTAMP。`events` CTE で `occurred_at` を残しているのでそのまま使える。

```sql
LEFT JOIN {{ ref('dim_member') }} AS dm
    ON a.member_id = dm.member_id
   AND e.occurred_at &gt;= dm.valid_from
   AND e.occurred_at &lt;  dm.valid_to
```

`dim_company` / `dim_agent` も同様。`e.event_date` は `event_date_key` の生成とパーティション列としてのみ使う。本文リード文にも「as-of join の比較は DATE ではなく TIMESTAMP で行う（境界日のずれを防ぐ。作法は05回）」を1文足す。

#### C2. `accepted_values` が INT64 列に対して型エラーになる（`quote: false` 欠落）

**箇所**: §5 `schema.yml`、`event_count` の列テスト（L270–275）

```yaml
      - name: event_count
        data_tests:
          - accepted_values:
              arguments:
                values: [1]
```

dbt の `accepted_values` は既定 `quote=True` で、生成 SQL は `where value_field not in ('1')` になる。`event_count` は INT64（`1 AS event_count`）なので BigQuery が `No matching signature for operator IN for argument types: INT64, STRING` を返し、`dbt test` が落ちる。数値列に `accepted_values` を張るときの定番の罠で、この記事は「テストとして粒度を固定する」が主題なのでテストが動かないのは致命的。

**修正案**:

```yaml
      - name: event_count
        description: "常に 1。粒度に忠実な唯一のメジャー。"
        data_tests:
          - accepted_values:
              arguments:
                values: [1]
                quote: false
```

（`arguments:` 入れ子が dbt 1.10.5 以降という本文の注記は公式ドキュメントで確認済み・正しい。`quote` も同じ `arguments:` の下に置く。）

### Important

#### I1. 全ファクトに `audit_key` を持たせる正典の規定に反している（`audit_key` が本文に1箇所も無い）

**箇所**: §5 の `fct_selection_event` SELECT（L307–415）と `schema.yml`（L245–298）。ファイル全体で `audit_key` の出現は **0件**。

domain.md §4 に「**全ファクトは `audit_key` を持つ**（下表の FK 列では省略している）」が追記されたため、`reports/01_report.md` の「正典への変更提案 2」は解消済み。§4 のファクト表に `audit_key` が並んでいないことは省略であって不在ではない、と正典が明示した以上、01 の SELECT に無いのは正典違反になる。

**修正案**: SELECT の外部キー群の末尾に1行足し、コメントで10回への forward pointer を置く。

```sql
    COALESCE(dcat.job_category_key, -1) AS job_category_key,
    COALESCE(dch.channel_key, -1) AS channel_key,
    {{ audit_key() }} AS audit_key,   -- 監査ディメンション（DT#164）。全ファクト共通、10回で扱う
```

（マクロ化まで踏み込みたくなければ `(SELECT audit_key FROM {{ ref('dim_audit') }} WHERE batch_id = '{{ invocation_id }}')` ではなく、`CROSS JOIN` 1行の `dim_audit` 現行バッチ行を結ぶ形でもよい。行数を変えないので粒度の議論とも整合する。）
`schema.yml` の `fct_selection_event.description` の「入れないもの」の直前に、粒度キーは `event_id` のままで `audit_key` は行の由来を示す FK であることを1文添えると、10回への接続が明確になる。

#### I2. 検算不一致 — 「company 列は10プロセス中9つに ✓」は 10/10

**箇所**: §3 バスマトリクス直後の読み取り3点目（L202）

自分でマトリクスの company 列を機械的に数えた結果、**10プロセスすべてに ✓ が付いている**（クチコミ投稿 ✓ / 審査 ✓ / 閲覧 ✓ / 求人掲載 ✓ / スカウト送信 ✓(送信主体) / スカウト反応 ✓ / 選考イベント ✓ / 応募〜入社 ✓ / 契約・枠消化 ✓ / 成果報酬 ✓）。domain.md §3 も同じ。

**修正案**: 「**company 列は10プロセス全てに ✓ が付く。**唯一、全プロセスを貫くコンフォームドディメンションであり、つまり `dim_company` の定義が全社の分析結果を左右する。」に直す。数が増える方向の訂正なので主張はむしろ強くなる。ついでに「同じ列に ✓ が2つ以上あるディメンションはコンフォームドでなければならない」（L174）との対応で、company が最優先の conforming 対象であることを1文で結べる。

#### I3. §2(a) の「平均が壊れる」例が、示したデータでは実際には壊れない

**箇所**: §2(a) 2つ目の箇条書き（L88）

> 遷移行を `review_count = 0` にする: 件数は 1 に戻るが、`AVG(overall_score)` が壊れる。…`R002`（`M002` → `C001`、`defamation` で却下）のように遷移数が違うクチコミと並べた瞬間、企業間の平均が比較不能になる。

論理が通らない。示された表は `C002` の `R001` 4行だけで、`AVG(overall_score)` = (3.5×4)/4 = **3.5** ＝ 真値。歪みは出ない。しかも `R002` は `C001` のクチコミなので `C002` の平均には入らず、企業ごとに1件しかクチコミが無いなら重みが何倍でも各社の平均は正しいままになる（重み付けの歪みは**同一企業内に遷移数の異なる複数クチコミがある時にだけ**現れる）。「企業間の平均が比較不能」も、この構成では成立しない。

**修正案**: 同じ企業に2件目を置いて、自分で検算できる数値にする。

> 遷移行を `review_count = 0` にする: 件数は 1 に戻るが、`AVG(overall_score)` が壊れる。`C002` に2件目のクチコミ（差し戻し無し＝遷移1回、`overall_score` = 1.5）が付いた状況を考える。真の平均は (3.5 + 1.5) / 2 = **2.5**。しかしこの表の行を素直に平均すると `R001` が4行・2件目が2行で (3.5×4 + 1.5×2) / 6 = **2.83**。**審査で差し戻された（＝遷移が多い）クチコミほど企業平均を強く引っ張る**という、業務上まったく正当化できない重み付けが入る。

（2件目のスコアを正典外の値として置くことになるので、`report` の「迷った判断」に「§2(a) の2件目は説明のための仮想行であり正典のサンプル値ではない」と1行残すか、本文で「仮に」と明示する。数値を出さずに定性的に済ませると、この節の主張自体が検証できないままになる。）

#### I4. INNER JOIN が「行数を1行たりとも変えない」という宣言と DT#43 の両方に反する

**箇所**: §5 リード文（L307）と SELECT の FROM 句（L388–393）

> この SQL で粒度を決めているのは `FROM {{ ref('stg_careervoice__selection_events') }}` の1行だけ。以降の JOIN は**全て多対一**で、行数を1行たりとも変えてはならない。

実際の SQL は `applications` と `postings` を **INNER JOIN** している。多対一であっても INNER JOIN は行を**減らす**。応募が論理削除されている（`deleted_at`）、求人が Datastream の遅延で未着、といった現実的なケースで選考イベントが黙って消え、しかも上に置いた `equal_rowcount` が落ちる。さらに本文は数行下で「外部キー。未知は NULL ではなく `-1`（DT#43）」と `COALESCE(..., -1)` を書いており、**「参照先が無いファクト行は落とさず `-1` で残す」という DT#43 の作法と、INNER JOIN で落とす実装が同じ SQL の中で矛盾している**。

**修正案**: 2つの JOIN を LEFT に変え、リード文を「減らさない」まで含めた表現にする。

```sql
FROM events AS e
LEFT JOIN applications AS a
    ON e.application_id = a.application_id
LEFT JOIN postings AS p
    ON a.job_posting_id = p.job_posting_id
LEFT JOIN scouts AS s
    ON a.scout_id = s.scout_id
```

リード文: 「以降の JOIN は**全て多対一の LEFT JOIN**で、行数を増やしalso減らしもしない。参照先が見つからない行を INNER JOIN で落とすと、粒度は保たれたまま**母数が静かに欠ける**（DT#43 の `-1` は、まさに落とさずに残すための仕掛け）。それを検出するのが上の `equal_rowcount`。」

#### I5. `agent_key` の導出が `agent_referral` を取りこぼし、`-1` の意味づけも誤っている

**箇所**: §5 SELECT の `agent_key`（L378）と `scouts` CTE（L342–350）

```sql
    COALESCE(da.agent_key, -1) AS agent_key,          -- -1 = 直接応募
```

`agent_key` は `scouts.sender_agent_id` からしか引いていない。domain.md §2 の `applications.source_channel` には `agent_referral`（スカウト経由ではないエージェント紹介）があり、この経路の応募は `scout_id` が NULL なので **エージェント経由なのに `agent_key = -1`** になる。コメントの「-1 = 直接応募」がそのまま誤りになり、domain.md §1 の主要な問い「スカウト送信主体（企業 vs エージェント）別ファネル」「チャネル別歩留まり」が恒常的に歪む。また `sender_type = 'company'` のスカウト経由応募も `sender_agent_id` が NULL なので同じ `-1` に落ち、`source_channel` で区別できるものが `agent_key` では区別できない。

**修正案**: `-1` の意味を「エージェントが特定できない」に正し、`agent_referral` を取りこぼしていることを本文で明示する（この回の主題は粒度なので解決は先送りでよいが、黙って誤ったコードを置かない）。

```sql
    -- -1 = エージェントが特定できない（直接応募、および企業スカウト経由）
    COALESCE(da.agent_key, -1) AS agent_key,
```

に変えたうえで、SELECT 直後の段落に1文:

> なお `source_channel = 'agent_referral'`（スカウトを介さないエージェント紹介）は `scouts` に行が無いため、この実装では `agent_key = -1` に落ちる。`job_postings.agency_id` は agency 止まりで agent を特定できないので、担当者を復元するにはソース側の追加が要る——**粒度の宣言が正しくても、ディメンションの解決漏れは別の欠陥として残る**（03回）。

### Minor

#### m1. 1段落3文までの規約違反が10箇所

style.md「1段落は3文まで」に対し、`<p>` のうち **10段落**が4文以上（うち2つは5文）。該当箇所（先頭）:

| 文数 | 冒頭 |
|---|---|
| 5 | §1「この回で固定するのは一点だけ。…」 |
| 5 | §7問3「**最大の落とし穴**: 「参考になった数」を…」 |
| 4 | §3「DT#179 の7項目のうち…」／§3「行 = ビジネスプロセス、列 = …」／§4「Joe Reis は概念（CDM）→…」／§4「この枠組みに Kimball の4ステップを…」／§5「この SQL で粒度を決めているのは…」／§5「`P001` をこのモデルに通すと 6 行…」／§7問2「行数: 9行…」／§7問2「加法性の注意: …」 |

**修正案**: どれも2段落に割れば済む（例: §1 は「この回で固定するのは一点だけ。…宣言できない表は作らない。」／「宣言の順序は…。粒度が混ざった表は例外なく二重計上する。」）。内容を削る必要はない。

#### m2. `moderation_rounds = 2` が、示した3遷移と噛み合わない

**箇所**: §2(a) 末尾（L89）と遷移表（L79–83）

表の3遷移は `submitted→screening`（03-10）／`screening→submitted`（差し戻し, 03-11）／`submitted→published`（03-12）。3本目が `submitted` から直接 `published` へ飛んでおり、**審査（screening）を1度しか通っていない**。それで `moderation_rounds` = 2 と書くと、読者が「rounds は何を数えたのか」で止まる。

**修正案**: 3本目を `screening → published` にして、直前に `submitted → screening`（2巡目）を…とすると遷移が4本になりブリーフの「3遷移」を外れる。素直なのは rounds の定義を1句添えること: 「`moderation_rounds` = 2（審査に回された回数ではなく、投稿者に差し戻された往復を1として数える）」。あるいは3本目を `screening → published` に変え、2本目の差し戻し先を `screening` 内の再審査扱いにする。いずれでも可だが、**現状の遷移列と数値のどちらかは直す必要がある**。

#### m3. 「1行 × 7 個の日付キー」は domain.md §4 では8本

**箇所**: §2(c) リード文（L114）

`fct_application_pipeline` の FK は domain.md §4 で `applied_ / document_ / first_interview_ / final_interview_ / offer_ / accepted_ / hired_ / closed_date_key` の **8本**（§3 のマトリクスは `closed` を書いていないので正典内で表記に幅がある）。本文の「7個の日付キー」は `P001` が到達したマイルストーン数としては正しいが、列数の主張としては1本足りない。

**修正案**: 「累積スナップショットでは **1行**（`P001` が到達した7つのマイルストーンがそれぞれ日付キー列に埋まる。列としては未使用の `closed_date_key` を含め8本）」のように、行数の主張と列数の主張を分ける。

#### m4. DWT の章番号が本文中に一度も出てこない

`ch.2–3` の出現は `p.meta`（L44）と参照文献（L578）のみ。style.md の自己チェック「原典参照（DWT 章 / DT#）が `p.meta` と**各節**にある」を満たしていない（DT# は §1〜§7 に散っていて十分）。

**修正案**: §3 の4ステップ表のリード（現状リード文なし、いきなり `<h3>` から表）に1文: 「4ステップは Grain（2003）の定式化で、DWT 3rd ed. ch.2 でも同じ順序で提示される（ch.3 が小売の実例）。」 §2 の累積スナップショットの説明に「DWT ch.4 で扱う型」と添えてもよい。

#### m5. 原典引用が `<code>` に入っている（1箇所）

**箇所**: §3 原子粒度の原則（L160）

`<code>“Atomic data has the most dimensionality and so it can be constrained and rolled up in every way possible.”</code>` — 他の原典引用は `<div class="aside kimball">` か `<em>` を使っているのに、ここだけ `<code>`（等幅・枠付き）になっており、識別子の表示と見分けが付かない。原文は `…in every way possible **for that data source**.` で終わるので、途中で切るなら省略記号が要る（WebFetch で原文確認済み）。

**修正案**: `<em>“Atomic data has the most dimensionality and so it can be constrained and rolled up in every way possible for that data source.”</em>`（Grain, 2003）として `<em>` に統一。段落末で浮いているので、直前の文に「Kimball の言い方では——」と繋ぐと収まりがよい。

#### m6. The Matrix（1999）の「行」は原文では first-level data mart

**箇所**: §3 バスマトリクスのリード（L174）

「行 = ビジネスプロセス、列 = コンフォームドディメンション。*“a column in the matrix is a map of where the dimension is required”*（The Matrix, 1999）」——引用は原文どおり（確認済み）。ただし 1999年の原文は行を *“all the first-level data marts that you could possibly build”* と呼んでおり、「行＝ビジネスプロセス」は DWT 3rd ed.（2013）／DT#3 での言い直し。style.md は「原典の主張と現代的再解釈を分けて書く」を求めているので、原典内の用語の変遷も1行で示すのが本シリーズの流儀に合う。

**修正案**: 「行 = ビジネスプロセス（1999年の原文は *first-level data mart*、DWT 3rd ed. で「ビジネスプロセス」に言い直された。単一ソース1つ＝1行という中身は同じ）、列 = コンフォームドディメンション。」

#### m7. 演習1の設問に、未検証の前提が断定で入っている

**箇所**: §7 問1（L485）

> セッション粒度なら行数は 1/10 以下になり、パーティションスキャン量も同じだけ減る。

前段（行数）は仮定として妥当だが、後段は誤りに近い。`fct_page_view` は `view_date` パーティション + `company_key` クラスタで、企業・日付で絞るクエリのスキャン量は行数に比例して減るとは限らない（解答側でも「実スキャンは行数ほど増えない」と自分で否定している）。設問と解答で主張が衝突する。

**修正案**: 設問を「セッション粒度なら行数は 1/10 以下になる。**性能を理由にこちらを選ぶべきか**」と問いの形に落とす。断定を消せば解答の「判断は性能ではなく問いで決まる」がそのまま効く。

#### m8. 演習3の `fct_review_vote` は、ソース側テーブルが正典に無いことに触れていない

**箇所**: §7 問3（L549 の表）

`fct_review_vote` / `vote_count` は「正典への追加提案」と明記されており、report にも提案として書かれている（対応は妥当）。ただし本文は投票のソーステーブル（`review_votes` 相当）が domain.md §2 に**存在しない**ことに触れていない。4ステップの第1歩が「ソースを決める」である以上、演習の解答が第1歩を飛ばしている形になる。

**修正案**: 解答の冒頭に1行: 「前提として、ソース側に `review_votes`（`vote_id`, `review_id`, `member_id`, `voted_at`）が要る。**バスマトリクスに行を足すとは、ソースを1つ増やすと宣言すること**（4ステップの①）。」

---

## 3. 良かった点（修正不要・記録用）

- **バスマトリクスの完全再現**: 10行 × 全列を domain.md §3 と機械照合したが、`✓` / `✗` / 空セル / 注記（`✓(送信主体)` / `✗（下記参照）`）まで完全一致。この回が正本という位置づけに耐える。
- **引用の正確さ**: Grain の4引用、DT#77 の2引用、The Matrix の1引用、DT#3 の1引用を原典に当たって照合し、**すべて原文どおり**（`report` の「WebFetch で実読した」は事実）。特に「DT#179 には原子粒度・コンフォームド・4ステップの項目は無いので帰属させていない」という report の注意書きは、実際に本文でも守られている。
- **空セルの2種類**（「関係ない」と「意図的に持たない」）という読み方は原典に無い付加価値で、`fct_review` の匿名性方針（domain.md §6）と噛み合っている。
- **DT#77 の非対称性**を §2(c) → §3 → §6 共通ルール → 演習1 の4箇所で同じ形に貫いており、回全体の背骨になっている。
- §6 の「これ以上畳むと失うもの」列は、判断基準の表を「状況→選択→理由」から一段深くしている。特に「6月に送った分の返信率」と「6月に返信された数」の対比はコホートの説明として簡潔。

---

## 4. 総合判定

**REVISE**

- **Critical 2件**（C1 as-of join の DATE/TIMESTAMP 型エラー、C2 `accepted_values` の `quote: false` 欠落）は、いずれも本文に載っているコードがそのままでは BigQuery / `dbt test` で落ちるもの。「粒度をテストで固定する」がこの回の実装節の主張なので、テストが動かないのは主張の自己否定になる。
- **Important 5件**のうち I1（`audit_key`）は正典 §4 の追記への追随、I2 は算数、I3 は例が主張を支えていない、I4 は自分で書いた不変条件と実装の矛盾、I5 は正典のチャネル定義の取りこぼし。いずれも局所修正で済む。
- Minor 8件は体裁と精度。m1（段落の文数）だけは10箇所あるので一括で見直したい。

修正後の再レビューは C1 / C2 / I1 / I4 / I5 が集中する §5 と、I2 / I3 の2文で足りる。
