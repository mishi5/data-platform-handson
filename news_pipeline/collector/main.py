"""
news_pipeline メインモジュール。

Flask サーバーとして起動し、以下の2エンドポイントを提供する:
  POST /       - Cloud Scheduler からの定期実行トリガー
  POST /slack  - Slack スラッシュコマンド（/news-update）からの手動実行トリガー

パイプライン処理は _run_pipeline() に集約されており、
Slack エンドポイントではタイムアウト対策としてバックグラウンドスレッドで実行する。
"""
import hashlib
import hmac
import logging
import os
import threading
import time

from article_parser import fetch_content
from bq_client import BQClient
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from notifier import send_slack_notification
from rss_fetcher import fetch_articles
from summarizer import summarize_article

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

PROJECT_ID = os.environ["GCP_PROJECT_ID"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
SLACK_WEBHOOK_URL = os.environ["SLACK_WEBHOOK_URL"]
SLACK_SIGNING_SECRET = os.environ.get("SLACK_SIGNING_SECRET", "")
# ローカルテスト時に件数を絞る（未設定 = 無制限）
MAX_ARTICLES = int(os.environ.get("MAX_ARTICLES", 0)) or None

HIGH_PRIORITY_KEYWORDS = [
    "bigquery",
    "dataform",
    "data catalog",
    "data lineage",
    "data governance",
    "data modeling",
    "data pipeline",
    "data warehouse",
    "data lake",
    "dbt",
    "apache spark",
    "apache iceberg",
    "data mesh",
    "analytics engineering",
    "data quality",
    "data platform",
    "metadata",
    "data discovery",
    "looker",
    "tableau",
    "metabase",
    "bi tool",
    "business intelligence",
    "data observability",
]


def _is_relevant(title: str, content: str) -> bool:
    """タイトルと本文に HIGH_PRIORITY_KEYWORDS が含まれるか判定する。"""
    text = (title + " " + (content or "")).lower()
    return any(kw in text for kw in HIGH_PRIORITY_KEYWORDS)


def _verify_slack_signature(req) -> bool:
    """Slack からのリクエストを署名で検証する。"""
    timestamp = req.headers.get("X-Slack-Request-Timestamp", "")
    try:
        if abs(time.time() - int(timestamp)) > 300:
            return False
    except ValueError:
        return False
    sig_basestring = f"v0:{timestamp}:{req.get_data(as_text=True)}"
    expected = (
        "v0="
        + hmac.new(
            SLACK_SIGNING_SECRET.encode(), sig_basestring.encode(), hashlib.sha256
        ).hexdigest()
    )
    return hmac.compare_digest(expected, req.headers.get("X-Slack-Signature", ""))


def _run_pipeline() -> int:
    """パイプライン実行。通知件数を返す。"""
    bq = BQClient(project=PROJECT_ID)

    # 1. RSS 取得
    articles = fetch_articles()
    logger.info("[pipeline] fetched %d articles from RSS", len(articles))

    # 2. dedup
    existing_urls = bq.get_existing_urls()
    new_articles = [a for a in articles if a["url"] not in existing_urls]
    logger.info("[pipeline] %d new articles after dedup", len(new_articles))

    if not new_articles:
        logger.info("[pipeline] no new articles")
        return 0

    if MAX_ARTICLES:
        new_articles = new_articles[:MAX_ARTICLES]
        logger.info("[pipeline] limited to %d articles (MAX_ARTICLES)", MAX_ARTICLES)

    # 3. 本文取得
    for article in new_articles:
        article["content"] = fetch_content(article["url"])

    # 4. raw_articles 保存
    bq.insert_raw_articles(new_articles)
    logger.info("[pipeline] saved %d to raw_articles", len(new_articles))

    # 5. フィルタリング
    relevant = [a for a in new_articles if _is_relevant(a["title"], a["content"])]
    logger.info("[pipeline] %d relevant articles after filtering", len(relevant))

    # 6. 要約生成
    summaries = []
    for article in relevant:
        try:
            result = summarize_article(
                title=article["title"],
                content=article["content"] or "",
                api_key=ANTHROPIC_API_KEY,
            )
        except Exception as e:
            logger.warning("[pipeline] summarize failed for %s: %s", article["url"], e)
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

    # 7. summaries 保存
    if summaries:
        bq.insert_summaries(summaries)
        logger.info("[pipeline] saved %d summaries", len(summaries))

    # 8. 通知（importance_score 降順で最大5件）
    top5 = sorted(summaries, key=lambda x: x.get("importance_score", 0), reverse=True)[
        :5
    ]
    send_slack_notification(top5, webhook_url=SLACK_WEBHOOK_URL)

    return len(top5)


@app.route("/", methods=["POST"])
def run_pipeline():
    """Cloud Scheduler からの定期実行エンドポイント。パイプラインを同期実行する。"""
    notified = _run_pipeline()
    return jsonify({"status": "ok", "notified": notified})


@app.route("/slack", methods=["POST"])
def slack_command():
    """Slack スラッシュコマンド（/news-update）のエンドポイント。"""
    if SLACK_SIGNING_SECRET and not _verify_slack_signature(request):
        logger.warning("[slack] invalid signature")
        return jsonify({"error": "invalid signature"}), 403

    # Slack は 3 秒以内のレスポンスを要求するため、バックグラウンドで実行
    threading.Thread(target=_run_pipeline, daemon=True).start()

    return jsonify(
        {
            "response_type": "in_channel",
            "text": ":hourglass: ニュースを収集中です。しばらくお待ちください...",
        }
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
