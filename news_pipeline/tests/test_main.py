"""_run_collect の繰り越し（取りこぼし防止）ロジックのテスト。"""

import os
import sys
from unittest.mock import MagicMock, patch

# main は import 時に環境変数を要求するので先に設定する
os.environ.setdefault("GCP_PROJECT_ID", "test-project")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ.setdefault("SLACK_WEBHOOK_URL", "https://hooks.slack.com/test")

# main.py は兄弟モジュールを bare import するため collector ディレクトリを path に追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "collector"))

from collector import main as main_mod


def _make_article(i: int) -> dict:
    return {
        "article_id": f"id{i}",
        "title": f"Title {i}",
        "url": f"https://example.com/{i}",
        "source": "Example",
        "published_at": "2026-06-20T00:00:00Z",
        "collected_at": "2026-06-20T01:00:00Z",
    }


def _config(max_summarize: str) -> dict:
    return {
        "feeds": {"https://example.com/rss": "Example"},
        "keywords": [],
        "feed_blocks": {},
        "settings": {
            "general": {
                "max_summarize": max_summarize,
                "importance_threshold": "0.65",
                "max_content_retries": "3",
            }
        },
    }


@patch("collector.main.summarize_article")
@patch("collector.main.fetch_content")
@patch("collector.main.fetch_articles")
@patch("collector.main.load_config")
@patch("collector.main.BQClient")
def test_overflow_saved_to_raw_and_deferred(
    mock_bqclass,
    mock_load_config,
    mock_fetch_articles,
    mock_fetch_content,
    mock_summarize,
):
    """新着 > バジェットでも全件 raw_articles に保存し、超過分は pending で繰り越す。"""
    mock_load_config.return_value = _config(max_summarize="3")
    bq = MagicMock()
    mock_bqclass.return_value = bq
    bq.get_existing_urls.return_value = set()
    bq.get_pending_articles.return_value = []
    bq.get_existing_summary_ids.return_value = set()

    mock_fetch_articles.return_value = [_make_article(i) for i in range(5)]
    mock_fetch_content.return_value = ("body", True)
    mock_summarize.return_value = {
        "summary": "s",
        "tags": [],
        "importance_score": 0.9,
    }

    main_mod._run_collect()

    # 全5件が raw_articles に保存される（取りこぼしゼロ）
    saved = bq.insert_raw_articles.call_args[0][0]
    assert len(saved) == 5

    statuses = [a["content_status"] for a in saved]
    assert statuses.count("ok") == 3  # バジェット分は処理
    assert statuses.count("pending") == 2  # 超過分は繰り越し

    deferred = [a for a in saved if a["content_status"] == "pending"]
    assert all(a["content"] is None and a["retry_count"] == 0 for a in deferred)

    # 要約は3件のみ（バジェット内）
    assert mock_summarize.call_count == 3


@patch("collector.main.summarize_article")
@patch("collector.main.fetch_content")
@patch("collector.main.fetch_articles")
@patch("collector.main.load_config")
@patch("collector.main.BQClient")
def test_pending_consumes_budget_before_new(
    mock_bqclass,
    mock_load_config,
    mock_fetch_articles,
    mock_fetch_content,
    mock_summarize,
):
    """繰り越し（pending）がバジェットを先に消費し、新着の処理枠が減る。"""
    mock_load_config.return_value = _config(max_summarize="3")
    bq = MagicMock()
    mock_bqclass.return_value = bq
    bq.get_existing_urls.return_value = set()
    # 既存 pending 2件（古いバックログ）
    bq.get_pending_articles.return_value = [
        {
            "article_id": "p1",
            "url": "https://example.com/p1",
            "title": "P1",
            "source": "Example",
            "retry_count": 0,
        },
        {
            "article_id": "p2",
            "url": "https://example.com/p2",
            "title": "P2",
            "source": "Example",
            "retry_count": 0,
        },
    ]
    bq.get_existing_summary_ids.return_value = set()

    mock_fetch_articles.return_value = [_make_article(i) for i in range(4)]
    mock_fetch_content.return_value = ("body", True)
    mock_summarize.return_value = {
        "summary": "s",
        "tags": [],
        "importance_score": 0.9,
    }

    main_mod._run_collect()

    # バジェット3 - pending成功2 = 残り1 のみ新着を即時処理、残り3件は繰り越し
    saved = bq.insert_raw_articles.call_args[0][0]
    assert len(saved) == 4  # 新着は全件保存
    statuses = [a["content_status"] for a in saved]
    assert statuses.count("ok") == 1
    assert statuses.count("pending") == 3

    # 要約は pending 2 + 新着 1 = 3件
    assert mock_summarize.call_count == 3

    # get_pending_articles は limit=max_summarize で呼ばれる
    assert bq.get_pending_articles.call_args.kwargs.get("limit") == 3 or (
        len(bq.get_pending_articles.call_args.args) >= 2
        and bq.get_pending_articles.call_args.args[1] == 3
    )


@patch("collector.main.summarize_article")
@patch("collector.main.fetch_content")
@patch("collector.main.fetch_articles")
@patch("collector.main.load_config")
@patch("collector.main.BQClient")
def test_under_budget_processes_all_new_no_defer(
    mock_bqclass,
    mock_load_config,
    mock_fetch_articles,
    mock_fetch_content,
    mock_summarize,
):
    """新着がバジェット以下なら従来通り全件即時処理し、繰り越しは発生しない。"""
    mock_load_config.return_value = _config(max_summarize="10")
    bq = MagicMock()
    mock_bqclass.return_value = bq
    bq.get_existing_urls.return_value = set()
    bq.get_pending_articles.return_value = []
    bq.get_existing_summary_ids.return_value = set()

    mock_fetch_articles.return_value = [_make_article(i) for i in range(3)]
    mock_fetch_content.return_value = ("body", True)
    mock_summarize.return_value = {
        "summary": "s",
        "tags": [],
        "importance_score": 0.9,
    }

    main_mod._run_collect()

    saved = bq.insert_raw_articles.call_args[0][0]
    assert len(saved) == 3
    assert all(a["content_status"] == "ok" for a in saved)
    assert mock_summarize.call_count == 3


def _speakerdeck_article(i: int, desc: str = "") -> dict:
    return {
        "article_id": f"sd{i}",
        "title": f"Slide {i}",
        "url": f"https://speakerdeck.com/user/talk-{i}",
        "source": "Speaker Deck",
        "published_at": "2026-06-20T00:00:00Z",
        "collected_at": "2026-06-20T01:00:00Z",
        "description": desc,
    }


@patch("collector.main.score_slide_relevance")
@patch("collector.main.summarize_article")
@patch("collector.main.fetch_content")
@patch("collector.main.fetch_articles")
@patch("collector.main.load_config")
@patch("collector.main.BQClient")
def test_slide_prefilter_skips_low_relevance(
    mock_bqclass,
    mock_load_config,
    mock_fetch_articles,
    mock_fetch_content,
    mock_summarize,
    mock_prefilter,
):
    """関連度が閾値未満の Speaker Deck スライドは PDF を取得せず filtered で保存する。"""
    mock_load_config.return_value = _config(max_summarize="10")
    bq = MagicMock()
    mock_bqclass.return_value = bq
    bq.get_existing_urls.return_value = set()
    bq.get_pending_articles.return_value = []
    bq.get_existing_summary_ids.return_value = set()

    # 1件目=低スコア(弾く), 2件目=高スコア(通す)
    mock_prefilter.side_effect = [0.1, 0.9]
    mock_fetch_articles.return_value = [
        _speakerdeck_article(0),
        _speakerdeck_article(1),
    ]
    mock_fetch_content.return_value = ("slide body", True)
    mock_summarize.return_value = {"summary": "s", "tags": [], "importance_score": 0.9}

    main_mod._run_collect()

    saved = bq.insert_raw_articles.call_args[0][0]
    assert len(saved) == 2  # 両方 raw_articles に保存（filtered も記録）
    statuses = {a["url"]: a["content_status"] for a in saved}
    assert statuses["https://speakerdeck.com/user/talk-0"] == "filtered"
    assert statuses["https://speakerdeck.com/user/talk-1"] == "ok"
    # description はスキーマ外なので保存前に除去される
    assert all("description" not in a for a in saved)
    # 弾いた1件は PDF 取得も要約もされない
    assert mock_fetch_content.call_count == 1
    assert mock_summarize.call_count == 1


@patch("collector.main.score_slide_relevance")
@patch("collector.main.summarize_article")
@patch("collector.main.fetch_content")
@patch("collector.main.fetch_articles")
@patch("collector.main.load_config")
@patch("collector.main.BQClient")
def test_prefilter_not_applied_to_non_speakerdeck(
    mock_bqclass,
    mock_load_config,
    mock_fetch_articles,
    mock_fetch_content,
    mock_summarize,
    mock_prefilter,
):
    """通常記事には1次フィルタを適用しない（score_slide_relevance を呼ばない）。"""
    mock_load_config.return_value = _config(max_summarize="10")
    bq = MagicMock()
    mock_bqclass.return_value = bq
    bq.get_existing_urls.return_value = set()
    bq.get_pending_articles.return_value = []
    bq.get_existing_summary_ids.return_value = set()

    mock_fetch_articles.return_value = [_make_article(i) for i in range(2)]
    mock_fetch_content.return_value = ("body", True)
    mock_summarize.return_value = {"summary": "s", "tags": [], "importance_score": 0.9}

    main_mod._run_collect()

    mock_prefilter.assert_not_called()
    assert mock_summarize.call_count == 2


@patch("collector.main.summarize_article")
@patch("collector.main.fetch_content")
@patch("collector.main.fetch_articles")
@patch("collector.main.load_config")
@patch("collector.main.BQClient")
def test_below_threshold_new_articles_marked_summarized(
    mock_bqclass,
    mock_load_config,
    mock_fetch_articles,
    mock_fetch_content,
    mock_summarize,
):
    """閾値未満の新着は content_status='summarized'（終端）で保存し orphan にしない。"""
    mock_load_config.return_value = _config(max_summarize="10")
    bq = MagicMock()
    mock_bqclass.return_value = bq
    bq.get_existing_urls.return_value = set()
    bq.get_pending_articles.return_value = []
    bq.get_existing_summary_ids.return_value = set()

    mock_fetch_articles.return_value = [_make_article(0), _make_article(1)]
    mock_fetch_content.return_value = ("body", True)
    # 1件目=閾値以上, 2件目=閾値未満
    mock_summarize.side_effect = [
        {"summary": "s", "tags": [], "importance_score": 0.9},
        {"summary": "s", "tags": [], "importance_score": 0.3},
    ]

    main_mod._run_collect()

    saved = bq.insert_raw_articles.call_args[0][0]
    statuses = {a["article_id"]: a["content_status"] for a in saved}
    assert statuses["id0"] == "ok"
    assert statuses["id1"] == "summarized"
    # 新着はストリーミング挿入前に dict を書き換えるので DML マークは呼ばれない
    bq.mark_article_summarized.assert_not_called()


@patch("collector.main.summarize_article")
@patch("collector.main.fetch_content")
@patch("collector.main.fetch_articles")
@patch("collector.main.load_config")
@patch("collector.main.BQClient")
def test_below_threshold_pending_articles_marked_via_dml(
    mock_bqclass,
    mock_load_config,
    mock_fetch_articles,
    mock_fetch_content,
    mock_summarize,
):
    """閾値未満の繰り越し（pending由来）記事は DML で summarized にマークする。"""
    mock_load_config.return_value = _config(max_summarize="10")
    bq = MagicMock()
    mock_bqclass.return_value = bq
    bq.get_existing_urls.return_value = set()
    bq.get_pending_articles.return_value = [
        {
            "article_id": "p1",
            "url": "https://example.com/p1",
            "title": "P1",
            "source": "Example",
            "retry_count": 0,
        }
    ]
    bq.get_existing_summary_ids.return_value = set()

    mock_fetch_articles.return_value = []
    mock_fetch_content.return_value = ("body", True)
    mock_summarize.return_value = {"summary": "s", "tags": [], "importance_score": 0.3}

    main_mod._run_collect()

    bq.mark_article_summarized.assert_called_once_with("p1")
    bq.insert_summaries.assert_not_called()


@patch("collector.main.summarize_article")
@patch("collector.main.fetch_content")
@patch("collector.main.fetch_articles")
@patch("collector.main.load_config")
@patch("collector.main.BQClient")
def test_collect_dedupes_same_url_within_batch(
    mock_bqclass,
    mock_load_config,
    mock_fetch_articles,
    mock_fetch_content,
    mock_summarize,
):
    """同一実行内で同じURLが複数フィードから来ても1件だけ処理・保存する。"""
    mock_load_config.return_value = _config(max_summarize="10")
    bq = MagicMock()
    mock_bqclass.return_value = bq
    bq.get_existing_urls.return_value = set()
    bq.get_pending_articles.return_value = []
    bq.get_existing_summary_ids.return_value = set()
    bq.get_favorite_tag_counts.return_value = []

    dup_a = _make_article(0)
    dup_b = dict(_make_article(0), source="Another Feed")  # 同一URL・別フィード
    mock_fetch_articles.return_value = [dup_a, dup_b, _make_article(1)]
    mock_fetch_content.return_value = ("body", True)
    mock_summarize.return_value = {"summary": "s", "tags": [], "importance_score": 0.9}

    main_mod._run_collect()

    saved = bq.insert_raw_articles.call_args[0][0]
    assert len(saved) == 2  # URL重複は1件に統合
    assert mock_summarize.call_count == 2


def _config_with_personalize(top_tags: str) -> dict:
    config = _config(max_summarize="10")
    config["settings"]["general"]["personalize_top_tags"] = top_tags
    return config


@patch("collector.main.summarize_article")
@patch("collector.main.fetch_content")
@patch("collector.main.fetch_articles")
@patch("collector.main.load_config")
@patch("collector.main.BQClient")
def test_collect_passes_favorite_tags_to_summarize(
    mock_bqclass,
    mock_load_config,
    mock_fetch_articles,
    mock_fetch_content,
    mock_summarize,
):
    """お気に入り由来タグを取得し summarize_article に渡す。"""
    mock_load_config.return_value = _config(max_summarize="10")
    bq = MagicMock()
    mock_bqclass.return_value = bq
    bq.get_existing_urls.return_value = set()
    bq.get_pending_articles.return_value = []
    bq.get_existing_summary_ids.return_value = set()
    bq.get_favorite_tag_counts.return_value = ["dbt", "bigquery"]

    mock_fetch_articles.return_value = [_make_article(0)]
    mock_fetch_content.return_value = ("body", True)
    mock_summarize.return_value = {"summary": "s", "tags": [], "importance_score": 0.9}

    main_mod._run_collect()

    bq.get_favorite_tag_counts.assert_called_once_with(5)  # 既定値
    assert mock_summarize.call_args.kwargs["favorite_tags"] == ["dbt", "bigquery"]


@patch("collector.main.summarize_article")
@patch("collector.main.fetch_content")
@patch("collector.main.fetch_articles")
@patch("collector.main.load_config")
@patch("collector.main.BQClient")
def test_collect_personalize_disabled_skips_query(
    mock_bqclass,
    mock_load_config,
    mock_fetch_articles,
    mock_fetch_content,
    mock_summarize,
):
    """personalize_top_tags=0 なら BigQuery クエリ自体をスキップする。"""
    mock_load_config.return_value = _config_with_personalize("0")
    bq = MagicMock()
    mock_bqclass.return_value = bq
    bq.get_existing_urls.return_value = set()
    bq.get_pending_articles.return_value = []
    bq.get_existing_summary_ids.return_value = set()

    mock_fetch_articles.return_value = [_make_article(0)]
    mock_fetch_content.return_value = ("body", True)
    mock_summarize.return_value = {"summary": "s", "tags": [], "importance_score": 0.9}

    main_mod._run_collect()

    bq.get_favorite_tag_counts.assert_not_called()
    assert mock_summarize.call_args.kwargs["favorite_tags"] == []


@patch("collector.main.summarize_article")
@patch("collector.main.fetch_content")
@patch("collector.main.fetch_articles")
@patch("collector.main.load_config")
@patch("collector.main.BQClient")
def test_collect_continues_when_favorite_tags_query_fails(
    mock_bqclass,
    mock_load_config,
    mock_fetch_articles,
    mock_fetch_content,
    mock_summarize,
):
    """タグ取得失敗時は空リストで続行（パーソナライズなしにフォールバック）。"""
    mock_load_config.return_value = _config(max_summarize="10")
    bq = MagicMock()
    mock_bqclass.return_value = bq
    bq.get_existing_urls.return_value = set()
    bq.get_pending_articles.return_value = []
    bq.get_existing_summary_ids.return_value = set()
    bq.get_favorite_tag_counts.side_effect = Exception("BQ error")

    mock_fetch_articles.return_value = [_make_article(0)]
    mock_fetch_content.return_value = ("body", True)
    mock_summarize.return_value = {"summary": "s", "tags": [], "importance_score": 0.9}

    summarized = main_mod._run_collect()

    assert summarized == 1  # 収集は止まらない
    assert mock_summarize.call_args.kwargs["favorite_tags"] == []


@patch("collector.main.send_error_notification")
@patch("collector.main.load_config")
@patch("collector.main.BQClient")
def test_collect_raises_and_alerts_when_feeds_empty(
    mock_bqclass, mock_load_config, mock_alert
):
    """設定ロード失敗（feeds空）は「成功・0件」ではなくエラーにし、Slackアラートを送る。"""
    import pytest

    mock_load_config.return_value = {}
    bq = MagicMock()
    mock_bqclass.return_value = bq

    with pytest.raises(RuntimeError):
        main_mod._run_collect()

    mock_alert.assert_called_once()
    # pipeline_logs には status='error' で記録される
    saved_log = bq.insert_pipeline_log.call_args[0][0]
    assert saved_log["status"] == "error"


@patch("collector.main.send_error_notification")
@patch("collector.main.load_config")
@patch("collector.main.BQClient")
def test_notify_raises_and_alerts_when_config_empty(
    mock_bqclass, mock_load_config, mock_alert
):
    """設定ロード失敗時の /notify はブロックリスト未適用のまま通知せずエラーにする。"""
    import pytest

    mock_load_config.return_value = {}
    bq = MagicMock()
    mock_bqclass.return_value = bq

    with pytest.raises(RuntimeError):
        main_mod._run_notify()

    mock_alert.assert_called_once()
    bq.mark_summaries_notified.assert_not_called()


@patch("collector.main.send_no_news_notification")
@patch("collector.main.send_slack_notification")
@patch("collector.main.load_config")
@patch("collector.main.BQClient")
def test_notify_send_failure_does_not_mark_notified(
    mock_bqclass, mock_load_config, mock_send, mock_no_news
):
    """Slack送信失敗時は通知済みマークせず、「新着なし」通知もしない。"""
    mock_load_config.return_value = {
        "feeds": {"https://example.com/rss": "Example"},
        "keywords": [],
        "feed_categories": {},
        "feed_blocks": {},
        "settings": {},
    }
    bq = MagicMock()
    mock_bqclass.return_value = bq
    bq.get_unnotified_summaries.return_value = [
        {
            "article_id": "a1",
            "title": "T",
            "url": "https://example.com/1",
            "source": "Example",
            "summary": "- x",
            "importance_score": 0.9,
        }
    ]
    mock_send.return_value = False

    notified = main_mod._run_notify()

    assert notified == 0
    bq.mark_summaries_notified.assert_not_called()
    mock_no_news.assert_not_called()


@patch("collector.main.send_no_news_notification")
@patch("collector.main.send_slack_notification")
@patch("collector.main.load_config")
@patch("collector.main.BQClient")
def test_notify_success_marks_notified(
    mock_bqclass, mock_load_config, mock_send, mock_no_news
):
    """Slack送信成功時は通知済みマークする。"""
    mock_load_config.return_value = {
        "feeds": {"https://example.com/rss": "Example"},
        "keywords": [],
        "feed_categories": {},
        "feed_blocks": {},
        "settings": {},
    }
    bq = MagicMock()
    mock_bqclass.return_value = bq
    bq.get_unnotified_summaries.return_value = [
        {
            "article_id": "a1",
            "title": "T",
            "url": "https://example.com/1",
            "source": "Example",
            "summary": "- x",
            "importance_score": 0.9,
        }
    ]
    mock_send.return_value = True

    notified = main_mod._run_notify()

    assert notified == 1
    bq.mark_summaries_notified.assert_called_once_with(["a1"])


def _resummarize_config() -> dict:
    return {
        "feeds": {"https://example.com/rss": "Example"},
        "keywords": [],
        "feed_blocks": {},
        "settings": {
            "general": {
                "importance_threshold": "0.65",
                "resummarize_limit": "50",
                "resummarize_days": "7",
            }
        },
    }


def _orphan(i: int) -> dict:
    return {
        "article_id": f"orphan{i}",
        "title": f"Orphan {i}",
        "url": f"https://example.com/orphan-{i}",
        "source": "Example",
        "content": "recovered body",
    }


@patch("collector.main.summarize_article")
@patch("collector.main.load_config")
@patch("collector.main.BQClient")
def test_resummarize_above_threshold_inserts_summary(
    mock_bqclass, mock_load_config, mock_summarize
):
    """閾値以上のorphanは summaries に復旧し、summarized マークはしない。"""
    mock_load_config.return_value = _resummarize_config()
    bq = MagicMock()
    mock_bqclass.return_value = bq
    bq.get_unsummarized_articles.return_value = [_orphan(0)]
    mock_summarize.return_value = {"summary": "s", "tags": [], "importance_score": 0.8}

    recovered, _ = main_mod._run_resummarize()

    assert recovered == 1
    bq.insert_summaries.assert_called_once()
    inserted = bq.insert_summaries.call_args[0][0][0]
    assert inserted["article_id"] == "orphan0"
    assert inserted["scoring_version"] == main_mod.SCORING_VERSION
    bq.mark_article_summarized.assert_not_called()


@patch("collector.main.summarize_article")
@patch("collector.main.load_config")
@patch("collector.main.BQClient")
def test_resummarize_below_threshold_marks_summarized(
    mock_bqclass, mock_load_config, mock_summarize
):
    """閾値未満のorphanは summaries に入れず content_status='summarized' にマーク。"""
    mock_load_config.return_value = _resummarize_config()
    bq = MagicMock()
    mock_bqclass.return_value = bq
    bq.get_unsummarized_articles.return_value = [_orphan(0)]
    mock_summarize.return_value = {"summary": "s", "tags": [], "importance_score": 0.3}

    recovered, _ = main_mod._run_resummarize()

    assert recovered == 0
    bq.insert_summaries.assert_not_called()
    bq.mark_article_summarized.assert_called_once_with("orphan0")


@patch("collector.main.summarize_article")
@patch("collector.main.load_config")
@patch("collector.main.BQClient")
def test_resummarize_failure_skips_without_marking(
    mock_bqclass, mock_load_config, mock_summarize
):
    """要約失敗（None）は summaries挿入もマークもせず 'ok' のまま残す（次回リトライ）。"""
    mock_load_config.return_value = _resummarize_config()
    bq = MagicMock()
    mock_bqclass.return_value = bq
    bq.get_unsummarized_articles.return_value = [_orphan(0)]
    mock_summarize.return_value = None

    recovered, _ = main_mod._run_resummarize()

    assert recovered == 0
    bq.insert_summaries.assert_not_called()
    bq.mark_article_summarized.assert_not_called()


# --- relevance ゲート（データ基盤との関連度による足切り）----------------------


def test_passes_thresholds_accepts_relevant_and_important():
    s = {"importance_score": 0.8, "relevance_score": 0.9}
    assert main_mod.passes_thresholds(s, 0.65, 0.55) is True


def test_passes_thresholds_rejects_low_importance():
    s = {"importance_score": 0.5, "relevance_score": 0.9}
    assert main_mod.passes_thresholds(s, 0.65, 0.55) is False


def test_passes_thresholds_rejects_offtopic_despite_high_importance():
    """良質だが対象領域外の記事は importance が高くても落とす（今回の主目的）。"""
    s = {"importance_score": 0.82, "relevance_score": 0.1}
    assert main_mod.passes_thresholds(s, 0.65, 0.55) is False


def test_passes_thresholds_passes_when_relevance_unknown():
    """relevance が判定不能（None／キー欠落）なら通す＝取りこぼし防止。"""
    assert main_mod.passes_thresholds(
        {"importance_score": 0.8, "relevance_score": None}, 0.65, 0.55
    ) is True
    assert main_mod.passes_thresholds({"importance_score": 0.8}, 0.65, 0.55) is True


def test_passes_thresholds_boundaries_are_inclusive():
    """閾値ちょうどは通す（>= 判定）。"""
    s = {"importance_score": 0.65, "relevance_score": 0.55}
    assert main_mod.passes_thresholds(s, 0.65, 0.55) is True


def test_passes_thresholds_rejects_just_below_relevance_boundary():
    s = {"importance_score": 0.8, "relevance_score": 0.5}
    assert main_mod.passes_thresholds(s, 0.65, 0.55) is False


def test_passes_thresholds_handles_non_numeric_relevance():
    """非数値は判定不能として扱い、落とさない。"""
    s = {"importance_score": 0.8, "relevance_score": "n/a"}
    assert main_mod.passes_thresholds(s, 0.65, 0.55) is True


def test_default_relevance_threshold_avoids_model_mode_value():
    """モデルは 0.5 のような丸い値を出しがちなので境界をずらす。"""
    assert main_mod._DEFAULT_RELEVANCE_THRESHOLD == 0.55


@patch("collector.main.summarize_article")
@patch("collector.main.fetch_content")
@patch("collector.main.fetch_articles")
@patch("collector.main.load_config")
@patch("collector.main.BQClient")
def test_offtopic_articles_are_gated_out_of_summaries(
    mock_bqclass,
    mock_load_config,
    mock_fetch_articles,
    mock_fetch_content,
    mock_summarize,
):
    """良質でも対象領域外（relevance 低）は summaries に保存せず終端化する。"""
    mock_load_config.return_value = _config(max_summarize="10")
    bq = MagicMock()
    mock_bqclass.return_value = bq
    bq.get_existing_urls.return_value = set()
    bq.get_pending_articles.return_value = []
    bq.get_existing_summary_ids.return_value = set()

    mock_fetch_articles.return_value = [_make_article(0), _make_article(1)]
    mock_fetch_content.return_value = ("body", True)
    # 両方とも importance は高いが、2件目は対象領域外
    mock_summarize.side_effect = [
        {"summary": "s", "tags": [], "importance_score": 0.82, "relevance_score": 0.9},
        {"summary": "s", "tags": [], "importance_score": 0.82, "relevance_score": 0.1},
    ]

    main_mod._run_collect()

    saved_summaries = bq.insert_summaries.call_args[0][0]
    assert [s["article_id"] for s in saved_summaries] == ["id0"]
    # 落ちた側は orphan にせず終端化する
    statuses = {
        a["article_id"]: a["content_status"]
        for a in bq.insert_raw_articles.call_args[0][0]
    }
    assert statuses["id1"] == "summarized"


@patch("collector.main.summarize_article")
@patch("collector.main.fetch_content")
@patch("collector.main.fetch_articles")
@patch("collector.main.load_config")
@patch("collector.main.BQClient")
def test_relevance_score_is_persisted_to_summaries(
    mock_bqclass,
    mock_load_config,
    mock_fetch_articles,
    mock_fetch_content,
    mock_summarize,
):
    """relevance_score は後からチューニング検証できるよう summaries に保存する。"""
    mock_load_config.return_value = _config(max_summarize="10")
    bq = MagicMock()
    mock_bqclass.return_value = bq
    bq.get_existing_urls.return_value = set()
    bq.get_pending_articles.return_value = []
    bq.get_existing_summary_ids.return_value = set()

    mock_fetch_articles.return_value = [_make_article(0)]
    mock_fetch_content.return_value = ("body", True)
    mock_summarize.return_value = {
        "summary": "s",
        "tags": [],
        "importance_score": 0.82,
        "relevance_score": 0.9,
    }

    main_mod._run_collect()

    saved = bq.insert_summaries.call_args[0][0][0]
    assert saved["relevance_score"] == 0.9


@patch("collector.main.summarize_article")
@patch("collector.main.fetch_content")
@patch("collector.main.fetch_articles")
@patch("collector.main.load_config")
@patch("collector.main.BQClient")
def test_relevance_threshold_read_from_settings(
    mock_bqclass,
    mock_load_config,
    mock_fetch_articles,
    mock_fetch_content,
    mock_summarize,
):
    """relevance_threshold は settings シートで調整でき、再デプロイを不要にする。"""
    config = _config(max_summarize="10")
    config["settings"]["general"]["relevance_threshold"] = "0.2"
    mock_load_config.return_value = config
    bq = MagicMock()
    mock_bqclass.return_value = bq
    bq.get_existing_urls.return_value = set()
    bq.get_pending_articles.return_value = []
    bq.get_existing_summary_ids.return_value = set()

    mock_fetch_articles.return_value = [_make_article(0)]
    mock_fetch_content.return_value = ("body", True)
    # 既定 0.55 なら落ちるが、シートで 0.2 に緩めたので通る
    mock_summarize.return_value = {
        "summary": "s",
        "tags": [],
        "importance_score": 0.82,
        "relevance_score": 0.3,
    }

    main_mod._run_collect()

    assert [s["article_id"] for s in bq.insert_summaries.call_args[0][0]] == ["id0"]


@patch("collector.main.summarize_article")
@patch("collector.main.fetch_content")
@patch("collector.main.fetch_articles")
@patch("collector.main.load_config")
@patch("collector.main.BQClient")
def test_default_relevance_threshold_rejects_borderline_article(
    mock_bqclass,
    mock_load_config,
    mock_fetch_articles,
    mock_fetch_content,
    mock_summarize,
):
    """settings に指定が無ければ既定 0.55 が効き、relevance 0.3 は落ちる。"""
    mock_load_config.return_value = _config(max_summarize="10")
    bq = MagicMock()
    mock_bqclass.return_value = bq
    bq.get_existing_urls.return_value = set()
    bq.get_pending_articles.return_value = []
    bq.get_existing_summary_ids.return_value = set()

    mock_fetch_articles.return_value = [_make_article(0)]
    mock_fetch_content.return_value = ("body", True)
    mock_summarize.return_value = {
        "summary": "s",
        "tags": [],
        "importance_score": 0.82,
        "relevance_score": 0.3,
    }

    main_mod._run_collect()

    bq.insert_summaries.assert_not_called()


@patch("collector.main.score_article")
@patch("collector.main.load_config")
@patch("collector.main.BQClient")
def test_recalculate_persists_relevance_score(
    mock_bqclass, mock_load_config, mock_score
):
    """再採点は relevance も保存し、既存行の relevance_score を埋める。"""
    mock_load_config.return_value = _config(max_summarize="10")
    bq = MagicMock()
    mock_bqclass.return_value = bq
    bq.get_favorite_tag_counts.return_value = []
    bq.get_outdated_summaries.return_value = [
        {"article_id": "a1", "title": "T", "content": "body"}
    ]
    mock_score.return_value = {"importance_score": 0.4, "relevance_score": 0.1}

    main_mod._run_recalculate()

    args, kwargs = bq.update_summary_score.call_args
    assert args[0] == "a1"
    assert args[1] == 0.4
    assert kwargs["relevance_score"] == 0.1


@patch("collector.main.score_article")
@patch("collector.main.load_config")
@patch("collector.main.BQClient")
def test_recalculate_skips_failed_scoring(mock_bqclass, mock_load_config, mock_score):
    """採点失敗（None）の行は更新しない。"""
    mock_load_config.return_value = _config(max_summarize="10")
    bq = MagicMock()
    mock_bqclass.return_value = bq
    bq.get_favorite_tag_counts.return_value = []
    bq.get_outdated_summaries.return_value = [
        {"article_id": "a1", "title": "T", "content": "body"}
    ]
    mock_score.return_value = None

    # 採点失敗は成功0件・エラー1件として報告される
    assert main_mod._run_recalculate() == (0, 1)
    bq.update_summary_score.assert_not_called()


# --- BigQuery スキーマとの整合 ------------------------------------------------


def _terraform_schema_fields(table_id: str) -> set[str]:
    """infra/bigquery.tf から指定テーブルのカラム名集合を読む。"""
    import pathlib
    import re

    tf = pathlib.Path(__file__).resolve().parent.parent / "infra" / "bigquery.tf"
    text = tf.read_text()
    for chunk in re.split(r'(?=resource "google_bigquery_table")', text):
        if re.search(rf'table_id\s*=\s*"{table_id}"', chunk):
            return set(re.findall(r'name\s*=\s*"(\w+)"', chunk))
    raise AssertionError(f"table {table_id} not found in bigquery.tf")


@patch("collector.main.summarize_article")
@patch("collector.main.fetch_content")
@patch("collector.main.fetch_articles")
@patch("collector.main.load_config")
@patch("collector.main.BQClient")
def test_summaries_payload_fits_bigquery_schema(
    mock_bqclass,
    mock_load_config,
    mock_fetch_articles,
    mock_fetch_content,
    mock_summarize,
):
    """insert する dict のキーが summaries のスキーマに収まること。

    insert_rows_json はスキーマに無いフィールドを含む行をエラーにする。
    Terraform より先に Cloud Run を更新すると /collect 全体が落ちるため、
    ここで齟齬をローカルに捕まえる。
    """
    mock_load_config.return_value = _config(max_summarize="10")
    bq = MagicMock()
    mock_bqclass.return_value = bq
    bq.get_existing_urls.return_value = set()
    bq.get_pending_articles.return_value = []
    bq.get_existing_summary_ids.return_value = set()

    mock_fetch_articles.return_value = [_make_article(0)]
    mock_fetch_content.return_value = ("body", True)
    mock_summarize.return_value = {
        "summary": "s",
        "tags": ["dbt"],
        "importance_score": 0.82,
        "relevance_score": 0.9,
    }

    main_mod._run_collect()

    payload_keys = set(bq.insert_summaries.call_args[0][0][0].keys())
    assert payload_keys <= _terraform_schema_fields("summaries")


@patch("collector.main.summarize_article")
@patch("collector.main.fetch_content")
@patch("collector.main.fetch_articles")
@patch("collector.main.load_config")
@patch("collector.main.BQClient")
def test_raw_articles_payload_fits_bigquery_schema(
    mock_bqclass,
    mock_load_config,
    mock_fetch_articles,
    mock_fetch_content,
    mock_summarize,
):
    mock_load_config.return_value = _config(max_summarize="10")
    bq = MagicMock()
    mock_bqclass.return_value = bq
    bq.get_existing_urls.return_value = set()
    bq.get_pending_articles.return_value = []
    bq.get_existing_summary_ids.return_value = set()

    mock_fetch_articles.return_value = [_make_article(0)]
    mock_fetch_content.return_value = ("body", True)
    mock_summarize.return_value = {
        "summary": "s",
        "tags": [],
        "importance_score": 0.82,
        "relevance_score": 0.9,
    }

    main_mod._run_collect()

    payload_keys = set(bq.insert_raw_articles.call_args[0][0][0].keys())
    assert payload_keys <= _terraform_schema_fields("raw_articles")


def test_slide_prefilter_threshold_lowered_for_stricter_domain_criteria():
    """ドメイン定義の追加でプレフィルタも厳しくなるため既定を下げる。

    content_status='filtered' は終端で再取得されない（不可逆）ので、
    スライドの取りこぼしを避ける側に倒す。
    """
    assert main_mod._DEFAULT_SLIDE_PREFILTER_THRESHOLD == 0.2


# --- バッチ系エンドポイントの error_count -----------------------------------


@patch("collector.main.score_article")
@patch("collector.main.load_config")
@patch("collector.main.BQClient")
def test_recalculate_reports_error_count(mock_bqclass, mock_load_config, mock_score):
    """全件失敗（0件更新）と対象なし（0件更新）を呼び出し側で区別できること。

    戻り値が成功件数だけだと、クレジット枯渇などで全件失敗しても 0 が返り、
    「対象が無くなった＝完了」と誤認する。
    """
    mock_load_config.return_value = _config(max_summarize="10")
    bq = MagicMock()
    mock_bqclass.return_value = bq
    bq.get_favorite_tag_counts.return_value = []
    bq.get_outdated_summaries.return_value = [
        {"article_id": f"a{i}", "title": "T", "content": "body"} for i in range(3)
    ]
    mock_score.return_value = None  # 採点が全件失敗

    recalculated, error_count = main_mod._run_recalculate()

    assert recalculated == 0
    assert error_count == 3


@patch("collector.main.score_article")
@patch("collector.main.load_config")
@patch("collector.main.BQClient")
def test_recalculate_no_targets_reports_zero_errors(
    mock_bqclass, mock_load_config, mock_score
):
    """対象なしのときは (0, 0)。全件失敗の (0, N) と区別できる。"""
    mock_load_config.return_value = _config(max_summarize="10")
    bq = MagicMock()
    mock_bqclass.return_value = bq
    bq.get_favorite_tag_counts.return_value = []
    bq.get_outdated_summaries.return_value = []

    assert main_mod._run_recalculate() == (0, 0)


@patch("collector.main.summarize_article")
@patch("collector.main.load_config")
@patch("collector.main.BQClient")
def test_resummarize_reports_error_count(
    mock_bqclass, mock_load_config, mock_summarize
):
    """/resummarize も同じ落とし穴を持つので error_count を返す。"""
    mock_load_config.return_value = _config(max_summarize="10")
    bq = MagicMock()
    mock_bqclass.return_value = bq
    bq.get_favorite_tag_counts.return_value = []
    bq.get_unsummarized_articles.return_value = [
        {"article_id": "a1", "title": "T", "url": "u", "source": "s", "content": "body"}
    ]
    mock_summarize.return_value = None  # 要約が失敗

    recovered, error_count = main_mod._run_resummarize()

    assert recovered == 0
    assert error_count == 1


def test_pipeline_response_exposes_error_count():
    """レスポンスモデルが error_count を持つ（既定0で後方互換）。"""
    r = main_mod.PipelineResponse(status="ok", notified=5)
    assert r.error_count == 0
    assert main_mod.PipelineResponse(status="ok", notified=0, error_count=3).error_count == 3


@patch("collector.main.summarize_article")
@patch("collector.main.load_config")
@patch("collector.main.BQClient")
def test_resummarize_overrides_days_and_limit(
    mock_bqclass, mock_load_config, mock_summarize
):
    """days/limit をリクエストで上書きできる（古い orphan の一括処理用）。"""
    config = _config(max_summarize="10")
    config["settings"]["general"]["resummarize_days"] = "7"
    config["settings"]["general"]["resummarize_limit"] = "50"
    mock_load_config.return_value = config
    bq = MagicMock()
    mock_bqclass.return_value = bq
    bq.get_favorite_tag_counts.return_value = []
    bq.get_unsummarized_articles.return_value = []

    main_mod._run_resummarize("manual", days=120, limit=200)

    bq.get_unsummarized_articles.assert_called_once_with(120, 200)


@patch("collector.main.summarize_article")
@patch("collector.main.load_config")
@patch("collector.main.BQClient")
def test_resummarize_falls_back_to_settings(
    mock_bqclass, mock_load_config, mock_summarize
):
    """未指定なら従来どおり settings シートの値を使う。"""
    config = _config(max_summarize="10")
    config["settings"]["general"]["resummarize_days"] = "7"
    config["settings"]["general"]["resummarize_limit"] = "50"
    mock_load_config.return_value = config
    bq = MagicMock()
    mock_bqclass.return_value = bq
    bq.get_favorite_tag_counts.return_value = []
    bq.get_unsummarized_articles.return_value = []

    main_mod._run_resummarize()

    bq.get_unsummarized_articles.assert_called_once_with(7, 50)


# --- 上限到達・予算超過での中断 ----------------------------------------------


@patch("collector.main.summarize_article")
@patch("collector.main.load_config")
@patch("collector.main.BQClient")
def test_resummarize_aborts_immediately_on_quota_error(
    mock_bqclass, mock_load_config, mock_summarize
):
    """上限到達を検知したら残りを呼ばずに中断する（無駄打ちの防止）。

    例外クラスは main が import したものを使う。main は bare import
    （from summarizer import ...）なので collector.summarizer から取ると
    別モジュールとして二重ロードされ except が一致しない。
    """
    QuotaExceededError = main_mod.QuotaExceededError

    mock_load_config.return_value = _config(max_summarize="10")
    bq = MagicMock()
    mock_bqclass.return_value = bq
    bq.get_favorite_tag_counts.return_value = []
    bq.get_unsummarized_articles.return_value = [
        {"article_id": f"a{i}", "title": "T", "url": "u", "source": "s", "content": "c"}
        for i in range(50)
    ]
    mock_summarize.side_effect = QuotaExceededError("usage limits")

    recovered, error_count = main_mod._run_resummarize()

    assert recovered == 0
    # 50件あっても1件目で止まる
    assert mock_summarize.call_count == 1


@patch("collector.main.score_article")
@patch("collector.main.load_config")
@patch("collector.main.BQClient")
def test_recalculate_aborts_immediately_on_quota_error(
    mock_bqclass, mock_load_config, mock_score
):
    QuotaExceededError = main_mod.QuotaExceededError

    mock_load_config.return_value = _config(max_summarize="10")
    bq = MagicMock()
    mock_bqclass.return_value = bq
    bq.get_favorite_tag_counts.return_value = []
    bq.get_outdated_summaries.return_value = [
        {"article_id": f"a{i}", "title": "T", "content": "c"} for i in range(50)
    ]
    mock_score.side_effect = QuotaExceededError("credit balance is too low")

    recalculated, _ = main_mod._run_recalculate()

    assert recalculated == 0
    assert mock_score.call_count == 1


@patch("collector.main.summarize_article")
@patch("collector.main.load_config")
@patch("collector.main.BQClient")
def test_resummarize_stops_when_budget_exceeded(
    mock_bqclass, mock_load_config, mock_summarize
):
    """1バッチの予算（settings: batch_budget_usd）を超えたら以降を処理しない。"""
    config = _config(max_summarize="10")
    config["settings"]["general"]["batch_budget_usd"] = "0.001"
    mock_load_config.return_value = config
    bq = MagicMock()
    mock_bqclass.return_value = bq
    bq.get_favorite_tag_counts.return_value = []
    bq.get_unsummarized_articles.return_value = [
        {"article_id": f"a{i}", "title": "T", "url": "u", "source": "s", "content": "c"}
        for i in range(10)
    ]

    def _spend(*args, **kwargs):
        # 1件で予算を超える量を積む
        kwargs["tracker"].add(input_tokens=1_000_000, output_tokens=0)
        return {"summary": "s", "tags": [], "importance_score": 0.9,
                "relevance_score": 0.9}

    mock_summarize.side_effect = _spend

    main_mod._run_resummarize()

    # 1件目で予算超過を検知し、2件目以降は呼ばない
    assert mock_summarize.call_count == 1


def test_default_batch_budget_is_unlimited():
    """既定は無制限（既存挙動を変えない）。"""
    assert main_mod._DEFAULT_BATCH_BUDGET_USD is None
