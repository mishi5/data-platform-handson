# Flask → FastAPI Migration Design

## Goal

`main.py` のWebフレームワークをFlaskからFastAPIに移行する。目的は型安全性とFastAPIのイディオマティックなパターン（`async def`・`BackgroundTasks`・`Depends`）の習得。

## Scope

変更ファイル: `collector/main.py`, `collector/requirements.txt`, `collector/Dockerfile`
変更なし: `bq_client.py`, `summarizer.py`, `deepdiver.py`, `notifier.py` 等すべての他モジュール

---

## Architecture

### 依存関係

| 変更前 | 変更後 |
|--------|--------|
| `Flask==3.1.0` | 削除 |
| （なし） | `fastapi` |
| （なし） | `uvicorn[standard]` |

### エンドポイント対応表

| エンドポイント | 実行方式 | Flask | FastAPI |
|--------------|---------|-------|---------|
| `POST /` | 同期待機 | `_run_pipeline()` | `await asyncio.to_thread(_run_pipeline)` |
| `POST /slack` | 即時返却 | `threading.Thread(...).start()` | `background_tasks.add_task(...)` |
| `POST /slack/deepdive` | 即時返却 | `threading.Thread(...).start()` | `background_tasks.add_task(...)` |

---

## Components

### 1. Pydantic レスポンスモデル

```python
from pydantic import BaseModel

class PipelineResponse(BaseModel):
    status: str
    notified: int

class SlackResponse(BaseModel):
    response_type: str
    text: str
```

`response_model` パラメータに渡すことで、レスポンス型が自動ドキュメント化・バリデーションされる。

### 2. `verify_slack` Dependency

```python
async def verify_slack(request: Request) -> None:
    """Slack署名を検証するDependency。失敗時は HTTPException(403)。"""
    if not SLACK_SIGNING_SECRET:
        return
    timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
    try:
        if abs(time.time() - int(timestamp)) > 300:
            raise HTTPException(status_code=403, detail="invalid signature")
    except ValueError:
        raise HTTPException(status_code=403, detail="invalid signature")
    body = await request.body()
    sig_basestring = f"v0:{timestamp}:{body.decode()}"
    expected = (
        "v0="
        + hmac.new(SLACK_SIGNING_SECRET.encode(), sig_basestring.encode(), hashlib.sha256).hexdigest()
    )
    if not hmac.compare_digest(expected, request.headers.get("X-Slack-Signature", "")):
        raise HTTPException(status_code=403, detail="invalid signature")
```

`_verify_slack_signature(req) -> bool` から、`HTTPException` を raise する Dependency 関数に変更。
両Slackエンドポイントで `_: None = Depends(verify_slack)` として再利用する。

### 3. エンドポイント実装

```python
@app.post("/", response_model=PipelineResponse)
async def run_pipeline():
    notified = await asyncio.to_thread(_run_pipeline)
    return PipelineResponse(status="ok", notified=notified)

@app.post("/slack", response_model=SlackResponse)
async def slack_command(
    background_tasks: BackgroundTasks,
    text: str = Form(default=""),
    _: None = Depends(verify_slack),
):
    background_tasks.add_task(_run_pipeline, "slack_command")
    return SlackResponse(
        response_type="in_channel",
        text=":hourglass: ニュースを収集中です。しばらくお待ちください...",
    )

@app.post("/slack/deepdive", response_model=SlackResponse)
async def slack_deepdive(
    background_tasks: BackgroundTasks,
    text: str = Form(default=""),
    response_url: str = Form(default=""),
    _: None = Depends(verify_slack),
):
    article_id_prefix = text.strip()
    background_tasks.add_task(_run_deepdive, article_id_prefix, response_url)
    msg = f"ID `{article_id_prefix}` の記事を深堀り中です..." if article_id_prefix else "最新記事を深堀り中です..."
    return SlackResponse(response_type="in_channel", text=f":mag: {msg}")
```

### 4. エントリーポイント

```python
# main.py
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
```

```dockerfile
# Dockerfile CMD
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
```

---

## import 変更まとめ

```python
# 削除
from flask import Flask, jsonify, request
import threading

# 追加
import asyncio
from fastapi import BackgroundTasks, Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
```

---

## テスト方針

既存テスト（`test_bq_client.py`, `test_notifier.py` 等）はすべて他モジュールのテストのため変更不要。
`main.py` 自体のテストは現在存在しないため追加しない（スコープ外）。

---

## 非対応事項（スコープ外）

- 他モジュールの非同期化（`bq_client`, `summarizer` 等）
- `lifespan` による起動/終了フック
- `/docs` (Swagger UI) の活用
