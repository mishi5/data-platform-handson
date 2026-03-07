import pytest

@pytest.fixture
def sample_article():
    return {
        "article_id": "abc123",
        "title": "BigQuery new features 2026",
        "url": "https://cloud.google.com/blog/bigquery-2026",
        "source": "Google Cloud Blog",
        "published_at": "2026-03-08T09:00:00Z",
        "collected_at": "2026-03-08T10:00:00Z",
        "content": "BigQuery announced new features including...",
    }
