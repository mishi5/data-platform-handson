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
@patch("publish.find_content_by_title")
@patch("publish.get_id_token")
def test_dry_run_sends_nothing(mock_token, mock_find, mock_upload, mock_slack):
    """--dry-run は書き込みを一切しない。

    公開済み一覧の照合（GET）だけは本番と同じに通す。本番で止まる条件を
    dry-run でも検出するため。POST しないことは test_dry_run_never_posts で見る。
    """
    mock_token.return_value = "t"
    mock_find.return_value = None

    rc = publish.run(
        html_path=__file__, title="t", content_id=None, slack=True,
        dry_run=True, webhook_url="https://hooks/x",
    )

    assert rc == 0
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


# --- Slack ペイロードの妥当性 -------------------------------------------


def test_slack_payload_omits_headline_block_when_empty():
    """空文字の section は Slack が invalid_blocks で弾く（アップロード後に失敗する）。"""
    payload = publish.build_slack_payload(title="t", url="https://fs/view/1", headlines=[])

    for block in payload["blocks"]:
        assert block["text"]["text"].strip() != ""
    assert len(payload["blocks"]) == 1


def test_slack_payload_truncates_long_section_text():
    """section の mrkdwn は 3000 文字上限。超えると 400 で通知が落ちる。"""
    payload = publish.build_slack_payload(
        title="t", url="https://fs/view/1", headlines=["あ" * 500] * 20
    )

    for block in payload["blocks"]:
        assert len(block["text"]["text"]) <= publish.SLACK_SECTION_LIMIT


def test_slack_payload_escapes_mrkdwn_specials():
    """`<` `>` `&` を素通しすると Slack のリンク記法を壊す。"""
    payload = publish.build_slack_payload(
        title="A <b> & C", url="https://fs/view/1", headlines=["x > y"]
    )

    body = "".join(b["text"]["text"] for b in payload["blocks"])
    assert "A &lt;b&gt; &amp; C" in body
    assert "x &gt; y" in body
    # 自分で組み立てたリンクは壊さない
    assert "<https://fs/view/1|" in body


# --- 取り返しのつかない操作の手前で止める -------------------------------


@patch("publish.notify_slack")
@patch("publish.upload_html")
@patch("publish.find_content_by_title")
@patch("publish.get_id_token")
def test_missing_webhook_aborts_before_upload(mock_token, mock_find, mock_upload, mock_slack):
    """--slack なのに webhook が無いなら、上げる前に止める。

    上げてから気づくと、消せない資料が残ったうえ通知だけ落ちる。
    """
    mock_token.return_value = "t"
    mock_find.return_value = None

    rc = publish.run(
        html_path=__file__, title="t", content_id=None, slack=True,
        dry_run=False, webhook_url=None,
    )

    assert rc != 0
    mock_upload.assert_not_called()


@patch("publish.notify_slack")
@patch("publish.upload_html")
@patch("publish.find_content_by_title")
@patch("publish.get_id_token")
def test_duplicate_title_aborts_new_upload(mock_token, mock_find, mock_upload, mock_slack):
    """同じタイトルが既にあるなら新規アップロードしない（削除は Web UI からしかできない）。"""
    mock_token.return_value = "t"
    mock_find.return_value = {"id": "01OLD", "url": "https://fs/view/01OLD"}

    rc = publish.run(
        html_path=__file__, title="週次ダイジェスト 2026-08-30", content_id=None,
        slack=False, dry_run=False, webhook_url=None,
    )

    assert rc != 0
    mock_upload.assert_not_called()


@patch("publish.notify_slack")
@patch("publish.upload_html")
@patch("publish.find_content_by_title")
@patch("publish.get_id_token")
def test_duplicate_title_message_shows_the_content_id_to_reuse(
    mock_token, mock_find, mock_upload, mock_slack, capsys
):
    """2回目以降に必要な --content-id を、その場で分かるように出す。"""
    mock_token.return_value = "t"
    mock_find.return_value = {"id": "01OLD", "url": "https://fs/view/01OLD"}

    publish.run(
        html_path=__file__, title="t", content_id=None, slack=False,
        dry_run=False, webhook_url=None,
    )

    out = capsys.readouterr()
    assert "01OLD" in out.out + out.err
    assert "--content-id" in out.out + out.err


@patch("publish.notify_slack")
@patch("publish.upload_html")
@patch("publish.find_content_by_title")
@patch("publish.get_id_token")
def test_force_new_allows_duplicate_title(mock_token, mock_find, mock_upload, mock_slack):
    """意図的な2本目は --force-new で通す。"""
    mock_token.return_value = "t"
    mock_find.return_value = {"id": "01OLD", "url": "https://fs/view/01OLD"}
    mock_upload.return_value = {"id": "01NEW", "url": "https://fs/view/01NEW"}

    rc = publish.run(
        html_path=__file__, title="t", content_id=None, slack=False,
        dry_run=False, webhook_url=None, force_new=True,
    )

    assert rc == 0
    mock_upload.assert_called_once()


@patch("publish.notify_slack")
@patch("publish.upload_html")
@patch("publish.find_content_by_title")
@patch("publish.get_id_token")
def test_overwrite_skips_the_title_collision_check(mock_token, mock_find, mock_upload, mock_slack):
    """--content-id は上書きなので、同名があって当然。"""
    mock_token.return_value = "t"
    mock_upload.return_value = {"id": "01X", "url": "https://fs/view/01X"}

    rc = publish.run(
        html_path=__file__, title="t", content_id="01X", slack=False,
        dry_run=False, webhook_url=None,
    )

    assert rc == 0
    mock_find.assert_not_called()


# --- dry-run の網羅性 ---------------------------------------------------


@patch("publish.find_content_by_title")
@patch("publish.get_id_token")
def test_dry_run_reports_duplicate_title(mock_token, mock_find, capsys):
    """本番で止まる条件は dry-run でも分かること（そのための dry-run）。"""
    mock_token.return_value = "t"
    mock_find.return_value = {"id": "01OLD", "url": "https://fs/view/01OLD"}

    rc = publish.run(
        html_path=__file__, title="t", content_id=None, slack=False,
        dry_run=True, webhook_url=None,
    )

    captured = capsys.readouterr()
    assert rc != 0
    assert "01OLD" in captured.out + captured.err


@patch("publish.find_content_by_title")
@patch("publish.get_id_token")
def test_dry_run_reports_missing_webhook(mock_token, mock_find, capsys):
    mock_token.return_value = "t"
    mock_find.return_value = None

    rc = publish.run(
        html_path=__file__, title="t", content_id=None, slack=True,
        dry_run=True, webhook_url=None,
    )

    assert rc != 0
    assert "SLACK_WEBHOOK_URL" in capsys.readouterr().err


@patch("publish.find_content_by_title")
@patch("publish.get_id_token")
def test_dry_run_shows_the_slack_text(mock_token, mock_find, capsys):
    """通知文は送る前に読めること。"""
    mock_token.return_value = "t"
    mock_find.return_value = None

    publish.run(
        html_path=__file__, title="週次ダイジェスト", content_id=None, slack=True,
        dry_run=True, webhook_url="https://hooks/x", headlines=["記事A"],
    )

    assert "記事A" in capsys.readouterr().out


@patch("publish.requests.post")
@patch("publish.find_content_by_title")
@patch("publish.get_id_token")
def test_dry_run_never_posts(mock_token, mock_find, mock_post):
    """一覧の照合は GET のみ。POST は一切しない。"""
    mock_token.return_value = "t"
    mock_find.return_value = None

    publish.run(
        html_path=__file__, title="t", content_id=None, slack=True,
        dry_run=True, webhook_url="https://hooks/x",
    )

    mock_post.assert_not_called()


# --- アップロード応答の扱い ---------------------------------------------


@patch("publish.requests.post")
def test_upload_raises_when_response_has_no_url(mock_post):
    """URL が無いのに成功扱いすると、空リンクを Slack に流す。"""
    mock_post.return_value = MagicMock(status_code=201, json=lambda: {"id": "01X"})

    with pytest.raises(RuntimeError, match="url"):
        publish.upload_html(token="t", html_path=__file__, title="t", content_id=None)


@patch("publish.requests.post")
def test_upload_raises_on_non_json_response(mock_post):
    """IAP が HTML のログイン画面を返すことがある。JSON 前提で落とさない。"""
    resp = MagicMock(status_code=200, text="<html>login</html>")
    resp.json.side_effect = ValueError("no json")
    mock_post.return_value = resp

    with pytest.raises(RuntimeError):
        publish.upload_html(token="t", html_path=__file__, title="t", content_id=None)


def test_empty_file_is_rejected(tmp_path):
    """0バイトの資料を上げても消せない。"""
    empty = tmp_path / "empty.html"
    empty.write_text("")

    rc = publish.run(
        html_path=str(empty), title="t", content_id=None, slack=False,
        dry_run=True, webhook_url=None,
    )

    assert rc != 0


def test_oversized_file_is_rejected_before_upload(tmp_path):
    """family-share の上限は 30MB。413 を食う前に止める。"""
    big = tmp_path / "big.html"
    big.write_bytes(b"x" * (publish.MAX_UPLOAD_BYTES + 1))

    rc = publish.run(
        html_path=str(big), title="t", content_id=None, slack=False,
        dry_run=True, webhook_url=None,
    )

    assert rc != 0


# --- 一覧の照合 ---------------------------------------------------------


@patch("publish.requests.get")
def test_find_content_by_title_matches_exactly(mock_get):
    mock_get.return_value = MagicMock(
        status_code=200,
        json=lambda: {
            "items": [
                {"id": "01A", "title": "週次ダイジェスト 2026-08-23"},
                {"id": "01B", "title": "週次ダイジェスト 2026-08-30"},
            ]
        },
    )

    hit = publish.find_content_by_title(token="t", title="週次ダイジェスト 2026-08-30")

    assert hit["id"] == "01B"
    assert publish.find_content_by_title(token="t", title="無い") is None
