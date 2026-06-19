from unittest.mock import patch
from collector.notifier import (
    format_date_label,
    send_no_news_notification,
    send_slack_notification,
)


@patch("collector.notifier.requests.post")
def test_send_notification_posts_to_webhook(mock_post):
    mock_post.return_value.status_code = 200

    articles = [
        {
            "title": "BigQuery update",
            "url": "https://cloud.google.com/blog/1",
            "source": "Google Cloud Blog",
            "summary": "- Feature A\n- Feature B",
        }
    ]
    send_slack_notification(articles, webhook_url="https://hooks.slack.com/test")

    mock_post.assert_called_once()
    call_json = mock_post.call_args.kwargs["json"]
    blocks_str = str(call_json["blocks"])
    assert "BigQuery update" in blocks_str


@patch("collector.notifier.requests.post")
def test_send_notification_no_articles_skips_post(mock_post):
    send_slack_notification([], webhook_url="https://hooks.slack.com/test")
    mock_post.assert_not_called()


@patch("collector.notifier.requests.post")
def test_format_includes_article_id_and_url(mock_post):
    mock_post.return_value.status_code = 200

    articles = [
        {
            "article_id": "abc12345xyz",
            "title": "BigQuery update",
            "url": "https://cloud.google.com/blog/1",
            "source": "Google Cloud Blog",
            "summary": "- Feature A\n- Feature B",
        }
    ]
    send_slack_notification(articles, webhook_url="https://hooks.slack.com/test")

    call_json = mock_post.call_args.kwargs["json"]
    blocks_str = str(call_json["blocks"])
    assert "BigQuery update" in blocks_str
    assert "abc12345xyz" in blocks_str  # article_id（ボタンのvalue）
    assert "https://cloud.google.com/blog/1" in blocks_str  # ボタンのurl


@patch("collector.notifier.requests.post")
def test_send_no_news_notification_posts_to_webhook(mock_post):
    mock_post.return_value.status_code = 200

    send_no_news_notification(
        webhook_url="https://hooks.slack.com/test",
        reason="新着記事はありませんでした。",
    )

    mock_post.assert_called_once()
    call_json = mock_post.call_args.kwargs["json"]
    assert "新着記事はありませんでした。" in call_json["text"]


@patch("collector.notifier.requests.post")
def test_send_notification_uses_custom_header(mock_post):
    mock_post.return_value.status_code = 200

    articles = [
        {
            "article_id": "id1",
            "title": "Some article",
            "url": "https://example.com/1",
            "source": "Example Blog",
            "summary": "- point",
        }
    ]
    send_slack_notification(
        articles, webhook_url="https://hooks.slack.com/test", header="📢 公式ブログ"
    )

    call_json = mock_post.call_args.kwargs["json"]
    assert call_json["text"] == "📢 公式ブログ"
    # ヘッダーブロックにラベルが入っている
    header_block = call_json["blocks"][0]
    assert header_block["type"] == "header"
    assert header_block["text"]["text"] == "📢 公式ブログ"


def test_format_date_label_uses_published():
    # JST: 2026-06-18T09:00Z -> 18:00 JST 同日
    assert (
        format_date_label("2026-06-18T09:00:00+00:00", "2026-06-19T00:00:00+00:00")
        == "🗓 発行: 2026-06-18"
    )


def test_format_date_label_falls_back_to_collected():
    assert format_date_label(None, "2026-06-18T09:00:00+00:00") == "🗓 取得: 2026-06-18"
    assert format_date_label("", "2026-06-18T09:00:00+00:00") == "🗓 取得: 2026-06-18"


def test_format_date_label_both_missing_returns_empty():
    assert format_date_label(None, None) == ""
    assert format_date_label("", "") == ""


def test_format_date_label_utc_to_jst_rolls_over():
    # UTC 2026-06-18T20:00Z -> JST 2026-06-19T05:00
    assert format_date_label("2026-06-18T20:00:00+00:00", None) == "🗓 発行: 2026-06-19"


def test_format_date_label_accepts_datetime():
    from datetime import datetime, timezone

    dt = datetime(2026, 6, 18, 20, 0, 0, tzinfo=timezone.utc)
    assert format_date_label(dt, None) == "🗓 発行: 2026-06-19"


def test_format_date_label_unparseable_published_falls_back():
    assert (
        format_date_label("not-a-date", "2026-06-18T09:00:00+00:00")
        == "🗓 取得: 2026-06-18"
    )


@patch("collector.notifier.requests.post")
def test_notification_includes_published_date(mock_post):
    mock_post.return_value.status_code = 200
    articles = [
        {
            "title": "BigQuery update",
            "url": "https://cloud.google.com/blog/1",
            "source": "Google Cloud Blog",
            "summary": "- Feature A",
            "published_at": "2026-06-18T09:00:00+00:00",
        }
    ]
    send_slack_notification(articles, webhook_url="https://hooks.slack.com/test")
    blocks_str = str(mock_post.call_args.kwargs["json"]["blocks"])
    assert "🗓 発行: 2026-06-18" in blocks_str


@patch("collector.notifier.requests.post")
def test_notification_without_date_has_no_date_label(mock_post):
    mock_post.return_value.status_code = 200
    articles = [
        {
            "title": "No date article",
            "url": "https://example.com/1",
            "source": "Example",
            "summary": "- x",
        }
    ]
    send_slack_notification(articles, webhook_url="https://hooks.slack.com/test")
    blocks_str = str(mock_post.call_args.kwargs["json"]["blocks"])
    assert "🗓" not in blocks_str
