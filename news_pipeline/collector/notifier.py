"""Slack Incoming Webhook でニュースサマリーを通知するモジュール。"""
import logging
import requests

logger = logging.getLogger(__name__)


def _format_blocks(articles: list[dict]) -> list:
    """記事リストを Slack Block Kit 形式に変換する。"""
    blocks: list[dict] = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "本日のデータエンジニアリング技術ニュース"},
        }
    ]
    for i, a in enumerate(articles, 1):
        article_id = a.get("article_id", "")
        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{i}. {a['title']}*\n{a.get('summary', '')}\n_出典: {a['source']}_",
                },
            }
        )
        blocks.append(
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "⭐ お気に入り"},
                        "action_id": "add_favorite",
                        "value": article_id,
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "🔗 記事を読む"},
                        "action_id": "open_article",
                        "url": a["url"],
                    },
                ],
            }
        )
        blocks.append({"type": "divider"})
    return blocks


def format_favorites_blocks(favorites: list[dict]) -> list:
    """お気に入り記事リストを Slack Block Kit 形式に変換する。"""
    blocks: list[dict] = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"⭐ お気に入り記事 ({len(favorites)}件)"},
        }
    ]
    for i, f in enumerate(favorites, 1):
        title = f.get("title") or f["article_id"]
        url = f.get("url", "")
        source = f.get("source", "")
        article_id = f["article_id"]
        blocks.append(
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*{i}. {title}*\n_出典: {source}_"},
            }
        )
        elements: list[dict] = []
        if url:
            elements.append(
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "🔗 記事を読む"},
                    "action_id": "open_article_fav",
                    "url": url,
                }
            )
        elements.append(
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "🗑️ 削除"},
                "action_id": "remove_favorite",
                "value": article_id,
                "style": "danger",
                "confirm": {
                    "title": {"type": "plain_text", "text": "削除の確認"},
                    "text": {"type": "mrkdwn", "text": f"*{title}* をお気に入りから削除しますか？"},
                    "confirm": {"type": "plain_text", "text": "削除"},
                    "deny": {"type": "plain_text", "text": "キャンセル"},
                },
            }
        )
        blocks.append({"type": "actions", "elements": elements})
        blocks.append({"type": "divider"})
    return blocks


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

    blocks = _format_blocks(articles)
    payload = {"text": "本日のデータエンジニアリング技術ニュース", "blocks": blocks}
    try:
        resp = requests.post(webhook_url, json=payload, timeout=10)
        if resp.status_code != 200:
            logger.error("[notifier] slack error: %s %s", resp.status_code, resp.text)
        else:
            logger.info("[notifier] sent %d articles to slack", len(articles))
    except Exception as e:
        logger.error("[notifier] failed to post to slack: %s", e)
