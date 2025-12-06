# コスト管理ガイド

## 概要

このドキュメントでは、ハンズオン環境のコスト管理方法をまとめています。

## 現在の課金状況

### Phase 1完了時点でのコスト内訳

| サービス | 使用量 | 月額料金 | 備考 |
|---------|--------|---------|------|
| S3ストレージ | ~10MB | ~$0.0002 | サンプルログ保存 |
| S3リクエスト | ~10リクエスト | ~$0.0001 | PUT/GET操作 |
| Lambda実行 | ~5回 | $0 | 100万リクエスト/月まで無料 |
| Lambda実行時間 | ~10秒 | $0 | 40万GB秒/月まで無料 |
| ECR | 200MB | $0 | 500MBまで無料 |
| CloudWatch Logs | ~1MB | $0 | 5GB/月まで無料 |
| **合計** | - | **~$0.01/日** | **~$0.30/月** |

### 無料枠の詳細

#### AWS Lambda（常時無料）
- リクエスト: 100万リクエスト/月
- 実行時間: 40万GB秒/月
- 現在の使用: 0.001%未満

#### S3（12ヶ月無料枠は期限切れ）
- ストレージ: $0.023/GB/月
- PUT/COPY/POST: $0.005/1,000リクエスト
- GET/SELECT: $0.0004/1,000リクエスト

#### ECR（常時無料）
- ストレージ: 500MBまで無料
- 超過分: $0.10/GB/月
- 現在の使用: 200MB（無料枠内）

#### CloudWatch Logs（常時無料）
- ログ取り込み: 5GB/月
- ログ保存: 5GB/月
- 現在の使用: 1MB未満（無料枠内）

## コスト削減施策

### 自動削除設定（既に実装済み）

**S3ライフサイクルルール**
```hcl
# 30日後に自動削除
resource "aws_s3_bucket_lifecycle_configuration" "raw_logs" {
  rule {
    id     = "delete-old-logs"
    status = "Enabled"
    expiration {
      days = 30
    }
  }
}
```

**ECRライフサイクルポリシー**
```hcl
# 最新5イメージのみ保持
resource "aws_ecr_lifecycle_policy" "log_processor" {
  policy = jsonencode({
    rules = [{
      description  = "Keep last 5 images"
      selection = {
        countType   = "imageCountMoreThan"
        countNumber = 5
      }
      action = {
        type = "expire"
      }
    }]
  })
}
```

## リソース削除方法

### オプション1: 完全削除（推奨：ハンズオン終了後）

すべてのAWSリソースを削除し、課金を完全に停止します。
```bash
cd ~/dev/data-platform-handson/terraform

# すべてのリソースを削除
terraform destroy

# 確認プロンプトで "yes" と入力
```

**削除されるリソース:**
- S3バケット2つ（raw, processed）とその中身
- Lambda関数
- ECRリポジトリとDockerイメージ
- IAMロール・ポリシー
- S3イベント通知設定

**注意事項:**
- バケットにバージョニングが有効な場合、古いバージョンも自動削除されます
- 削除は不可逆的です（元に戻せません）
- 再構築するには最初から `terraform apply` が必要

**実行例:**
```bash
$ terraform destroy

Plan: 0 to add, 0 to change, 15 to destroy.

Do you really want to destroy all resources?
  Terraform will destroy all your managed infrastructure, as shown above.
  There is no undo. Only 'yes' will be accepted to confirm.

  Enter a value: yes

Destroy complete! Resources: 15 destroyed.
```

### オプション2: 一時停止（データのみ削除）

インフラは残して、課金の原因となるデータのみ削除します。
後で再開する予定がある場合に推奨。
```bash
cd ~/dev/data-platform-handson/terraform

# バケット名を取得
export RAW_BUCKET=$(terraform output -raw raw_logs_bucket_name)
export PROCESSED_BUCKET=$(terraform output -raw processed_logs_bucket_name)

# S3の中身を削除
aws s3 rm s3://${RAW_BUCKET}/logs/ --recursive
aws s3 rm s3://${PROCESSED_BUCKET}/processed/ --recursive

# バージョニングされたオブジェクトも削除
aws s3api delete-objects \
  --bucket ${RAW_BUCKET} \
  --delete "$(aws s3api list-object-versions \
    --bucket ${RAW_BUCKET} \
    --query '{Objects: Versions[].{Key:Key,VersionId:VersionId}}' \
    --max-items 1000)"

aws s3api delete-objects \
  --bucket ${PROCESSED_BUCKET} \
  --delete "$(aws s3api list-object-versions \
    --bucket ${PROCESSED_BUCKET} \
    --query '{Objects: Versions[].{Key:Key,VersionId:VersionId}}' \
    --max-items 1000)"

# ECRイメージを削除
aws ecr batch-delete-image \
  --repository-name log-processor \
  --image-ids imageTag=latest

# 確認
echo "S3 raw bucket contents:"
aws s3 ls s3://${RAW_BUCKET}/ --recursive

echo "S3 processed bucket contents:"
aws s3 ls s3://${PROCESSED_BUCKET}/ --recursive

echo "ECR images:"
aws ecr list-images --repository-name log-processor
```

**削除後のコスト:**
- ほぼゼロ（数セント/月）
- 空のS3バケット、Lambda関数、ECRリポジトリは料金不要

**再開方法:**
```bash
# Dockerイメージを再ビルド・プッシュ
cd ~/dev/data-platform-handson/docker/log-processor
docker build --platform linux/amd64 --provenance=false -t log-processor:latest .
docker push ${ECR_REPO}

# Lambda関数を更新
cd ~/dev/data-platform-handson/terraform
terraform apply

# サンプルログを再アップロード
cd ~/dev/data-platform-handson/sample-data
aws s3 cp access.log s3://${RAW_BUCKET}/logs/access.log
```

### オプション3: 特定リソースのみ削除

Terraformで特定のリソースのみ削除します。
```bash
cd ~/dev/data-platform-handson/terraform

# 削除するリソースを確認
terraform state list

# 特定リソースのみ削除（例：Lambda関数）
terraform destroy -target=module.lambda.aws_lambda_function.log_processor

# または複数指定
terraform destroy \
  -target=module.lambda.aws_lambda_function.log_processor \
  -target=module.lambda.aws_s3_bucket_notification.log_upload
```

**用途:**
- 開発中に特定の機能だけ削除したい場合
- トラブルシューティング時に再作成が必要な場合

## コスト監視

### AWS Budgetアラート（設定済み）

以下の予算アラートが設定されています:

1. **月次予算: $50**
   - 80%（$40）到達時にメール通知
   - 100%（$50）到達時にメール通知

2. **早期警告: $10**
   - 100%（$10）到達時にメール通知

### コストの確認方法

**AWSコンソール:**
```
https://console.aws.amazon.com/billing/home#/bills
```

**AWS CLI:**
```bash
# 今月のコストを確認
aws ce get-cost-and-usage \
  --time-period Start=2025-12-01,End=2025-12-31 \
  --granularity MONTHLY \
  --metrics BlendedCost \
  --group-by Type=SERVICE

# 日次のコスト推移
aws ce get-cost-and-usage \
  --time-period Start=2025-12-01,End=2025-12-08 \
  --granularity DAILY \
  --metrics BlendedCost
```

**サービス別のコスト:**
```bash
# S3のコストのみ
aws ce get-cost-and-usage \
  --time-period Start=2025-12-01,End=2025-12-31 \
  --granularity MONTHLY \
  --metrics BlendedCost \
  --filter file://filter.json

# filter.json の内容:
# {
#   "Dimensions": {
#     "Key": "SERVICE",
#     "Values": ["Amazon Simple Storage Service"]
#   }
# }
```

### コストエクスプローラーの活用

AWS Cost Explorerで視覚的にコストを確認:
```
https://console.aws.amazon.com/cost-management/home#/cost-explorer
```

**確認ポイント:**
- サービス別コスト内訳
- 日次/月次のトレンド
- リソース別の使用量

## Phase別のコスト見積もり

### Phase 1（現在）
- **月額: $0.30-$0.50**
- 主な費用: S3ストレージとリクエスト
- Lambda/ECRは無料枠内

### Phase 2（CI/CD追加後）
- **月額: $0.50-$1.00**
- 追加費用: GitHub Actions実行（パブリックリポジトリは無料）
- Terraform Cloud（無料枠で十分）

### Phase 3（本格運用想定）
- **月額: $5-$10**
- 追加サービス: Athena（クエリ実行）、QuickSight（可視化）
- ログ量が増えると S3/Lambda のコスト増

## トラブルシューティング

### terraform destroy が失敗する場合

**問題1: S3バケットが空でない**
```
Error: deleting S3 Bucket (log-analysis-raw-xxx): BucketNotEmpty
```

**解決策:**
```bash
# バケットを強制的に空にする
aws s3 rm s3://バケット名/ --recursive

# バージョニングされたオブジェクトも削除
aws s3api delete-objects \
  --bucket バケット名 \
  --delete "$(aws s3api list-object-versions \
    --bucket バケット名 \
    --query '{Objects: Versions[].{Key:Key,VersionId:VersionId}}')"

# 削除マーカーも削除
aws s3api delete-objects \
  --bucket バケット名 \
  --delete "$(aws s3api list-object-versions \
    --bucket バケット名 \
    --query '{Objects: DeleteMarkers[].{Key:Key,VersionId:VersionId}}')"

# 再度 terraform destroy
terraform destroy
```

**問題2: Lambda関数が削除できない**
```
Error: error deleting Lambda Function: ResourceConflictException
```

**解決策:**
```bash
# S3イベント通知を先に削除
terraform destroy -target=module.lambda.aws_s3_bucket_notification.log_upload

# その後、Lambda関数を削除
terraform destroy
```

**問題3: ECRリポジトリが削除できない**
```
Error: deleting ECR Repository: RepositoryNotEmptyException
```

**解決策:**
```bash
# イメージを先に削除
aws ecr batch-delete-image \
  --repository-name log-processor \
  --image-ids "$(aws ecr list-images \
    --repository-name log-processor \
    --query 'imageIds[*]' \
    --output json)"

# 再度 terraform destroy
terraform destroy
```

### リソースが残っている場合

`terraform destroy` 後も手動で確認:
```bash
# S3バケット
aws s3 ls

# Lambda関数
aws lambda list-functions --query 'Functions[?starts_with(FunctionName, `log-processor`)]'

# ECRリポジトリ
aws ecr describe-repositories

# IAMロール
aws iam list-roles --query 'Roles[?starts_with(RoleName, `log-processor`)]'
```

不要なリソースが残っていれば手動削除:
```bash
# S3バケット削除
aws s3 rb s3://バケット名 --force

# Lambda関数削除
aws lambda delete-function --function-name log-processor

# ECRリポジトリ削除
aws ecr delete-repository --repository-name log-processor --force

# IAMロール削除
aws iam delete-role --role-name log-processor-lambda-role
```

## ベストプラクティス

### 1. 定期的なコスト確認
- 週1回、AWSコンソールでコストを確認
- 予想外の課金がないかチェック

### 2. 不要なリソースの削除
- 実験が終わったら `terraform destroy`
- 長期間使わない場合は必ず削除

### 3. タグの活用
```hcl
default_tags {
  tags = {
    Project   = "data-platform-handson"
    ManagedBy = "terraform"
    Owner     = "your-name"
  }
}
```

これにより、Cost Explorerでプロジェクト別のコストが確認可能

### 4. Terraformステートの管理
- ローカルの `.tfstate` ファイルを削除しない
- `terraform destroy` する前に必ず `terraform state list` で確認

### 5. 削除前のバックアップ
```bash
# 重要なログやデータは削除前にダウンロード
aws s3 sync s3://バケット名/logs/ ./backup/logs/

# Terraformステートのバックアップ
cp terraform.tfstate terraform.tfstate.backup
```

## チェックリスト

### ハンズオン終了時
- [ ] サンプルデータをダウンロード（必要な場合）
- [ ] スクリーンショットやログを保存
- [ ] `terraform destroy` を実行
- [ ] AWSコンソールでリソースが削除されたことを確認
- [ ] 翌日、請求ダッシュボードで課金がないことを確認

### 長期休止時
- [ ] S3のデータを削除
- [ ] ECRのイメージを削除
- [ ] Lambda関数は残しても課金なし
- [ ] 月次でコストを確認

### 再開時
- [ ] Dockerイメージを再ビルド・プッシュ
- [ ] `terraform apply` で再構築
- [ ] サンプルログを再アップロード
- [ ] 動作確認

## まとめ

**現在のコスト:** 月$0.30-$0.50（ほぼ無料）

**推奨アクション:**
1. Phase 2（CI/CD）まで完了させる（約30分）
2. すべての学習が終わったら `terraform destroy` で完全削除
3. 月次で請求額を確認する習慣をつける

**重要:** 
削除忘れが最もコストがかかる原因です。不要になったら必ず削除しましょう。