"""scripts/digest/fetch_articles.py のテスト。"""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts", "digest"))

import fetch_articles as fa


def test_period_week_is_seven_days():
    assert fa.resolve_days(period="week", days=None) == 7


def test_period_month_is_thirty_days():
    assert fa.resolve_days(period="month", days=None) == 30


def test_explicit_days_overrides_period():
    """--days は --period より優先する。"""
    assert fa.resolve_days(period="week", days=14) == 14


def test_list_query_applies_gate_and_period():
    q = fa.build_list_query(project="p", days=7, min_importance=0.65, min_relevance=0.55)
    assert "INTERVAL 7 DAY" in q
    assert "importance_score >= 0.65" in q
    # relevance が NULL の旧データは落とさない（本番のゲートと同じ規則）
    assert "relevance_score IS NULL" in q
    assert "relevance_score >= 0.55" in q
    # 一覧モードでは本文を返さない（42件分の本文は巨大になる）
    assert "r.content" not in q


def test_list_query_dedupes_by_article_id():
    """summaries・raw_articles の重複行で記事が増幅しないこと。"""
    q = fa.build_list_query(project="p", days=7, min_importance=0.65, min_relevance=0.55)
    assert "GROUP BY" in q


def test_content_query_includes_body_and_filters_ids():
    q, params = fa.build_content_query(project="p", article_ids=["a1", "a2"])
    assert "content" in q
    assert params[0].values == ["a1", "a2"]


def test_content_query_rejects_empty_ids():
    with pytest.raises(ValueError):
        fa.build_content_query(project="p", article_ids=[])


@patch("fetch_articles.bigquery.Client")
def test_fetch_returns_rows_as_dicts(mock_client_class):
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    row = {"article_id": "a1", "title": "T", "importance_score": 0.8}
    mock_client.query.return_value.result.return_value = [row]

    result = fa.run_query(project="p", query="SELECT 1", params=None)

    assert result == [{"article_id": "a1", "title": "T", "importance_score": 0.8}]
