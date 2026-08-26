"""speakerdeck モジュール（Speaker Deck スライドPDFの書き起こし）のテスト。"""

import anthropic
from anthropic.types import TextBlock

from collector import speakerdeck
from collector.speakerdeck import (
    _extract_pdf_url,
    fetch_slide_text,
    is_speakerdeck_url,
)


def test_is_speakerdeck_url_true():
    assert is_speakerdeck_url("https://speakerdeck.com/twada/some-talk")


def test_is_speakerdeck_url_false_for_other_site():
    assert not is_speakerdeck_url("https://zenn.dev/user/articles/x")


def test_is_speakerdeck_url_false_for_files_host():
    # PDF 直リンク（files.speakerdeck.com/.../presentations/...）は記事URLではない
    assert not is_speakerdeck_url(
        "https://files.speakerdeck.com/presentations/abc/slide.pdf"
    )


def test_extract_pdf_url_found():
    html = (
        '<a href="https://files.speakerdeck.com/presentations/'
        'cdf6/pyramid-20241029.pdf">Download PDF</a>'
    )
    assert (
        _extract_pdf_url(html)
        == "https://files.speakerdeck.com/presentations/cdf6/pyramid-20241029.pdf"
    )


def test_extract_pdf_url_none():
    html = '<img src="https://files.speakerdeck.com/presentations/abc/slide_0.jpg">'
    assert _extract_pdf_url(html) is None


def _mock_text_message(text: str):
    msg = type("Msg", (), {})()
    msg.content = [TextBlock(type="text", text=text)]
    return msg


def test_fetch_slide_text_success(mocker):
    page = mocker.MagicMock()
    page.text = (
        '<a href="https://files.speakerdeck.com/presentations/abc/talk.pdf">PDF</a>'
    )
    page.raise_for_status.return_value = None
    pdf = mocker.MagicMock()
    pdf.content = b"%PDF-1.4 fake"
    pdf.raise_for_status.return_value = None
    mocker.patch("collector.speakerdeck.requests.get", side_effect=[page, pdf])

    mock_client = mocker.MagicMock()
    mock_client.messages.create.return_value = _mock_text_message(
        "- スライドの要点1\n- スライドの要点2"
    )
    mocker.patch("collector.speakerdeck.anthropic.Anthropic", return_value=mock_client)

    text, ok = fetch_slide_text("https://speakerdeck.com/u/talk", "key")
    assert ok is True
    assert "要点1" in text
    # PDF が document ブロックとして渡されている
    sent = mock_client.messages.create.call_args.kwargs["messages"][0]["content"]
    assert sent[0]["type"] == "document"
    assert sent[0]["source"]["media_type"] == "application/pdf"


def test_fetch_slide_text_no_pdf_is_skip(mocker):
    page = mocker.MagicMock()
    page.text = "<html>no pdf link here</html>"
    page.raise_for_status.return_value = None
    mocker.patch("collector.speakerdeck.requests.get", return_value=page)

    text, ok = fetch_slide_text("https://speakerdeck.com/u/talk", "key")
    assert text is None
    assert ok is True  # リトライ不要のスキップ


def test_fetch_slide_text_page_error_is_retriable(mocker):
    page = mocker.MagicMock()
    page.raise_for_status.side_effect = Exception("503")
    mocker.patch("collector.speakerdeck.requests.get", return_value=page)

    text, ok = fetch_slide_text("https://speakerdeck.com/u/talk", "key")
    assert text is None
    assert ok is False  # リトライ対象


def test_fetch_slide_text_pdf_too_large_is_skip(mocker):
    page = mocker.MagicMock()
    page.text = (
        '<a href="https://files.speakerdeck.com/presentations/abc/talk.pdf">PDF</a>'
    )
    page.raise_for_status.return_value = None
    pdf = mocker.MagicMock()
    pdf.content = b"x" * (speakerdeck._MAX_PDF_BYTES + 1)
    pdf.raise_for_status.return_value = None
    mocker.patch("collector.speakerdeck.requests.get", side_effect=[page, pdf])

    text, ok = fetch_slide_text("https://speakerdeck.com/u/talk", "key")
    assert text is None
    assert ok is True


def test_fetch_slide_text_api_400_is_skip(mocker):
    page = mocker.MagicMock()
    page.text = (
        '<a href="https://files.speakerdeck.com/presentations/abc/talk.pdf">PDF</a>'
    )
    page.raise_for_status.return_value = None
    pdf = mocker.MagicMock()
    pdf.content = b"%PDF fake"
    pdf.raise_for_status.return_value = None
    mocker.patch("collector.speakerdeck.requests.get", side_effect=[page, pdf])

    err = anthropic.APIStatusError(
        "bad request",
        response=mocker.MagicMock(status_code=400),
        body=None,
    )
    mock_client = mocker.MagicMock()
    mock_client.messages.create.side_effect = err
    mocker.patch("collector.speakerdeck.anthropic.Anthropic", return_value=mock_client)

    text, ok = fetch_slide_text("https://speakerdeck.com/u/talk", "key")
    assert text is None
    assert ok is True  # 400 はリトライ不要


def test_model_id_has_no_date_suffix():
    """モデルIDは日付サフィックスなしの正規形を使う。"""
    from collector.speakerdeck import _MODEL

    assert _MODEL == "claude-haiku-4-5"
