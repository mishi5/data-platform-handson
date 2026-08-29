---
name: news-digest
description: news_pipeline に溜まった技術記事から週次/月次のダイジェスト資料を作り、family-share に公開して Slack に通知する。「今週のニュースまとめて」「週次ダイジェスト作って」「今月の技術動向を資料にして」といった依頼で使う。深掘り記事は図解付きで、残りは一覧で載せる。
---

# 週次/月次ニュースダイジェスト

BigQuery `tech_news` に溜まった記事を編集し、図解付きの HTML 資料にして family-share に
公開、Slack に通知する。

**読者は本人のみ。** 専門用語はそのまま使い、噛み砕くより密度を優先する。

## 準備

作業ディレクトリは `news_pipeline/`。スクリプトは `uv run python scripts/digest/...` で動かす。

中間ファイルはセッションのスクラッチパッド（システムプロンプトに示されるディレクトリ。
無ければ `/tmp`）に置く。以下は `$W` と書く。**最初の Bash 呼び出しで決めて、以降は同じ場所を
使う**（Bash 呼び出しをまたぐと変数は消えるので、各コマンドで書き下すか毎回 export する）:

```bash
cd news_pipeline
W=<スクラッチパッドの絶対パス>
```

生成物は `$W/digest.html` に置く。以降の検査・公開コマンドはこのパスを前提にしている。

## 手順

### 1. 対象記事を取り出す

```bash
uv run python scripts/digest/fetch_articles.py --period week --out "$W/list.json"
```

`--period week`（7日）/ `month`（30日）。`--days N` で直接指定もできる。
本文は含まれない（件数が多く巨大になるため）。

対象期間は**「昨日まで」の N 日間（JST）**。当日は収集途中（毎朝6:00 JST）なので入らない。
実行すると stderr に

```
対象期間 2026-08-23 〜 2026-08-29（JST・7日間）
42 件を .../list.json に出力しました
```

と出る。**この日付をそのまま資料のヘッダーに使う。自分で計算しない。**

0件なら終了コード2で止まり、出力ファイルは書かれない（前回の残りを読まないよう、
ファイルの中身ではなく終了コードで判断する）。

### 2. 深掘り候補を選び、承認を得る

一覧から **4〜6件** を選ぶ。基準は以下を併用する:

| 基準 | 内容 |
|---|---|
| スコア | `importance_score × relevance_score` が高い |
| トピック分散 | 同一タグに偏らせない（同じタグは最大2件まで） |
| 深掘り適性 | **図解にできる技術的な中身があるか**。製品リリース告知・参加レポート・企業ニュースは一覧側へ回す |
| 関心傾向 | `metadata` / `data governance` / `data modeling` / `data pipeline` / `bigquery` のタグに寄せる |

選んだ理由を1行ずつ添えて提示し、**承認を得てから次に進む**。ここで止まらずに深掘りすると、
違う記事を掘って時間を無駄にする。

### 3. 本文を取得する

```bash
uv run python scripts/digest/fetch_articles.py --ids id1,id2,id3 --out "$W/full.json"
```

指定した `article_id` が見つからなければ stderr に警告が出る（黙って件数が減らない）。
`content` が null の記事は要約だけでは図解が描けないので、深掘りから外して2に戻る。

### 4. 各記事を読んで書く

深掘り記事ごとに:

- **要約**: 3〜5項目。何が変わったか、なぜ効くか、どういうトレードオフがあるか
- **図解**: 手順5
- **実務への示唆**: 自分の環境（BigQuery / dbt / Dataform / Snowflake）にどう効くか。
  効かないなら「効かない理由」を書く。無理に結びつけない

一覧側の記事は**タイトル + 出典 + 1行要約 + タグ**のみ。

### 5. 図解を描く

**`svg-diagram` スキルを使う。** インライン SVG で描くこと（family-share は IAP 配下の静的配信で、
外部 CDN が読める保証がない。mermaid.js などの外部 JS は使えない）。

図にする価値があるものだけ描く。以下は図解が効く:

- 仕組み・データの流れが言葉だと追いにくいもの
- 旧方式と新方式の対比
- コンポーネント間の関係

逆に「新機能が増えた」「GA になった」だけの記事に無理やり図を付けない。その記事は一覧側が適切。

### 6. HTML を組み立てる

**単一ファイル・外部依存ゼロ。** CSS も SVG もインライン。ライト/ダーク両対応。
`$W/digest.html` に書き出す。

骨格（実際に公開した資料の構造。セレクタ名まで合わせておくと手順7の検査がそのまま通る）:

```html
<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>週次ダイジェスト YYYY-MM-DD</title>
<style>
  :root {
    --bg:#ffffff; --fg:#1a1a1a; --muted:#666; --border:#e0e0e0;
    --accent:#0b6bcb; --card:#f7f8fa;
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --bg:#14171a; --fg:#e8e8e8; --muted:#9aa0a6; --border:#2c3136;
      --accent:#6aa9ff; --card:#1b1f23;
    }
  }
  * { box-sizing: border-box; }
  body { background:var(--bg); color:var(--fg);
    font-family:-apple-system,BlinkMacSystemFont,"Hiragino Sans","Noto Sans JP","Yu Gothic UI",Meiryo,sans-serif;
    line-height:1.8; max-width:900px; margin:0 auto; padding:24px 20px 64px; }
  h1 { font-size:1.6rem; margin:0 0 4px; }
  h2.section { font-size:1.1rem; letter-spacing:.06em; color:var(--muted);
    border-bottom:1px solid var(--border); padding-bottom:8px; margin:48px 0 24px; }
  article { border:1px solid var(--border); border-radius:10px; padding:20px 22px;
    margin-bottom:28px; background:var(--card); }
  article h2 { font-size:1.2rem; margin:0 0 8px; line-height:1.5; }
  a { color:var(--accent); }
  .meta { color:var(--muted); font-size:.85rem; margin-top:0; }
  .src { color:var(--muted); font-size:.8rem; }
  .tag { display:inline-block; border:1px solid var(--border); border-radius:4px;
    padding:1px 7px; margin-right:4px; font-size:.72rem; color:var(--muted);
    vertical-align:middle; }
  code { background:var(--bg); border:1px solid var(--border); border-radius:4px;
    padding:1px 5px; font-size:.85em; }
  svg { max-width:100%; height:auto; display:block; margin:20px 0; }
  ul { padding-left:1.2em; }
  ul.brief { list-style:none; padding-left:0; }
  ul.brief li { border-bottom:1px solid var(--border); padding:12px 0; font-size:.92rem; }
  ul.brief li:last-child { border-bottom:none; }
</style>
</head>
<body>
  <h1>週次ダイジェスト</h1>
  <p class="meta">対象期間 YYYY-MM-DD 〜 YYYY-MM-DD　／　ゲート通過 N 件（深掘り M 件・一覧 K 件）</p>

  <h2 class="section">深掘り</h2>
  <article>
    <h2>記事タイトル</h2>
    <p class="meta"><a href="https://...">出典名</a>
      ／ <span class="tag">tag</span><span class="tag">tag</span></p>
    <ul>
      <li>要約項目。強調は <strong>…</strong>、識別子は <code>…</code>。</li>
    </ul>
    <!-- svg-diagram スキルが出すインライン SVG をそのまま貼る -->
    <p><strong>実務への示唆:</strong> …</p>
  </article>

  <h2 class="section">その他の記事</h2>
  <ul class="brief">
    <li><a href="https://...">タイトル</a> <span class="src">出典名</span><br>1行要約
      <span class="tag">tag</span></li>
  </ul>
</body>
</html>
```

図の SVG は `svg-diagram` スキルの出力をそのまま貼る（`id` スコープの `<style>` に
CSS 変数を置き、`@media (prefers-color-scheme:dark)` と `:root[data-theme="dark"]` の
両方で色を切り替える形）。**ページ側の `:root` 変数を SVG の中で参照しない** ―
図ごとに配色が閉じている方が、後で図だけ差し替えられる。

### 7. 検査する

HTML を書いてから検査する。テキストのはみ出しや矩形の重なりは目視では見落とす:

```bash
python3 ~/.claude/skills/svg-diagram/scripts/check_svg.py "$W/digest.html"
```

`0 errors` になるまで直す（warning のグリッドずれも直しておくと後で崩れにくい）。

仕上げにライト/ダーク両方で実際にレンダリングして目視する:

```bash
uv run --with playwright python - <<EOF
from playwright.sync_api import sync_playwright
W = "$W"
with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    for scheme in ("light", "dark"):
        page = b.new_page(color_scheme=scheme, viewport={"width": 900, "height": 1000})
        page.goto(f"file://{W}/digest.html"); page.wait_for_load_state("networkidle")
        for i, svg in enumerate(page.locator("svg").all(), 1):
            svg.screenshot(path=f"{W}/svg{i}_{scheme}.png")
        page.screenshot(path=f"{W}/page_{scheme}.png")
        page.close()
    b.close()
EOF
```

ヒアドキュメントを `<<EOF`（クォートなし）にしているのは `$W` を展開させるため。
`Executable doesn't exist` で落ちたら `uv run --with playwright playwright install chromium`。
出力した PNG を Read で開いて確認する。

### 8. 公開して通知する

**まず `--dry-run`。**

```bash
uv run python scripts/digest/publish.py --html "$W/digest.html" \
  --title "週次ダイジェスト 2026-08-30" --slack --dry-run \
  --headline "深掘り記事のタイトル1" --headline "深掘り記事のタイトル2"
```

`--headline` には**深掘りした記事のタイトルを選んだ数だけ**渡す（Slack 本文の箇条書きになる）。
`--dry-run` は本番と同じ判定（ファイルの有無・サイズ、webhook の有無、タイトル重複）を通し、
送る Slack ペイロードをそのまま表示する。**違いは POST しないことだけ**なので、ここで
`rc=0` かつ表示内容が意図どおりなら、そのまま `--dry-run` を外して実行する:

```bash
uv run python scripts/digest/publish.py --html "$W/digest.html" \
  --title "週次ダイジェスト 2026-08-30" --slack \
  --headline "深掘り記事のタイトル1" --headline "深掘り記事のタイトル2"
```

成功すると URL と `content_id`、次回の更新コマンドが表示される。

**タイトルには必ず対象期間の終了日を入れる**（`週次ダイジェスト 2026-08-30`）。publish.py は
公開済み一覧をタイトル完全一致で照合し、同名があれば新規アップロードを拒否して既存の
`content_id` を教える。日付入りなら回が違えば衝突せず、同じ回を2本上げる事故だけを止められる。

### 同じ回を差し替えるとき

図の修正など、**公開済みの回を直す場合は上書きする**:

```bash
uv run python scripts/digest/publish.py --html "$W/digest.html" \
  --title "週次ダイジェスト 2026-08-30" --content-id <ID>
```

URL は変わらず、直近10世代が保持される。`content_id` の入手経路は3つ:

1. 初回アップロードの出力（`content_id: 01...`）
2. 同名タイトルで `--dry-run` を叩く → 重複エラーが既存の `content_id` を出す
3. `family-share` スキルの一覧 API（`GET /api/contents`）

上書き時は `--slack` を付けない限り再通知しない（同じ URL を二度流さない）。

## 注意

- **`--dry-run` を挟まずにいきなり公開しない。** family-share は Web UI からしか削除できない
- 対象0件のときは資料を作らない（`fetch_articles.py` が終了コード2で止まる）
- 期間は半開区間（昨日まで）なので、週次を回す限り前回と重複しない。月次は週次と重複するが、
  総括として意図的
- 記事本文が取れていない記事（`content` が null）は深掘りに選ばない。要約だけでは
  図解が描けない
- 意図して同名の資料を2本上げたいときだけ `--force-new`。既定では止まる
