output "raw_logs_bucket_name" {
  description = "生ログバケット名"
  value       = module.s3.raw_logs_bucket_name
}

output "processed_logs_bucket_name" {
  description = "処理済みログバケット名"
  value       = module.s3.processed_logs_bucket_name
}

output "lambda_role_arn" {
  description = "Lambda実行ロールARN"
  value       = module.iam.lambda_role_arn
}

output "ecr_repository_url" {
  description = "ECRリポジトリURL"
  value       = module.ecr.repository_url
}

output "lambda_function_name" {
  description = "Lambda関数名"
  value       = module.lambda.function_name
}
