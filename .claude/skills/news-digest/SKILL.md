---
name: news-digest
description: news_pipeline に溜まった技術記事から週次/月次のダイジェスト資料を作り、family-share に公開して Slack に通知する。「今週のニュースまとめて」「週次ダイジェスト作って」「今月の技術動向を資料にして」といった依頼で使う。深掘り記事は図解付きで、残りは一覧で載せる。
---

# 週次/月次ニュースダイジェスト

BigQuery `tech_news` に溜まった記事を編集し、図解付きの HTML 資料にして family-share に
公開、Slack に通知する。

**読者は本人のみ。** 専門用語はそのまま使い、噛み砕くより密度を優先する。

作業ディレクトリは `news_pipeline/`。スクリプトは `uv run python scripts/digest/...` で動かす。

## 手順

### 1. 対象記事を取り出す

```bash
cd news_pipeline
uv run python scripts/digest/fetch_articles.py --period week --out /tmp/digest_list.json
```

`--period week`（7日）/ `month`（30日）。`--days N` で直接指定もできる。
本文は含まれない（件数が多く巨大になるため）。0件なら終了コード2で止まる。

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
uv run python scripts/digest/fetch_articles.py --ids id1,id2,id3 --out /tmp/digest_full.json
```

### 4. 各記事を読んで書く

深掘り記事ごとに:

- **要約**: 3〜5項目。何が変わったか、なぜ効くか、どういうトレードオフがあるか
- **図解**: 後述
- **実務への示唆**: 自分の環境（BigQuery / dbt / Dataform / Snowflake）にどう効くか。
  効かないなら「効かない理由」を書く。無理に結びつけない

一覧側の記事は**タイトル + 1行要約 + リンク + タグ**のみ。

### 5. 図解を描く

**`svg-diagram` スキルを使う。** インライン SVG で描くこと（family-share は IAP 配下の静的配信で、
外部 CDN が読める保証がない。mermaid.js などの外部 JS は使えない）。

描いたら**必ず静的検査にかける**。テキストのはみ出しや矩形の重なりは目視では見落とす:

```bash
python3 ~/.claude/skills/svg-diagram/scripts/check_svg.py <生成した html>
```

`0 errors` になるまで直す（warning のグリッドずれも直しておくと後で崩れにくい）。
仕上げにライト/ダーク両方で実際にレンダリングして目視する:

```bash
uv run --with playwright python - <<'EOF'
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    for scheme in ("light", "dark"):
        page = b.new_page(color_scheme=scheme, viewport={"width": 900, "height": 1000})
        page.goto("file:///tmp/digest.html"); page.wait_for_load_state("networkidle")
        for i, svg in enumerate(page.locator("svg").all(), 1):
            svg.screenshot(path=f"/tmp/svg{i}_{scheme}.png")
        page.close()
    b.close()
EOF
```

図にする価値があるものだけ描く。以下は図解が効く:

- 仕組み・データの流れが言葉だと追いにくいもの
- 旧方式と新方式の対比
- コンポーネント間の関係

逆に「新機能が増えた」「GA になった」だけの記事に無理やり図を付けない。その記事は一覧側が適切。

### 6. HTML を組み立てる

**単一ファイル・外部依存ゼロ。** CSS も SVG もインライン。ライト/ダーク両対応。

骨格:

```html
<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>週次ダイジェスト YYYY-MM-DD</title>
<style>
  :root {
    --bg: #ffffff; --fg: #1a1a1a; --muted: #666; --border: #e0e0e0;
    --accent: #0b6bcb; --card: #f7f8fa;
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --bg: #14171a; --fg: #e8e8e8; --muted: #9aa0a6; --border: #2c3136;
      --accent: #6aa9ff; --card: #1b1f23;
    }
  }
  body { background: var(--bg); color: var(--fg);
         font-family: -apple-system, "Hiragino Kaku Gothic ProN", "Noto Sans JP", sans-serif;
         line-height: 1.75; max-width: 900px; margin: 0 auto; padding: 24px; }
  article { border: 1px solid var(--border); border-radius: 10px;
            padding: 20px; margin-bottom: 28px; background: var(--card); }
  h2 { font-size: 1.25rem; margin-top: 0; }
  a { color: var(--accent); }
  .meta { color: var(--muted); font-size: .85rem; }
  .tag { display: inline-block; border: 1px solid var(--border); border-radius: 4px;
         padding: 1px 7px; margin-right: 4px; font-size: .75rem; color: var(--muted); }
  svg { max-width: 100%; height: auto; display: block; margin: 16px 0; }
  ul.brief li { margin-bottom: 10px; }
</style>
</head>
<body>
  <h1>週次ダイジェスト</h1>
  <p class="meta">対象期間: YYYY-MM-DD 〜 YYYY-MM-DD ／ 対象 N 件（深掘り M 件）</p>

  <h2>深掘り</h2>
  <article>
    <h2>記事タイトル</h2>
    <p class="meta"><a href="...">出典名</a> ／ <span class="tag">tag</span></p>
    <ul>…要約…</ul>
    <svg viewBox="0 0 800 400" role="img" aria-label="図の説明">…</svg>
    <p><strong>実務への示唆:</strong> …</p>
  </article>

  <h2>その他の記事</h2>
  <ul class="brief">
    <li><a href="...">タイトル</a> — 1行要約 <span class="tag">tag</span></li>
  </ul>
</body>
</html>
```

SVG は `fill="currentColor"` や CSS 変数を使い、ライト/ダークの両方で見えるようにする。
図の中で色に意味を持たせる場合は、ダークでもコントラストが保てる色を選ぶ。

### 7. 公開して通知する

**初回は必ず `--dry-run` で確認する。**

```bash
uv run python scripts/digest/publish.py --html /tmp/digest.html \
  --title "週次ダイジェスト 2026-08-30" --slack --dry-run
```

問題なければ実行:

```bash
uv run python scripts/digest/publish.py --html /tmp/digest.html \
  --title "週次ダイジェスト 2026-08-30" --slack \
  --headline "記事タイトル1" --headline "記事タイトル2"
```

成功すると URL と `content_id` が表示される。**同じ資料を更新する場合は
`--content-id <ID>` を付ける**（URL が変わらず、直近10世代が保持される）。

Slack 通知はアップロード成功後にのみ実行される。失敗した URL は通知されない。

## 注意

- **`--dry-run` を挟まずにいきなり公開しない。** family-share は Web UI からしか削除できない
- 対象0件のときは資料を作らない（`fetch_articles.py` が終了コード2で止まる）
- 期間で区切っているので週次を回す限り前回と重複しない。月次は週次と重複するが、
  総括として意図的
- 記事本文が取れていない記事（`content` が null）は深掘りに選ばない。要約だけでは
  図解が描けない
