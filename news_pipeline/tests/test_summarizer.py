from unittest.mock import MagicMock, patch
from anthropic.types import ToolUseBlock
from collector.summarizer import (
    summarize_article,
    score_article,
    _build_system_prompt,
    _build_scoring_criteria,
)


def _mock_tool_response(mock_anthropic_class, tool_input: dict) -> MagicMock:
    """tool_use ブロックを1つ返す messages.create のモックを組み立てる。"""
    mock_client = MagicMock()
    mock_anthropic_class.return_value = mock_client
    block = MagicMock(spec=ToolUseBlock)
    block.input = tool_input
    mock_client.messages.create.return_value.content = [block]
    return mock_client


@patch("collector.summarizer.anthropic.Anthropic")
def test_summarize_article_returns_dict(mock_anthropic_class):
    mock_client = _mock_tool_response(
        mock_anthropic_class,
        {
            "summary": "- BigQuery added new feature\n- Improves performance",
            "tags": ["bigquery", "performance"],
            "importance_score": 0.85,
        },
    )

    result = summarize_article(
        title="BigQuery update",
        content="BigQuery announced...",
        api_key="test-key",
        keywords=["BigQuery", "データエンジニアリング"],
    )

    assert result["summary"] == "- BigQuery added new feature\n- Improves performance"
    assert "bigquery" in result["tags"]
    assert result["importance_score"] == 0.85

    # tool use を強制し temperature=0 で呼び出す（structured output・採点の一貫性）
    call_kwargs = mock_client.messages.create.call_args.kwargs
    assert call_kwargs["temperature"] == 0
    assert call_kwargs["tool_choice"]["type"] == "tool"
    assert call_kwargs["tool_choice"]["name"] == "record_summary"


@patch("collector.summarizer.anthropic.Anthropic")
def test_summarize_article_joins_list_summary(mock_anthropic_class):
    _mock_tool_response(
        mock_anthropic_class,
        {"summary": ["- A", "- B"], "tags": [], "importance_score": 0.5},
    )

    result = summarize_article(title="T", content="C", api_key="key")
    assert result["summary"] == "- A\n- B"


@patch("collector.summarizer.anthropic.Anthropic")
def test_summarize_article_returns_none_on_api_error(mock_anthropic_class):
    mock_client = MagicMock()
    mock_anthropic_class.return_value = mock_client
    mock_client.messages.create.side_effect = Exception("API error")

    result = summarize_article(title="T", content="C", api_key="key")
    assert result is None


@patch("collector.summarizer.anthropic.Anthropic")
def test_summarize_article_returns_none_without_tool_block(mock_anthropic_class):
    mock_client = MagicMock()
    mock_anthropic_class.return_value = mock_client
    mock_client.messages.create.return_value.content = []

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
    mock_client = _mock_tool_response(mock_anthropic_class, {"importance_score": 0.72})

    score = score_article(title="T", content="C", api_key="k", keywords=["BigQuery"])
    assert score == 0.72

    call_kwargs = mock_client.messages.create.call_args.kwargs
    assert call_kwargs["temperature"] == 0
    assert call_kwargs["tool_choice"]["name"] == "record_score"


@patch("collector.summarizer.anthropic.Anthropic")
def test_score_article_returns_none_on_error(mock_anthropic_class):
    mock_client = MagicMock()
    mock_anthropic_class.return_value = mock_client
    mock_client.messages.create.side_effect = Exception("API error")

    assert score_article(title="T", content="C", api_key="k") is None


def test_build_scoring_criteria_includes_favorite_tags():
    c = _build_scoring_criteria(["BigQuery"], favorite_tags=["dbt", "airflow"])
    assert "お気に入り" in c
    assert "dbt" in c
    assert "airflow" in c


def test_build_scoring_criteria_without_favorite_tags_unchanged():
    """favorite_tags が空/None なら既存の基準と完全に同一（パーソナライズなし）。"""
    base = _build_scoring_criteria(["BigQuery"])
    assert _build_scoring_criteria(["BigQuery"], favorite_tags=[]) == base
    assert _build_scoring_criteria(["BigQuery"], favorite_tags=None) == base
    assert "お気に入り" not in base


@patch("collector.summarizer.anthropic.Anthropic")
def test_summarize_article_passes_favorite_tags_to_prompt(mock_anthropic_class):
    mock_client = _mock_tool_response(
        mock_anthropic_class,
        {"summary": "- x", "tags": [], "importance_score": 0.5},
    )

    summarize_article(
        title="T",
        content="C",
        api_key="key",
        keywords=["BigQuery"],
        favorite_tags=["dbt"],
    )

    system_prompt = mock_client.messages.create.call_args.kwargs["system"]
    assert "お気に入り" in system_prompt
    assert "dbt" in system_prompt


def test_build_scoring_criteria_uses_de_value_axis():
    c = _build_scoring_criteria(["BigQuery"])
    # DE価値ベースの主軸とアンカーが含まれる
    assert "読む価値" in c
    assert "スコアの目安" in c
    # 高/低スコア軸の語
    assert "実務" in c
    assert "宣伝" in c


def test_scoring_version_is_2():
    from collector.summarizer import SCORING_VERSION

    assert SCORING_VERSION == 2


@patch("collector.summarizer.anthropic.Anthropic")
def test_score_slide_relevance_returns_float(mock_anthropic_class):
    from collector.summarizer import score_slide_relevance

    mock_client = _mock_tool_response(mock_anthropic_class, {"relevance_score": 0.8})

    score = score_slide_relevance("Title", "desc", "key", keywords=["dbt"])
    assert score == 0.8

    call_kwargs = mock_client.messages.create.call_args.kwargs
    assert call_kwargs["tool_choice"]["name"] == "record_relevance"


@patch("collector.summarizer.anthropic.Anthropic")
def test_score_slide_relevance_failure_returns_none(mock_anthropic_class):
    from collector.summarizer import score_slide_relevance

    mock_client = MagicMock()
    mock_anthropic_class.return_value = mock_client
    mock_client.messages.create.side_effect = Exception("boom")

    assert score_slide_relevance("Title", "desc", "key") is None
