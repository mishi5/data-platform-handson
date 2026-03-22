# Plan 3: お気に入り / ピン留め機能

idea: #5

## 概要

気になった記事をSlackコマンドでピン留めし、後から一覧表示できるようにする。
BigQueryに `favorites` テーブルを持ち、Slackから add/list/remove を操作する。

---

## 機能仕様

### Slackコマンド

```
/news-fav add <article_id>      → 記事をお気に入りに追加
/news-fav list                  → お気に入り一覧を表示（最新10件）
/news-fav remove <article_id>   → お気に入りから削除
```

`article_id` はPlan 1で通知に表示される先頭8文字のID。

### 表示例（list）

```
📌 お気に入り記事（3件）

1. *title*
   _追加日: 2026-03-10 | 出典: source_
   ID: `abc12345` | `url`

2. ...
```

---

## BigQueryテーブル設計

**テーブル名**: `tech_news.favorites`

| カラム | 型 | 説明 |
|--------|-----|------|
| `article_id` | STRING | 記事ID |
| `added_at` | TIMESTAMP | 追加日時 |
| `added_by` | STRING | SlackユーザーID（将来の複数ユーザー対応用） |
| `note` | STRING | メモ（NULLABLE、将来拡張用） |

- `remove` は物理削除ではなく論理削除（`removed_at` カラム追加）でも可だが、シンプルにするため今回は物理削除（DELETE文）で実装
- BigQuery は DML DELETE をサポートしているが、ストリーミングバッファ中の行は削除不可（追加直後の削除は数分待つ必要あり）

---

## 実装方針

### `bq_client.py` への追加

```python
def add_favorite(self, article_id: str, added_by: str = "unknown") -> None:
    """お気に入りに追加。既存の場合はスキップ（重複チェックあり）。"""

def remove_favorite(self, article_id: str) -> None:
    """お気に入りから削除（DML DELETE）。"""

def get_favorites(self, limit: int = 10) -> list[dict]:
    """お気に入り一覧を返す（summaries と JOIN して title/url も含む）。"""
```

### `main.py` への追加

新エンドポイント `/slack/fav` を追加：

```python
@app.route("/slack/fav", methods=["POST"])
def slack_fav():
    text = request.form.get("text", "").strip()
    user_id = request.form.get("user_id", "unknown")
    parts = text.split()
    subcommand = parts[0] if parts else "list"

    if subcommand == "add" and len(parts) >= 2:
        # add <article_id>
    elif subcommand == "remove" and len(parts) >= 2:
        # remove <article_id>
    else:
        # list
```

このエンドポイントは処理が軽いため同期実行で3秒以内に応答できる想定。

---

## 考慮事項

### BigQuery DELETE の制約

ストリーミング挿入直後の行はDELETE不可（バッファクリアに最大数分かかる）。
`remove` 実行時に対象行がバッファ中だった場合のエラー処理が必要：
- エラー時: ユーザーに「少し待ってから再試行してください」と返す

### 複数ユーザー対応

現状は1ユーザー想定だが、`added_by`（SlackユーザーID）を保存しておくことで
将来的に個人ごとのリスト表示に拡張できる。今回の `list` は全ユーザー共通で表示。

---

## Terraform変更

- `infra/bigquery.tf`: `favorites` テーブル追加

---

## 変更ファイル

- `collector/bq_client.py`: 3メソッド追加
- `collector/main.py`: `/slack/fav` エンドポイント追加
- `infra/bigquery.tf`: `favorites` テーブル追加

---

## テスト方針

- `bq_client.py` の新メソッドのテスト（モック）
- `/slack/fav` エンドポイントの各サブコマンドのテスト

## 実装順序

1. BigQuery テーブル追加（Terraform）
2. `bq_client.py` にメソッド追加
3. `main.py` にエンドポイント追加
4. Slack App に `/news-fav` コマンド追加
5. テスト追加
