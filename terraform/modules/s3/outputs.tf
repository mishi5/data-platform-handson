output "raw_logs_bucket_name" {
  description = "生ログ保存用バケット名"
  value       = aws_s3_bucket.raw_logs.id
}

output "raw_logs_bucket_arn" {
  description = "生ログ保存用バケットARN"
  value       = aws_s3_bucket.raw_logs.arn
}

output "processed_logs_bucket_name" {
  description = "処理済みログ保存用バケット名"
  value       = aws_s3_bucket.processed_logs.id
}

output "processed_logs_bucket_arn" {
  description = "処理済みログ保存用バケットARN"
  value       = aws_s3_bucket.processed_logs.arn
}