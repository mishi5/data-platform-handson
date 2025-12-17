# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project overview

This repository is a hands-on project for building a small AWS-based data platform using Terraform. The README describes the stack as including Docker, Terraform, AWS (Lambda, S3, Athena, ECR), and GitHub Actions for CI/CD; the code currently present is focused on Terraform infrastructure for S3 and IAM.

## How to work with Terraform in this repo

All Terraform code lives under the `terraform/` directory.

### Initialize Terraform

From the repository root:

```bash path=null start=null
cd terraform
terraform init
```

Notes:
- The backend is currently local (see `terraform/main.tf` comment about switching to S3 later), so state is stored in the `terraform/` directory by default.

### Validate and format Terraform code

From `terraform/`:

```bash path=null start=null
terraform fmt -recursive
terraform validate
```

Use `terraform fmt -recursive` before committing to keep Terraform code formatted.

### Plan and apply infrastructure

Standard workflow from `terraform/`:

```bash path=null start=null
# Show what will change
terraform plan

# Apply changes (will prompt for confirmation)
terraform apply
```

To target a specific region instead of the default `ap-northeast-1` (defined in `terraform/variables.tf`):

```bash path=null start=null
terraform plan  -var "aws_region=us-east-1"
terraform apply -var "aws_region=us-east-1"
```

### Destroy infrastructure

From `terraform/`:

```bash path=null start=null
terraform destroy
```

You can combine this with `-var "aws_region=..."` if you overrode the region when applying.

## High-level architecture

### Top-level Terraform configuration (`terraform/`)

- `terraform/main.tf` defines:
  - Terraform version and required providers: `aws` (v5.x) and `random` (v3.6+).
  - An `aws` provider with `region = var.aws_region` and default tags:
    - `Project = "data-platform-handson"`
    - `ManagedBy = "terraform"`
  - Two child modules:
    - `module "s3"` from `./modules/s3` (S3 buckets and related configuration).
    - `module "iam"` from `./modules/iam` (IAM role and policies for Lambda), wired with:
      - `raw_logs_bucket_arn       = module.s3.raw_logs_bucket_arn`
      - `processed_logs_bucket_arn = module.s3.processed_logs_bucket_arn`
- `terraform/variables.tf` exposes `aws_region` (default `ap-northeast-1`).
- `terraform/outputs.tf` surfaces key infrastructure references:
  - `raw_logs_bucket_name`
  - `processed_logs_bucket_name`
  - `lambda_role_arn`

The top-level Terraform stack is thus a thin composition layer that wires the S3 and IAM modules together and exposes the main identifiers needed by application code or other stacks (for example, a Lambda function that consumes raw logs and writes processed data).

### S3 module (`terraform/modules/s3`)

This module is responsible for the storage layer for log ingestion and processed data.

Key behavior:
- Generates a random suffix once per workspace with `random_id.bucket_suffix` to avoid S3 bucket name collisions.
- Creates two S3 buckets:
  - `aws_s3_bucket.raw_logs` named `log-analysis-raw-${random_id.bucket_suffix.hex}` for **raw logs**.
  - `aws_s3_bucket.processed_logs` named `log-analysis-processed-${random_id.bucket_suffix.hex}` for **processed data**.
- Enables versioning on both buckets via `aws_s3_bucket_versioning` resources (protection against accidental deletion/overwrites).
- Configures a lifecycle rule on the raw logs bucket (`aws_s3_bucket_lifecycle_configuration.raw_logs`) to delete objects after 30 days (cost control for raw log storage).
- Enforces security best practices by attaching `aws_s3_bucket_public_access_block` to both buckets, fully blocking public access (ACLs and policies) to ensure buckets are private.

Module outputs provide both bucket names and ARNs so that other modules can consume them:
- `raw_logs_bucket_name`, `raw_logs_bucket_arn`
- `processed_logs_bucket_name`, `processed_logs_bucket_arn`

### IAM module (`terraform/modules/iam`)

This module defines a Lambda execution role tailored to the S3-based log processing pipeline.

Key resources:
- `aws_iam_role.lambda_execution`:
  - Name: `log-processor-lambda-role`.
  - Trust policy allows the `lambda.amazonaws.com` service to assume the role.
  - Tagged with `Environment = "handson"` and `Name = "Lambda Execution Role"`.
- `aws_iam_role_policy_attachment.lambda_logs`:
  - Attaches the AWS-managed `AWSLambdaBasicExecutionRole` policy, granting permissions needed for CloudWatch Logs.
- `aws_iam_role_policy.lambda_s3_access`:
  - Custom inline policy granting the Lambda role minimum S3 access needed for the pipeline:
    - `s3:GetObject` and `s3:ListBucket` on the **raw logs bucket** and its objects.
    - `s3:PutObject` on objects in the **processed logs bucket**.
  - Uses the ARNs passed in via module variables:
    - `var.raw_logs_bucket_arn`
    - `var.processed_logs_bucket_arn`

Module outputs:
- `lambda_role_arn` – used at the root level (and by any Lambda stack) to attach this role to a function.
- `lambda_role_name` – available if name-based references are needed (e.g., in CI/CD or additional IAM integrations).

Overall, the IAM module is tightly coupled to the S3 module via ARNs, forming a minimal but complete permission model for a Lambda-based log processing workflow.

## How to extend this infra

If you add Lambda functions, Athena queries, or other components mentioned in the README, keep the current modular pattern:
- Add new modules under `terraform/modules/` (e.g., `lambda`, `athena`) and compose them in `terraform/main.tf`.
- Prefer passing ARNs and names via module outputs/inputs (as done between the S3 and IAM modules) instead of hardcoding resource identifiers.
