---
name: news-digest
description: news_pipeline に溜まった技術記事から週次/2週間/月次のダイジェスト資料を作り、family-share に公開して Slack に通知する。「今週のニュースまとめて」「2週間のまとめをつくって」「週次ダイジェスト作って」「今月の技術動向を資料にして」といった依頼で使う。深掘り記事は図解付きで、残りはテーマ別の一覧で載せる。
---

# ニュースダイジェスト（週次 / 2週間 / 月次）

BigQuery `tech_news` に溜まった記事を編集し、図解付きの HTML 資料にする。それを family-share に
公開し（タグ `DataNews`）、Slack に通知する。

**読者は本人のみ。** 専門用語はそのまま使い、噛み砕くより密度を優先する。
**業務環境は BigQuery ＋ Dataform。** 実務への示唆はこのリポジトリの dbt ではなく Dataform を前提に書く。

## 準備

コマンドはリポジトリのルートから `uv run --directory news_pipeline …` で動かす
（`cd news_pipeline && …` と束ねない）。

中間ファイルはセッションのスクラッチパッド（システムプロンプトに示されるディレクトリ。
無ければ `/tmp`）に置く。以下は `$W` と書く。Bash 呼び出しをまたぐと変数は消えるので、
**各コマンドの先頭で `W=<絶対パス>` を書き直す**。

| ファイル | 中身 |
|---|---|
| `$W/list.json` | 対象期間の一覧（本文なし） |
| `$W/full.json`・`$W/art<N>.txt` | 深掘り記事の本文 |
| `$W/digest_src.html` | 原稿（プレースホルダ入り） |
| `$W/list_frag.html` | 一覧の HTML 断片 |
| `$W/digest.html` | 公開用。検査・公開コマンドはこのパスを前提にする |

## 期間とタイトル

| 依頼 | 取り出し | タイトル（`<title>`・`--title`） |
|---|---|---|
| 今週・週次 | `--period week` | `週次ダイジェスト <終了日>` |
| 2週間・隔週 | `--days 14` | `2週間ダイジェスト <終了日>` |
| 今月・月次 | `--period month` | `月次ダイジェスト <終了日>` |
| その他の日数 | `--days N` | `<N>日間ダイジェスト <終了日>` |

**終了日は `fetch_articles.py` が stderr に出す値をそのまま使う。自分で計算しない。**
タイトルに終了日を入れるのは、publish.py の同名チェックで「同じ回を2本上げる事故」だけを止めるため。

## 手順

### 1. 対象記事を取り出す

```bash
W=<スクラッチパッド>
uv run --directory news_pipeline python scripts/digest/fetch_articles.py --days 14 --out "$W/list.json"
```

stderr に `対象期間 2026-11-03 〜 2026-11-16（JST・14日間）` と `127 件を … に出力しました` が出る。
期間は**昨日までの N 日間（JST）**。当日は収集途中（毎朝 6:00 JST）なので入らない。

0件なら終了コード2で止まり、出力ファイルは書かれない。前回の残りを読まないよう、
ファイルの中身ではなく終了コードで判断する。

### 2. 深掘り候補を選び、承認を得る

一覧はスコア順の1行表示で見る（JSON をそのまま読むと 100 件超で数十 KB になる）:

```bash
uv run --directory news_pipeline python scripts/digest/list_view.py rank --list "$W/list.json"
```

`score article_id(12桁) [出典] タイトル | タグ` の形で出る。ここから **4〜6件** を選ぶ:

| 基準 | 内容 |
|---|---|
| スコア | `importance × relevance` が高い |
| トピック分散 | 同じタグに偏らせない（同じタグは最大2件まで） |
| 深掘り適性 | **図解にできる技術的な中身があるか**。製品リリース告知・参加レポート・企業ニュースは一覧へ回す |
| 関心傾向 | `metadata` / `data governance` / `data modeling` / `data pipeline` / `bigquery` / `dataform` に関係する記事を優先する |
| 期間の主題 | 発表が集中したテーマ（例: セマンティックレイヤー）は、個別の発表ではなく**整理している記事**を1本選ぶ。個別の発表は「この期間の動き」と一覧で扱う |

表で提示する（列: 記事・選んだ理由1行）。一覧へ回す主な記事と、入れ替え候補を2件ほど添える。
**承認を得てから次に進む。** ここで止まらずに深掘りすると、違う記事を掘って時間を無駄にする。

承認と一緒に分量や形式の指示が来たら、手順4の既定より優先する。

### 3. 本文を取得する

rank の id は12桁なので、完全な id に引き直してから本文を取る:

```bash
W=<スクラッチパッド>
IDS=$(uv run --directory news_pipeline python scripts/digest/list_view.py ids --list "$W/list.json" 51748b415356,23a8ffc3cc07)
uv run --directory news_pipeline python scripts/digest/fetch_articles.py --ids "$IDS" --out "$W/full.json"
```

`ids` は接頭辞が一意に決まらないと終了コード1で止まる。`--ids` で見つからない id は
stderr に警告が出る（黙って件数は減らない）。

本文は1記事1ファイルに書き出してから Read で読む（6本まとめて cat すると出力が切り詰められる）:

```bash
python3 - "$W" <<'EOF'
import json, sys
W = sys.argv[1]
for i, a in enumerate(json.load(open(f"{W}/full.json"))):
    c = a.get("content") or ""
    open(f"{W}/art{i}.txt", "w").write(f"{a['title']}\n{a['url']}\nSUMMARY: {a.get('summary')}\n\n{c}")
    print(i, len(c), a["title"][:50])
EOF
```

`content` が空の記事は図解が描けないので深掘りから外し、手順2に戻る。

本文を読む前にユーザーへ一言、進捗を伝える（ここから図と原稿で時間がかかる）。

### 4. 原稿を書く

`template.html`（このスキルのディレクトリ）を `$W/digest_src.html` にコピーして埋める。
CSS・目次・節の骨格・プレースホルダが入っている。

**この期間の動き（冒頭）**
- 一覧全体から読める動きを2〜4段落。各段落は太字の1文で始め、根拠の記事・数字を続ける
- BigQuery リリースノートが期間内にあれば、日付・内容・状態（GA / Preview）の表にする。
  リリースノートの要約は `list.json` の該当記事（出典 `BigQuery Release Notes`）から取る

**深掘り記事（1本あたり）**

| 節 | 内容 |
|---|---|
| 背景 | 何が問題で、記事は何をしたか（3〜4文） |
| 要点 | 6〜8項目。各項目は太字の結論＋根拠・数字・条件。数字は記事の値をそのまま書く |
| 図 | 手順5 |
| 補足 | 表・コード・手順のどれか1つ。記事の比較表、判定コード、導入手順など |
| 実務への示唆 | 3〜4項目。BigQuery / Dataform で同じことをどう実現するか、何が違うか。当てはまらないなら当てはまらない理由を書く |
| 留保 | 必要なときだけ。数字の出どころ、ベンダー自身の測定、原典が確認できない点 |

**二次資料に注意する。** 複数の資料を束ねた記事（note のまとめ記事など）は、
タイトルの数字が誰のものか取り違えやすい。資料ごとに「主張・数字」を表にして出どころを分け、
タイトルと中身が食い違えば留保に書く。

**一覧（その他の記事）**は手で書かない。原稿には `<!--LIST-->` だけを置き、手順6で差し込む。

### 5. 図解を描く

**`svg-diagram` スキルを読み込んでから描く。** インライン SVG のみ（family-share は IAP 配下の
静的配信で、外部 CDN が読める保証がない。mermaid.js などの外部 JS は使えない）。

各図は `<svg id="dg-<短い名前>">` とし、`<title>`・`<desc>` の直後に
`<!--SVG-HEAD:dg-<短い名前>-->` を置く。手順6でこの位置に、id でスコープした `<style>`
（ライト/ダーク3系統の色トークン）と矢印の `<marker>` が入る。**style を手で書かない。**

使えるクラス:

| クラス | 用途 |
|---|---|
| `.box` / `.box-soft` / `.box-focal` | ノード（通常 / 補助 / 主役）。主役は1系統だけ |
| `.zone` | 破線のゾーン枠 |
| `.name` / `.code` | ノード名（sans 14px）/ 識別子のノード名（mono 15px） |
| `.sub` / `.subm` | サブラベル。日本語は `.sub`（sans 11px）、識別子・パスは `.subm`（mono 11px） |
| `.em` | 強調ラベル（accent 色 11px） |
| `.lead` / `.lead-focal` | 矢印（通常 / 主役）。`.dash` を足すと破線（非同期・戻り・任意） |
| `.link` | 矢印なしの関係線（対応づけなど） |
| `.life` | シーケンス図のライフライン |
| `.mask` | 矢印ラベルの下敷き |

`.tag`（10px mono）は英数字専用。日本語のラベルには使わない。

図にする価値があるものだけ描く: 仕組み・データの流れ、旧方式と新方式の対比、
コンポーネント間の関係、分岐条件の組み合わせ（「A かつ B なら C」）、時系列のやり取り。
「新機能が増えた」「GA になった」だけの記事に図を付けない。表で足りるなら表にする。

### 6. 組み立てる

```bash
W=<スクラッチパッド>
uv run --directory news_pipeline python scripts/digest/list_view.py html --list "$W/list.json" \
  --exclude "$IDS" --out "$W/list_frag.html"
uv run --directory news_pipeline python scripts/digest/assemble.py \
  --src "$W/digest_src.html" --list "$W/list_frag.html" --out "$W/digest.html"
```

`list_view.py html` は深掘り以外をテーマ別（BigQuery・Google Cloud／セマンティックレイヤー・
オントロジー・AIエージェント／テーブルフォーマット・データ共有／パイプライン・ストリーミング・CDC／
DWH運用・コスト・モデリング）に分け、要約の先頭2行とタグ4つを載せる。テーマ別の件数が stderr に出るので、
「この期間の動き」で件数に触れるときはこの値を使い、「機械的な振り分けで」と断る。
`--exclude` に一覧に無い id（12桁の接頭辞など）を渡すと止まる。深掘り記事が一覧に重複して載るのを防ぐため。

`assemble.py` は、`SVG-HEAD` の id に対応する `<svg>` が無い、id が重複している、
`<!--LIST-->` が無いか2つ以上ある、のいずれかで止まる。

原稿を直したら、`digest.html` ではなく `digest_src.html` を直して組み立て直す。

### 7. 検査する

```bash
W=<スクラッチパッド>
python3 ~/.claude/skills/svg-diagram/scripts/check_svg.py "$W/digest.html"
```

`0 errors` になるまで直す。テキストのはみ出しは、サブラベルを短くするか箱を広げる。
warning の「ノード数が密度予算超え」は、名前の見本を並べただけの段など、意図があれば残してよい。

続いてライト/ダークで描画して目視する:

```bash
W=<スクラッチパッド>
uv run --directory news_pipeline --with playwright python - <<EOF
from playwright.sync_api import sync_playwright
W = "$W"
with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    for scheme in ("light", "dark"):
        page = b.new_page(color_scheme=scheme, viewport={"width": 900, "height": 1000})
        page.goto(f"file://{W}/digest.html"); page.wait_for_load_state("networkidle")
        for i, svg in enumerate(page.locator("svg").all(), 1):
            svg.screenshot(path=f"{W}/svg{i}_{scheme}.png")
        page.close()
    b.close()
EOF
```

`Executable doesn't exist` のエラーで止まったら、
`uv run --directory news_pipeline --with playwright playwright install chromium`（約100MB）を実行してから再実行する。
PNG を Read で開き、全図を少なくとも片方のテーマで、主役の色が出ている図は両方のテーマで確認する。

### 8. セルフレビューする

公開前に原稿を読み直す。直したら手順6・7をやり直す。

- **記事に無いことを書いた箇所**（主に実務への示唆）を洗い出す。製品の機能・制約を書いたなら、
  確かなものだけ残し、不確かなものは削るか「〜とされる」と書いて区別する。最終報告で「記事の外の知識で補った箇所」として列挙する
- **数字と出どころ**: 数字はどの資料のものか。別々の測定を同じものとして書いていないか。逆に同じ測定を別物と断定していないか
- **言い過ぎ**: 「大半」「必ず」「完全に」など、記事に根拠の無い量や断定を書いていないか
- **一覧の要約から書いた部分**（この期間の動き）は、要約に無い事実（改名・移管・GA など）を足していないか
- **禁止語**: AI 的な言い回しを使わない。次で 0 件にする

```bash
python3 - "$W/digest_src.html" <<'EOF'
import re, sys
s = open(sys.argv[1]).read()
for m in re.finditer(r"壊れ|罠|効く|効か|効い|落ち|落と|焼く|畳む|畳ん|潰す|寄せ|刺さ|踏む|踏ん|解像度", s):
    print(s[max(0, m.start() - 30):m.end() + 20].replace("\n", " "))
EOF
```

「壊れる」→「誤った結果になる」のように、何が起きるかを具体的に書き換える。

### 9. 公開して通知する

**まず `--dry-run`。**

```bash
W=<スクラッチパッド>
uv run --directory news_pipeline python scripts/digest/publish.py --html "$W/digest.html" \
  --title "2週間ダイジェスト 2026-11-16" --slack --dry-run \
  --headline "深掘り1の短い見出し" --headline "深掘り2の短い見出し"
```

- `--headline` は深掘りした記事の数だけ渡す（Slack 本文の箇条書きになる）。原題ではなく、
  目次と同じ短い見出しにする（原題は長く、煽り調のものもある）
- 新規アップロードにはタグ `DataNews` が自動で付く。dry-run の出力に `タグ: DataNews` と出る

`--dry-run` は本番と同じ判定（ファイルの有無・サイズ、webhook の有無、タイトル重複、タグの形式）を通し、
送る Slack ペイロードをそのまま表示する。**違いは POST しないことだけ**なので、`rc=0` かつ表示が
意図どおりなら、`--dry-run` を外して実行する。成功すると URL・`content_id`・次回の更新コマンドが出る。

### 10. 報告する

最終報告に含めるもの:

- URL と `content_id`、付けたタグ、Slack 通知の有無
- 構成（この期間の動き・深掘り N 本・一覧 K 件のテーマ別）
- セルフレビューで直した点
- 記事の外の知識で補った箇所（未検証のもの）と、検査の結果（`check_svg.py` の残り warning とその理由）

## 公開済みの回を直すとき

**上書きする**（URL は変わらず、直近10世代が保持される）:

```bash
uv run --directory news_pipeline python scripts/digest/publish.py --html "$W/digest.html" \
  --title "2週間ダイジェスト 2026-11-16" --content-id <ID>
```

上書きでは `--tag` を渡したときだけタグを送る。渡さなければ公開済みのタグがそのまま残る。
`--slack` を付けない限り再通知しない（同じ URL を二度流さない）。

`content_id` の入手経路:

1. 初回アップロードの出力（`content_id: 01...`）
2. 同名タイトルで `--dry-run` を叩く → 重複エラーが既存の `content_id` を出す
3. `family-share` スキルの一覧 API（`GET /api/contents`）

タグだけ変えるなら `family-share` スキルのタグ置換 API を使う。

## 注意

- **`--dry-run` を挟まずにいきなり公開しない。** family-share は Web UI からしか削除できない
- 対象0件のときは資料を作らない（`fetch_articles.py` が終了コード2で止まる）
- 期間は「昨日まで」なので、同じ周期で回す限り前回と重複しない。月次は週次と重複するが、総括として意図的
- 意図して同名の資料を2本上げたいときだけ `--force-new`。既定では止まる
- 対象記事の閾値は `fetch_articles.py` の既定（importance 0.65 / relevance 0.55）。本番の通知ゲート
  （settings シートの `relevance_threshold`、既定 0.2）より relevance を**意図的に厳しく**している。
  ダイジェストではデータ基盤との関連が確かな記事に絞るため。件数が少なすぎる回だけ `--min-relevance` で緩める
