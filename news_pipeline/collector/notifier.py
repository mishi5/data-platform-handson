import logging
import requests

logger = logging.getLogger(__name__)

MAX_ARTICLES = 5


def _format_message(articles: list[dict]) -> str:
    lines = ["*本日のデータエンジニアリング技術ニュース*\n"]
    for i, a in enumerate(articles[:MAX_ARTICLES], 1):
        lines.append(f"*{i}. {a['title']}*")
        lines.append(f"出典: {a['source']}")
        lines.append(a.get("summary", ""))
        lines.append(f"<{a['url']}|記事を読む>\n")
    return "\n".join(lines)


def send_slack_notification(articles: list[dict], webhook_url: str) -> None:
    """summaries リストを Slack に通知する。"""
    if not articles:
        logger.info("[notifier] no articles to notify")
        return

    text = _format_message(articles)
    resp = requests.post(webhook_url, json={"text": text})
    if resp.status_code != 200:
        logger.error("[notifier] slack error: %s %s", resp.status_code, resp.text)
