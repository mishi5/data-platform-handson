from unittest.mock import MagicMock, patch
from collector.notifier import send_slack_notification


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
def test_send_notification_limits_to_5(mock_post):
    mock_post.return_value.status_code = 200

    articles = [{"title": f"Article {i}", "url": f"https://x.com/{i}",
                 "source": "s", "summary": "s"} for i in range(10)]
    send_slack_notification(articles, webhook_url="https://hooks.slack.com/test")

    posted_text = mock_post.call_args.kwargs["json"]["text"]
    assert posted_text.count("https://x.com/") == 5


@patch("collector.notifier.requests.post")
def test_send_notification_no_articles_skips_post(mock_post):
    send_slack_notification([], webhook_url="https://hooks.slack.com/test")
    mock_post.assert_not_called()
