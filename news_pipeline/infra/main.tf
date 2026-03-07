terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# Cloud Run Job
resource "google_cloud_run_v2_job" "news_collector" {
  name     = "news-collector"
  location = var.region

  template {
    template {
      containers {
        image = "gcr.io/${var.project_id}/news-collector:latest"

        env {
          name  = "GCP_PROJECT_ID"
          value = var.project_id
        }
        env {
          name = "ANTHROPIC_API_KEY"
          value_source {
            secret_key_ref {
              secret  = "anthropic-api-key"
              version = "latest"
            }
          }
        }
        env {
          name = "SLACK_WEBHOOK_URL"
          value_source {
            secret_key_ref {
              secret  = "slack-webhook-url"
              version = "latest"
            }
          }
        }
      }
    }
  }
}

# Cloud Scheduler（平日7:30 JST = 22:30 UTC 前日）
resource "google_cloud_scheduler_job" "news_pipeline_trigger" {
  name      = "news-pipeline-daily"
  schedule  = "30 22 * * 0-4"
  time_zone = "UTC"
  region    = var.region

  http_target {
    http_method = "POST"
    uri         = "https://${var.region}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${var.project_id}/jobs/news-collector:run"

    oauth_token {
      service_account_email = google_service_account.scheduler.email
    }
  }
}

resource "google_service_account" "scheduler" {
  account_id   = "news-pipeline-scheduler"
  display_name = "News Pipeline Scheduler"
}

resource "google_project_iam_member" "scheduler_run_invoker" {
  project = var.project_id
  role    = "roles/run.invoker"
  member  = "serviceAccount:${google_service_account.scheduler.email}"
}
