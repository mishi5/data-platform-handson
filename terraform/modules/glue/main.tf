# Glue Database
resource "aws_glue_catalog_database" "logs_database" {
  name        = "logs_database"
  description = "Database for log analysis"
}

# Glue Crawler用のIAMロール
resource "aws_iam_role" "glue_crawler" {
  name = "glue-crawler-logs-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "glue.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name        = "Glue Crawler Role"
    Environment = "handson"
  }
}

# Glue Crawlerの基本権限
resource "aws_iam_role_policy_attachment" "glue_service" {
  role       = aws_iam_role.glue_crawler.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole"
}

# S3アクセス権限
resource "aws_iam_role_policy" "glue_s3_access" {
  name = "glue-s3-access"
  role = aws_iam_role.glue_crawler.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          var.processed_logs_bucket_arn,
          "${var.processed_logs_bucket_arn}/*"
        ]
      }
    ]
  })
}

# Glue Crawler for Access Logs
resource "aws_glue_crawler" "access_logs" {
  name          = "access-logs-crawler"
  role          = aws_iam_role.glue_crawler.arn
  database_name = aws_glue_catalog_database.logs_database.name

  s3_target {
    path = "s3://${var.processed_logs_bucket_name}/parquet/access/"
  }

  configuration = jsonencode({
    Version = 1.0
    CrawlerOutput = {
      Partitions = {
        AddOrUpdateBehavior = "InheritFromTable"
      }
    }
  })

  tags = {
    Name        = "Access Logs Crawler"
    Environment = "handson"
  }
}

# Glue Crawler for App Logs
resource "aws_glue_crawler" "app_logs" {
  name          = "app-logs-crawler"
  role          = aws_iam_role.glue_crawler.arn
  database_name = aws_glue_catalog_database.logs_database.name

  s3_target {
    path = "s3://${var.processed_logs_bucket_name}/parquet/app/"
  }

  configuration = jsonencode({
    Version = 1.0
    CrawlerOutput = {
      Partitions = {
        AddOrUpdateBehavior = "InheritFromTable"
      }
    }
  })

  tags = {
    Name        = "App Logs Crawler"
    Environment = "handson"
  }
}
