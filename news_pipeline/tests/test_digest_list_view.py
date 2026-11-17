"""scripts/digest/list_view.py のテスト。"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts", "digest"))

import list_view


def _a(aid, title="t", source="s", tags=None, imp=0.8, rel=0.9, summary="一行目\n二行目\n三行目"):
    return {
        "article_id": aid, "title": title, "url": f"https://x/{aid}", "source": source,
        "tags": tags or [], "importance_score": imp, "relevance_score": rel, "summary": summary,
    }


def test_bigquery_theme_is_decided_by_source_not_tags():
    """他社記事が連携先として bigquery タグを持っていても BigQuery 欄に入れない。"""
    other = _a("1", title="Procore と OpenSharing", source="Databricks Blog", tags=["bigquery", "data sharing"])
    bq = _a("2", title="パーティションの話", source="Zenn BigQuery", tags=["sql"])

    assert list_view.classify(other) != list_view.BIGQUERY_THEME
    assert list_view.classify(bq) == list_view.BIGQUERY_THEME


def test_unmatched_article_goes_to_last_theme():
    assert list_view.classify(_a("1", tags=["redshift"])) == list_view.THEMES[-1][0]


def test_score_treats_null_relevance_as_one():
    """fetch_articles の並び順（IFNULL(relevance, 1.0)）と合わせる。"""
    assert list_view.score(_a("1", imp=0.7, rel=None)) == 0.7


def test_html_excludes_deep_dive_and_escapes():
    arts = [_a("deep"), _a("x", title="<b>A&B</b>")]

    frag = list_view.build_html(arts, exclude={"deep"})

    assert "https://x/deep" not in frag
    assert "&lt;b&gt;A&amp;B&lt;/b&gt;" in frag


def test_html_shows_first_two_summary_lines_without_bullets():
    frag = list_view.build_html([_a("x", summary="• 一行目\n• 二行目\n• 三行目")], exclude=set())

    assert '<span class="pt">一行目</span><span class="pt">二行目</span>' in frag
    assert "三行目" not in frag


def test_resolve_ids_rejects_ambiguous_prefix():
    arts = [_a("abc111"), _a("abc222"), _a("def333")]

    resolved, unresolved = list_view.resolve_ids(arts, ["abc", "def"])

    assert resolved == ["def333"]
    assert unresolved == ["abc"]


def test_rank_is_sorted_by_score():
    out = list_view.format_rank([_a("low", imp=0.5), _a("high", imp=0.9)])

    assert out.index("high") < out.index("low")
