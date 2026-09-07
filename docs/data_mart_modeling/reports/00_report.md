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
| Manifesto（1997） | ER モデリングは OLTP には適切で最高の性能と整合性を出す。ユーザーに届く前に次元モデルへ変換する。次元モデルの4つの強み = 予測可能な枠組み / 対称性 / 優雅な拡張性 / **定型の対処法が揃っていること** | 3 |
| Techniques PDF（= DWT 3rd ed. の技法集） | 4ステップの正確な順序と「粒度は必ずディメンション・ファクトより先」「粒度宣言は拘束力のある契約」「異なる粒度を同じファクトに混ぜない」。ch.18 相当の「Gather Business Requirements and Data Realities」 | 2, 5 |
| DT#3 | 「データマートは部門で定義される」は業界最大級の誤り。マーケとセールスに同じ受注が入ると真実のバージョンが割れ、開発・保守・ストレージが重複する。プロセス単位で一度だけ公開しコンフォームドディメンションで参照させる | 4 |
| Reis, Practical Data Modeling ch.14 | CDM =「町の地図」、名詞と動詞のみ／LDM = 属性・PK・FK・多重度、技術非依存／PDM = 技術選定と最適化。階層を飛ばすと「セマンティックな衝突」が起きる | 5 |
| Hightouch Part 1 | raw → staging（raw と 1:1、軽い変換）→ reporting models の3層。**raw を直接使ってレポート層を作らない**。Kimball の再評価は Part 2 に持ち越されている | 4 |

DWT 3rd ed. の書籍ページ（kimballgroup.com）は目次を公開していないため、ch.1 / ch.18 の内容は Techniques PDF（同書から抜き出された公式技法集）経由で確認した。章番号での参照はブリーフの指定どおり `p.meta` と本文に置いている。

## check_svg の結果

```
$ python3 ~/.claude/skills/svg-diagram/scripts/check_svg.py docs/data_mart_modeling/html/00_domain.html
0 errors, 0 warnings
```

図の仕様: ノード 9（`members` `companies` `reviews` `job_postings` `scouts` `applications` `selection_events` `contracts` `agents`）／矢印 12（すべて FK の子→親）／ゾーン 3（会員側・企業側・エージェント側）／accent 1系統。

## 迷った判断とその理由

1. **図に描かなかった FK 3本**。密度予算（矢印 ≤12）に収めるため、`members.current_company_id` → `companies`、`companies.parent_company_id` 自己参照、`agents.agency_id` → `agencies` を図から外し、図の直下の注記に落とした（`agencies` はそもそも9ノードに含まれない）。`page_views` と参照マスタもブリーフ指定どおり注記へ。**残した12本は「イベントが誰と誰を結ぶか」を全て説明できる集合**を優先した（`scouts` の `sender_company_id` / `sender_agent_id` の2本は 06回の supertype の伏線なので必ず残した）。

2. **accent の意味を「イベント行が積まれるテーブル」にした**。ER 図で色を使う自然な候補は「マスタ vs トランザクション」だが、`job_postings` と `contracts` は OLTP では状態を上書きするテーブルでありながらバスマトリクスではプロセス（`fct_job_posting_daily` / `fct_contract_monthly`）を持つ。そこで色分けの軸を「ファクトになるか」ではなく「行が積まれるか、上書きされるか」にした。これは 02回（定期スナップショットが必要になる理由）へそのまま繋がる。

3. **ゾーンにトランザクション帯を含めなかった**。会員側 = `members`、エージェント側 = `agents`、企業側 = `companies` `contracts` `job_postings`。中段の4テーブル（`reviews` `scouts` `applications` `selection_events`）はどの当事者にも属さないので枠に入れず、accent の塗りだけで示している。ゾーン ≤3 の予算とも整合する。

4. **§6 の1行目が Kimball と衝突することを明示した**。`fct_review` から `member_key` を落とす判断は 10 Rules #1（原子の詳細）と #5（NULL FK 禁止）に正面から反する。正典の決定なので本文はそのまま採用しつつ、「なぜ原典を外すのか」（少人数企業では属性だけで投稿者が特定できる）を書き、詰めは 01/03回に送った。原典と再解釈を分けて書く style.md の方針を、ここでは「原典と本シリーズの決定」の対比として適用している。

5. **演習(b) の「現在の `status` そのもの」を「どちらでもない」に分類した**。正典の `fct_review_moderation` は4つの日付キーと `is_published` / `is_rejected` を持ち、`status` 列は持たない。状態列を別に持つと二重管理になるので、ディメンション化もメジャー化もしない、が正典に沿った答えになる。

6. **§5 の「各回がどの段階に属するか」表の◎/○は本文の判断**。plan.md の「中心の判断」列から機械的に導いたが、正典に明文の対応表は無い。01回以降が別の割り当てを採るなら、こちらを直すべき箇所として挙げておく。

## 正典への変更提案

なし。`canon/domain.md` の §1 §2 §3 §6 と `canon/plan.md` の一覧表は、列を落とさずそのまま転載した。執筆中に `canon/domain.md` §4 が更新された（SCD2 の共通列、全ファクトの `audit_key`、パーティション用 DATE 列）が、00回は §4 の内容を本文で使っていないため影響なし。

## 未達事項

- SQL / YAML のコード例はゼロ。00回はブリーフ上「題材の定義」であり、`<pre><code>` を要する節が無いため意図的に入れていない（style.md の SQL 検査項目は n/a）。
- Playwright でのライト/ダーク目視は未実施（plan.md の手順5-6 の工程であり、この回の担当範囲外）。
- 図の実効フォントサイズ: viewBox 960 / `max-width:900px` で係数 0.9375。ノード名 14px → 実効 13.1px、日本語サブラベル 12px → 実効 11.3px。本文カラムの実幅（900 − padding 40 = 860px）でも 12 × 0.896 = 10.75px で下限 10px を維持する。初稿は 13/11px だったが 860px 幅で 9.85px まで落ちるため 14/12px へ引き上げた。モバイル幅ではさらに縮む（`svg { max-width:100% }`）点は responsive SVG 共通の割り切り。
