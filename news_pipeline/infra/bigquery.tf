resource "google_bigquery_dataset" "tech_news" {
  dataset_id = "tech_news"
  location   = var.region
}

resource "google_bigquery_table" "raw_articles" {
  dataset_id          = google_bigquery_dataset.tech_news.dataset_id
  table_id            = "raw_articles"
  deletion_protection = false

  schema = jsonencode([
    { name = "article_id",   type = "STRING",    mode = "REQUIRED" },
    { name = "title",        type = "STRING",    mode = "REQUIRED" },
    { name = "url",          type = "STRING",    mode = "REQUIRED" },
    { name = "source",       type = "STRING",    mode = "REQUIRED" },
    { name = "published_at", type = "TIMESTAMP", mode = "NULLABLE" },
    { name = "collected_at", type = "TIMESTAMP", mode = "REQUIRED" },
    { name = "content",      type = "STRING",    mode = "NULLABLE" },
  ])
}

resource "google_bigquery_table" "summaries" {
  dataset_id          = google_bigquery_dataset.tech_news.dataset_id
  table_id            = "summaries"
  deletion_protection = false

  schema = jsonencode([
    { name = "article_id",       type = "STRING",  mode = "REQUIRED" },
    { name = "title",            type = "STRING",  mode = "REQUIRED" },
    { name = "url",              type = "STRING",  mode = "REQUIRED" },
    { name = "source",           type = "STRING",  mode = "REQUIRED" },
    { name = "summary",          type = "STRING",  mode = "NULLABLE" },
    { name = "tags",             type = "STRING",  mode = "REPEATED" },
    { name = "importance_score", type = "FLOAT64", mode = "NULLABLE" },
  ])
}

resource "google_bigquery_table" "notification_log" {
  dataset_id          = google_bigquery_dataset.tech_news.dataset_id
  table_id            = "notification_log"
  deletion_protection = false

  schema = jsonencode([
    { name = "article_id",  type = "STRING",    mode = "REQUIRED" },
    { name = "notified_at", type = "TIMESTAMP", mode = "REQUIRED" },
  ])
}

resource "google_bigquery_table" "article_chunks" {
  dataset_id          = google_bigquery_dataset.tech_news.dataset_id
  table_id            = "article_chunks"
  deletion_protection = false

  schema = jsonencode([
    { name = "chunk_id",   type = "STRING", mode = "REQUIRED" },
    { name = "article_id", type = "STRING", mode = "REQUIRED" },
    { name = "chunk_text", type = "STRING", mode = "NULLABLE" },
    { name = "embedding",  type = "FLOAT64", mode = "REPEATED" },
  ])
}
