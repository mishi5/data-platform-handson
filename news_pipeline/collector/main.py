import logging
import os

from flask import Flask, jsonify

from rss_fetcher import fetch_articles
from article_parser import fetch_content
from bq_client import BQClient
from summarizer import summarize_article
from notifier import send_slack_notification

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

PROJECT_ID = os.environ["GCP_PROJECT_ID"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
SLACK_WEBHOOK_URL = os.environ["SLACK_WEBHOOK_URL"]

HIGH_PRIORITY_KEYWORDS = [
    "bigquery", "dataform", "data catalog", "data lineage",
    "data governance", "google cloud", "data modeling",
]


def _is_relevant(title: str, content: str) -> bool:
    text = (title + " " + (content or "")).lower()
    return any(kw in text for kw in HIGH_PRIORITY_KEYWORDS)


@app.route("/", methods=["POST"])
def run_pipeline():
    bq = BQClient(project=PROJECT_ID)

    # 1. RSS 取得
    articles = fetch_articles()
    logger.info("[pipeline] fetched %d articles from RSS", len(articles))

    # 2. dedup
    existing_urls = bq.get_existing_urls()
    new_articles = [a for a in articles if a["url"] not in existing_urls]
    logger.info("[pipeline] %d new articles after dedup", len(new_articles))

    if not new_articles:
        return jsonify({"status": "ok", "message": "no new articles"})

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
            summaries.append({
                "article_id": article["article_id"],
                "title": article["title"],
                "url": article["url"],
                "source": article["source"],
                **result,
            })

    # 7. summaries 保存
    if summaries:
        bq.insert_summaries(summaries)
        logger.info("[pipeline] saved %d summaries", len(summaries))

    # 8. 通知（importance_score 降順で最大5件）
    top_articles = sorted(summaries, key=lambda x: x.get("importance_score", 0), reverse=True)
    top5 = top_articles[:5]
    send_slack_notification(top5, webhook_url=SLACK_WEBHOOK_URL)

    return jsonify({"status": "ok", "notified": len(top5)})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
