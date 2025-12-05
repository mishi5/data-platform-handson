#!/usr/bin/env python3
"""
ログ処理Lambda関数
S3に保存されたログファイルを読み取り、集計してS3に書き戻す
"""

import json
import os
import re
from collections import defaultdict
from datetime import datetime
from urllib.parse import unquote_plus

import boto3

s3_client = boto3.client("s3")

# Nginx log format pattern
NGINX_PATTERN = re.compile(
    r"(?P<ip>[\d.]+) - - \[(?P<timestamp>[^\]]+)\] "
    r'"(?P<method>\w+) (?P<url>[^\s]+) [^"]*" '
    r'(?P<status>\d+) (?P<size>\d+) "[^"]*" "[^"]*" '
    r"rt=(?P<response_time>[\d.]+)"
)


def parse_access_log(content):
    """Nginxアクセスログをパース"""
    results = {
        "total_requests": 0,
        "status_codes": defaultdict(int),
        "url_hits": defaultdict(int),
        "avg_response_time": 0,
        "errors": 0,
    }

    lines = content.strip().split("\n")
    total_response_time = 0

    for line in lines:
        match = NGINX_PATTERN.match(line)
        if not match:
            continue

        data = match.groupdict()
        results["total_requests"] += 1

        # ステータスコード集計
        status = data["status"]
        results["status_codes"][status] += 1

        # エラー数カウント
        if status.startswith("4") or status.startswith("5"):
            results["errors"] += 1

        # URL別アクセス数
        results["url_hits"][data["url"]] += 1

        # レスポンスタイム
        total_response_time += float(data["response_time"])

    # 平均レスポンスタイム計算
    if results["total_requests"] > 0:
        results["avg_response_time"] = round(
            total_response_time / results["total_requests"], 3
        )

    # 人気URLトップ5
    top_urls = sorted(results["url_hits"].items(), key=lambda x: x[1], reverse=True)[:5]
    results["top_urls"] = dict(top_urls)

    # defaultdictを通常のdictに変換
    results["status_codes"] = dict(results["status_codes"])
    del results["url_hits"]

    return results


def parse_app_log(content):
    """JSONアプリケーションログをパース"""
    results = {
        "total_events": 0,
        "log_levels": defaultdict(int),
        "actions": defaultdict(int),
        "errors": [],
        "avg_duration_ms": 0,
    }

    lines = content.strip().split("\n")
    total_duration = 0

    for line in lines:
        try:
            log_entry = json.loads(line)
            results["total_events"] += 1

            # ログレベル集計
            level = log_entry.get("level", "UNKNOWN")
            results["log_levels"][level] += 1

            # アクション集計
            action = log_entry.get("action", "unknown")
            results["actions"][action] += 1

            # 処理時間
            duration = log_entry.get("duration_ms", 0)
            total_duration += duration

            # エラー情報保存
            if level == "ERROR" and "error" in log_entry:
                results["errors"].append(
                    {
                        "timestamp": log_entry.get("timestamp"),
                        "type": log_entry["error"].get("type"),
                        "message": log_entry["error"].get("message"),
                    }
                )

        except json.JSONDecodeError:
            continue

    # 平均処理時間
    if results["total_events"] > 0:
        results["avg_duration_ms"] = round(total_duration / results["total_events"], 2)

    # defaultdictを通常のdictに変換
    results["log_levels"] = dict(results["log_levels"])
    results["actions"] = dict(results["actions"])

    return results


def lambda_handler(event, context):
    """Lambda ハンドラー関数"""

    print(f"Event: {json.dumps(event)}")

    # S3イベントから情報取得
    for record in event["Records"]:
        bucket = record["s3"]["bucket"]["name"]
        key = unquote_plus(record["s3"]["object"]["key"])

        print(f"Processing: s3://{bucket}/{key}")

        try:
            # S3からログファイル取得
            response = s3_client.get_object(Bucket=bucket, Key=key)
            content = response["Body"].read().decode("utf-8")

            # ログタイプを判定して処理
            if "access" in key.lower():
                results = parse_access_log(content)
                log_type = "access"
            elif "app" in key.lower():
                results = parse_app_log(content)
                log_type = "app"
            else:
                print(f"Unknown log type: {key}")
                continue

            # メタデータ追加
            results["log_type"] = log_type
            results["source_file"] = key
            results["processed_at"] = datetime.utcnow().isoformat()

            # 処理結果をS3に保存
            output_bucket = os.environ.get("OUTPUT_BUCKET")
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            output_key = f"processed/{log_type}/{timestamp}_{log_type}_summary.json"

            s3_client.put_object(
                Bucket=output_bucket,
                Key=output_key,
                Body=json.dumps(results, indent=2, ensure_ascii=False),
                ContentType="application/json",
            )

            print(f"✓ Processed and saved to: s3://{output_bucket}/{output_key}")

        except Exception as e:
            print(f"Error processing {key}: {str(e)}")
            raise

    return {"statusCode": 200, "body": json.dumps("Log processing completed")}


# ローカルテスト用
if __name__ == "__main__":
    # テストイベント
    test_event = {
        "Records": [
            {
                "s3": {
                    "bucket": {"name": "test-bucket"},
                    "object": {"key": "test/access.log"},
                }
            }
        ]
    }

    # 環境変数設定
    os.environ["OUTPUT_BUCKET"] = "test-output-bucket"

    # ローカルのログファイルでテスト
    with open("../../sample-data/access.log", "r") as f:
        content = f.read()
        results = parse_access_log(content)
        print("\n=== Access Log Analysis ===")
        print(json.dumps(results, indent=2))

    with open("../../sample-data/app.log", "r") as f:
        content = f.read()
        results = parse_app_log(content)
        print("\n=== App Log Analysis ===")
        print(json.dumps(results, indent=2))
