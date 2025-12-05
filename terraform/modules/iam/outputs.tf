output "lambda_role_arn" {
  description = "Lambda実行ロールのARN"
  value       = aws_iam_role.lambda_execution.arn
}

output "lambda_role_name" {
  description = "Lambda実行ロール名"
  value       = aws_iam_role.lambda_execution.name
}