import json
from unittest.mock import MagicMock, patch
from anthropic.types import TextBlock
from collector.summarizer import (
    summarize_article,
    score_article,
    _build_system_prompt,
    _build_scoring_criteria,
)


@patch("collector.summarizer.anthropic.Anthropic")
def test_summarize_article_returns_dict(mock_anthropic_class):
    mock_client = MagicMock()
    mock_anthropic_class.return_value = mock_client

    response_text = json.dumps(
        {
            "summary": "- BigQuery added new feature\n- Improves performance",
            "tags": ["bigquery", "performance"],
            "importance_score": 0.85,
        }
    )
    mock_client.messages.create.return_value.content = [
        MagicMock(spec=TextBlock, text=response_text)
    ]

    result = summarize_article(
        title="BigQuery update",
        content="BigQuery announced...",
        api_key="test-key",
        keywords=["BigQuery", "データエンジニアリング"],
    )

    assert result["summary"] == "- BigQuery added new feature\n- Improves performance"
    assert "bigquery" in result["tags"]
    assert result["importance_score"] == 0.85


@patch("collector.summarizer.anthropic.Anthropic")
def test_summarize_article_returns_none_on_api_error(mock_anthropic_class):
    mock_client = MagicMock()
    mock_anthropic_class.return_value = mock_client
    mock_client.messages.create.side_effect = Exception("API error")

    result = summarize_article(title="T", content="C", api_key="key")
    assert result is None


def test_build_system_prompt_includes_keywords():
    prompt = _build_system_prompt(["BigQuery", "dbt", "Spark"])
    assert "BigQuery" in prompt
    assert "dbt" in prompt
    assert "Spark" in prompt


def test_build_system_prompt_no_keywords():
    prompt = _build_system_prompt([])
    assert "キーワード未設定" in prompt


def test_build_scoring_criteria_includes_keywords():
    c = _build_scoring_criteria(["BigQuery", "dbt"])
    assert "BigQuery" in c
    assert "dbt" in c


def test_build_scoring_criteria_no_keywords():
    c = _build_scoring_criteria([])
    assert "キーワード未設定" in c


@patch("collector.summarizer.anthropic.Anthropic")
def test_score_article_returns_float(mock_anthropic_class):
    mock_client = MagicMock()
    mock_anthropic_class.return_value = mock_client
    response_text = json.dumps({"importance_score": 0.72})
    mock_client.messages.create.return_value.content = [
        MagicMock(spec=TextBlock, text=response_text)
    ]

    score = score_article(title="T", content="C", api_key="k", keywords=["BigQuery"])
    assert score == 0.72


@patch("collector.summarizer.anthropic.Anthropic")
def test_score_article_strips_code_fence(mock_anthropic_class):
    mock_client = MagicMock()
    mock_anthropic_class.return_value = mock_client
    response_text = '```json\n{"importance_score": 0.4}\n```'
    mock_client.messages.create.return_value.content = [
        MagicMock(spec=TextBlock, text=response_text)
    ]

    score = score_article(title="T", content="C", api_key="k")
    assert score == 0.4


@patch("collector.summarizer.anthropic.Anthropic")
def test_score_article_returns_none_on_error(mock_anthropic_class):
    mock_client = MagicMock()
    mock_anthropic_class.return_value = mock_client
    mock_client.messages.create.side_effect = Exception("API error")

    assert score_article(title="T", content="C", api_key="k") is None
