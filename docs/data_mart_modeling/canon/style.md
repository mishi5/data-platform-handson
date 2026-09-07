# 執筆規約 — データマート設計シリーズ

## 読者と文体

- **読者は本人（データエンジニア）のみ。** 専門用語はそのまま。噛み砕くより密度。
- **判断基準は表で示す。散文は最小限。** 1段落は3文まで。「〜と言えるでしょう」的な緩衝語は禁止。
- 一般論で終わらせない。**必ず題材（`canon/domain.md`）の具体テーブル・具体 ID で語る。** 「例えば顧客テーブル」ではなく「`dim_member` の `M001`」。
- 環境は **BigQuery + dbt**。SQL は BigQuery 方言、モデルは dbt（`{{ ref() }}`, `config()`, `schema.yml`）。Dataform は言及程度。
- 原典（Kimball）の主張と、現代的再解釈（`canon/references.md`）の主張を**分けて書く**。「Kimball はこう言う／現代の列指向 DWH ではこう変わる／この題材ではこう決める」の3段。
- 数値・技法名は原典どおり（SCD Type 0〜7、DT#番号）。DWT 3rd ed. の章番号で参照する。

## 各回の型（見出し構造を固定する）

```
h1  <タイトル>
p.meta  データマート設計 NN ／ 参照: DWT ch.X, Design Tip #NN ／ 再解釈: <記事名>
h2  1. この回が決めること            … 1段落 + 判断の一覧表
h2  2. どこで壊れるか                … 失敗形を題材の具体 ID で 2〜3 例
h2  3. Kimball の原則                … 原典の技法を表で整理（技法 / 定義 / 使う条件）
h2  4. 現代の再解釈                  … references.md の該当記事の要点。何が変わり何が残るか
h2  5. BigQuery + dbt での実装        … SQL / schema.yml / dbt config。題材のテーブルで
h2  6. 判断基準                      … 表。「状況 → 選択 → 理由」
h2  7. 演習                          … 2〜3問。<details><summary>解答例</summary> で同回内に解答
h2  8. 参考: 手元の基盤ではどうか     … 3〜5行の aside。dbt_logs_analysis / news_pipeline への言及はここだけ
h2  参照文献                          … 原典・記事の URL 一覧（この回で使ったものだけ）
```

節を増やしてよいが減らさない。00 回だけは「題材の定義」が主なので 2〜4 を「ソースモデル / ビジネスプロセス / バスマトリクス」に差し替える。

## 図

- **`svg-diagram` スキル（`~/.claude/skills/svg-diagram/SKILL.md`）を必ず読んでから描く。** §0 の判断基準（表で足りるなら図にしない）に従う。ブリーフで指定された図だけ描く。追加したくなったら report に理由を書く（描かない）。
- インライン SVG。`<style>` は `#dg-<id>` でスコープ、ダーク3系統、marker id 前置。
- 描いたら `python3 ~/.claude/skills/svg-diagram/scripts/check_svg.py <html>` を **0 errors** にする。warning も可能な限り消す。
- ER 図・スタースキーマ図は「ノード ≤9」の密度予算内に収める。ファクト1つ＋周囲のディメンションで描く（バスマトリクス全体を図にしない。それは表）。

## HTML

- 単一ファイル・外部依存ゼロ・ライト/ダーク両対応。ファイル名 `html/NN_<slug>.html`。
- `<title>` は `<タイトル> — データマート設計 NN`。
- 骨格は下記。CSS 変数名を変えない（シリーズで統一）。

```html
<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>粒度を宣言する — データマート設計 01</title>
<style>
  :root { --bg:#ffffff; --fg:#1a1a1a; --muted:#666; --border:#e0e0e0;
          --accent:#0b6bcb; --card:#f7f8fa; --code:#f3f4f6; }
  @media (prefers-color-scheme: dark) {
    :root { --bg:#14171a; --fg:#e8e8e8; --muted:#9aa0a6; --border:#2c3136;
            --accent:#6aa9ff; --card:#1b1f23; --code:#1f2429; }
  }
  * { box-sizing:border-box; }
  body { background:var(--bg); color:var(--fg);
    font-family:-apple-system,BlinkMacSystemFont,"Hiragino Sans","Noto Sans JP","Yu Gothic UI",Meiryo,sans-serif;
    line-height:1.8; max-width:900px; margin:0 auto; padding:24px 20px 64px; }
  h1 { font-size:1.6rem; margin:0 0 4px; line-height:1.4; }
  h2 { font-size:1.2rem; border-bottom:1px solid var(--border); padding-bottom:6px; margin:40px 0 16px; }
  h3 { font-size:1.02rem; margin:24px 0 8px; }
  .meta { color:var(--muted); font-size:.85rem; margin:0 0 24px; }
  a { color:var(--accent); }
  table { border-collapse:collapse; width:100%; margin:12px 0 20px; font-size:.9rem; }
  th, td { border:1px solid var(--border); padding:6px 10px; vertical-align:top; text-align:left; }
  th { background:var(--card); }
  .table-wrap { overflow-x:auto; }
  code { background:var(--code); border:1px solid var(--border); border-radius:4px; padding:1px 5px; font-size:.85em; }
  pre { background:var(--code); border:1px solid var(--border); border-radius:8px; padding:14px 16px;
        overflow-x:auto; font-size:.84rem; line-height:1.55; }
  pre code { background:none; border:none; padding:0; font-size:inherit; }
  .aside { border-left:3px solid var(--accent); background:var(--card); padding:10px 16px; margin:16px 0; font-size:.92rem; }
  .kimball { border-left-color:#8a6d3b; }
  .modern { border-left-color:#3b8a5a; }
  details { border:1px solid var(--border); border-radius:8px; padding:8px 14px; margin:10px 0; background:var(--card); }
  summary { cursor:pointer; font-weight:600; }
  svg { max-width:100%; height:auto; display:block; margin:20px 0; }
  ul, ol { padding-left:1.3em; }
  .ref li { font-size:.88rem; }
</style>
</head>
<body>
  <h1>…</h1>
  <p class="meta">データマート設計 01 ／ 参照: DWT ch.1–3, Design Tip #3 #77 ／ 再解釈: —</p>
  …
</body>
</html>
```

- 幅の広い表は `<div class="table-wrap">` で包む（横スクロールを表の中に閉じる）。
- SQL / YAML は `<pre><code>`。HTML エスケープ（`<` → `&lt;`）を忘れない。
- 原典の主張を引く枠は `<div class="aside kimball">`、再解釈は `<div class="aside modern">`。
- 前後の回へのリンクは張らない（family-share では個別 URL になる）。「→ 05回で扱う」のように回番号で参照する。

## 演習の形式

- 問いは題材の具体状況で出す（例: 「`M001` が 6/15 に `active` へ変わった。6/20 の `S001` をどの `member_key` に結ぶか」）。
- 解答例は SQL または表で示す。1問 15 行以内。
- 「正解が1つでない」問いには、判断基準の表のどの行を適用したかを書く。

## 参考ボックス（8節）

- `dbt_logs_analysis`（`mart_url_performance` v1/v2/incremental、`mart_error_analysis`、増分境界 `> MAX(date)`、粒度テスト無し）と `news_pipeline`（`summaries` のスコア上書き＝Type1、`tags` が REPEATED、パーティション無し、日時列が `raw_articles` 側にしかない）から、**その回の論点に関係するものだけ** 3〜5 行。
- 弱点は正直に書く。ただし「直せ」とは書かず、「この回の基準ならどう判断されるか」を書く。
- 「今後試せるチュートリアルの種」を1行添えてよい。

## 出力前の自己チェック

- [ ] `canon/domain.md` に無いテーブル名・列名・ID を使っていない
- [ ] 8節構成（00回は差し替え形）が揃っている
- [ ] 原典参照（DWT 章 / DT#）が `p.meta` と各節にある
- [ ] SQL は BigQuery で実行可能な形（`SAFE_DIVIDE`、`FARM_FINGERPRINT`、`DATE_SUB`、`PARTITION BY`）。架空関数を使わない
- [ ] 図があるなら `check_svg.py` が 0 errors
- [ ] 全 URL は `canon/references.md` にあるものか、原典の kimballgroup.com のもの
- [ ] ファイルは `html/NN_<slug>.html` に保存し、report を `reports/NN_report.md` に書いた
