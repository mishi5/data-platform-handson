from unittest.mock import MagicMock, patch

from anthropic.types import TextBlock

from collector.deepdiver import deepdive_article


@patch("collector.deepdiver.anthropic.Anthropic")
def test_deepdive_article_returns_markdown(mock_anthropic_class):
    mock_client = MagicMock()
    mock_anthropic_class.return_value = mock_client

    mock_block = MagicMock(spec=TextBlock, text="📌 背景・概要\nBigQueryの新機能が発表された。\n\n🔍 技術的なポイント\n• 高速化")
    mock_client.messages.create.return_value.content = [mock_block]

    result = deepdive_article(
        title="BigQuery update",
        content="BigQuery announced new features...",
        api_key="test-key",
    )

    assert result is not None
    assert isinstance(result, str)
    assert len(result) > 0
    call_kwargs = mock_client.messages.create.call_args.kwargs
    assert call_kwargs["model"] == "claude-sonnet-4-6"
    assert call_kwargs["max_tokens"] == 1024


@patch("collector.deepdiver.anthropic.Anthropic")
def test_deepdive_article_returns_none_on_error(mock_anthropic_class):
    mock_client = MagicMock()
    mock_anthropic_class.return_value = mock_client
    mock_client.messages.create.side_effect = Exception("API error")

    result = deepdive_article(title="title", content="body", api_key="test-key")

    assert result is None


@patch("collector.deepdiver.anthropic.Anthropic")
def test_deepdive_article_truncates_long_content(mock_anthropic_class):
    mock_client = MagicMock()
    mock_anthropic_class.return_value = mock_client

    mock_block = MagicMock(spec=TextBlock, text="深堀り結果")
    mock_client.messages.create.return_value.content = [mock_block]

    long_content = "x" * 10000
    deepdive_article(title="title", content=long_content, api_key="test-key")

    call_kwargs = mock_client.messages.create.call_args.kwargs
    user_msg = call_kwargs["messages"][0]["content"]
    assert len(user_msg) < 10000 + 200  # 本文が切り詰められていること
