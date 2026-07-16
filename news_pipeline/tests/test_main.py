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

    recovered = main_mod._run_resummarize()

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

    recovered = main_mod._run_resummarize()

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

    recovered = main_mod._run_resummarize()

    assert recovered == 0
    bq.insert_summaries.assert_not_called()
    bq.mark_article_summarized.assert_not_called()
