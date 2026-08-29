# 週次/月次ニュースダイジェスト設計

作成日: 2026-08-30

## 背景と目的

`news_pipeline` は毎朝の Slack 通知で新着記事を流している。だが通知は流れて消えるだけで、
「今週何が起きたか」を後から俯瞰できない。週次・月次で記事を編集し、図解付きの資料として
残せるようにする。

日次通知（Cloud Run・従量課金の `ANTHROPIC_API_KEY`）とは別に、**Claude Code のプラン内**で
動かす。従量課金が発生しないため、Opus で厚く読み込んで資料を作れる。

## 確定した要件

| 項目 | 決定 | 理由 |
|---|---|---|
| 読者 | 本人のみ | 専門用語をそのまま使い、密度を優先する |
| 期間 | 引数で `week` / `month`、既定は週次 | 週次で回しつつ月末に総括を出せる |
| 図解 | 記事内容の図解のみ | タグ分布などの集計グラフは求められていない |
| ワークフロー | 選定だけ確認、以降は自動 | 誤った記事を深掘りして時間を浪費する事故を防ぐ |
| 構成 | 深掘り 4〜6 件（図解付き）＋ 残りは1行要約の一覧 | 見逃しを防ぎつつ読み応えを保つ |
| 実行主体 | Claude Code（プラン定額内） | 従量課金なし。Cloud Run のタイムアウト制約も受けない |

母数の実測（2026-08-30 時点）:

| 期間 | 収集 | ゲート通過 | 高価値(imp≥0.8 かつ rel≥0.8) |
|---|---|---|---|
| 直近7日 | 63 | 42 | 11 |
| 8〜30日前 | 326 | 110 | 27 |

## アーキテクチャ

決定的な操作をスクリプトに固め、判断が要る部分を Claude が担う。

```
[BigQuery tech_news]
        |
        v
  fetch_articles.py  ... 期間指定で記事を取得（決定的）
        |
        v  JSON
   Claude Code       ... 選定・要約・図解（判断）
        |            ... svg-diagram スキルで SVG を描く
        v  HTML
    publish.py       ... family-share アップロード + Slack 通知（決定的）
        |
        v
  family-share URL --> Slack
```

**この分担にした理由**: BigQuery の JOIN、IAP のIDトークン取得、curl の組み立ては手順が
決まりきっており、Claude が毎回組み立てる価値がない。逆に選定・要約・図解は判断そのもので、
スクリプト化すると硬直する。

### 配置

```
news_pipeline/scripts/digest/
├── fetch_articles.py   # BigQuery から記事を取得して JSON 出力
└── publish.py          # family-share アップロード + Slack 通知

.claude/skills/news-digest/
└── SKILL.md            # 選定基準・要約方針・HTML 骨格・実行手順
```

スクリプトを `news_pipeline/scripts/` 配下に置くのは、既存の `eval_scoring.py` と実行環境
（`uv run`・`.env` の読み込み）を揃えるため。スキルはプロジェクト固有（この BigQuery に依存）
なのでリポジトリ内の `.claude/skills/` に置く。

## コンポーネント

### fetch_articles.py

2つのモードを持つ。選定と深掘りで必要なデータ量が違うため。

**一覧モード**（選定用・本文なし）

```
uv run python scripts/digest/fetch_articles.py --period week
```

ゲートを通過した記事を JSON 配列で返す。本文は含めない（42件分の本文は巨大になる）。

```json
[{"article_id","title","url","source","summary","tags",
  "importance_score","relevance_score","collected_at"}]
```

**本文モード**（深掘り用）

```
uv run python scripts/digest/fetch_articles.py --ids id1,id2,id3
```

指定した記事の本文（`raw_articles.content`）を含めて返す。

引数:
- `--period week|month`（既定 `week`）— それぞれ7日・30日
- `--days N` — 期間を直接指定（`--period` より優先）
- `--ids a,b,c` — 本文モード
- `--min-importance` / `--min-relevance` — 既定はゲートと同じ 0.65 / 0.55

### publish.py

```
uv run python scripts/digest/publish.py --html digest.html --title "週次ダイジェスト 2026-08-30" [--content-id ID] [--slack] [--dry-run]
```

- IDトークンを取得（`gcloud auth print-identity-token --impersonate-service-account=...`）
- `--content-id` があれば上書き（URL 不変）、なければ新規アップロード
- `--slack` で Incoming Webhook に通知（URL + 見出し）
- `--dry-run` は実行内容を表示するだけで送信しない

Slack Webhook URL と GCP プロジェクトは `news_pipeline/.env` から読む。

### SKILL.md

Claude への指示。内容:

1. 期間を確認し `fetch_articles.py --period` を実行
2. 一覧から深掘り候補 4〜6 件を選び、**理由を添えてユーザーに提示して承認を得る**
3. 承認後、`--ids` で本文を取得
4. 各記事を読み、要約と図解（`svg-diagram` スキルを使用）を作る
5. HTML を組み立てる
6. `publish.py` でアップロードし Slack 通知

## 選定基準

`importance_score` の降順に並べるだけでは、同じトピックが並んだり速報が上位を占めたりする。
以下を併用する:

1. **スコア**: `importance_score` × `relevance_score` が高いもの
2. **トピックの分散**: 同一タグに偏らない（同じタグの記事は最大2件まで）
3. **深掘り適性**: 図解にできる技術的な中身があるか。製品リリース告知や参加レポートは
   一覧側に回す
4. **お気に入り傾向**: `favorites` に多いタグ（`metadata`, `data governance`, `data modeling`,
   `data pipeline`, `bigquery`）に寄せる

選定結果は必ずユーザーに提示して承認を得る。

## HTML の仕様

- **単一ファイル・外部依存ゼロ**。CSS も SVG もインライン。family-share は IAP 配下の静的
  配信で、外部 CDN が読める保証がないため
- ライト/ダーク両対応（`prefers-color-scheme`）
- 構成:
  - ヘッダー（期間、対象記事数）
  - 深掘りセクション（記事ごとに: タイトル・出典リンク・要約・**図解 SVG**・実務への示唆）
  - 一覧セクション（タイトル + 1行要約 + リンク、タグ付き）
- 図解は `svg-diagram` スキルの規約に従う（インライン SVG、viewBox 指定、ライト/ダーク考慮）

## 重複の扱い

期間で区切ることで前回分と重ならない（`collected_at` の範囲で切る）。月次は週次と重複するが、
総括として意図的な重複とする。掲載履歴テーブルのような仕組みは作らない（YAGNI）。

## エラー処理

- `fetch_articles.py`: 対象0件なら明示して終了（空の資料を作らない）
- `publish.py`: IDトークン取得失敗・アップロード失敗・Slack 送信失敗をそれぞれ区別して
  エラー終了する。**Slack 通知はアップロード成功後にのみ実行する**（存在しない URL を
  通知しない）
- `--dry-run` を既定にはしない。ただし SKILL.md では初回に dry-run を挟むよう指示する

## テスト方針

スクリプトは決定的なので通常のユニットテストで担保する:

- `fetch_articles.py`: 期間の境界、ゲート条件、`--ids` モード、0件時の扱い。BigQuery クライアントは
  モックする
- `publish.py`: 新規/上書きの分岐、`--dry-run` で送信しないこと、アップロード失敗時に Slack を
  呼ばないこと、トークン取得失敗の扱い

SKILL.md の内容（選定・要約・図解の質）はテストで担保できない。実際に1回通して出来を確認する。

## スコープ外

- 定期実行（cron）: 手動起動のみ。Claude Code のプラン内で動かす前提のため
- 過去ダイジェストの一覧ページ: family-share の一覧機能で足りる
- 集計グラフ（タグ分布・件数推移）: 要件から外れた
- PDF 出力: HTML で足りる
