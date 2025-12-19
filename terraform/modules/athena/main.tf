# Athena Workgroup
resource "aws_athena_workgroup" "logs_analysis" {
  name        = "logs-analysis"
  description = "Workgroup for log analysis"

  configuration {
    result_configuration {
      output_location = "s3://${var.athena_results_bucket_name}/query-results/"

      encryption_configuration {
        encryption_option = "SSE_S3"
      }
    }

    enforce_workgroup_configuration    = true
    publish_cloudwatch_metrics_enabled = true
  }

  tags = {
    Name        = "Logs Analysis Workgroup"
    Environment = "handson"
  }
}
