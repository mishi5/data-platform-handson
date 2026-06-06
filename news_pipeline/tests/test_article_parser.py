from collector.article_parser import fetch_content


def test_fetch_content_returns_text_and_ok(mocker):
    mock_resp = mocker.MagicMock()
    mock_resp.text = "<html><body><p>BigQuery is great.</p></body></html>"
    mock_resp.raise_for_status.return_value = None
    mocker.patch("collector.article_parser.requests.get", return_value=mock_resp)
    mocker.patch(
        "collector.article_parser.trafilatura.extract",
        return_value="BigQuery is great.",
    )

    text, ok = fetch_content("https://example.com/article")
    assert text == "BigQuery is great."
    assert ok is True


def test_fetch_content_http_error_returns_none_false(mocker):
    mock_resp = mocker.MagicMock()
    mock_resp.raise_for_status.side_effect = Exception("403 Forbidden")
    mocker.patch("collector.article_parser.requests.get", return_value=mock_resp)

    text, ok = fetch_content("https://example.com/article")
    assert text is None
    assert ok is False


def test_fetch_content_extract_none_is_ok(mocker):
    mock_resp = mocker.MagicMock()
    mock_resp.text = "<html></html>"
    mock_resp.raise_for_status.return_value = None
    mocker.patch("collector.article_parser.requests.get", return_value=mock_resp)
    mocker.patch("collector.article_parser.trafilatura.extract", return_value=None)

    text, ok = fetch_content("https://example.com/article")
    assert text is None
    assert ok is True


def test_fetch_content_sends_user_agent(mocker):
    mock_resp = mocker.MagicMock()
    mock_resp.text = "<html></html>"
    mock_resp.raise_for_status.return_value = None
    mock_get = mocker.patch(
        "collector.article_parser.requests.get", return_value=mock_resp
    )
    mocker.patch("collector.article_parser.trafilatura.extract", return_value="x")

    fetch_content("https://example.com/article")
    headers = mock_get.call_args.kwargs["headers"]
    assert "User-Agent" in headers
    assert "Mozilla" in headers["User-Agent"]
