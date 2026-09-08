# 06 多対多・不揃い階層・異種ディメンション — 執筆報告

- 出力: `docs/data_mart_modeling/html/06_bridges.html`
- 図: 1枚（比較図「ブリッジ vs ARRAY」、`#dg-brv`）
- `check_svg.py`: **0 errors, 0 warnings**

## 1. 完了した節

| 節 | 内容 | ブリーフ必須項目の充足 |
|---|---|---|
| 1 | 3つの問題と手段の表（多値 / 不揃い階層×2 / 異種）+ 「崩すコストをどこに払わせるか」の軸 | ✓ 4行の判断表（職種の階層を企業グループと分けて2行にした） |
| 2 | (a) 重みなし結合で `M002` のスカウトが 2倍 (b) `level3_name` NULL で `ENG-DATA`/`J001` が落ちる (c) 2本の FK で「送信主体別」が UNION | ✓ |
| 3 | 技法表 9行（多値ブリッジ / 重み / impact・weighted / 時間可変ブリッジ / 固定深さ / slightly ragged / 階層ブリッジ / pathstring / supertype-subtype）+ 原典引用 aside 2枚 + 題材への当てはめ | ✓ |
| 4 | BQ nested ガイドの要点、比較図、「何が変わり何が残るか」表 5行（結合コスト / 重み / グループキー / BI からの見え方 / 更新） | ✓ |
| 5 | (a) ブリッジ生成 + weighted report + `schema.yml` + 合計1の singular test (b) `WITH RECURSIVE` の階層ブリッジ + 「C001 グループのクチコミ数」 (c) `dim_scout_sender` の UNION (d) ARRAY 版 `dim_member` + `UNNEST` クエリ | ✓ |
| 6 | 判断基準 3表（多値 5行 / 階層 6行 / 異種 4行） | ✓ |
| 7 | (a) クチコミのタグ (b) `C003` の離脱と SCD (c) `fct_placement.agent_key = -1` — 各 `<details>` に解答例 | ✓ |
| 8 | `news_pipeline` の `summaries.tags`（REPEATED）＝ ARRAY 選択、`get_favorite_tag_counts` が impact report である指摘、`dbt_logs_analysis` の `url_path` を階層ブリッジにするチュートリアルの種 | ✓ |
| 参照文献 | 6件 | ✓ |

## 2. 読んだ文献と引用した要点

### Design Tip #142「Building Bridges」（Warren Thornthwaite）— WebFetch 済み
- ブリッジを **静的**（1ファクト行に紐づく値の集合が時間変化しない。救急外来の受診時診断）と **時間可変**（関係が測定対象のトランザクションと独立に存在し時間で変わる。顧客と口座）に分ける。
- 作り方は「値の組合せを重複排除して**グループ**を作る → グループに一意キーを振る → 行方向に展開する」。
- **この Design Tip は重み付け係数・impact/weighted・階層ブリッジには一切触れていない**（記事自身が「静的ブリッジの手順だけを扱う」と明記）。本文でもその旨を書き、重み付けの出典は DWT の口座-顧客ブリッジ側に振った。

### Kimball Dimensional Modeling Techniques（PDF, 2013）— pdftotext で全文抽出して該当節を読了
本文の `aside kimball` に原文引用。使った節:
- *Ragged/Variable Depth Hierarchies*: SQL の再帰拡張では「代替階層の差し替え・共有所有・時間変化」が扱えず、その全部がブリッジ表（あり得る全経路に1行）で解ける。
- *Alternative pathstring approach*: 経路を符号化した1列。ただし代替階層の差し替えと共有所有は表現できず、構造変更で全体の付け替えが要る。
- *Slightly Ragged/Variable Depth Hierarchies*: 深さの幅が小さいなら「複雑な機構を使うよりは」最大深さの位置属性に force-fit してよい。→ `dim_job_category` の平坦化の根拠。
- *Multivalued Dimensions and Bridge Tables*: グループディメンションキー経由でブリッジを繋ぐ。両端が Type2 なら有効/失効タイムスタンプが要り、クエリ側が特定時点に制約する。
- *Supertype and Subtype Schemas for Heterogeneous Products*: 共通属性の supertype と種別ごとの subtype（core / custom）。

### Google Cloud「ネストされた繰り返しフィールド」ガイド — WebFetch 済み
- 推奨は低〜中カーディナリティの 1対多で、一緒にクエリされるもの。理由は結合シャッフルの排除（"Denormalization localizes the data to individual slots"）。
- "Increases in storage costs are worth the performance gains of using denormalized data."
- **高カーディナリティの 1対多は避ける**、および **「すでに分析向けに最適化されたスタースキーマは、さらに非正規化してもそれほど得をしない」** と明記。この2点を根拠に、本文では「性能は選択理由にならない／決め手は BI からの見え方と更新頻度」と結論した。

### BigQuery `WITH RECURSIVE` の仕様 — 公式ドキュメントを WebFetch で確認
再帰項は CTE をちょうど1回参照、`UNION ALL` で接続、再帰項に集計/分析関数・`LIMIT` を置かない、反復上限 500。本文に反映（URL は正典に無いので引用リンクは張っていない）。

## 3. 正典への変更提案

1. **`M002` 宛のスカウトのサンプル ID が無い。** §2(a) の二重計上を語るには「希望職種2件の会員が受け取ったスカウト」が要るが、正典のスカウトは `S001`（→`M001`）と `S002`（→`M003`）だけ。本文では ID を作らず「2026-06 に `M002` 宛のスカウトが 10 件」と件数だけを仮定して書いた。**提案: `S003` = `AG02`(agent) → `M002`、`J001`、2026-06-18 送信 を追加**すると、06回の二重計上と、スカウト送信主体の agent 側の例が同じ会員で繋がる。
2. **`br_member_desired_job_category` の `member_key` をどの SCD2 版に張るかが未定義。** 正典は PK を (`member_key`, `job_category_key`) と定めるが、`dim_member` は SCD2 なので「現行版だけ」か「全版」かで、ファクトからの結合の書き方が変わる。本文では **全版に複製**する実装を採った（`fct_scout.member_key` と直結できるため）。理由と代償（「2026-06 時点の希望職種」に答えられない）は本文の aside に明記。**提案: 正典の備考に「`dim_member` の全 SCD2 版に展開する」と1行足す。**
3. **`br_company_hierarchy` の祖先側／子孫側で SCD2 版の扱いが非対称になる。** 本文の実装は祖先＝`is_current` のみ、子孫＝全版。これも正典に明記がないので暫定判断。演習(b) でこの非対称性が「時間変化する階層」の論点そのものになることを扱っている。
4. **`dim_member` の ARRAY 対案の列名。** ブリーフ指定の `desired_job_categories ARRAY<STRUCT<code STRING, priority INT64, weight FLOAT64>>` を本文で使ったが、正典の `dim_member` 属性一覧には無い。**対案（採用しない設計）としてのみ提示**しており、正典の `dim_member` は変更していない。
5. **`snap_members` という名前を1箇所で使った**（§5(d) の ARRAY 版 `dim_member` が参照する SCD2 本体）。正典の命名規約「dbt snapshot `snap_*`」の素直な具体化だが、テーブル名として列挙はされていない。
6. **演習(a) のタグ用ブリッジ表名を本文では出していない。** 「命名規約 `br_*` に従うブリッジを1本置く（表名は正典に追加が要る）」と書くに留めた。**提案: 将来 `br_review_tag` (`review_id`, `tag_key`, `weighting_factor`) と `dim_review_tag` を追加。**
7. **ブリーフの「DWT ch.6（supertype/subtype）」は 3rd ed. の章割と合っていない可能性がある。** 3rd ed. では ch.7 = Accounting（不揃い階層）、ch.8 = CRM（多値ブリッジ）は一致するが、supertype/subtype（heterogeneous products）は ch.10 Financial Services にある。`p.meta` はブリーフ指定どおり「DWT ch.6–8」としたうえで、本文中では supertype/subtype に章番号を振らず Techniques（技法一覧）に帰属させた。**正典側で章番号を確認されたい。**

## 4. 迷った判断とその理由

| 迷い | 決めたこと | 理由 |
|---|---|---|
| 図をどの節に置くか | §4（再解釈）の中、ARRAY ガイドの要点表の直後 | 図の主題が「ブリッジ表 vs ARRAY 内包」で、ARRAY を導入した直後でないと右パネルが読めない。§1 に置くと3つの問題のうち1つだけを図にする理由が説明できない |
| 図の accent をどちらのパネルに置くか | **両パネルの差分ノード**（左＝ブリッジ表、右＝ARRAY を内包した `dim_member`） | ブリーフの指定どおり。accent は「多値をどこに置くか」という1つの意味で1系統に収まる。旧 vs 新ではなく対等な2案なので、片側だけを accent にすると優劣を示唆してしまう |
| §5(c) のサロゲートキー生成 | `dbt_utils.generate_surrogate_key` を使い、「生成方式そのものは 03回の判断に従う」とコメント1行 | 正典は「03回以外は `_key` と書くだけで型に踏み込まない」。ただし `dim_scout_sender` の生成 SQL を出す以上、実行可能な形にするにはキー生成行が要る。踏み込みは最小1行に留めた |
| §5(c) に `-1` 行を入れるか | 入れない | ブリーフの必須内容は「`companies` と `agents` の UNION、`sender_type` + 固有属性は NULL 許容」まで。`-1` は演習(c) の主題なのでそちらに寄せた |
| 演習(c) の前提の扱い | 正典更新後の定義（`fct_placement.agent_key` は `applications.scout_id`→`scouts.sender_agent_id` で解決、無ければ `-1`）に合わせ、`-1` の意味を「直接応募」ではなく**「仲介した担当者を特定できない」**と読み替えて解答した | 執筆中に正典が更新され、`fct_job_posting_daily` が `agent_key` → `agency_key` に、`fct_placement` に `agency_key` と `dim_agency`（縮約ディメンション）が追加された。ブリーフの「`-1`（直接応募）」という但し書きは更新前の正典に基づくものと判断。新しい正典のほうが論点として強い（「`-1` 行を置くこと」と「`-1` が多い軸を主軸にしないこと」が別の判断であることを示せる）ので、そちらに寄せた |
| ブリッジと ARRAY のどちらを正典の第一選択にするか | ブリッジ | Google のガイド自身が「スタースキーマはすでに最適化済みで、さらなる非正規化の恩恵は小さい」と書いており、CareerVoice の規模では性能差が測定誤差。決め手は BI ツールが繰り返しフィールドを直接扱えないこと（セルフサービス性）と、ARRAY が部分更新できないこと |
| 職種の階層をブリッジにするか平坦化するか | 平坦化（正典の決定を踏襲） | Techniques の *Slightly Ragged* の条件（深さの幅が小さい）に正確に当てはまる。深さ 1〜3 で、レベル名が合意されている |

## 5. 未達事項・弱いところ

- **BI ツール側の挙動を一次情報で確認していない。** 「多くの BI ツールが繰り返しフィールドをディメンションとして直接扱えず、カスタムクエリで `UNNEST` するか、モデリング層で展開済みビューを定義する必要がある」と書いたが、正典の references.md に BI 側のドキュメントが無いため WebFetch していない。製品名（Looker Studio / Looker）を特定した断定は避け、一般化した記述にしてある。**正典に BI 側の文献を1本足すか、この記述を削るかの判断を仰ぎたい。**
- **DWT 3rd ed. 本体は WebFetch できない**（書籍）。章番号での参照は `p.meta` のみで、本文の技法定義は全て Techniques PDF（一次情報）に帰属させた。
- **`fct_review` にタグを持たせる演習(a) で、ブリッジの結合キーを `review_id`（退化ディメンション）としている。** 正典の `fct_review` は `review_id` を退化ディメンションとして持つのでこれで結べるが、サロゲートキーを介さない結合は 03回の方針次第で変わりうる。
- **§2(a) の「10件」は仮定値**（上記の変更提案1）。他の数値は全て正典のサンプル値から取っている。
