# importance_score 再計算の仕組み Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** importance_score のスコアロジックを変えた際に、既存の summaries 行を `scoring_version` 差分で再計算できる `/recalculate` 基盤を作る。

**Architecture:** スコア基準を `summarizer._build_scoring_criteria()` に集約し collect の結合プロンプトと新設の score-only プロンプトで共用。`SCORING_VERSION` 定数で版管理。summaries に `scoring_version` 列を足し、`/recalculate` が版の古い行を settings 上限件数ずつ再採点して DML UPDATE する。

**Tech Stack:** Python 3.12 / FastAPI / Anthropic（Haiku 4.5）/ BigQuery / Terraform / pytest（`uv run pytest`）

---

## File Structure

- **Modify** `news_pipeline/collector/summarizer.py` — `SCORING_VERSION`、`_build_scoring_criteria`、`score_article`、`_build_system_prompt` のリファクタ
- **Modify** `news_pipeline/tests/test_summarizer.py` — criteria / score_article のテスト追加
- **Modify** `news_pipeline/collector/bq_client.py` — `get_outdated_summaries` / `update_summary_score`
- **Modify** `news_pipeline/tests/test_bq_client.py` — 上記2メソッドのテスト
- **Modify** `news_pipeline/infra/bigquery.tf` — summaries に `scoring_version` 列
- **Modify** `news_pipeline/collector/main.py` — `_run_recalculate`・`/recalculate`・collect の version 刻印
- **Modify** `CLAUDE.md` / `news_pipeline/README.md` — 追従

テストは `cd news_pipeline && uv run pytest ...`（uv 必須）。

---

## Task 1: summarizer に SCORING_VERSION・共有criteria・score_article

**Files:**
- Modify: `news_pipeline/collector/summarizer.py`
- Test: `news_pipeline/tests/test_summarizer.py`

着手前に `news_pipeline/collector/summarizer.py` を Read すること。現状は `_SYSTEM_PROMPT_TEMPLATE`（`{keywords_list}` 置換）+ `_build_system_prompt(keywords)` + `summarize_article(...)` で、スコア判定基準がテンプレートに埋め込まれている。

- [ ] **Step 1: Write the failing test**

`news_pipeline/tests/test_summarizer.py` の import 行を以下に変更:

```python
from collector.summarizer import (
    summarize_article,
    score_article,
    _build_system_prompt,
    _build_scoring_criteria,
)
```

ファイル末尾に追加:

```python
def test_build_scoring_criteria_includes_keywords():
    c = _build_scoring_criteria(["BigQuery", "dbt"])
    assert "BigQuery" in c
    assert "dbt" in c


def test_build_scoring_criteria_no_keywords():
    c = _build_scoring_criteria([])
    assert "キーワード未設定" in c


@patch("collector.summarizer.anthropic.Anthropic")
def test_score_article_returns_float(mock_anthropic_class):
    mock_client = MagicMock()
    mock_anthropic_class.return_value = mock_client
    response_text = json.dumps({"importance_score": 0.72})
    mock_client.messages.create.return_value.content = [
        MagicMock(spec=TextBlock, text=response_text)
    ]

    score = score_article(title="T", content="C", api_key="k", keywords=["BigQuery"])
    assert score == 0.72


@patch("collector.summarizer.anthropic.Anthropic")
def test_score_article_strips_code_fence(mock_anthropic_class):
    mock_client = MagicMock()
    mock_anthropic_class.return_value = mock_client
    response_text = "```json\n{\"importance_score\": 0.4}\n```"
    mock_client.messages.create.return_value.content = [
        MagicMock(spec=TextBlock, text=response_text)
    ]

    score = score_article(title="T", content="C", api_key="k")
    assert score == 0.4


@patch("collector.summarizer.anthropic.Anthropic")
def test_score_article_returns_none_on_error(mock_anthropic_class):
    mock_client = MagicMock()
    mock_anthropic_class.return_value = mock_client
    mock_client.messages.create.side_effect = Exception("API error")

    assert score_article(title="T", content="C", api_key="k") is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd news_pipeline && uv run pytest tests/test_summarizer.py -v`
Expected: FAIL（`ImportError: cannot import name 'score_article'` / `_build_scoring_criteria'`）

- [ ] **Step 3: Implement — summarizer.py を書き換え**

`news_pipeline/collector/summarizer.py` を以下で全面置き換え:

```python
"""Claude API を使って記事を要約・採点するモジュール。

- summarize_article: 要約(summary)+タグ(tags)+重要度(importance_score) を1回で生成
- score_article: 重要度スコアのみを再計算（/recalculate 用）
スコア判定基準は _build_scoring_criteria に集約し両者で共用する。
スコアロジックを変えたら SCORING_VERSION を +1 すること。
"""
import json
import logging
import anthropic
from anthropic.types import TextBlock

logger = logging.getLogger(__name__)

# スコアロジックの版。_build_scoring_criteria を変えたら +1 する。
SCORING_VERSION = 1

_MODEL = "claude-haiku-4-5-20251001"

_SUMMARY_PROMPT_TEMPLATE = """あなたはデータエンジニアリングの技術ニュースを要約するアシスタントです。
記事を読んで以下の JSON 形式で回答してください。

{{
  "summary": "箇条書きで3〜5項目の技術ポイント（日本語・文字列・改行区切り）",
  "tags": ["タグ1", "タグ2"],
  "importance_score": 0.0〜1.0
}}

{scoring_criteria}

JSON のみを返してください。説明文は不要です。"""

_SCORE_PROMPT_TEMPLATE = """あなたはデータエンジニアリングの技術ニュースの重要度を評価するアシスタントです。
記事を読んで以下の JSON 形式で重要度スコアのみを回答してください。

{{
  "importance_score": 0.0〜1.0
}}

{scoring_criteria}

JSON のみを返してください。説明文は不要です。"""


def _build_scoring_criteria(keywords: list[str]) -> str:
    """importance_score の判定基準を組み立てる。summarize / score_article で共用。"""
    if keywords:
        items = "\n".join(f"  - {kw}" for kw in keywords)
    else:
        items = "  （キーワード未設定のため、データエンジニアリング全般を対象とする）"
    return (
        "importance_score の判定基準：\n"
        "- 以下のキーワードに関連する内容であるほど高いスコアを付ける\n"
        f"{items}\n"
        "- 複数のキーワードに関連するほど高くする\n"
        "- 全く関連しない場合は 0.1 以下にする"
    )


def _build_system_prompt(keywords: list[str]) -> str:
    """要約+タグ+スコア用のシステムプロンプト。"""
    return _SUMMARY_PROMPT_TEMPLATE.format(scoring_criteria=_build_scoring_criteria(keywords))


def _build_score_only_prompt(keywords: list[str]) -> str:
    """スコアのみ用のシステムプロンプト。"""
    return _SCORE_PROMPT_TEMPLATE.format(scoring_criteria=_build_scoring_criteria(keywords))


def _strip_code_fence(text: str) -> str:
    """```json ... ``` や ``` ... ``` のコードフェンスを除去する。"""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    return text


def summarize_article(
    title: str, content: str, api_key: str, keywords: list[str] | None = None
) -> dict | None:
    """Claude で記事を要約する。失敗時は None。keywords に基づいて importance_score を判定する。"""
    system_prompt = _build_system_prompt(keywords or [])
    try:
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model=_MODEL,
            max_tokens=512,
            system=system_prompt,
            messages=[
                {"role": "user", "content": f"タイトル: {title}\n\n本文:\n{content[:3000]}"}
            ],
        )
        block = message.content[0]
        if not isinstance(block, TextBlock):
            return None
        result = json.loads(_strip_code_fence(block.text))
        if isinstance(result.get("summary"), list):
            result["summary"] = "\n".join(result["summary"])
        return result
    except Exception as e:
        logger.error("[summarizer] failed: %s", e)
        return None


def score_article(
    title: str, content: str, api_key: str, keywords: list[str] | None = None
) -> float | None:
    """記事の importance_score のみを再計算する。失敗時は None。"""
    system_prompt = _build_score_only_prompt(keywords or [])
    try:
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model=_MODEL,
            max_tokens=64,
            system=system_prompt,
            messages=[
                {"role": "user", "content": f"タイトル: {title}\n\n本文:\n{content[:3000]}"}
            ],
        )
        block = message.content[0]
        if not isinstance(block, TextBlock):
            return None
        result = json.loads(_strip_code_fence(block.text))
        score = result.get("importance_score")
        if score is None:
            return None
        return float(score)
    except Exception as e:
        logger.error("[summarizer] score failed: %s", e)
        return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd news_pipeline && uv run pytest tests/test_summarizer.py -v`
Expected: PASS（既存4テスト + 新規5テスト）

- [ ] **Step 5: Commit**

```bash
git add news_pipeline/collector/summarizer.py news_pipeline/tests/test_summarizer.py
git commit -m "feat(summarizer): SCORING_VERSION とスコア専用 score_article・共有criteria を追加

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: bq_client に outdated 取得・スコア更新

**Files:**
- Modify: `news_pipeline/collector/bq_client.py`（`insert_summaries` の直後にメソッド追加）
- Test: `news_pipeline/tests/test_bq_client.py`（末尾に追加）

- [ ] **Step 1: Write the failing test**

`news_pipeline/tests/test_bq_client.py` の末尾に追加:

```python
@patch("collector.bq_client.bigquery.Client")
def test_get_outdated_summaries_filters_version(mock_bq_class):
    mock_client = MagicMock()
    mock_bq_class.return_value = mock_client
    _data = {"article_id": "a1", "title": "T", "content": "body", "source": "S"}
    mock_row = MagicMock()
    mock_row.keys.return_value = list(_data.keys())
    mock_row.__getitem__ = lambda self, key: _data[key]
    mock_client.query.return_value.result.return_value = [mock_row]

    bq = BQClient(project="test-project")
    result = bq.get_outdated_summaries(version=2, limit=50)

    assert result[0]["article_id"] == "a1"
    q = mock_client.query.call_args[0][0]
    assert "summaries" in q
    assert "raw_articles" in q
    assert "scoring_version" in q


@patch("collector.bq_client.bigquery.Client")
def test_update_summary_score_runs_update_dml(mock_bq_class):
    mock_client = MagicMock()
    mock_bq_class.return_value = mock_client

    bq = BQClient(project="test-project")
    bq.update_summary_score("a1", 0.9, 2)

    q = mock_client.query.call_args[0][0]
    assert "UPDATE" in q
    assert "summaries" in q
    assert "scoring_version" in q
    assert "importance_score" in q
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd news_pipeline && uv run pytest tests/test_bq_client.py -k "outdated or update_summary_score" -v`
Expected: FAIL（`AttributeError: 'BQClient' object has no attribute 'get_outdated_summaries'`）

- [ ] **Step 3: Implement**

`news_pipeline/collector/bq_client.py` の `insert_summaries` メソッドの直後に追加:

```python
    def get_outdated_summaries(self, version: int, limit: int) -> list[dict]:
        """scoring_version が古い（NULL含む）summaries を本文付きで返す。"""
        query = (
            f"SELECT s.article_id, s.title, r.content, s.source"
            f" FROM `{self.project}.{DATASET}.summaries` s"
            f" LEFT JOIN `{self.project}.{DATASET}.raw_articles` r"
            f" ON s.article_id = r.article_id"
            f" WHERE (s.scoring_version IS NULL OR s.scoring_version < @version)"
            f" LIMIT @limit"
        )
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("version", "INT64", version),
                bigquery.ScalarQueryParameter("limit", "INT64", limit),
            ]
        )
        rows = self.client.query(query, job_config=job_config).result()
        return [dict(row) for row in rows]

    def update_summary_score(
        self, article_id: str, importance_score: float, scoring_version: int
    ) -> None:
        """summaries の importance_score と scoring_version を DML UPDATE で更新する。

        例外は送出する（呼び出し側が1件ずつ握って次回繰り越し）。
        """
        query = (
            f"UPDATE `{self.project}.{DATASET}.summaries`"
            f" SET importance_score = @score, scoring_version = @ver"
            f" WHERE article_id = @aid"
        )
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("score", "FLOAT64", importance_score),
                bigquery.ScalarQueryParameter("ver", "INT64", scoring_version),
                bigquery.ScalarQueryParameter("aid", "STRING", article_id),
            ]
        )
        self.client.query(query, job_config=job_config).result()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd news_pipeline && uv run pytest tests/test_bq_client.py -v`
Expected: PASS（既存 + 新規2テスト）

- [ ] **Step 5: Commit**

```bash
git add news_pipeline/collector/bq_client.py news_pipeline/tests/test_bq_client.py
git commit -m "feat(bq_client): scoring_version 差分取得とスコア UPDATE を追加

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: summaries スキーマに scoring_version 追加（Terraform）

**Files:**
- Modify: `news_pipeline/infra/bigquery.tf` の summaries の schema

単体テスト対象外。検証は `terraform validate`。

- [ ] **Step 1: schema に列を追加**

`news_pipeline/infra/bigquery.tf` の summaries の `schema = jsonencode([...])` を以下に変更（`importance_score` 行の後に1行追加）:

```hcl
  schema = jsonencode([
    { name = "article_id",       type = "STRING",  mode = "REQUIRED" },
    { name = "title",            type = "STRING",  mode = "REQUIRED" },
    { name = "url",              type = "STRING",  mode = "REQUIRED" },
    { name = "source",           type = "STRING",  mode = "REQUIRED" },
    { name = "summary",          type = "STRING",  mode = "NULLABLE" },
    { name = "tags",             type = "STRING",  mode = "REPEATED" },
    { name = "importance_score", type = "FLOAT64", mode = "NULLABLE" },
    { name = "scoring_version",  type = "INT64",   mode = "NULLABLE" },
  ])
```

- [ ] **Step 2: terraform validate**

Run: `cd news_pipeline/infra && terraform validate`
Expected: `Success! The configuration is valid.`
（必要なら `terraform init -backend=false` を先に実行）

- [ ] **Step 3: Commit**

```bash
git add news_pipeline/infra/bigquery.tf
git commit -m "feat(infra): summaries に scoring_version 列を追加

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

> 補足: NULLABLE 列追加は非破壊スキーマ更新。既存行は NULL = 旧版扱いで再計算対象になる。

---

## Task 4: main.py に /recalculate と version 刻印

**Files:**
- Modify: `news_pipeline/collector/main.py`

**重要:** main.py は import 不可のため単体テストなし。検証は「構文 + ダミー環境変数 import + 全テスト緑 + grep」。

着手前に `news_pipeline/collector/main.py` を Read すること。現状の関連箇所:
- import: `from summarizer import summarize_article`
- 定数: `_DEFAULT_MAX_SUMMARIZE = 10`、`_DEFAULT_IMPORTANCE_THRESHOLD = 0.65`、`_DEFAULT_MAX_CONTENT_RETRIES = 3`
- `_run_collect` の要約保存箇所で summary dict を `{... , **result}` で構築している
- エンドポイント `@app.post("/collect")`、`@app.post("/notify")`

- [ ] **Step 1: import を変更**

`from summarizer import summarize_article` を以下に変更:

```python
from summarizer import SCORING_VERSION, score_article, summarize_article
```

- [ ] **Step 2: 定数を追加**

`_DEFAULT_MAX_CONTENT_RETRIES = 3` の近くに追加:

```python
_DEFAULT_RECALCULATE_LIMIT = 50
```

- [ ] **Step 3: collect の summary dict に scoring_version を刻印**

`_run_collect` 内の summary 構築箇所を変更:

```python
            if result:
                summaries.append(
                    {
                        "article_id": article["article_id"],
                        "title": article["title"],
                        "url": article["url"],
                        "source": article["source"],
                        "scoring_version": SCORING_VERSION,
                        **result,
                    }
                )
```

（既存の dict に `"scoring_version": SCORING_VERSION,` を1行加えるだけ。`**result` は summary/tags/importance_score を含む）

- [ ] **Step 4: `_run_recalculate` を追加**

`_run_notify` 関数の直後に追加:

```python
def _run_recalculate(triggered_by: str = "manual") -> int:
    """既存 summaries の importance_score を現行 SCORING_VERSION で再計算する。成功件数を返す。"""
    import uuid
    from datetime import datetime, timezone

    run_id = str(uuid.uuid4())
    started_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    log: dict = {
        "run_id": run_id,
        "triggered_by": triggered_by,
        "started_at": started_at,
        "finished_at": None,
        "articles_fetched": 0,
        "new_articles": 0,
        "summaries_generated": 0,
        "notified_count": 0,
        "error_count": 0,
        "status": "success",
        "error_message": None,
        "keywords": [],
    }

    config = load_config()
    keywords: list[str] = config.get("keywords", [])
    settings: dict = config.get("settings", {})
    general: dict = settings.get("general", {})
    recalculate_limit: int = int(
        general.get("recalculate_limit", _DEFAULT_RECALCULATE_LIMIT)
    )
    log["keywords"] = keywords

    bq = BQClient(project=PROJECT_ID)

    try:
        rows = bq.get_outdated_summaries(SCORING_VERSION, recalculate_limit)
        logger.info(
            "[recalculate] %d outdated summaries (version < %d)", len(rows), SCORING_VERSION
        )

        recalculated = 0
        for row in rows:
            score = score_article(
                title=row["title"],
                content=row.get("content") or "",
                api_key=ANTHROPIC_API_KEY,
                keywords=keywords,
            )
            if score is None:
                log["error_count"] += 1
                continue
            try:
                bq.update_summary_score(row["article_id"], score, SCORING_VERSION)
                recalculated += 1
            except Exception as e:
                logger.warning(
                    "[recalculate] update failed for %s: %s", row["article_id"], e
                )
                log["error_count"] += 1

        log["summaries_generated"] = recalculated
        logger.info("[recalculate] recalculated %d summaries", recalculated)
        return recalculated

    except Exception as e:
        log["status"] = "error"
        log["error_message"] = str(e)
        logger.error("[recalculate] error: %s", e)
        raise

    finally:
        log["finished_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        try:
            bq.insert_pipeline_log(log)
            logger.info("[recalculate] saved pipeline log run_id=%s", run_id)
        except Exception as e:
            logger.error("[recalculate] failed to save pipeline log: %s", e)
```

- [ ] **Step 5: `/recalculate` エンドポイントを追加**

`@app.post("/notify", ...)` の直後に追加:

```python
@app.post("/recalculate", response_model=PipelineResponse)
async def recalculate():
    """importance_score を現行ロジックで再計算する手動エンドポイント。"""
    n = await asyncio.to_thread(_run_recalculate)
    return PipelineResponse(status="ok", notified=n)
```

- [ ] **Step 6: 検証**

Run: `cd news_pipeline && uv run python -c "import ast; ast.parse(open('collector/main.py').read()); print('syntax ok')"`
Expected: `syntax ok`

Run: `cd news_pipeline/collector && GCP_PROJECT_ID=x ANTHROPIC_API_KEY=x SLACK_WEBHOOK_URL=x uv run python -c "import main; print('import ok')"`
Expected: `import ok`

Run: `cd news_pipeline && uv run pytest tests/ -q`
Expected: 全テスト PASS

Run: `cd news_pipeline && grep -n "scoring_version\|_run_recalculate\|/recalculate" collector/main.py`
Expected: scoring_version 刻印・`_run_recalculate`・`/recalculate` が存在

- [ ] **Step 7: Commit**

```bash
git add news_pipeline/collector/main.py
git commit -m "feat(main): /recalculate エンドポイントと collect の scoring_version 刻印を追加

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 5: ドキュメント更新（CLAUDE.md / README）

**Files:**
- Modify: `CLAUDE.md`
- Modify: `news_pipeline/README.md`

- [ ] **Step 1: CLAUDE.md を更新**

(a) `collector/` 構造説明の main.py 行を、`/collect` `/notify` に加え `/recalculate` を含む内容に更新:

```
│   ├── main.py         # /collect(収集) /notify(通知) /recalculate(再採点) と /slack エンドポイント
```

(b) 「Google Sheets 設定」セクションの settings 説明に1行追記:

```markdown
  - `general / recalculate_limit`: 1回の /recalculate で再採点する最大件数（未設定は 50）
```

(c) `### Gotchas` に1点追加:

```markdown
- **スコア再計算**: importance_score のロジック（`summarizer._build_scoring_criteria`）を変えたら `SCORING_VERSION` を +1 してデプロイし、`POST /recalculate` を古い版が無くなるまで数回叩く。`summaries.scoring_version` で差分管理（既存行は NULL=旧版）。1回 `recalculate_limit` 件ずつ処理。
```

- [ ] **Step 2: README を更新**

`news_pipeline/README.md` を編集:

(a) アーキテクチャ図のエンドポイント一覧に1行追加:

```
  POST /recalculate ← 手動: importance_score を現行ロジックで再採点（scoring_version 差分）
```

(b) BigQuery テーブル表の summaries 行を更新:

```
| `tech_news.summaries` | Claude 生成サマリー（importance_score 閾値以上のみ）。`scoring_version` でスコアロジックの版を管理 |
```

(c) 「Google Sheets で管理する設定」表の settings 行に `general/recalculate_limit`（既定50）を追記。

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md news_pipeline/README.md
git commit -m "docs: /recalculate と scoring_version・recalculate_limit を反映

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Self-Review メモ（実装者向け）

- **Spec coverage:** SCORING_VERSION/共有criteria（Task1）、score_article（Task1）、get_outdated_summaries/update_summary_score（Task2）、summaries.scoring_version 列（Task3）、_run_recalculate/`/recalculate`/collect 刻印/recalculate_limit（Task4）、ドキュメント（Task5）— すべて対応。
- **型整合:** `score_article(title, content, api_key, keywords) -> float|None`（Task1 定義 = Task4 呼び出し）、`get_outdated_summaries(version, limit)` / `update_summary_score(article_id, importance_score, scoring_version)`（Task2 = Task4）、`SCORING_VERSION`（Task1 = Task4 import/使用）一致。
- **注意:** settings 値は config_loader が int 変換可能なら int 化。`recalculate_limit`（"50"）は int で来るが `int()` で再ラップ。`importance_threshold`（"0.65"）は別タスクで float ラップ済み。
- **既存テスト回帰:** `_build_system_prompt` の戻りは criteria 経由でも keywords / 「キーワード未設定」を含むため既存2テストは通る。`summarize_article` の挙動は不変。
- streaming buffer: recalc は過去行のみ対象。collect 直後の新規行は現行版で対象外のため UPDATE が buffer に当たらない。
