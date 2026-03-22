# Plan 2: 深堀り機能 + 質問機能

ideas: #1 (深堀り) + #2 (質問・手動リクエスト)

## 概要

特定の記事をClaude Sonnetで詳しく分析し、Slackから任意の記事を指定して深堀りできるようにする。
定期実行では自動選択しない（ユーザーが明示的にリクエストする設計）。

---

## 機能仕様

### Slackコマンド

```
/news-deepdive <article_id>
```

- `article_id`: Plan 1で通知に表示される先頭8文字のID（`abc12345` 形式）
- 省略時: 最新の未深堀り記事の中から `importance_score` 最上位のものを自動選択
- 既に深堀り済みの場合: キャッシュ済みの結果を返す（再生成しない）

### 深堀りの出力内容（Sonnetで生成）

```
*[深堀り] title*

📌 背景・概要
...

🔍 技術的なポイント（詳細）
• ポイント1
• ポイント2
...

💡 実践への示唆
...

🔗 <url|元記事を読む>
```

通常の要約（Haiku, 3〜5項目）より詳細な分析を行う。

---

## 実装方針

### 新規ファイル: `collector/deepdiver.py`

```python
def deepdive_article(title: str, content: str, api_key: str) -> str | None:
    """Claude Sonnet を使って記事を深堀り分析する。Markdown文字列を返す。"""
```

- モデル: `claude-sonnet-4-6`（Haikuより詳細な分析）
- `max_tokens`: 1024
- 既存の `summarize_article()` とは独立したプロンプト・関数

### BigQueryテーブル追加: `tech_news.deepdives`

| カラム | 型 | 説明 |
|--------|-----|------|
| `article_id` | STRING | 対象記事のID |
| `deepdive_text` | STRING | 深堀りテキスト（Markdown） |
| `created_at` | TIMESTAMP | 生成日時 |

- 同じ `article_id` が既存なら再生成しない（キャッシュとして使う）

### `bq_client.py` への追加

```python
def get_deepdive(self, article_id: str) -> str | None:
    """既存の深堀り結果を取得。なければ None。"""

def insert_deepdive(self, article_id: str, text: str) -> None:
    """深堀り結果を保存。"""

def get_article_by_id(self, article_id_prefix: str) -> dict | None:
    """先頭8文字のIDプレフィックスで記事を取得。summaries + raw_articles を JOIN。"""
```

### `main.py` への追加

新エンドポイント `/slack/deepdive` を追加（または既存の `/slack` を拡張）：

**方針A（推奨）: コマンドテキストで分岐**

```
/news-update     → 既存のパイプライン実行
/news-deepdive   → 深堀り実行
```

Slackのスラッシュコマンドは1コマンド = 1エンドポイントのため、
`/news-deepdive` 用に **新しいエンドポイント `/slack/deepdive`** を追加する。

```python
@app.route("/slack/deepdive", methods=["POST"])
def slack_deepdive():
    # article_id を request.form["text"] から取得
    # バックグラウンドで deepdive を実行
    # 結果を response_url に POST（Slack遅延応答）
```

**Slack遅延応答**（3秒制限対策）:
- 即時: `"深堀り中です..."`を返す
- バックグラウンド: 処理完了後に `response_url` へ POST

---

## Slackアプリ設定変更

`/news-deepdive` コマンドを追加し、Request URLを Cloud Run の `/slack/deepdive` に向ける。
（Terraform の Cloud Run サービスへの影響はなし、Slack App の設定変更のみ）

---

## Terraform変更

- `infra/bigquery.tf`: `deepdives` テーブル追加

---

## 変更ファイル

- `collector/deepdiver.py`: 新規作成
- `collector/bq_client.py`: 3メソッド追加
- `collector/main.py`: `/slack/deepdive` エンドポイント追加
- `infra/bigquery.tf`: `deepdives` テーブル追加

---

## テスト方針

- `deepdiver.py` のユニットテスト（Claudeクライアントをモック）
- `bq_client.py` の新メソッドのテスト
- `/slack/deepdive` エンドポイントのテスト

## 実装順序

1. BigQuery テーブル追加（Terraform）
2. `deepdiver.py` 作成
3. `bq_client.py` にメソッド追加
4. `main.py` にエンドポイント追加
5. Slack App に `/news-deepdive` コマンド追加
6. テスト追加
