"""Slack Incoming Webhook でニュースサマリーを通知するモジュール。"""

import logging
from datetime import datetime
from zoneinfo import ZoneInfo

import requests

logger = logging.getLogger(__name__)

_JST = ZoneInfo("Asia/Tokyo")


def _to_jst_date(value) -> str | None:
    """datetime / ISO文字列を JST の YYYY-MM-DD に変換する。無効なら None。"""
    if not value:
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        try:
            dt = datetime.fromisoformat(str(value))
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo("UTC"))
    return dt.astimezone(_JST).strftime("%Y-%m-%d")


def format_date_label(published_at, collected_at) -> str:
    """発行日優先・無ければ取得日を「🗓 発行: YYYY-MM-DD」形式で返す。両方無効なら空文字。"""
    pub = _to_jst_date(published_at)
    if pub:
        return f"🗓 発行: {pub}"
    col = _to_jst_date(collected_at)
    if col:
        return f"🗓 取得: {col}"
    return ""


def _format_blocks(articles: list[dict], header_text: str) -> list:
    """記事リストを Slack Block Kit 形式に変換する。"""
    blocks: list[dict] = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": header_text},
        }
    ]
    for i, a in enumerate(articles, 1):
        article_id = a.get("article_id", "")
        date_label = format_date_label(a.get("published_at"), a.get("collected_at"))
        source_line = f"_出典: {a['source']}"
        if date_label:
            source_line += f" ・ {date_label}"
        source_line += "_"
        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{i}. {a['title']}*\n{a.get('summary', '')}\n{source_line}",
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
                        "text": {"type": "plain_text", "text": "🔍 深堀り"},
                        "action_id": "deepdive_article",
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
            "text": {
                "type": "plain_text",
                "text": f"⭐ お気に入り記事 ({len(favorites)}件)",
            },
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
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*{title}* をお気に入りから削除しますか？",
                    },
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


def send_slack_notification(
    articles: list[dict],
    webhook_url: str,
    header: str = "本日のデータエンジニアリング技術ニュース",
) -> None:
    """summaries リストを Slack に通知する。header はメッセージ見出し。"""
    if not articles:
        logger.info("[notifier] no articles to notify")
        return

    blocks = _format_blocks(articles, header)
    payload = {"text": header, "blocks": blocks}
    try:
        resp = requests.post(webhook_url, json=payload, timeout=10)
        if resp.status_code != 200:
            logger.error("[notifier] slack error: %s %s", resp.status_code, resp.text)
        else:
            logger.info(
                "[notifier] sent %d articles to slack (%s)", len(articles), header
            )
    except Exception as e:
        logger.error("[notifier] failed to post to slack: %s", e)
