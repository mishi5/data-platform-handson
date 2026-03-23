"""
news_pipeline メインモジュール。

FastAPI サーバーとして起動し、以下の3エンドポイントを提供する:
  POST /              - Cloud Scheduler からの定期実行トリガー
  POST /slack         - Slack スラッシュコマンド（/news-update）からの手動実行トリガー
  POST /slack/deepdive - Slack スラッシュコマンド（/news-deepdive）からの深堀りトリガー

パイプライン処理は _run_pipeline() に集約されており、
Slack エンドポイントではタイムアウト対策として BackgroundTasks で実行する。
"""
import asyncio
import hashlib
import hmac
import json
import logging
import os
import time
import urllib.parse

from article_parser import fetch_content
from bq_client import BQClient
from config_loader import load_config
from deepdiver import deepdive_article
from dotenv import load_dotenv
from fastapi import BackgroundTasks, Depends, FastAPI, Form, HTTPException, Request
from notifier import format_favorites_blocks, send_no_news_notification, send_slack_notification
from pydantic import BaseModel
from rss_fetcher import fetch_articles
from summarizer import summarize_article

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

PROJECT_ID = os.environ["GCP_PROJECT_ID"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
SLACK_WEBHOOK_URL = os.environ["SLACK_WEBHOOK_URL"]
SLACK_SIGNING_SECRET = os.environ.get("SLACK_SIGNING_SECRET", "")
# MAX_NOTIFY: importance_scoreフィルタ後に実際に通知する件数の上限（未設定 = 5件）
MAX_NOTIFY = int(os.environ.get("MAX_NOTIFY", 5))
# IMPORTANCE_THRESHOLD: このスコア以上の記事のみ summaries に保存・通知対象とする
IMPORTANCE_THRESHOLD = float(os.environ.get("IMPORTANCE_THRESHOLD", 0.5))

# max_summarize: 1実行で要約する記事の最大件数（Google Sheetsのsettingsシートから取得）
_DEFAULT_MAX_SUMMARIZE = 10


class PipelineResponse(BaseModel):
    status: str
    notified: int


class SlackResponse(BaseModel):
    response_type: str
    text: str


def _post_to_response_url(response_url: str, text: str) -> None:
    """Slack の response_url に遅延応答を POST する。"""
    import requests as _requests
    try:
        _requests.post(
            response_url,
            json={"response_type": "in_channel", "text": text},
            timeout=10,
        )
    except Exception as e:
        logger.error("[deepdive] failed to post to response_url: %s", e)


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
        + hmac.new(
            SLACK_SIGNING_SECRET.encode(), sig_basestring.encode(), hashlib.sha256
        ).hexdigest()
    )
    if not hmac.compare_digest(expected, request.headers.get("X-Slack-Signature", "")):
        raise HTTPException(status_code=403, detail="invalid signature")


def _run_pipeline(triggered_by: str = "scheduler") -> int:
    """パイプライン実行。通知件数を返す。"""
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
    feeds: dict[str, str] = config.get("feeds", {})
    keywords: list[str] = config.get("keywords", [])
    max_summarize: int = config.get("max_summarize", _DEFAULT_MAX_SUMMARIZE)
    log["keywords"] = keywords

    bq = BQClient(project=PROJECT_ID)

    try:
        # 1. RSS 取得
        articles = fetch_articles(feeds)
        log["articles_fetched"] = len(articles)
        logger.info("[pipeline] fetched %d articles from RSS", len(articles))

        # 2. dedup（raw_articlesベース）
        existing_urls = bq.get_existing_urls()
        new_articles = [a for a in articles if a["url"] not in existing_urls]
        log["new_articles"] = len(new_articles)
        logger.info("[pipeline] %d new articles after dedup", len(new_articles))

        if new_articles:
            # 3. 要約する件数を上限に絞る
            new_articles = new_articles[:max_summarize]
            logger.info("[pipeline] limited to %d articles (max_summarize)", max_summarize)

            # 4. 本文取得
            for article in new_articles:
                article["content"] = fetch_content(article["url"])

            # 5. raw_articles 保存
            bq.insert_raw_articles(new_articles)
            logger.info("[pipeline] saved %d to raw_articles", len(new_articles))

            # 6. 要約生成（全新着記事）
            summaries = []
            for article in new_articles:
                try:
                    result = summarize_article(
                        title=article["title"],
                        content=article["content"] or "",
                        api_key=ANTHROPIC_API_KEY,
                        keywords=keywords,
                    )
                except Exception as e:
                    logger.warning("[pipeline] summarize failed for %s: %s", article["url"], e)
                    log["error_count"] += 1
                    continue
                if result:
                    summaries.append(
                        {
                            "article_id": article["article_id"],
                            "title": article["title"],
                            "url": article["url"],
                            "source": article["source"],
                            **result,
                        }
                    )

            # 7. importance_score によるフィルタリング
            relevant_summaries = [
                s for s in summaries if s.get("importance_score", 0) >= IMPORTANCE_THRESHOLD
            ]
            log["summaries_generated"] = len(relevant_summaries)
            logger.info(
                "[pipeline] %d relevant summaries (importance_score >= %.1f)",
                len(relevant_summaries),
                IMPORTANCE_THRESHOLD,
            )

            # 8. summaries 保存（関連あり記事のみ・article_id 重複を排除）
            if relevant_summaries:
                existing_summary_ids = bq.get_existing_summary_ids()
                relevant_summaries = [
                    s for s in relevant_summaries if s["article_id"] not in existing_summary_ids
                ]
            if relevant_summaries:
                bq.insert_summaries(relevant_summaries)
                logger.info("[pipeline] saved %d summaries", len(relevant_summaries))
        else:
            logger.info("[pipeline] no new articles, checking unnotified summaries")

        # 9. 未通知サマリーを取得して通知（新着ありなしに関わらず実施）
        unnotified = bq.get_unnotified_summaries()
        logger.info("[pipeline] %d unnotified summaries in BQ", len(unnotified))

        if not unnotified:
            send_no_news_notification(SLACK_WEBHOOK_URL, "新着記事はありませんでした。")
            return 0

        # 10. importance_score 降順で最大 MAX_NOTIFY 件を通知
        top = sorted(unnotified, key=lambda x: x.get("importance_score", 0), reverse=True)[
            :MAX_NOTIFY
        ]
        send_slack_notification(top, webhook_url=SLACK_WEBHOOK_URL)
        logger.info("[pipeline] notified %d articles", len(top))

        # 11. 通知済みマーク
        notified_ids = [a["article_id"] for a in top]
        bq.mark_summaries_notified(notified_ids)
        logger.info("[pipeline] marked %d summaries as notified", len(notified_ids))

        log["notified_count"] = len(top)
        return len(top)

    except Exception as e:
        log["status"] = "error"
        log["error_message"] = str(e)
        logger.error("[pipeline] pipeline error: %s", e)
        raise

    finally:
        log["finished_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        try:
            bq.insert_pipeline_log(log)
            logger.info("[pipeline] saved pipeline log run_id=%s", run_id)
        except Exception as e:
            logger.error("[pipeline] failed to save pipeline log: %s", e)


def _run_deepdive(article_id_prefix: str, response_url: str) -> None:
    """深堀り処理。完了後に response_url へ結果を POST する。"""
    bq = BQClient(project=PROJECT_ID)

    # 1. 対象記事を取得
    if article_id_prefix:
        article = bq.get_article_by_id(article_id_prefix)
        if not article:
            _post_to_response_url(response_url, f"ID `{article_id_prefix}` の記事が見つかりませんでした。")
            return
    else:
        article = bq.get_top_undived_article()
        if not article:
            _post_to_response_url(response_url, "深堀り対象の記事がありません。")
            return

    title = article["title"]
    url = article["url"]
    article_id = article["article_id"]

    # 2. キャッシュ確認
    cached = bq.get_deepdive(article_id)
    if cached:
        logger.info("[deepdive] cache hit for %s", article_id)
        _post_to_response_url(response_url, f"*[深堀り] {title}*\n\n{cached}\n\n🔗 <{url}|元記事を読む>")
        return

    # 3. 深堀り生成
    logger.info("[deepdive] generating for %s", article_id)
    text = deepdive_article(
        title=title,
        content=article.get("content") or "",
        api_key=ANTHROPIC_API_KEY,
    )
    if not text:
        _post_to_response_url(response_url, "深堀り生成に失敗しました。しばらく経ってから再試行してください。")
        return

    # 4. キャッシュ保存
    try:
        bq.insert_deepdive(article_id, text)
    except Exception as e:
        logger.error("[deepdive] failed to cache deepdive: %s", e)

    # 5. 結果を送信
    _post_to_response_url(response_url, f"*[深堀り] {title}*\n\n{text}\n\n🔗 <{url}|元記事を読む>")
    logger.info("[deepdive] completed for %s", article_id)


@app.post("/", response_model=PipelineResponse)
async def run_pipeline():
    """Cloud Scheduler からの定期実行エンドポイント。パイプラインを同期実行する。"""
    notified = await asyncio.to_thread(_run_pipeline)
    return PipelineResponse(status="ok", notified=notified)


@app.post("/slack", response_model=SlackResponse)
async def slack_command(
    background_tasks: BackgroundTasks,
    _: None = Depends(verify_slack),
):
    """Slack スラッシュコマンド（/news-update）のエンドポイント。"""
    background_tasks.add_task(_run_pipeline, "slack_command")
    return SlackResponse(
        response_type="in_channel",
        text=":hourglass: ニュースを収集中です。しばらくお待ちください...",
    )


@app.post("/slack/actions")
async def slack_actions(
    request: Request,
    _: None = Depends(verify_slack),
):
    """Slack インタラクティブコンポーネント（ボタン押下など）のエンドポイント。"""
    # Form(...)を使わず手動パース（verify_slackがbodyを先に読んでキャッシュするため）
    body = await request.body()
    form_data = urllib.parse.parse_qs(body.decode())
    payload_str = form_data.get("payload", [""])[0]
    data = json.loads(payload_str)
    actions = data.get("actions", [])
    if not actions:
        return {}

    action = actions[0]
    action_id = action.get("action_id", "")

    if action_id == "add_favorite":
        article_id = action.get("value", "")
        bq = BQClient(project=PROJECT_ID)
        if bq.is_favorited(article_id):
            return {"response_type": "ephemeral", "text": "すでにお気に入り済みです。"}
        bq.insert_favorite(article_id)
        logger.info("[favorite] added article_id=%s", article_id)
        return {"response_type": "ephemeral", "text": "⭐ お気に入りに追加しました！"}

    if action_id == "remove_favorite":
        article_id = action.get("value", "")
        bq = BQClient(project=PROJECT_ID)
        bq.delete_favorite(article_id)
        logger.info("[favorite] removed article_id=%s", article_id)
        return {"response_type": "ephemeral", "text": "🗑️ お気に入りから削除しました。"}

    return {}


def _run_show_favorites(response_url: str) -> None:
    """お気に入り一覧を取得して response_url に POST する。"""
    import requests as _requests
    bq = BQClient(project=PROJECT_ID)
    favorites = bq.get_favorites()
    if not favorites:
        _post_to_response_url(response_url, "お気に入り記事はありません。")
        return
    blocks = format_favorites_blocks(favorites)
    try:
        _requests.post(
            response_url,
            json={"response_type": "ephemeral", "blocks": blocks},
            timeout=10,
        )
    except Exception as e:
        logger.error("[favorites] failed to post to response_url: %s", e)


@app.post("/slack/favorites", response_model=SlackResponse)
async def slack_favorites(
    request: Request,
    background_tasks: BackgroundTasks,
    _: None = Depends(verify_slack),
):
    """Slack スラッシュコマンド（/news-favorites）のエンドポイント。"""
    body = await request.body()
    form_data = urllib.parse.parse_qs(body.decode())
    response_url = form_data.get("response_url", [""])[0]
    background_tasks.add_task(_run_show_favorites, response_url)
    return SlackResponse(response_type="ephemeral", text=":hourglass: お気に入り一覧を取得中...")


@app.post("/slack/deepdive", response_model=SlackResponse)
async def slack_deepdive(
    request: Request,
    background_tasks: BackgroundTasks,
    _: None = Depends(verify_slack),
):
    """Slack スラッシュコマンド（/news-deepdive）のエンドポイント。"""
    body = await request.body()
    form_data = urllib.parse.parse_qs(body.decode())
    article_id_prefix = form_data.get("text", [""])[0].strip()
    response_url = form_data.get("response_url", [""])[0]
    background_tasks.add_task(_run_deepdive, article_id_prefix, response_url)
    msg = f"ID `{article_id_prefix}` の記事を深堀り中です..." if article_id_prefix else "最新記事を深堀り中です..."
    return SlackResponse(response_type="in_channel", text=f":mag: {msg}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
