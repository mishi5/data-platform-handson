from unittest.mock import MagicMock, patch
from collector.bq_client import BQClient


@patch("collector.bq_client.bigquery.Client")
def test_get_existing_urls_queries_raw_articles(mock_bq_class):
    mock_client = MagicMock()
    mock_bq_class.return_value = mock_client

    mock_row1 = MagicMock()
    mock_row1.url = "https://example.com/1"
    mock_client.query.return_value.result.return_value = [mock_row1]

    bq = BQClient(project="test-project")
    urls = bq.get_existing_urls()

    assert urls == {"https://example.com/1"}
    query_arg = mock_client.query.call_args[0][0]
    assert "raw_articles" in query_arg
    assert "summaries" not in query_arg


@patch("collector.bq_client.bigquery.Client")
def test_get_unnotified_summaries_returns_list(mock_bq_class):
    mock_client = MagicMock()
    mock_bq_class.return_value = mock_client

    mock_row = MagicMock()
    _data = {
        "article_id": "abc123",
        "title": "Test",
        "url": "https://example.com",
        "source": "Test Source",
        "summary": "summary text",
        "importance_score": 0.8,
    }
    mock_row.keys.return_value = list(_data.keys())
    mock_row.__getitem__ = lambda self, key: _data[key]
    mock_client.query.return_value.result.return_value = [mock_row]

    bq = BQClient(project="test-project")
    result = bq.get_unnotified_summaries()

    assert isinstance(result, list)
    query_arg = mock_client.query.call_args[0][0]
    assert "notification_log" in query_arg
    assert "summaries" in query_arg
    assert "LEFT JOIN" in query_arg


@patch("collector.bq_client.bigquery.Client")
def test_mark_summaries_notified_inserts_to_log(mock_bq_class):
    mock_client = MagicMock()
    mock_bq_class.return_value = mock_client
    mock_client.insert_rows_json.return_value = []

    bq = BQClient(project="test-project")
    bq.mark_summaries_notified(["id1", "id2"])

    mock_client.insert_rows_json.assert_called_once()
    call_args = mock_client.insert_rows_json.call_args
    assert "notification_log" in call_args[0][0]
    rows = call_args[0][1]
    assert len(rows) == 2
    assert rows[0]["article_id"] == "id1"
    assert "notified_at" in rows[0]


@patch("collector.bq_client.bigquery.Client")
def test_mark_summaries_notified_skips_empty(mock_bq_class):
    mock_client = MagicMock()
    mock_bq_class.return_value = mock_client

    bq = BQClient(project="test-project")
    bq.mark_summaries_notified([])

    mock_client.insert_rows_json.assert_not_called()


@patch("collector.bq_client.bigquery.Client")
def test_get_existing_urls_returns_set(mock_bq_class):
    mock_client = MagicMock()
    mock_bq_class.return_value = mock_client

    mock_row1 = MagicMock()
    mock_row1.url = "https://example.com/1"
    mock_row2 = MagicMock()
    mock_row2.url = "https://example.com/2"
    mock_client.query.return_value.result.return_value = [mock_row1, mock_row2]

    bq = BQClient(project="test-project")
    urls = bq.get_existing_urls()

    assert urls == {"https://example.com/1", "https://example.com/2"}


@patch("collector.bq_client.bigquery.Client")
def test_insert_raw_articles_calls_insert_rows(mock_bq_class):
    mock_client = MagicMock()
    mock_bq_class.return_value = mock_client
    mock_client.insert_rows_json.return_value = []  # no errors

    bq = BQClient(project="test-project")
    articles = [
        {
            "article_id": "abc",
            "title": "T",
            "url": "https://x.com",
            "source": "s",
            "published_at": None,
            "collected_at": "2026-03-08T10:00:00Z",
            "content": "body",
        }
    ]
    bq.insert_raw_articles(articles)

    mock_client.insert_rows_json.assert_called_once()


@patch("collector.bq_client.bigquery.Client")
def test_insert_pipeline_log_calls_insert_rows(mock_bq_class):
    mock_client = MagicMock()
    mock_bq_class.return_value = mock_client
    mock_client.insert_rows_json.return_value = []

    bq = BQClient(project="test-project")
    log = {
        "run_id": "run-1",
        "triggered_by": "scheduler",
        "started_at": "2026-03-16T10:00:00Z",
        "finished_at": "2026-03-16T10:01:00Z",
        "articles_fetched": 10,
        "new_articles": 5,
        "summaries_generated": 3,
        "notified_count": 3,
        "error_count": 0,
        "status": "success",
        "error_message": None,
        "keywords": ["dbt", "BigQuery"],
    }
    bq.insert_pipeline_log(log)

    mock_client.insert_rows_json.assert_called_once()
    call_args = mock_client.insert_rows_json.call_args
    assert "pipeline_logs" in call_args[0][0]
    assert call_args[0][1][0]["run_id"] == "run-1"
    assert call_args[0][1][0]["keywords"] == ["dbt", "BigQuery"]


@patch("collector.bq_client.bigquery.Client")
def test_get_deepdive_returns_text_when_found(mock_bq_class):
    mock_client = MagicMock()
    mock_bq_class.return_value = mock_client

    mock_row = MagicMock()
    mock_row.deepdive_text = "📌 背景...\n🔍 技術的なポイント..."
    mock_client.query.return_value.result.return_value = [mock_row]

    bq = BQClient(project="test-project")
    result = bq.get_deepdive("abc12345")

    assert result == "📌 背景...\n🔍 技術的なポイント..."
    query_arg = mock_client.query.call_args[0][0]
    assert "deepdives" in query_arg
    # article_id は SQL に埋め込まずクエリパラメータで渡す（SQLi 対策）
    assert "abc12345" not in query_arg
    job_config = mock_client.query.call_args.kwargs["job_config"]
    params = {p.name: p.value for p in job_config.query_parameters}
    assert params["aid"] == "abc12345"


@patch("collector.bq_client.bigquery.Client")
def test_get_deepdive_returns_none_when_not_found(mock_bq_class):
    mock_client = MagicMock()
    mock_bq_class.return_value = mock_client
    mock_client.query.return_value.result.return_value = []

    bq = BQClient(project="test-project")
    result = bq.get_deepdive("notfound")

    assert result is None


@patch("collector.bq_client.bigquery.Client")
def test_insert_deepdive_calls_insert_rows(mock_bq_class):
    mock_client = MagicMock()
    mock_bq_class.return_value = mock_client
    mock_client.insert_rows_json.return_value = []

    bq = BQClient(project="test-project")
    bq.insert_deepdive("abc123full", "深堀りテキスト")

    mock_client.insert_rows_json.assert_called_once()
    call_args = mock_client.insert_rows_json.call_args
    assert "deepdives" in call_args[0][0]
    row = call_args[0][1][0]
    assert row["article_id"] == "abc123full"
    assert row["deepdive_text"] == "深堀りテキスト"
    assert "created_at" in row


@patch("collector.bq_client.bigquery.Client")
def test_get_article_by_id_returns_dict_when_found(mock_bq_class):
    mock_client = MagicMock()
    mock_bq_class.return_value = mock_client

    mock_row = MagicMock()
    _data = {
        "article_id": "abc12345xyz",
        "title": "BigQuery update",
        "url": "https://example.com",
        "content": "article body",
    }
    mock_row.keys.return_value = list(_data.keys())
    mock_row.__getitem__ = lambda self, key: _data[key]
    mock_client.query.return_value.result.return_value = [mock_row]

    bq = BQClient(project="test-project")
    result = bq.get_article_by_id("abc12345")

    assert result is not None
    assert result["article_id"] == "abc12345xyz"
    query_arg = mock_client.query.call_args[0][0]
    assert "raw_articles" in query_arg
    assert "summaries" in query_arg
    # プレフィックスは SQL に埋め込まずクエリパラメータで渡す（SQLi 対策）
    assert "abc12345" not in query_arg
    job_config = mock_client.query.call_args.kwargs["job_config"]
    params = {p.name: p.value for p in job_config.query_parameters}
    assert params["prefix"] == "abc12345"


@patch("collector.bq_client.bigquery.Client")
def test_favorites_queries_use_parameters(mock_bq_class):
    """delete_favorite / is_favorited は article_id をパラメータで渡す（SQLi 対策）。"""
    mock_client = MagicMock()
    mock_bq_class.return_value = mock_client
    mock_client.query.return_value.result.return_value = []

    bq = BQClient(project="test-project")
    malicious = "x' OR '1'='1"

    bq.delete_favorite(malicious)
    q = mock_client.query.call_args[0][0]
    assert malicious not in q
    params = {
        p.name: p.value
        for p in mock_client.query.call_args.kwargs["job_config"].query_parameters
    }
    assert params["aid"] == malicious

    bq.is_favorited(malicious)
    q = mock_client.query.call_args[0][0]
    assert malicious not in q
    params = {
        p.name: p.value
        for p in mock_client.query.call_args.kwargs["job_config"].query_parameters
    }
    assert params["aid"] == malicious


@patch("collector.bq_client.bigquery.Client")
def test_get_article_by_id_returns_none_when_not_found(mock_bq_class):
    mock_client = MagicMock()
    mock_bq_class.return_value = mock_client
    mock_client.query.return_value.result.return_value = []

    bq = BQClient(project="test-project")
    result = bq.get_article_by_id("notfound")

    assert result is None


@patch("collector.bq_client.bigquery.Client")
def test_get_top_undived_article_returns_dict(mock_bq_class):
    mock_client = MagicMock()
    mock_bq_class.return_value = mock_client

    mock_row = MagicMock()
    _data = {
        "article_id": "top123",
        "title": "Top article",
        "url": "https://example.com/top",
        "content": "top content",
    }
    mock_row.keys.return_value = list(_data.keys())
    mock_row.__getitem__ = lambda self, key: _data[key]
    mock_client.query.return_value.result.return_value = [mock_row]

    bq = BQClient(project="test-project")
    result = bq.get_top_undived_article()

    assert result is not None
    assert result["article_id"] == "top123"
    query_arg = mock_client.query.call_args[0][0]
    assert "deepdives" in query_arg
    assert "importance_score" in query_arg


@patch("collector.bq_client.bigquery.Client")
def test_get_top_undived_article_returns_none_when_all_dived(mock_bq_class):
    mock_client = MagicMock()
    mock_bq_class.return_value = mock_client
    mock_client.query.return_value.result.return_value = []

    bq = BQClient(project="test-project")
    result = bq.get_top_undived_article()

    assert result is None


@patch("collector.bq_client.bigquery.Client")
def test_insert_summaries_calls_insert_rows(mock_bq_class):
    mock_client = MagicMock()
    mock_bq_class.return_value = mock_client
    mock_client.insert_rows_json.return_value = []

    bq = BQClient(project="test-project")
    summaries = [
        {
            "article_id": "abc",
            "title": "T",
            "url": "u",
            "source": "s",
            "summary": "sum",
            "tags": ["bigquery"],
            "importance_score": 0.9,
        }
    ]
    bq.insert_summaries(summaries)

    mock_client.insert_rows_json.assert_called_once()


@patch("collector.bq_client.bigquery.Client")
def test_get_pending_articles_filters_pending_and_retry(mock_bq_class):
    mock_client = MagicMock()
    mock_bq_class.return_value = mock_client

    _data = {
        "article_id": "p1",
        "url": "https://example.com/p1",
        "title": "Pending",
        "source": "Src",
        "retry_count": 1,
    }
    mock_row = MagicMock()
    mock_row.keys.return_value = list(_data.keys())
    mock_row.__getitem__ = lambda self, key: _data[key]
    mock_client.query.return_value.result.return_value = [mock_row]

    bq = BQClient(project="test-project")
    result = bq.get_pending_articles(max_retries=3)

    assert isinstance(result, list)
    assert result[0]["article_id"] == "p1"
    query_arg = mock_client.query.call_args[0][0]
    assert "raw_articles" in query_arg
    assert "content_status" in query_arg
    assert "pending" in query_arg
    assert "retry_count" in query_arg


@patch("collector.bq_client.bigquery.Client")
def test_get_pending_articles_applies_limit_and_fifo_order(mock_bq_class):
    mock_client = MagicMock()
    mock_bq_class.return_value = mock_client
    mock_client.query.return_value.result.return_value = []

    bq = BQClient(project="test-project")
    bq.get_pending_articles(max_retries=3, limit=5)

    query_arg = mock_client.query.call_args[0][0]
    # 古い順（FIFO）に並べてバジェット分だけ取得する
    assert "ORDER BY" in query_arg
    assert "collected_at" in query_arg
    assert "LIMIT" in query_arg
    # limit はクエリパラメータとして渡す
    job_config = mock_client.query.call_args.kwargs["job_config"]
    param_names = {p.name for p in job_config.query_parameters}
    assert "limit" in param_names


@patch("collector.bq_client.bigquery.Client")
def test_update_article_content_runs_update_dml(mock_bq_class):
    mock_client = MagicMock()
    mock_bq_class.return_value = mock_client

    bq = BQClient(project="test-project")
    bq.update_article_content("p1", "body text", "ok", 1)

    query_arg = mock_client.query.call_args[0][0]
    assert "UPDATE" in query_arg
    assert "raw_articles" in query_arg
    assert "content_status" in query_arg


@patch("collector.bq_client.bigquery.Client")
def test_update_article_content_swallows_streaming_buffer_error(mock_bq_class):
    mock_client = MagicMock()
    mock_bq_class.return_value = mock_client
    mock_client.query.return_value.result.side_effect = Exception(
        "UPDATE or DELETE statement over table would affect rows in the streaming buffer"
    )

    bq = BQClient(project="test-project")
    # 例外を送出せず黙って握りつぶす（pending のまま次回に回す）
    bq.update_article_content("p1", "body text", "ok", 1)


@patch("collector.bq_client.bigquery.Client")
def test_get_outdated_summaries_filters_version(mock_bq_class):
    mock_client = MagicMock()
    mock_bq_class.return_value = mock_client
    _data = {"article_id": "a1", "title": "T", "content": "body", "source": "S"}
    mock_row = MagicMock()
    mock_row.keys.return_value = list(_data.keys())
    mock_row.__getitem__ = lambda self, key: _data[key]
    mock_client.query.return_value.result.return_value = [mock_row]

    bq = BQClient(project="test-project")
    result = bq.get_outdated_summaries(version=2, limit=50)

    assert result[0]["article_id"] == "a1"
    q = mock_client.query.call_args[0][0]
    assert "summaries" in q
    assert "raw_articles" in q
    assert "scoring_version" in q
    assert "LEFT JOIN" in q
    assert "LIMIT" in q


@patch("collector.bq_client.bigquery.Client")
def test_update_summary_score_runs_update_dml(mock_bq_class):
    mock_client = MagicMock()
    mock_bq_class.return_value = mock_client

    bq = BQClient(project="test-project")
    bq.update_summary_score("a1", 0.9, 2)

    q = mock_client.query.call_args[0][0]
    assert "UPDATE" in q
    assert "summaries" in q
    assert "scoring_version" in q
    assert "importance_score" in q


@patch("collector.bq_client.bigquery.Client")
def test_get_unsummarized_articles_filters_orphans(mock_bq_class):
    mock_client = MagicMock()
    mock_bq_class.return_value = mock_client
    _data = {
        "article_id": "o1",
        "title": "Orphan",
        "url": "https://example.com/o1",
        "source": "Src",
        "content": "body",
    }
    mock_row = MagicMock()
    mock_row.keys.return_value = list(_data.keys())
    mock_row.__getitem__ = lambda self, key: _data[key]
    mock_client.query.return_value.result.return_value = [mock_row]

    bq = BQClient(project="test-project")
    result = bq.get_unsummarized_articles(days=7, limit=50)

    assert result[0]["article_id"] == "o1"
    q = mock_client.query.call_args[0][0]
    assert "raw_articles" in q
    assert "summaries" in q
    assert "LEFT JOIN" in q
    assert "IS NULL" in q  # summaries に無い
    assert "content_status = 'ok'" in q
    assert "ORDER BY" in q
    assert "collected_at" in q
    assert "LIMIT" in q
    param_names = {
        p.name
        for p in mock_client.query.call_args.kwargs["job_config"].query_parameters
    }
    assert "days" in param_names and "limit" in param_names


@patch("collector.bq_client.bigquery.Client")
def test_get_favorite_tag_counts_aggregates_tags(mock_bq_class):
    """favorites × summaries のタグを集計し、出現2回以上を頻度降順で返す。"""
    mock_client = MagicMock()
    mock_bq_class.return_value = mock_client
    row1 = MagicMock()
    row1.tag = "bigquery"
    row2 = MagicMock()
    row2.tag = "dbt"
    mock_client.query.return_value.result.return_value = [row1, row2]

    bq = BQClient(project="test-project")
    tags = bq.get_favorite_tag_counts(limit=5)

    assert tags == ["bigquery", "dbt"]
    q = mock_client.query.call_args[0][0]
    assert "favorites" in q
    assert "summaries" in q
    assert "UNNEST" in q
    assert "HAVING cnt >= 2" in q
    assert "ORDER BY cnt DESC" in q
    params = {
        p.name: p.value
        for p in mock_client.query.call_args.kwargs["job_config"].query_parameters
    }
    assert params["limit"] == 5


@patch("collector.bq_client.bigquery.Client")
def test_mark_article_summarized_runs_update_dml(mock_bq_class):
    mock_client = MagicMock()
    mock_bq_class.return_value = mock_client

    bq = BQClient(project="test-project")
    bq.mark_article_summarized("o1")

    q = mock_client.query.call_args[0][0]
    assert "UPDATE" in q
    assert "raw_articles" in q
    assert "summarized" in q


@patch("collector.bq_client.bigquery.Client")
def test_mark_article_summarized_swallows_streaming_buffer_error(mock_bq_class):
    mock_client = MagicMock()
    mock_bq_class.return_value = mock_client
    mock_client.query.return_value.result.side_effect = Exception(
        "UPDATE or DELETE statement over table would affect rows in the streaming buffer"
    )

    bq = BQClient(project="test-project")
    # 例外を送出しない
    bq.mark_article_summarized("o1")
