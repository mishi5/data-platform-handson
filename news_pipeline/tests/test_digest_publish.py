"""scripts/digest/publish.py のテスト。"""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts", "digest"))

import publish


@patch("publish.subprocess.run")
def test_get_id_token_impersonates_service_account(mock_run):
    mock_run.return_value = MagicMock(returncode=0, stdout="tok123\n", stderr="")

    token = publish.get_id_token()

    assert token == "tok123"
    cmd = mock_run.call_args[0][0]
    assert "print-identity-token" in cmd
    assert any("family-share-api@" in c for c in cmd)
    assert any("--audiences=" in c for c in cmd)


@patch("publish.subprocess.run")
def test_get_id_token_raises_on_failure(mock_run):
    """トークン取得の失敗は握りつぶさない（後続が必ず失敗するため）。"""
    mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="no creds")

    with pytest.raises(RuntimeError, match="ID token"):
        publish.get_id_token()


@patch("publish.requests.post")
def test_upload_new_content_posts_to_upload_endpoint(mock_post):
    mock_post.return_value = MagicMock(
        status_code=201, json=lambda: {"id": "01X", "url": "https://fs/view/01X"}
    )

    result = publish.upload_html(
        token="t", html_path=__file__, title="週次ダイジェスト", content_id=None
    )

    assert result["url"] == "https://fs/view/01X"
    assert mock_post.call_args[0][0].endswith("/api/upload")


@patch("publish.requests.post")
def test_upload_existing_content_uses_overwrite_endpoint(mock_post):
    """content_id 指定時は上書き（URL が変わらない）。"""
    mock_post.return_value = MagicMock(
        status_code=200, json=lambda: {"id": "01X", "url": "https://fs/view/01X"}
    )

    publish.upload_html(token="t", html_path=__file__, title="t", content_id="01X")

    assert mock_post.call_args[0][0].endswith("/api/content/01X/upload")


@patch("publish.requests.post")
def test_upload_raises_on_error_status(mock_post):
    mock_post.return_value = MagicMock(status_code=500, text="boom")

    with pytest.raises(RuntimeError, match="upload"):
        publish.upload_html(token="t", html_path=__file__, title="t", content_id=None)


@patch("publish.requests.post")
def test_notify_slack_sends_url_and_title(mock_post):
    mock_post.return_value = MagicMock(status_code=200)

    publish.notify_slack(
        webhook_url="https://hooks/x",
        title="週次ダイジェスト 2026-08-30",
        url="https://fs/view/01X",
        headlines=["記事A", "記事B"],
    )

    payload = mock_post.call_args.kwargs["json"]
    body = str(payload)
    assert "https://fs/view/01X" in body
    assert "週次ダイジェスト 2026-08-30" in body
    assert "記事A" in body


@patch("publish.notify_slack")
@patch("publish.upload_html")
@patch("publish.get_id_token")
def test_dry_run_sends_nothing(mock_token, mock_upload, mock_slack):
    """--dry-run は一切送信しない。"""
    rc = publish.run(
        html_path=__file__, title="t", content_id=None, slack=True,
        dry_run=True, webhook_url="https://hooks/x",
    )

    assert rc == 0
    mock_token.assert_not_called()
    mock_upload.assert_not_called()
    mock_slack.assert_not_called()


@patch("publish.notify_slack")
@patch("publish.upload_html")
@patch("publish.get_id_token")
def test_slack_not_called_when_upload_fails(mock_token, mock_upload, mock_slack):
    """アップロードが失敗したら Slack に通知しない（存在しない URL を流さない）。"""
    mock_token.return_value = "t"
    mock_upload.side_effect = RuntimeError("upload failed")

    rc = publish.run(
        html_path=__file__, title="t", content_id=None, slack=True,
        dry_run=False, webhook_url="https://hooks/x",
    )

    assert rc != 0
    mock_slack.assert_not_called()
