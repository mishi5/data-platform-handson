output "repository_url" {
  description = "ECRリポジトリURL"
  value       = aws_ecr_repository.log_processor.repository_url
}

output "repository_name" {
  description = "ECRリポジトリ名"
  value       = aws_ecr_repository.log_processor.name
}

output "repository_arn" {
  description = "ECRリポジトリARN"
  value       = aws_ecr_repository.log_processor.arn
}
