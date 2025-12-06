output "function_name" {
  description = "Lambda関数名"
  value       = aws_lambda_function.log_processor.function_name
}

output "function_arn" {
  description = "Lambda関数ARN"
  value       = aws_lambda_function.log_processor.arn
}
