"""Slack Incoming Webhook でニュースサマリーを通知するモジュール。"""
import logging
import requests

logger = logging.getLogger(__name__)

def _format_message(articles: list[dict]) -> str:
    """記事リストを Slack 投稿用のテキストにフォーマットする。"""
    lines = ["*本日のデータエンジニアリング技術ニュース*\n"]
    for i, a in enumerate(articles, 1):
        article_id_short = a.get("article_id", "")[:8]
        lines.append(f"*{i}. {a['title']}*")
        lines.append(a.get("summary", ""))
        lines.append(
            f"_出典: {a['source']}_ | ID: `{article_id_short}` | <{a['url']}|リンクを開く>"
        )
        lines.append(f"`{a['url']}`\n")
    return "\n".join(lines)


def send_no_news_notification(webhook_url: str, reason: str) -> None:
    """ネタ切れ時に Slack へ通知する。"""
    text = f":newspaper: *本日のデータエンジニアリングニュース*\n{reason}"
    try:
        resp = requests.post(webhook_url, json={"text": text}, timeout=10)
        if resp.status_code != 200:
            logger.error("[notifier] slack error: %s %s", resp.status_code, resp.text)
        else:
            logger.info("[notifier] sent no-news notification")
    except Exception as e:
        logger.error("[notifier] failed to post to slack: %s", e)


def send_slack_notification(articles: list[dict], webhook_url: str) -> None:
    """summaries リストを Slack に通知する。"""
    if not articles:
        logger.info("[notifier] no articles to notify")
        return

    text = _format_message(articles)
    try:
        resp = requests.post(webhook_url, json={"text": text}, timeout=10)
        if resp.status_code != 200:
            logger.error("[notifier] slack error: %s %s", resp.status_code, resp.text)
        else:
            logger.info("[notifier] sent %d articles to slack", len(articles))
    except Exception as e:
        logger.error("[notifier] failed to post to slack: %s", e)
