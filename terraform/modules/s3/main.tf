# ランダムなサフィックスを生成(バケット名の重複を避けるため)
resource "random_id" "bucket_suffix" {
  byte_length = 4
}

# 生ログ保存用バケット
resource "aws_s3_bucket" "raw_logs" {
  bucket = "log-analysis-raw-${random_id.bucket_suffix.hex}"

  tags = {
    Name        = "Raw Logs Bucket"
    Environment = "handson"
    Purpose     = "log-analysis"
  }
}

# 処理済みデータ保存用バケット
resource "aws_s3_bucket" "processed_logs" {
  bucket = "log-analysis-processed-${random_id.bucket_suffix.hex}"

  tags = {
    Name        = "Processed Logs Bucket"
    Environment = "handson"
    Purpose     = "log-analysis"
  }
}

# バージョニング設定(誤削除対策)
resource "aws_s3_bucket_versioning" "raw_logs" {
  bucket = aws_s3_bucket.raw_logs.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_versioning" "processed_logs" {
  bucket = aws_s3_bucket.processed_logs.id

  versioning_configuration {
    status = "Enabled"
  }
}

# ライフサイクルルール(コスト削減のため30日後に削除)
resource "aws_s3_bucket_lifecycle_configuration" "raw_logs" {
  bucket = aws_s3_bucket.raw_logs.id

  rule {
    id     = "delete-old-logs"
    status = "Enabled"

    filter {
      prefix = ""
    }

    expiration {
      days = 30
    }
  }
}

# パブリックアクセスブロック(セキュリティ)
resource "aws_s3_bucket_public_access_block" "raw_logs" {
  bucket = aws_s3_bucket.raw_logs.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_public_access_block" "processed_logs" {
  bucket = aws_s3_bucket.processed_logs.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}