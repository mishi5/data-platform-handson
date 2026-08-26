from unittest.mock import MagicMock, patch

from anthropic.types import TextBlock, ThinkingBlock

from collector.deepdiver import deepdive_article
from tests.sdk_signature import assert_matches_sdk_signature


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
    assert call_kwargs["model"] == "claude-sonnet-5"
    # Sonnet 5 は thinking が既定で走るぶん出力枠を食う。1024 では本文が切れる
    assert call_kwargs["max_tokens"] == 4096
    assert call_kwargs["thinking"] == {"type": "adaptive"}
    assert_matches_sdk_signature(call_kwargs)


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


@patch("collector.deepdiver.anthropic.Anthropic")
def test_deepdive_article_skips_thinking_block(mock_anthropic_class):
    """thinking ブロックが先頭に来ても本文（TextBlock）を取り出す。

    Sonnet 5 は adaptive thinking が既定で走るため content[0] が thinking に
    なりうる。content[0] 決め打ちだと常に None を返して機能停止する。
    """
    mock_client = MagicMock()
    mock_anthropic_class.return_value = mock_client

    thinking = MagicMock(spec=ThinkingBlock)
    text = MagicMock(spec=TextBlock, text="📌 背景・概要\n分析本文")
    mock_client.messages.create.return_value.content = [thinking, text]

    result = deepdive_article(title="T", content="C", api_key="k")

    assert result == "📌 背景・概要\n分析本文"


@patch("collector.deepdiver.anthropic.Anthropic")
def test_deepdive_article_returns_none_without_text_block(mock_anthropic_class):
    """TextBlock が1つも無ければ None（thinking だけで打ち切られた場合など）。"""
    mock_client = MagicMock()
    mock_anthropic_class.return_value = mock_client
    mock_client.messages.create.return_value.content = [MagicMock(spec=ThinkingBlock)]

    assert deepdive_article(title="T", content="C", api_key="k") is None
