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

# Cloud Run Service
resource "google_cloud_run_v2_service" "news_collector" {
  name                = "news-collector"
  location            = var.region
  ingress             = "INGRESS_TRAFFIC_ALL"
  deletion_protection = false

  template {
    containers {
      image = "asia-northeast1-docker.pkg.dev/${var.project_id}/news-collector/news-collector:latest"

      env {
        name  = "GCP_PROJECT_ID"
        value = var.project_id
      }
      env {
        name  = "MAX_ARTICLES"
        value = "20"
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
      env {
        name = "SLACK_SIGNING_SECRET"
        value_source {
          secret_key_ref {
            secret  = "slack-signing-secret"
            version = "latest"
          }
        }
      }

      resources {
        cpu_idle = false
      }
    }
  }
}

# Slack からのリクエストを受け付けるため未認証アクセスを許可
resource "google_cloud_run_service_iam_member" "allow_unauthenticated" {
  location = var.region
  service  = google_cloud_run_v2_service.news_collector.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Cloud Scheduler（平日7:30 JST = 22:30 UTC 前日）
resource "google_cloud_scheduler_job" "news_pipeline_trigger" {
  name      = "news-pipeline-daily"
  schedule  = "30 22 * * 0-4"
  time_zone = "UTC"
  region    = var.region

  http_target {
    http_method = "POST"
    uri         = "${google_cloud_run_v2_service.news_collector.uri}/"

    oidc_token {
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

# Cloud Run のデフォルトSAに Secret Manager アクセス権を付与
resource "google_project_iam_member" "cloudrun_secret_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${data.google_compute_default_service_account.default.email}"
}

data "google_compute_default_service_account" "default" {
  project = var.project_id
}
