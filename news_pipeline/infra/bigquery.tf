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
    { name = "content",        type = "STRING",    mode = "NULLABLE" },
    { name = "content_status", type = "STRING",    mode = "NULLABLE" },
    { name = "retry_count",    type = "INT64",     mode = "NULLABLE" },
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

resource "google_bigquery_table" "pipeline_logs" {
  dataset_id          = google_bigquery_dataset.tech_news.dataset_id
  table_id            = "pipeline_logs"
  deletion_protection = false

  schema = jsonencode([
    { name = "run_id",              type = "STRING",    mode = "REQUIRED" },
    { name = "triggered_by",        type = "STRING",    mode = "REQUIRED" },
    { name = "started_at",          type = "TIMESTAMP", mode = "REQUIRED" },
    { name = "finished_at",         type = "TIMESTAMP", mode = "NULLABLE" },
    { name = "articles_fetched",    type = "INT64",     mode = "NULLABLE" },
    { name = "new_articles",        type = "INT64",     mode = "NULLABLE" },
    { name = "summaries_generated", type = "INT64",     mode = "NULLABLE" },
    { name = "notified_count",      type = "INT64",     mode = "NULLABLE" },
    { name = "error_count",         type = "INT64",     mode = "NULLABLE" },
    { name = "status",              type = "STRING",    mode = "REQUIRED" },
    { name = "error_message",       type = "STRING",    mode = "NULLABLE" },
    { name = "keywords",            type = "STRING",    mode = "REPEATED" },
  ])
}

resource "google_bigquery_table" "deepdives" {
  dataset_id          = google_bigquery_dataset.tech_news.dataset_id
  table_id            = "deepdives"
  deletion_protection = false

  schema = jsonencode([
    { name = "article_id",    type = "STRING",    mode = "REQUIRED" },
    { name = "deepdive_text", type = "STRING",    mode = "REQUIRED" },
    { name = "created_at",    type = "TIMESTAMP", mode = "REQUIRED" },
  ])
}

resource "google_bigquery_table" "favorites" {
  dataset_id          = google_bigquery_dataset.tech_news.dataset_id
  table_id            = "favorites"
  deletion_protection = false

  schema = jsonencode([
    { name = "article_id",   type = "STRING",    mode = "REQUIRED" },
    { name = "favorited_at", type = "TIMESTAMP", mode = "REQUIRED" },
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
