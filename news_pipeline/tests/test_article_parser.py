from unittest.mock import patch
from collector.article_parser import fetch_content


def test_fetch_content_returns_text(mocker):
    mocker.patch(
        "collector.article_parser.trafilatura.fetch_url",
        return_value="<html><body><p>BigQuery is great.</p></body></html>",
    )
    mocker.patch(
        "collector.article_parser.trafilatura.extract",
        return_value="BigQuery is great.",
    )

    result = fetch_content("https://example.com/article")
    assert result == "BigQuery is great."


def test_fetch_content_returns_none_on_failure(mocker):
    mocker.patch(
        "collector.article_parser.trafilatura.fetch_url",
        return_value=None,
    )

    result = fetch_content("https://example.com/article")
    assert result is None


def test_fetch_content_handles_exception(mocker):
    mocker.patch(
        "collector.article_parser.trafilatura.fetch_url",
        side_effect=Exception("timeout"),
    )

    result = fetch_content("https://example.com/article")
    assert result is None
