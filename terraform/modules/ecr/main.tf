# ECRリポジトリ
resource "aws_ecr_repository" "log_processor" {
  name                 = "log-processor"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Name        = "Log Processor Repository"
    Environment = "handson"
  }
}

# ライフサイクルポリシー(古いイメージを自動削除してコスト削減)
resource "aws_ecr_lifecycle_policy" "log_processor" {
  repository = aws_ecr_repository.log_processor.name

  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep last 5 images"
      selection = {
        tagStatus     = "any"
        countType     = "imageCountMoreThan"
        countNumber   = 5
      }
      action = {
        type = "expire"
      }
    }]
  })
}
