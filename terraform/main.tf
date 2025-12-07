terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  # S3バックエンド設定
  backend "s3" {
    bucket         = "terraform-state-data-platform-handson-344085827455" # 自分のアカウントIDに変更
    key            = "terraform.tfstate"
    region         = "ap-northeast-1"
    encrypt        = true
    dynamodb_table = "terraform-state-lock"
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project   = "data-platform-handson"
      ManagedBy = "terraform"
    }
  }
}

# S3モジュール
module "s3" {
  source = "./modules/s3"
}

# IAMモジュール
module "iam" {
  source = "./modules/iam"

  raw_logs_bucket_arn       = module.s3.raw_logs_bucket_arn
  processed_logs_bucket_arn = module.s3.processed_logs_bucket_arn
}

# ECRモジュール
module "ecr" {
  source = "./modules/ecr"
}

# Lambda関数モジュール (最初はコメントアウト)
module "lambda" {
  source = "./modules/lambda"

  lambda_role_arn            = module.iam.lambda_role_arn
  image_uri                  = "${module.ecr.repository_url}:latest"
  raw_logs_bucket_name       = module.s3.raw_logs_bucket_name
  raw_logs_bucket_arn        = module.s3.raw_logs_bucket_arn
  processed_logs_bucket_name = module.s3.processed_logs_bucket_name
}