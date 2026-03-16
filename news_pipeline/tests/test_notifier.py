from unittest.mock import patch
from collector.notifier import send_no_news_notification, send_slack_notification


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
    assert "BigQuery update" in call_json["text"]


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
    text = call_json["text"]
    assert "BigQuery update" in text
    assert "abc12345" in text  # article_id先頭8文字
    assert "https://cloud.google.com/blog/1" in text  # コピー用URL


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
