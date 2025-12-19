output "database_name" {
  description = "Glue Database名"
  value       = aws_glue_catalog_database.logs_database.name
}

output "access_crawler_name" {
  description = "Access Logs Crawler名"
  value       = aws_glue_crawler.access_logs.name
}

output "app_crawler_name" {
  description = "App Logs Crawler名"
  value       = aws_glue_crawler.app_logs.name
}
