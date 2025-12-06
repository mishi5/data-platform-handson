# Phase 1: 基礎編 セットアップガイド

## 概要

このドキュメントは、AWSを使ったログ分析基盤のPhase 1（基礎編）の構築手順と、実際に遭遇したトラブルシューティングをまとめたものです。

## アーキテクチャ
```
[サンプルログ] → S3 (raw) → Lambda (Docker) → S3 (processed)
                              ↓
                          CloudWatch Logs
```

### 使用技術
- **IaC**: Terraform
- **コンテナ**: Docker
- **AWS**: S3, Lambda, ECR, IAM, CloudWatch Logs
- **言語**: Python 3.12

## 前提条件

- macOS
- Docker Desktop インストール済み
- VSCode インストール済み
- 既存のAWSアカウント（3-4年前作成）

## Step 1: 環境準備 (30分)

### 1-1. 予算アラート設定
```bash
# AWSコンソールにrootユーザーでログイン
# https://console.aws.amazon.com/billing/home#/budgets

# 2つの予算を作成:
# 1. 月次予算: $50（80%で通知）
# 2. 早期警告: $10（100%で通知）
```

### 1-2. IAMユーザー作成
```bash
# IAMコンソール: https://console.aws.amazon.com/iam/

# ユーザー名: terraform-handson-user
# アクセス権限: AdministratorAccess（学習用）
# アクセスキーを作成してメモ
```

### 1-3. AWS CLI設定
```bash
# AWS CLIインストール
brew install awscli

# 認証情報設定
aws configure
# Access Key ID: (作成したアクセスキー)
# Secret Access Key: (シークレットキー)
# Region: ap-northeast-1
# Output format: json

# 確認
aws sts get-caller-identity
```

### 1-4. Terraformインストール
```bash
# tfenvインストール
brew install tfenv

# 最新安定版をインストール
tfenv install latest
tfenv use latest

# 確認
terraform version
```

### 1-5. プロジェクト初期化
```bash
# プロジェクトディレクトリ作成
mkdir -p ~/dev/data-platform-handson
cd ~/dev/data-platform-handson

# ディレクトリ構造作成
mkdir -p terraform/modules/{s3,iam,lambda,ecr}
mkdir -p docker/log-processor
mkdir -p sample-data
mkdir -p .github/workflows
mkdir -p docs

# Git初期化
git init

# .gitignore作成
cat << 'EOF' > .gitignore
# Terraform
.terraform/
*.tfstate
*.tfstate.*
.terraform.lock.hcl
terraform.tfvars

# Python
__pycache__/
*.py[cod]
*$py.class
.venv/
venv/
*.egg-info/

# IDE
.vscode/
.idea/

# AWS
.aws/

# OS
.DS_Store

# Environment
.env
*.pem
*.key

# Logs
*.log
EOF

# README作成
cat << 'EOF' > README.md
# Data Platform Handson

AWSを使ったデータ分析基盤構築のハンズオン

## 構成
- Docker
- Terraform
- AWS (Lambda, S3, Athena, ECR)
- GitHub Actions (CI/CD)

## 学習内容
- インフラコード化(IaC)
- コンテナ化
- CI/CDパイプライン構築
- ログ分析基盤構築
EOF

# GitHubリポジトリ作成後
git remote add origin https://github.com/YOUR_USERNAME/data-platform-handson.git
git add .
git commit -m "Initial commit"
git branch -M main
git push -u origin main
```

## Step 2: Terraformでインフラ構築 (60分)

### 2-1. S3モジュール作成

**terraform/modules/s3/main.tf**
```hcl
# ランダムなサフィックスを生成
resource "random_id" "bucket_suffix" {
  byte_length = 4
}

# 生ログ保存用バケット
resource "aws_s3_bucket" "raw_logs" {
  bucket = "log-analysis-raw-${random_id.bucket_suffix.hex}"

  tags = {
    Name        = "Raw Logs Bucket"
    Environment = "handson"
    Purpose     = "log-analysis"
  }
}

# 処理済みデータ保存用バケット
resource "aws_s3_bucket" "processed_logs" {
  bucket = "log-analysis-processed-${random_id.bucket_suffix.hex}"

  tags = {
    Name        = "Processed Logs Bucket"
    Environment = "handson"
    Purpose     = "log-analysis"
  }
}

# バージョニング設定
resource "aws_s3_bucket_versioning" "raw_logs" {
  bucket = aws_s3_bucket.raw_logs.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_versioning" "processed_logs" {
  bucket = aws_s3_bucket.processed_logs.id

  versioning_configuration {
    status = "Enabled"
  }
}

# ライフサイクルルール
resource "aws_s3_bucket_lifecycle_configuration" "raw_logs" {
  bucket = aws_s3_bucket.raw_logs.id

  rule {
    id     = "delete-old-logs"
    status = "Enabled"

    filter {
      prefix = ""
    }

    expiration {
      days = 30
    }
  }
}

# パブリックアクセスブロック
resource "aws_s3_bucket_public_access_block" "raw_logs" {
  bucket = aws_s3_bucket.raw_logs.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_public_access_block" "processed_logs" {
  bucket = aws_s3_bucket.processed_logs.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
```

**terraform/modules/s3/outputs.tf**
```hcl
output "raw_logs_bucket_name" {
  description = "生ログ保存用バケット名"
  value       = aws_s3_bucket.raw_logs.id
}

output "raw_logs_bucket_arn" {
  description = "生ログ保存用バケットARN"
  value       = aws_s3_bucket.raw_logs.arn
}

output "processed_logs_bucket_name" {
  description = "処理済みログ保存用バケット名"
  value       = aws_s3_bucket.processed_logs.id
}

output "processed_logs_bucket_arn" {
  description = "処理済みログ保存用バケットARN"
  value       = aws_s3_bucket.processed_logs.arn
}
```

### 2-2. IAMモジュール作成

**terraform/modules/iam/main.tf**
```hcl
# Lambda実行ロール
resource "aws_iam_role" "lambda_execution" {
  name = "log-processor-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name        = "Lambda Execution Role"
    Environment = "handson"
  }
}

# CloudWatch Logsへの書き込み権限
resource "aws_iam_role_policy_attachment" "lambda_logs" {
  role       = aws_iam_role.lambda_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# S3アクセス用のカスタムポリシー
resource "aws_iam_role_policy" "lambda_s3_access" {
  name = "lambda-s3-access"
  role = aws_iam_role.lambda_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          var.raw_logs_bucket_arn,
          "${var.raw_logs_bucket_arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject"
        ]
        Resource = [
          "${var.processed_logs_bucket_arn}/*"
        ]
      }
    ]
  })
}
```

**terraform/modules/iam/variables.tf**
```hcl
variable "raw_logs_bucket_arn" {
  description = "生ログバケットのARN"
  type        = string
}

variable "processed_logs_bucket_arn" {
  description = "処理済みログバケットのARN"
  type        = string
}
```

**terraform/modules/iam/outputs.tf**
```hcl
output "lambda_role_arn" {
  description = "Lambda実行ロールのARN"
  value       = aws_iam_role.lambda_execution.arn
}

output "lambda_role_name" {
  description = "Lambda実行ロール名"
  value       = aws_iam_role.lambda_execution.name
}
```

### 2-3. メインTerraform設定

**terraform/main.tf**
```hcl
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

# Lambda関数モジュール
module "lambda" {
  source = "./modules/lambda"

  lambda_role_arn              = module.iam.lambda_role_arn
  image_uri                    = "${module.ecr.repository_url}:latest"
  raw_logs_bucket_name         = module.s3.raw_logs_bucket_name
  raw_logs_bucket_arn          = module.s3.raw_logs_bucket_arn
  processed_logs_bucket_name   = module.s3.processed_logs_bucket_name
}
```

**terraform/variables.tf**
```hcl
variable "aws_region" {
  description = "AWSリージョン"
  type        = string
  default     = "ap-northeast-1"
}
```

**terraform/outputs.tf**
```hcl
output "raw_logs_bucket_name" {
  description = "生ログバケット名"
  value       = module.s3.raw_logs_bucket_name
}

output "processed_logs_bucket_name" {
  description = "処理済みログバケット名"
  value       = module.s3.processed_logs_bucket_name
}

output "lambda_role_arn" {
  description = "Lambda実行ロールARN"
  value       = module.iam.lambda_role_arn
}

output "ecr_repository_url" {
  description = "ECRリポジトリURL"
  value       = module.ecr.repository_url
}

output "lambda_function_name" {
  description = "Lambda関数名"
  value       = module.lambda.function_name
}
```

### 2-4. Terraform実行
```bash
cd ~/dev/data-platform-handson/terraform

# 初期化
terraform init

# フォーマット
terraform fmt -recursive

# 構文チェック
terraform validate

# プラン確認
terraform plan

# 実行（S3とIAMのみ、ECRとLambdaは後で追加）
terraform apply
```

### トラブルシューティング: ライフサイクルルールの警告

**問題:**
```
Warning: Invalid Attribute Combination
No attribute specified when one (and only one) of [rule[0].filter,rule[0].prefix] is required
```

**解決策:**
`filter { prefix = "" }` ブロックを追加
```hcl
resource "aws_s3_bucket_lifecycle_configuration" "raw_logs" {
  bucket = aws_s3_bucket.raw_logs.id

  rule {
    id     = "delete-old-logs"
    status = "Enabled"

    filter {
      prefix = ""  # これを追加
    }

    expiration {
      days = 30
    }
  }
}
```

## Step 3: Dockerコンテナ開発 (60分)

### 3-1. サンプルログ生成スクリプト

**sample-data/generate_logs.py**

※ コードは長いため省略（実際のファイルを参照）
```bash
cd ~/dev/data-platform-handson/sample-data
python3 generate_logs.py

# access.log と app.log が生成される
```

### 3-2. ログ処理アプリケーション

**docker/log-processor/app.py**

※ コードは長いため省略（実際のファイルを参照）

**docker/log-processor/requirements.txt**
```
boto3==1.35.36
```

### 3-3. Dockerfile作成

**docker/log-processor/Dockerfile**
```dockerfile
FROM public.ecr.aws/lambda/python:3.12

WORKDIR ${LAMBDA_TASK_ROOT}

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

CMD ["app.lambda_handler"]
```

### 3-4. ローカルテスト
```bash
cd ~/dev/data-platform-handson/docker/log-processor

# 仮想環境作成（グローバル環境を汚さない）
python3 -m venv venv
source venv/bin/activate

# boto3インストール
pip install boto3

# テスト実行
python3 app.py

# 仮想環境を無効化
deactivate
```

### トラブルシューティング: boto3未インストール

**問題:**
`ModuleNotFoundError: No module named 'boto3'`

**解決策:**
仮想環境を使ってローカルにインストール
```bash
python3 -m venv venv
source venv/bin/activate
pip install boto3
python3 app.py
```

**理由:**
グローバルなPython環境を汚さないため、プロジェクトごとに仮想環境を使用

## Step 4: AWSへのデプロイ (60分)

### 4-1. ECRモジュール作成

**terraform/modules/ecr/main.tf**
```hcl
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
```

**terraform/modules/ecr/outputs.tf**
```hcl
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
```

### 4-2. Lambdaモジュール作成

**terraform/modules/lambda/main.tf**
```hcl
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

resource "aws_lambda_permission" "allow_s3" {
  statement_id  = "AllowExecutionFromS3"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.log_processor.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = var.raw_logs_bucket_arn
}

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
```

**terraform/modules/lambda/variables.tf**
```hcl
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
```

**terraform/modules/lambda/outputs.tf**
```hcl
output "function_name" {
  description = "Lambda関数名"
  value       = aws_lambda_function.log_processor.function_name
}

output "function_arn" {
  description = "Lambda関数ARN"
  value       = aws_lambda_function.log_processor.arn
}
```

### 4-3. ECRリポジトリ作成
```bash
cd ~/dev/data-platform-handson/terraform

# main.tfにECRモジュールを追加してから
terraform init
terraform apply

# ECRリポジトリURLを取得
export ECR_REPO=$(terraform output -raw ecr_repository_url)
echo $ECR_REPO
```

### 4-4. Dockerイメージのビルドとプッシュ
```bash
cd ~/dev/data-platform-handson/docker/log-processor

# ECRにログイン
aws ecr get-login-password --region ap-northeast-1 | \
  docker login --username AWS --password-stdin 344085827455.dkr.ecr.ap-northeast-1.amazonaws.com

# イメージをビルド（重要: --platform と --provenance オプション）
docker build --platform linux/amd64 --provenance=false -t log-processor:latest .

# タグ付け
docker tag log-processor:latest ${ECR_REPO}:latest

# プッシュ
docker push ${ECR_REPO}

# 確認
aws ecr describe-images --repository-name log-processor --image-ids imageTag=latest
```

### トラブルシューティング: シェル変数の展開

**問題:**
```bash
echo "$ECR_REPO:latest"
# 出力: 344085827455.dkr.ecr.ap-northeast-1.amazonaws.com/log-processoratest
```

`$ECR_REPO:latest` とすると、意図しない文字列が追加される

**解決策:**
`${ECR_REPO}:latest` の形式を使う
```bash
# NG
docker tag log-processor:latest $ECR_REPO:latest

# OK
docker tag log-processor:latest ${ECR_REPO}:latest
```

**原因:**
bashのシェル変数展開の仕様。`$変数名:` の形式だと、コロン以降が別の意味を持つ可能性がある。

### トラブルシューティング: Lambda イメージフォーマットエラー

**問題:**
```
Error: creating Lambda Function (log-processor): InvalidParameterValueException: 
The image manifest, config or layer media type for the source image is not supported.
```

**原因:**
Dockerイメージのmanifestフォーマットが `application/vnd.oci.image.index.v1+json` になっており、Lambdaがサポートしていない。

**解決策:**
`--provenance=false` オプションを追加してビルド
```bash
docker build --platform linux/amd64 --provenance=false -t log-processor:latest .
```

**確認方法:**
```bash
aws ecr describe-images --repository-name log-processor --image-ids imageTag=latest
```

`imageManifestMediaType` が `application/vnd.docker.distribution.manifest.v2+json` になっていればOK

### トラブルシューティング: ECR認証エラー

**問題:**
```
unknown: unexpected status from HEAD request: 403 Forbidden
```

**解決策:**
ECRへ再ログイン
```bash
aws ecr get-login-password --region ap-northeast-1 | \
  docker login --username AWS --password-stdin 344085827455.dkr.ecr.ap-northeast-1.amazonaws.com
```

ECRの認証トークンは12時間で期限切れになる

### 4-5. Lambda関数デプロイ
```bash
cd ~/dev/data-platform-handson/terraform

# main.tf と outputs.tf のLambdaモジュールのコメントを外す
terraform apply
```

### 4-6. 動作確認
```bash
cd ~/dev/data-platform-handson/sample-data

# バケット名を取得
export RAW_BUCKET=$(cd ../terraform && terraform output -raw raw_logs_bucket_name)
export PROCESSED_BUCKET=$(cd ../terraform && terraform output -raw processed_logs_bucket_name)

# ログをアップロード
aws s3 cp access.log s3://${RAW_BUCKET}/logs/access.log
aws s3 cp app.log s3://${RAW_BUCKET}/logs/app.log

# Lambda実行ログ確認
aws logs tail /aws/lambda/log-processor --follow

# 処理結果確認
aws s3 ls s3://${PROCESSED_BUCKET}/processed/ --recursive

# 結果ファイルをダウンロード
aws s3 cp s3://${PROCESSED_BUCKET}/processed/access/ . --recursive
aws s3 cp s3://${PROCESSED_BUCKET}/processed/app/ . --recursive

# 内容確認
cat *_access_summary.json
cat *_app_summary.json
```

## 学んだこと・ベストプラクティス

### 1. シェル変数の展開
- `${変数名}` の形式を使うと安全
- `$変数名:` の形式は避ける

### 2. Dockerイメージのビルド
- Lambda用は `--platform linux/amd64` 必須
- `--provenance=false` でmanifest形式を制御
- ECR認証は12時間で期限切れ

### 3. Python環境管理
- グローバル環境を汚さないため仮想環境を使用
- `python3 -m venv venv` で簡単に作成可能

### 4. Terraformモジュール設計
- 責務ごとにモジュールを分割（s3, iam, ecr, lambda）
- outputs.tfで値を受け渡し
- 段階的に構築（最初はS3/IAM、後からECR/Lambda）

### 5. VSCodeでのファイル作成
- `code ファイル名` でVSCodeを開いてコピペ
- ターミナルでのcatコマンドより確実で視認性が良い

## コスト見積もり

### 実際の月額コスト（Phase 1運用時）
- S3ストレージ: ~$0.50（10GB想定）
- S3リクエスト: ~$0.10
- Lambda実行: 無料枠内（100万リクエスト/月）
- ECR: 無料枠内（500MB）
- CloudWatch Logs: 無料枠内（5GB/月）

**合計: 月1-2ドル程度**

### コスト削減施策
- S3ライフサイクルルール（30日で削除）
- ECRライフサイクルポリシー（5イメージまで保持）
- Lambda実行時間の最適化（タイムアウト60秒）

## 次のステップ

Phase 2では以下を実装予定:
- GitHub ActionsでCI/CDパイプライン構築
- 複数環境管理（dev/prod）
- Athenaでのクエリ実行
- QuickSightでの可視化

## トラブルシューティング集

### エラー集とその解決策

| エラー内容 | 原因 | 解決策 |
|-----------|------|--------|
| `ModuleNotFoundError: No module named 'boto3'` | boto3未インストール | 仮想環境作成してインストール |
| `invalid reference format` | 変数展開の問題 | `${変数名}` 形式を使用 |
| `InvalidParameterValueException: image manifest not supported` | OCI形式のmanifest | `--provenance=false` オプション追加 |
| `403 Forbidden` on ECR push | ECR認証期限切れ | `aws ecr get-login-password` で再認証 |
| Lifecycle警告 | filter未指定 | `filter { prefix = "" }` 追加 |

## まとめ

Phase 1では、Terraform/Docker/AWSを使った基本的なログ分析基盤を構築しました。

**達成したこと:**
- ✅ IaCによるインフラ管理
- ✅ Dockerコンテナ化
- ✅ S3イベント駆動のLambda実行
- ✅ ログの自動集計・分析

**所要時間:**
- 実質: 約5時間（トラブルシューティング含む）
- 想定: 4時間

次のPhase 2では、CI/CDパイプラインを構築して、コード変更から本番デプロイまでを自動化します。