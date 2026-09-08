# 00 題材と簡易データモデル — 執筆報告

出力: `docs/data_mart_modeling/html/00_domain.html`（`<title>` = `題材と簡易データモデル — データマート設計 00`）

## 完了した節

| 節 | 内容 | ブリーフの必須要素 |
|---|---|---|
| 導入（h1 直後） | DMBOK シリーズ（総論）との役割分担を1段落で宣言 | ✓ |
| 1. このシリーズが扱うこと | `canon/plan.md` の全11回一覧表（回番号・タイトル・中心の判断・図）をそのまま転載。10 Rules #10 の aside | ✓ 全11回一覧表 |
| 2. 題材: CareerVoice | domain.md §1 のサービス概要表 + 分析側が答えたい問い5件。DWT ch.18 の「要求とデータの現実を同時に掴む」aside | ✓ |
| 3. ソースシステムの簡易モデル | domain.md §2 の4表（マスタ / クチコミ / 求人・スカウト・応募 / 契約・閲覧）を**列を落とさず**転載。OLTP 設計意図（正規化・状態列・論理削除）。Manifesto の aside。**OLTP ER 図** | ✓ 全テーブル表 / 図 |
| 4. ビジネスプロセスの棚卸し | DT#3 の aside（部門ではなくプロセス）、プロセスの見つけ方、domain.md §3 バスマトリクスを**予告として**転載。Hightouch Part 1 の3層 aside | ✓ バスマトリクス予告 |
| 5. 概念 → 論理 → 物理 | Reis ch.14 の3階層 aside、階層 × DWT 4ステップの対応表、全11回がどの段階に属するかの表、Techniques の4ステップ引用 aside | ✓ |
| 6. 判断基準: このシリーズで固定した設計判断 | domain.md §6 を「扱う回」列込みで転載 + 1行目（匿名性）が 10 Rules #1/#5 と衝突する点の明示 | ✓ |
| 7. 演習 | (a) プロセス棚卸し（3条件チェック形式、解答例は CareerVoice の5プロセス表 + 落とした候補）、(b) `reviews.status` 遷移の分類（ファクト/ディメンションの行き先表 + `R001`/`R002` の具体値）。両方 `<details>` で同回内に解答 | ✓ |
| 8. 参考: 手元の基盤 | `dbt_logs_analysis` = データソース起点（`mart_url_performance` はプロセス名でない）／ `news_pipeline` = プロセス起点（収集・要約・通知・お気に入り）の対比 + チュートリアルの種1行 | ✓ |
| 参照文献 | この回で使った9本のみ | ✓ |

## 読んだ文献と引用した要点

WebFetch で実際に読んだもの（Techniques PDF は WebFetch がバイナリを抽出できなかったため、保存された PDF を `pdftotext` でテキスト化して読んだ）。

| 文献 | 引用した要点 | 使った節 |
|---|---|---|
| 10 Rules（2009） | Rule #1 原子の詳細を入れる／#5 FK を NULL にしない／#7 コードと表示名はディメンションへ・NULL は意味のある既定値で置換／#10 要求とソースの現実の間に立つ | 1, 6, 7(b) |
| Manifesto（1997） | ER モデリングは OLTP には適切で最高の性能と整合性を出す。ユーザーに届く前に次元モデルへ変換する。次元モデルの5つの強み = 予測可能な枠組み / 対称性 / 優雅な拡張性 / **定型の対処法が揃っていること** / 集約を管理するユーティリティ群 | 3 |
| Techniques PDF（= DWT 3rd ed. の技法集） | 4ステップの正確な順序と「粒度は必ずディメンション・ファクトより先」「粒度宣言は拘束力のある契約」「異なる粒度を同じファクトに混ぜない」。ch.18 相当の「Gather Business Requirements and Data Realities」 | 2, 5 |
| DT#3 | 「データマートは部門で定義される」は業界最大級の誤り。マーケとセールスに同じ受注が入ると真実のバージョンが割れ、開発・保守・ストレージが重複する。プロセス単位で一度だけ公開しコンフォームドディメンションで参照させる | 4 |
| Reis, Practical Data Modeling ch.14 | CDM =「町の計画（Town Plan）」、名詞と動詞のみ／LDM = 属性・PK・FK・多重度、技術非依存／PDM = 技術選定と最適化。階層を飛ばすと部門ごとに「顧客」の定義が食い違う | 5 |
| Hightouch Part 1 | raw → staging（raw と 1:1、軽い変換）→ reporting models の3層。**raw を直接使ってレポート層を作らない**。Kimball の再評価は Part 2 に持ち越されている | 4 |

DWT 3rd ed. の書籍ページ（kimballgroup.com）は目次を公開していないため、ch.1 / ch.18 の内容は Techniques PDF（同書から抜き出された公式技法集）経由で確認した。章番号での参照はブリーフの指定どおり `p.meta` と本文に置いている。

## check_svg の結果

```
$ python3 ~/.claude/skills/svg-diagram/scripts/check_svg.py docs/data_mart_modeling/html/00_domain.html
0 errors, 0 warnings
```

図の仕様: ノード 9（`members` `companies` `reviews` `job_postings` `scouts` `applications` `selection_events` `contracts` `agents`）／矢印 12（すべて FK の子→親）／ゾーン 3（会員側・企業側・エージェント側）／accent 1系統。

## 迷った判断とその理由

1. **図に描かなかった FK 4本**。密度予算（矢印 ≤12）に収めるため、`members.current_company_id` → `companies`、`companies.parent_company_id` 自己参照、`agents.agency_id` → `agencies`、`job_postings.agency_id` → `agencies` を図から外し、図の直下の注記に落とした（`agencies` はそもそも9ノードに含まれないので、省略テーブルの列挙にも入れた）。`page_views` と参照マスタもブリーフ指定どおり注記へ。**残した12本は「イベントが誰と誰を結ぶか」を全て説明できる集合**を優先した（`scouts` の `sender_company_id` / `sender_agent_id` の2本は 06回の supertype の伏線なので必ず残した）。

2. **accent の意味を「イベントが1行として記録されるテーブル」にした**。ER 図で色を使う自然な候補は「マスタ vs トランザクション」だが、`job_postings` と `contracts` は OLTP では状態を上書きするテーブルでありながらバスマトリクスではプロセス（`fct_job_posting_daily` / `fct_contract_monthly`）を持つ。そこで色分けの軸を「ファクトになるか」ではなく「イベントが1行として記録されるか、当事者・契約のマスタか」にした。塗ったテーブル（`reviews` `scouts`）も `status` や `opened_at` が後から更新される点は図の注記で明示している（追記と更新が混ざることが 02回・05回の論点）。

3. **ゾーンにトランザクション帯を含めなかった**。会員側 = `members`、エージェント側 = `agents`、企業側 = `companies` `contracts` `job_postings`。中段の4テーブル（`reviews` `scouts` `applications` `selection_events`）はどの当事者にも属さないので枠に入れず、accent の塗りだけで示している。ゾーン ≤3 の予算とも整合する。

4. **§6 の1行目が Kimball と衝突することを明示した**。`fct_review` から `member_key` を落とす判断は 10 Rules #1（原子の詳細）と #5（NULL FK 禁止）に正面から反する。正典の決定なので本文はそのまま採用しつつ、「なぜ原典を外すのか」（少人数企業では属性だけで投稿者が特定できる）を書き、詰めは 01/03回に送った。原典と再解釈を分けて書く style.md の方針を、ここでは「原典と本シリーズの決定」の対比として適用している。

5. **演習(b) の「現在の `status` そのもの」を「どちらでもない」に分類した**。正典の `fct_review_moderation` は4つの日付キーと `is_published` / `is_rejected` を持ち、`status` 列は持たない。状態列を別に持つと二重管理になるので、ディメンション化もメジャー化もしない、が正典に沿った答えになる。

6. **§5 の「各回がどの段階に属するか」表の◎/○は本文の判断**。plan.md の「中心の判断」列から機械的に導いたが、正典に明文の対応表は無い。01回以降が別の割り当てを採るなら、こちらを直すべき箇所として挙げておく。

## 正典への変更提案

2件（いずれも本文は正典の表に合わせて修正済み。文言側の明確化提案）。

1. `canon/domain.md` §2 の前書き「`updated_at` / 論理削除 `deleted_at` を持つ」は主語が曖昧で、「全テーブルが両方を持つ」と読める。**「更新列 `updated_at` を持つのは下表で列挙したテーブルのみ。論理削除 `deleted_at` は `members` だけ」** と明確化したい。この誤読は 05回（SCD / CDC）や 09回（増分境界）で `stg_careervoice__scouts.updated_at` や `companies.deleted_at IS NULL` という正典上あり得ないコードを誘発する。
2. `canon/references.md` の Hightouch 1 の要点欄「Kimball → Inmon → OBT の整理」は誤り。実際の Part 1 は raw → staging → reporting models の3層のみを扱い、Kimball / Wide table の比較は Part 2 以降へ明示的に繰り越されている。**「raw / staging / reporting の3層。raw を直接レポート層に使わない。Kimball vs OBT の比較は Part 2 以降」** に修正したい（07回が Hightouch 2 を引くため、放置すると混乱する）。

なお `canon/domain.md` の §1 §2 §3 §6 と `canon/plan.md` の一覧表は、列を落とさずそのまま転載した。執筆中に `canon/domain.md` §4 が更新された（SCD2 の共通列、全ファクトの `audit_key`、パーティション用 DATE 列）が、00回は §4 の内容を本文で使っていないため影響なし。

## 未達事項

- SQL / YAML のコード例はゼロ。00回はブリーフ上「題材の定義」であり、`<pre><code>` を要する節が無いため意図的に入れていない（style.md の SQL 検査項目は n/a）。
- Playwright でのライト/ダーク目視は未実施（plan.md の手順5-6 の工程であり、この回の担当範囲外）。
- 図の実効フォントサイズ: viewBox 960 / `max-width:900px` で係数 0.9375。ノード名 14px → 実効 13.1px、日本語サブラベル 12px → 実効 11.3px。本文カラムの実幅（900 − padding 40 = 860px）でも 12 × 0.896 = 10.75px で下限 10px を維持する。初稿は 13/11px だったが 860px 幅で 9.85px まで落ちるため 14/12px へ引き上げた。モバイル幅ではさらに縮む（`svg { max-width:100% }`）点は responsive SVG 共通の割り切り。

## 修正ラウンド1（`review/00_review.md` への対応）

| ID | 対応 |
|---|---|
| Critical-1 | §3 冒頭を正典 §2 の列一覧に合わせ、`updated_at` を持つ8表と持たない9表を列挙、`deleted_at` は `members` のみと明記。「OLTP としての設計意図」の削除の記述も「`members` の削除も `deleted_at` を立てるだけ」に限定 |
| Important-1 | Manifesto の aside を「強みは5つ」に訂正し、第5の強み（集約を管理するユーティリティ群）を追記。「5つ目の集約は 04回・08回で扱う」で `agg_*` へ接続 |
| Important-2 | 図の凡例を「イベントが1行として記録されるテーブル（白は当事者・契約のマスタ）」に変更し、図直下に「塗ったテーブルも `reviews.status` / `scouts.opened_at` のように後から更新される」の注記を追加。図形・色分けは変更なし |
| Important-3 | 図注の省略 FK を 3本 → **4本**（`job_postings.agency_id` → `agencies` を追加、`J002` が `A01` 経由の根拠として明示）。`agencies` を省略テーブルの列挙（「仲介会社そのもの」）に追加。図のノードは9のまま |
| Minor-1 | §6 転載の1行目に `<strong>ジャンク化した <code>dim_review_attributes</code></strong>` の強調を復元 |
| Minor-2 | 10 Rules Rule #5 の要約を「多対多はファクトテーブルで解決し、その外部キーを NULL にしてはならない」に訂正 |
| Minor-3 | 地の文2箇所を分割。§3「状態は列で持つ…」を3文に、§6「1行目だけが Kimball の原則と…」を3文＋別段落2文に整理（`.aside` の引用枠は原典要約のため据え置き） |
| Minor-4 | §8 を `<p>` 3本から `<div class="aside">` 1つに集約。「Cloud Run のエンドポイントを分けた結果」の1文を削り、結論文（アプリの処理境界＝プロセス境界）に吸収して4行に圧縮 |
| Minor-5 | Reis の比喩を「町の計画（Town Plan）」に訂正。「セマンティックな衝突」の鉤括弧を外し「部門ごとに『顧客』の定義が食い違ったまま」に言い換え |
| Minor-6 | 「問いの半分」→「§2 に挙げた5つの問いのうち2つ」に訂正 |
| Minor-7 | 演習(b) の行見出しを「差し戻し回数」→「審査ラウンド数」に変更し、理由欄を `review_moderation_events` の行数＋「差し戻しを表現するなら正典の `status` 遷移に足す必要がある（01回で検討）」に書き換え |
| Minor-8 | 本報告の「正典への変更提案」を「なし」から2件（domain.md §2 前書きの明確化 / references.md の Hightouch 1 要点欄の訂正）に更新 |

再確認したもの: 正典 §2（17テーブル × 3列）・§3（10行 × 11列）・§6（7行 × 4列）を最新の `canon/domain.md` と機械照合し差分ゼロ（正典の §4 §5 は執筆後に更新されたが、00回は転載していないため影響なし）。`check_svg.py` は `0 errors, 0 warnings`。
