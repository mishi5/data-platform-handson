# Lambda関数
resource "aws_lambda_function" "log_processor" {
  function_name = "log-processor"
  role          = var.lambda_role_arn
  package_type  = "Image"
  image_uri     = var.image_uri
  timeout       = 60
  memory_size   = 512

  environment {
    variables = {
      OUTPUT_BUCKET = var.processed_logs_bucket_name
    }
  }

  tags = {
    Name        = "Log Processor Lambda"
    Environment = "handson"
  }
}

# S3イベント通知の権限
resource "aws_lambda_permission" "allow_s3" {
  statement_id  = "AllowExecutionFromS3"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.log_processor.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = var.raw_logs_bucket_arn
}

# S3バケット通知設定
resource "aws_s3_bucket_notification" "log_upload" {
  bucket = var.raw_logs_bucket_name

  lambda_function {
    lambda_function_arn = aws_lambda_function.log_processor.arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "logs/"
    filter_suffix       = ".log"
  }

  depends_on = [aws_lambda_permission.allow_s3]
}
