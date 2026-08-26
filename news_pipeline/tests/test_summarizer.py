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
def test_summarize_article_normalizes_tags(mock_anthropic_class):
    """タグは小文字化・アンダースコア→スペース・トリム・重複排除して返す。"""
    _mock_tool_response(
        mock_anthropic_class,
        {
            "summary": "- x",
            "tags": ["Data_Governance", " dbt ", "dbt", "BigQuery"],
            "importance_score": 0.5,
        },
    )

    result = summarize_article(title="T", content="C", api_key="key")
    assert result["tags"] == ["data governance", "dbt", "bigquery"]


@patch("collector.summarizer.anthropic.Anthropic")
def test_summarize_prompt_instructs_english_tags(mock_anthropic_class):
    """システムプロンプトとツール定義で英語タグを指示する。"""
    mock_client = _mock_tool_response(
        mock_anthropic_class,
        {"summary": "- x", "tags": [], "importance_score": 0.5},
    )

    summarize_article(title="T", content="C", api_key="key")

    kwargs = mock_client.messages.create.call_args.kwargs
    assert "英語" in kwargs["system"]
    tags_desc = kwargs["tools"][0]["input_schema"]["properties"]["tags"]["description"]
    assert "英語" in tags_desc


@patch("collector.summarizer.anthropic.Anthropic")
def test_summarize_article_joins_list_summary(mock_anthropic_class):
    _mock_tool_response(
        mock_anthropic_class,
        {"summary": ["- A", "- B"], "tags": [], "importance_score": 0.5},
    )

    result = summarize_article(title="T", content="C", api_key="key")
    assert result["summary"] == "- A\n- B"


@patch("collector.summarizer.anthropic.Anthropic")
def test_summarize_article_unescapes_literal_newlines(mock_anthropic_class):
    """モデルが二重エスケープしたリテラル \\n は実改行に直して保存する。"""
    _mock_tool_response(
        mock_anthropic_class,
        {
            "summary": "- A\\n- B\\n- C",
            "tags": [],
            "importance_score": 0.5,
        },
    )

    result = summarize_article(title="T", content="C", api_key="key")
    assert result["summary"] == "- A\n- B\n- C"


@patch("collector.summarizer.anthropic.Anthropic")
def test_summarize_article_unescapes_literal_newline_after_real_newline(
    mock_anthropic_class,
):
    """実際に混入したパターン（実改行の直後にリテラル \\n）も解消する。"""
    _mock_tool_response(
        mock_anthropic_class,
        {"summary": "- A\n\\n- B", "tags": [], "importance_score": 0.5},
    )

    result = summarize_article(title="T", content="C", api_key="key")
    assert result["summary"] == "- A\n\n- B"
    assert "\\n" not in result["summary"]


@patch("collector.summarizer.anthropic.Anthropic")
def test_summarize_article_keeps_quoted_literal_newline(mock_anthropic_class):
    """記事が改行文字そのものを扱う場合（クォート/カッコ囲み）は置換しない。"""
    _mock_tool_response(
        mock_anthropic_class,
        {
            "summary": "- 区切り文字は '\\n' を使う\n- 「\\n」でも同じ\n- `\\n` と (\\n) も保持",
            "tags": [],
            "importance_score": 0.5,
        },
    )

    result = summarize_article(title="T", content="C", api_key="key")
    assert result["summary"] == (
        "- 区切り文字は '\\n' を使う\n- 「\\n」でも同じ\n- `\\n` と (\\n) も保持"
    )


@patch("collector.summarizer.anthropic.Anthropic")
def test_summarize_article_unescape_applies_after_list_join(mock_anthropic_class):
    """summary が配列で返ってきた場合も各要素のリテラル \\n を解消する。"""
    _mock_tool_response(
        mock_anthropic_class,
        {"summary": ["- A\\n- B", "- C"], "tags": [], "importance_score": 0.5},
    )

    result = summarize_article(title="T", content="C", api_key="key")
    assert result["summary"] == "- A\n- B\n- C"


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
def test_score_article_returns_both_scores(mock_anthropic_class):
    """再採点は importance と relevance の両方を返す（relevance を保存経路に通すため）。"""
    mock_client = _mock_tool_response(
        mock_anthropic_class, {"importance_score": 0.72, "relevance_score": 0.9}
    )

    result = score_article(title="T", content="C", api_key="k", keywords=["BigQuery"])
    assert result["importance_score"] == 0.72
    assert result["relevance_score"] == 0.9

    call_kwargs = mock_client.messages.create.call_args.kwargs
    assert call_kwargs["temperature"] == 0
    assert call_kwargs["tool_choice"]["name"] == "record_score"


@patch("collector.summarizer.anthropic.Anthropic")
def test_score_article_relevance_none_when_absent(mock_anthropic_class):
    """relevance が欠けても importance だけで返す（判定不能は呼び出し側で通す）。"""
    _mock_tool_response(mock_anthropic_class, {"importance_score": 0.72})

    result = score_article(title="T", content="C", api_key="k")
    assert result["importance_score"] == 0.72
    assert result["relevance_score"] is None


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


def test_scoring_version_is_3():
    from collector.summarizer import SCORING_VERSION

    assert SCORING_VERSION == 3


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


# --- relevance 軸（データ基盤との関連度）------------------------------------


@patch("collector.summarizer.anthropic.Anthropic")
def test_summarize_article_returns_relevance_score(mock_anthropic_class):
    """要約時に relevance_score（データ基盤との関連度）も受け取る。"""
    _mock_tool_response(
        mock_anthropic_class,
        {
            "summary": "- x",
            "tags": ["dbt"],
            "importance_score": 0.8,
            "relevance_score": 0.9,
        },
    )

    result = summarize_article(title="T", content="C", api_key="key")
    assert result["relevance_score"] == 0.9


@patch("collector.summarizer.anthropic.Anthropic")
def test_summarize_article_keeps_importance_unmodified(mock_anthropic_class):
    """relevance が低くても importance は加工しない（キャップせずゲートで判定する）。"""
    _mock_tool_response(
        mock_anthropic_class,
        {
            "summary": "- x",
            "tags": [],
            "importance_score": 0.82,
            "relevance_score": 0.1,
        },
    )

    result = summarize_article(title="T", content="C", api_key="key")
    assert result["importance_score"] == 0.82


@patch("collector.summarizer.anthropic.Anthropic")
def test_summarize_article_relevance_none_when_absent(mock_anthropic_class):
    """モデルが relevance を返さない場合は None（呼び出し側で通す＝取りこぼし防止）。"""
    _mock_tool_response(
        mock_anthropic_class,
        {"summary": "- x", "tags": [], "importance_score": 0.8},
    )

    result = summarize_article(title="T", content="C", api_key="key")
    assert result["relevance_score"] is None


def test_summary_tool_requires_relevance_score():
    from collector.summarizer import _SCORE_TOOL, _SUMMARY_TOOL

    for tool in (_SUMMARY_TOOL, _SCORE_TOOL):
        assert "relevance_score" in tool["input_schema"]["properties"]
        assert "relevance_score" in tool["input_schema"]["required"]


# --- ドメイン定義（対象スコープ）--------------------------------------------


def test_domain_definition_lists_target_and_excluded_topics():
    from collector.summarizer import _build_domain_definition

    d = _build_domain_definition()
    # 対象ドメイン
    assert "dbt" in d
    assert "データ品質" in d
    # 対象外ドメイン
    assert "ネットワーク運用" in d
    # 判定原理: 技法ではなく「適用対象」で判断する
    assert "適用対象" in d


def test_scoring_criteria_includes_domain_definition():
    c = _build_scoring_criteria(["BigQuery"])
    assert "適用対象" in c
    assert "スコアの目安" in c


def test_relevance_criteria_omits_importance_guidance():
    """プレフィルタ用の基準には importance の目安を混ぜない（2つのスコア定義の混線防止）。"""
    from collector.summarizer import _build_relevance_criteria

    c = _build_relevance_criteria(["BigQuery"])
    assert "適用対象" in c
    assert "importance_score" not in c
    assert "スコアの目安" not in c
    assert "BigQuery" in c


@patch("collector.summarizer.anthropic.Anthropic")
def test_score_slide_relevance_prompt_omits_importance_guidance(mock_anthropic_class):
    from collector.summarizer import score_slide_relevance

    mock_client = _mock_tool_response(mock_anthropic_class, {"relevance_score": 0.8})
    score_slide_relevance("Title", "desc", "key", keywords=["dbt"])

    system_prompt = mock_client.messages.create.call_args.kwargs["system"]
    assert "適用対象" in system_prompt
    assert "importance_score" not in system_prompt
