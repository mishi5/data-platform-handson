# パイプライン分割・本文取得リトライ・閾値変更 設計書

作成日: 2026-06-07

## 目的

news_pipeline に対し、独立した3つの改善を行う:

1. **収集と通知の分割**: 要約処理が重く通知をブロックする問題を解消。収集（重い）と通知（軽い）を別エンドポイント・別スケジューラに分ける。
2. **本文取得のリトライ + 次回繰り越し**: 403 等で本文取得に失敗した記事を、次回スケジューラ実行で再取得する。上限到達で諦める。
3. **importance_threshold を 0.65 に引き上げ、settings シートで管理**。

関連分析: [2026-06-06-summary-notification-logic-analysis.md](2026-06-06-summary-notification-logic-analysis.md)

## 方針（確定事項）

| 項目 | 決定 |
|------|------|
| 分割方式 | 2エンドポイント（`/collect`・`/notify`）+ 2 Cloud Scheduler |
| collect スケジュール | 毎日 6:00 JST（`0 21 * * *` UTC） |
| notify スケジュール | 毎日 6:30 JST（`30 21 * * *` UTC） |
| Slack `/news-update` | notify のみ実行（軽量・即応答） |
| `/` エンドポイント | 廃止し、スケジューラを `/collect` に張り替え |
| リトライ回数の永続化 | raw_articles に列追加（`content_status` / `retry_count`） |
| リトライ粒度 | 次回繰り越しのみ（1実行1回。即時リトライはしない） |
| 上限到達時 | `content_status=failed`、要約せずスキップ（諦める） |
| 設定の置き場所 | settings シートの `general` グループ |
| importance_threshold | `general/importance_threshold`（値 0.65、既定 0.65） |
| 本文リトライ上限 | `general/max_content_retries`（既定 3） |
| pending 記事の更新 | BigQuery DML `UPDATE`（streaming insert は更新不可のため） |

## アーキテクチャ

```
┌─ POST /collect（重い・毎日6:00 JST）──────────────────────────┐
│  RSS取得 → dedup → 本文取得(+pending再取得) → raw_articles 保存/更新 │
│  → 要約（content_status=ok のみ）→ importance_threshold フィルタ      │
│  → summaries 保存                                                    │
└──────────────────────────────────────────────────────────────────┘

┌─ POST /notify（軽い・毎日6:30 JST / Slack /news-update）─┐
│  未通知サマリー取得 → カテゴリ別に通知 → notification_log 記録 │
└────────────────────────────────────────────────────────┘
```

### エンドポイントとパイプライン関数

現在の `_run_pipeline()` を2つに分割する:

- **`_run_collect() -> int`**: 現ステップ1〜8（収集〜summaries保存）。新着要約件数を返す。
- **`_run_notify() -> int`**: 現ステップ9〜11（未通知取得〜通知〜マーク）。通知件数を返す。

| エンドポイント | 処理 | トリガー |
|--------------|------|---------|
| `POST /collect` | `_run_collect()` を `asyncio.to_thread` で同期実行 | Cloud Scheduler（毎日6:00 JST） |
| `POST /notify` | `_run_notify()` を `asyncio.to_thread` で同期実行 | Cloud Scheduler（毎日6:30 JST） |
| `POST /slack`（`/news-update`） | `_run_notify()` を BackgroundTasks で実行 | Slack スラッシュコマンド |

- 既存 `POST /`（`run_pipeline`）は削除。
- pipeline_logs への記録は collect / notify それぞれで行う（`triggered_by` で識別）。通知系フィールド（notified_count）は notify 側、要約系（summaries_generated 等）は collect 側で埋める。

## コンポーネントと変更内容

### article_parser.py

`fetch_content` を成否を区別する形に変更する。

```python
def fetch_content(url: str) -> tuple[str | None, bool]:
    """URL から本文を抽出。戻り値 (text, ok)。
    ok=True: 取得成功（text は本文 or 抽出失敗時 None だが取得自体は成功）
    ok=False: HTTP/通信エラー（リトライ対象）
    """
```

- ブラウザ風 `User-Agent` ヘッダーを付与（403 bot ブロックの低減）。
- `requests` の例外・`raise_for_status` 失敗時は `(None, False)`（リトライ対象）。
- 取得成功し本文抽出が None の場合は `(None, True)`（取得は成功＝リトライ不要）。

> 注: 即時リトライはしない（1実行1回）。`ok=False` を collect 側が拾って retry_count を増やし次回に回す。

### bq_client.py

raw_articles スキーマに合わせて以下を追加・変更:

- `insert_raw_articles(articles)`: 各レコードに `content_status`・`retry_count` を含めて挿入（呼び出し側で付与）。
- 新規 `get_pending_articles(max_retries: int) -> list[dict]`:
  `content_status='pending' AND retry_count < max_retries` の記事（article_id, url, title, source, retry_count 等）を返す。
- 新規 `update_article_content(article_id, content, content_status, retry_count)`:
  DML `UPDATE` で pending 記事の本文・ステータス・retry_count を更新。

### infra/bigquery.tf

raw_articles の schema に NULLABLE 列を2つ追加（既存行は NULL = 処理済み扱いで非破壊）:

```hcl
{ name = "content_status", type = "STRING",  mode = "NULLABLE" },  # ok / pending / failed
{ name = "retry_count",    type = "INT64",   mode = "NULLABLE" },
```

- NULLABLE 列の追加は BigQuery の非破壊スキーマ更新であり、Terraform はテーブル再作成せず列追加で適用する。

### infra/main.tf

- 既存 `google_cloud_scheduler_job.news_pipeline_trigger` を `/collect` 向けに変更:
  - `schedule = "0 21 * * *"`（毎日6:00 JST）
  - `uri = "${...}/collect"`
- 新規 `google_cloud_scheduler_job` を notify 向けに追加:
  - `name = "news-pipeline-notify"`
  - `schedule = "30 21 * * *"`（毎日6:30 JST）
  - `uri = "${...}/notify"`
  - 同じ scheduler SA / OIDC を使用。

### main.py

- `IMPORTANCE_THRESHOLD` 環境変数を廃止。
- `_run_collect()` 内で settings から取得:
  - `importance_threshold = settings.get("general", {}).get("importance_threshold", 0.65)`（float 変換）
  - `max_content_retries = settings.get("general", {}).get("max_content_retries", 3)`（int 変換）
- 定数 `_DEFAULT_IMPORTANCE_THRESHOLD = 0.65`、`_DEFAULT_MAX_CONTENT_RETRIES = 3` を定義。

## データフロー（`/collect`）

```
1. fetch_articles(feeds) → articles
2. dedup: existing_urls = get_existing_urls()
          new_articles = [a for a if url not in existing_urls][:max_summarize]
3. 新着の本文取得（UA付き・1回）:
     (text, ok) = fetch_content(url)
     ok かつ text あり    → content=text, content_status="ok",      retry_count=0
     ok かつ text なし    → content=null, content_status="ok",      retry_count=0  （取得成功・本文空）
     ok=False             → content=null, content_status="pending", retry_count=1
4. insert_raw_articles(new_records)  ← content_status / retry_count 込み
5. pending 再取得: pending = get_pending_articles(max_content_retries)
     各 pending に対し fetch_content:
       ok かつ text あり → update_article_content(id, text, "ok", retry_count)
       ok=False:
         retry_count + 1 が max 以上 → update(..., "failed", retry_count+1)
         未満                        → update(..., "pending", retry_count+1)
6. 要約対象 = この実行で content_status="ok" になった記事
     （手順3で ok になった新着 + 手順5で pending→ok になった記事）のうち本文ありのもの
7. summarize_article() → importance_score
8. importance_threshold フィルタ（>= 0.65）→ article_id 重複除外 → insert_summaries
```

ポイント:
- pending 記事は raw_articles に保存済みなので dedup（手順2）では「新着」から外れる。再取得は手順5の専用クエリで拾う＝次回スケジューラ実行で繰り越し。
- 上限到達で `content_status=failed` → 以降 `get_pending_articles` の条件（retry_count < max）に掛からず再取得されない。要約もされない（手順6は ok のみ対象）。
- 本文が取得成功でも空（`ok かつ text なし`）の記事は status=ok 扱い。要約は本文空で行われる（現状踏襲、リトライ対象外）。

## エラー処理 / エッジケース

- **既存 raw_articles 行（content_status=NULL）**: `get_pending_articles` は `content_status='pending'` 条件なので対象外。再取得も要約もされず現状維持（既に処理済みのため正しい）。
- **streaming buffer 制約**: 挿入直後の行は数分 DML UPDATE 不可。通常運用では pending の更新は次回実行（翌日）なので抵触しない。ただし手動で `/collect` を短時間に連続実行すると、前回 INSERT した pending 行が buffer に残ったまま UPDATE しようとして `UPDATE or DELETE ... would affect rows in the streaming buffer` エラーになり得る。
  - **対処**: `update_article_content` を try/except で囲い、エラー時はログを出して**当該記事を pending のまま残す**（retry_count を進めない）。buffer が flush された次回実行で自然に成功する＝自己修復。再取得に成功していた本文はその回では破棄され次回再取得されるが、正しさは保たれる。
  - `get_pending_articles` は SELECT のため buffer 行も問題なく読める。制約に掛かるのは DML UPDATE のみ。
- **DML クォータ**: pending 件数は失敗分のみで小さいため、1行ずつの UPDATE でも問題ない想定。多数同時更新が必要になれば MERGE に変更可。
- **collect と notify の時間差**: notify(6:30) は collect(6:00) の要約完了後に走る前提。collect が30分以上かかった場合、その日の新着は翌日の notify で配信される（バックログとして残るだけで欠落はしない）。
- **片方のスケジューラ失敗**: collect 失敗時は当日の新着が無いだけ。notify 失敗時は未通知が翌日に繰り越し。いずれも欠落しない。

## テスト

- `article_parser`: UA 付与、(text, ok) の戻り（成功/HTTPエラー/本文空）の分岐
- `bq_client`: `get_pending_articles` のクエリ条件、`update_article_content` の DML 生成、`insert_raw_articles` が新列を含むこと（MagicMock でクエリ/挿入引数を検証）。`update_article_content` が UPDATE 例外時に送出せずログのみで握りつぶすこと（buffer 制約フォールバック）
- collect の要約対象選定（新着ok + pending→ok）と pending リトライの状態遷移（pending→ok / pending→pending / pending→failed）を純粋ロジックとして切り出せる部分はユニットテスト
- 既存テストの追従（`_run_pipeline` 分割に伴うシグネチャ変更、`fetch_content` 戻り値変更）

## 環境変数 / ドキュメント

- `IMPORTANCE_THRESHOLD` 環境変数を廃止（settings シートへ移行）。
- CLAUDE.md / README を更新:
  - エンドポイント構成（`/collect`・`/notify`、`/` 廃止）
  - 2スケジューラ構成と実行時刻
  - settings の `general/importance_threshold`・`general/max_content_retries`
  - raw_articles の `content_status`・`retry_count` 列
  - 本文取得リトライ（次回繰り越し）の挙動

## 非対象（YAGNI）

- 即時（実行内）リトライ・指数バックオフ
- 本文取得失敗記事の Slack 通知やダッシュボード化
- notify の高頻度化（バックログ drip 配信）。必要になれば notify スケジューラの頻度 or max_notify を調整するだけで対応可能
- カテゴリ別の importance_threshold（今回は general 一律）
- 専用リトライテーブル（raw_articles 列で対応）
