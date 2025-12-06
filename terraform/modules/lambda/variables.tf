variable "lambda_role_arn" {
  description = "Lambda実行ロールのARN"
  type        = string
}

variable "image_uri" {
  description = "DockerイメージのURI"
  type        = string
}

variable "raw_logs_bucket_name" {
  description = "生ログバケット名"
  type        = string
}

variable "raw_logs_bucket_arn" {
  description = "生ログバケットのARN"
  type        = string
}

variable "processed_logs_bucket_name" {
  description = "処理済みログバケット名"
  type        = string
}
