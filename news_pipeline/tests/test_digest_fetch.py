"""scripts/digest/fetch_articles.py のテスト。"""

import os
import sys
from datetime import date
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


def test_list_query_dedupes_both_sides_of_the_join():
    """summaries・raw_articles の重複行で記事が増幅しないこと。

    片側だけ畳んでも JOIN で増幅するので、両側が1行に絞られていること。
    """
    q = fa.build_list_query(project="p", days=7, min_importance=0.65, min_relevance=0.55)
    assert q.count("PARTITION BY article_id") == 2
    assert q.count("WHERE _rn = 1") == 2


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


# --- 期間の境界 ---------------------------------------------------------


def test_days_must_be_positive():
    """0日や負の日数は窓が空/未来になるだけなので弾く。"""
    with pytest.raises(ValueError):
        fa.resolve_days(period="week", days=0)
    with pytest.raises(ValueError):
        fa.resolve_days(period="week", days=-7)


def test_window_ends_yesterday_and_spans_exactly_n_days():
    """窓は「昨日まで」の N 日間。当日は収集途中なので含めない。"""
    today = date(2026, 8, 30)
    start, end = fa.window_dates(days=7, today=today)
    assert end == date(2026, 8, 29)
    assert start == date(2026, 8, 23)
    assert (end - start).days + 1 == 7


def test_consecutive_weekly_windows_do_not_overlap():
    """週次を回す限り前回と重複しない（設計の前提）。"""
    _, prev_end = fa.window_dates(days=7, today=date(2026, 8, 23))
    next_start, _ = fa.window_dates(days=7, today=date(2026, 8, 30))
    assert prev_end < next_start


def test_list_query_window_is_half_open():
    """当日を含めない（含めると翌週の窓と1日重なる）。"""
    q = fa.build_list_query(project="p", days=7, min_importance=0.65, min_relevance=0.55)
    assert "< CURRENT_DATE" in q
    assert "INTERVAL 7 DAY" in q


def test_list_query_uses_jst_day_boundary():
    """収集は 6:00 JST 起点。UTC で切ると日付が前日にずれる。"""
    q = fa.build_list_query(project="p", days=7, min_importance=0.65, min_relevance=0.55)
    assert "Asia/Tokyo" in q


# --- 行の一意化 ---------------------------------------------------------


def test_list_query_picks_a_single_coherent_row_per_article():
    """ANY_VALUE は列ごとに独立して選ぶため、別々の行から値が混ざりうる。

    summaries には同一 article_id で summary が異なる行が実在する。
    本番の get_unnotified_summaries と同じく ROW_NUMBER で1行に絞る。
    """
    q = fa.build_list_query(project="p", days=7, min_importance=0.65, min_relevance=0.55)
    assert "ANY_VALUE(" not in q
    assert "ROW_NUMBER() OVER" in q


def test_list_query_uses_earliest_collection_for_the_window():
    """再収集で新しい行が増えても、初回収集日で窓に入れる（再掲を防ぐ）。"""
    q = fa.build_list_query(project="p", days=7, min_importance=0.65, min_relevance=0.55)
    assert "collected_at ASC" in q


def test_content_query_prefers_the_row_that_has_content():
    """本文取得リトライで content が NULL の行が混ざっても本文を落とさない。"""
    q, _ = fa.build_content_query(project="p", article_ids=["a1"])
    assert "ANY_VALUE(" not in q
    assert "LENGTH(content)" in q


def test_missing_ids_are_reported():
    """指定した article_id が取れなかったら黙って減らさない。"""
    rows = [{"article_id": "a1"}, {"article_id": "a2"}]
    assert fa.missing_ids(["a1", "a2", "a3"], rows) == ["a3"]
    assert fa.missing_ids(["a1"], rows) == []
