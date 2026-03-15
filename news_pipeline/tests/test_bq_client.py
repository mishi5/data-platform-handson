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
    mock_row.keys.return_value = ["article_id", "title", "url", "source", "summary", "importance_score", "notified_at"]
    _data = {
        "article_id": "abc123", "title": "Test", "url": "https://example.com",
        "source": "Test Source", "summary": "summary text", "importance_score": 0.8, "notified_at": None,
    }
    mock_row.__getitem__ = lambda self, key: _data[key]
    mock_client.query.return_value.result.return_value = [mock_row]

    bq = BQClient(project="test-project")
    result = bq.get_unnotified_summaries()

    assert isinstance(result, list)
    query_arg = mock_client.query.call_args[0][0]
    assert "notified_at IS NULL" in query_arg
    assert "summaries" in query_arg


@patch("collector.bq_client.bigquery.Client")
def test_mark_summaries_notified_runs_update(mock_bq_class):
    mock_client = MagicMock()
    mock_bq_class.return_value = mock_client
    mock_client.query.return_value.result.return_value = []

    bq = BQClient(project="test-project")
    bq.mark_summaries_notified(["id1", "id2"])

    query_arg = mock_client.query.call_args[0][0]
    assert "UPDATE" in query_arg
    assert "notified_at" in query_arg
    assert "id1" in query_arg


@patch("collector.bq_client.bigquery.Client")
def test_mark_summaries_notified_skips_empty(mock_bq_class):
    mock_client = MagicMock()
    mock_bq_class.return_value = mock_client

    bq = BQClient(project="test-project")
    bq.mark_summaries_notified([])

    mock_client.query.assert_not_called()


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
    articles = [{"article_id": "abc", "title": "T", "url": "https://x.com", "source": "s",
                 "published_at": None, "collected_at": "2026-03-08T10:00:00Z", "content": "body"}]
    bq.insert_raw_articles(articles)

    mock_client.insert_rows_json.assert_called_once()


@patch("collector.bq_client.bigquery.Client")
def test_insert_summaries_calls_insert_rows(mock_bq_class):
    mock_client = MagicMock()
    mock_bq_class.return_value = mock_client
    mock_client.insert_rows_json.return_value = []

    bq = BQClient(project="test-project")
    summaries = [{"article_id": "abc", "title": "T", "url": "u", "source": "s",
                  "summary": "sum", "tags": ["bigquery"], "importance_score": 0.9}]
    bq.insert_summaries(summaries)

    mock_client.insert_rows_json.assert_called_once()
