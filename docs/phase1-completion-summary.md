# Phase 1 完了サマリー

## 構築したアーキテクチャ
```
GitHub
  ↓ (push)
GitHub Actions
  ↓
Terraform Cloud → AWS
  ├── S3 (raw logs)
  ├── Lambda (Docker)
  ├── S3 (processed)
  └── ECR (images)
```

## 実行可能なコマンド集

### ログのアップロードとテスト
```bash
# サンプルログ生成
cd ~/dev/data-platform-handson/sample-data
python3 generate_logs.py

# S3にアップロード
export RAW_BUCKET=$(cd ../terraform && terraform output -raw raw_logs_bucket_name)
aws s3 cp access.log s3://${RAW_BUCKET}/logs/access.log
aws s3 cp app.log s3://${RAW_BUCKET}/logs/app.log

# Lambda実行ログ確認
aws logs tail /aws/lambda/log-processor --follow

# 処理結果確認
export PROCESSED_BUCKET=$(cd ../terraform && terraform output -raw processed_logs_bucket_name)
aws s3 ls s3://${PROCESSED_BUCKET}/processed/ --recursive
```

### インフラ管理
```bash
# ローカルでのTerraform実行
cd ~/dev/data-platform-handson/terraform
terraform plan
terraform apply

# Terraform Cloud Web UI
https://app.terraform.io/
```

### CI/CD
```bash
# コード変更をpushすると自動デプロイ
git add .
git commit -m "Update infrastructure"
git push origin main

# GitHub Actions
https://github.com/YOUR_USERNAME/data-platform-handson/actions
```

## 現在のコスト

- **月額: $0.30-$0.50**
  - S3: ~$0.01
  - Lambda: 無料枠内
  - ECR: 無料枠内
  - DynamoDB: ~$0.25（ステートロック用）

## トラブルシューティング履歴

### 1. シェル変数の展開
**問題:** `$ECR_REPO:latest` で意図しない文字列
**解決:** `${ECR_REPO}:latest` を使用

### 2. Lambda イメージフォーマット
**問題:** `InvalidParameterValueException: image manifest not supported`
**解決:** `docker build --platform linux/amd64 --provenance=false`

### 3. ECR認証期限切れ
**問題:** `403 Forbidden`
**解決:** `aws ecr get-login-password | docker login`

### 4. Terraform Cloud移行
**問題:** 既存リソースが認識されない
**解決:** `terraform import` で既存リソースをインポート

## 次のステップ（Phase 2）

Phase 2では以下を実装予定:
- [ ] 複数環境管理（dev/prod）
- [ ] Athenaでのクエリ実行
- [ ] QuickSightでの可視化
- [ ] より高度なCI/CD（PR連携、承認フロー）
- [ ] コスト最適化
- [ ] セキュリティ強化

## 参考リンク

- Terraform Cloud: https://app.terraform.io/
- GitHub Actions: https://github.com/YOUR_USERNAME/data-platform-handson/actions
- AWS Console: https://console.aws.amazon.com/

## 学習成果

Phase 1を通じて、以下のスキルを習得:

✅ Terraformによるインフラコード化
✅ Dockerコンテナ化
✅ AWS Lambda + S3のイベント駆動アーキテクチャ
✅ GitHub Actionsでの自動デプロイ
✅ ステート管理（S3バックエンド + Terraform Cloud）
✅ 実践的なトラブルシューティング

---

**所要時間:** 約6時間（想定4時間 + トラブルシューティング2時間）

**達成日:** 2025年12月17日

## Phase 1完了後のクリーンアップ

### 学習過程で作成した不要なリソース

Phase 1の学習では、以下の一時的なリソースを作成しました:

**削除済み:**
- ✅ S3バケット: `terraform-state-data-platform-handson-xxx`
- ✅ DynamoDBテーブル: `terraform-state-lock`

**Terraform管理下（残存）:**
- S3: `log-analysis-raw-xxx`, `log-analysis-processed-xxx`
- Lambda: `log-processor`
- ECR: `log-processor`
- IAM: `log-processor-lambda-role`

### 現在のリソース状況
```bash
# 確認コマンド
aws s3 ls
aws dynamodb list-tables
aws lambda list-functions --query 'Functions[].FunctionName'
aws ecr describe-repositories --query 'repositories[].repositoryName'
```

### すべて削除する場合

Phase 1の学習を完全に終了し、すべてのリソースを削除する場合:
```bash
cd ~/dev/data-platform-handson/terraform
terraform destroy
```

**月額コスト: $0**（すべて削除後）