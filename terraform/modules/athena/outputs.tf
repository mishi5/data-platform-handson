output "workgroup_name" {
  description = "Athena Workgroup名"
  value       = aws_athena_workgroup.logs_analysis.name
}

output "workgroup_arn" {
  description = "Athena Workgroup ARN"
  value       = aws_athena_workgroup.logs_analysis.arn
}
