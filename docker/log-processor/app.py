#!/usr/bin/env python3
"""
ログ処理Lambda関数（Phase 2対応）
S3に保存されたログファイルを読み取り、
- JSON形式で集計結果を保存（Phase 1互換）
- Parquet形式で詳細データを保存（Phase 2: Athena用）
"""

import json
import os
import re
from collections import defaultdict
from datetime import datetime
from urllib.parse import unquote_plus

import boto3
import pandas as pd

s3_client = boto3.client("s3")

# Nginx log format pattern
NGINX_PATTERN = re.compile(
    r"(?P<ip>[\d.]+) - - \[(?P<timestamp>[^\]]+)\] "
    r'"(?P<method>\w+) (?P<url>[^\s]+) [^"]*" '
    r'(?P<status>\d+) (?P<size>\d+) "[^"]*" "[^"]*" '
    r"rt=(?P<response_time>[\d.]+)"
)


def parse_access_log(content):
    """Nginxアクセスログをパースして詳細データとサマリーを返す"""
    records = []
    summary = {
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

        # 詳細レコード（Parquet用）
        record = {
            "timestamp": data["timestamp"],
            "ip": data["ip"],
            "method": data["method"],
            "url": data["url"],
            "status": int(data["status"]),
            "size": int(data["size"]),
            "response_time": float(data["response_time"]),
        }
        records.append(record)

        # サマリー集計（JSON用）
        summary["total_requests"] += 1
        status = data["status"]
        summary["status_codes"][status] += 1

        if status.startswith("4") or status.startswith("5"):
            summary["errors"] += 1

        summary["url_hits"][data["url"]] += 1
        total_response_time += float(data["response_time"])

    # 平均レスポンスタイム計算
    if summary["total_requests"] > 0:
        summary["avg_response_time"] = round(
            total_response_time / summary["total_requests"], 3
        )

    # 人気URLトップ5
    top_urls = sorted(summary["url_hits"].items(), key=lambda x: x[1], reverse=True)[:5]
    summary["top_urls"] = dict(top_urls)

    # defaultdictを通常のdictに変換
    summary["status_codes"] = dict(summary["status_codes"])
    del summary["url_hits"]

    return records, summary


def parse_app_log(content):
    """JSONアプリケーションログをパースして詳細データとサマリーを返す"""
    records = []
    summary = {
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

            # 詳細レコード（Parquet用）
            record = {
                "timestamp": log_entry.get("timestamp"),
                "level": log_entry.get("level", "UNKNOWN"),
                "action": log_entry.get("action", "unknown"),
                "user_id": log_entry.get("user_id"),
                "session_id": log_entry.get("session_id"),
                "duration_ms": log_entry.get("duration_ms", 0),
                "ip": log_entry.get("metadata", {}).get("ip"),
                "endpoint": log_entry.get("metadata", {}).get("endpoint"),
                "error_type": log_entry.get("error", {}).get("type")
                if "error" in log_entry
                else None,
                "error_message": log_entry.get("error", {}).get("message")
                if "error" in log_entry
                else None,
            }
            records.append(record)

            # サマリー集計（JSON用）
            summary["total_events"] += 1

            level = log_entry.get("level", "UNKNOWN")
            summary["log_levels"][level] += 1

            action = log_entry.get("action", "unknown")
            summary["actions"][action] += 1

            duration = log_entry.get("duration_ms", 0)
            total_duration += duration

            if level == "ERROR" and "error" in log_entry:
                summary["errors"].append(
                    {
                        "timestamp": log_entry.get("timestamp"),
                        "type": log_entry["error"].get("type"),
                        "message": log_entry["error"].get("message"),
                    }
                )

        except json.JSONDecodeError:
            continue

    # 平均処理時間
    if summary["total_events"] > 0:
        summary["avg_duration_ms"] = round(total_duration / summary["total_events"], 2)

    # defaultdictを通常のdictに変換
    summary["log_levels"] = dict(summary["log_levels"])
    summary["actions"] = dict(summary["actions"])

    return records, summary


def save_as_parquet(records, output_bucket, log_type, process_date):
    """Parquet形式でS3に保存（パーティション分割）"""
    if not records:
        print(f"No records to save for {log_type}")
        return None

    # DataFrameに変換
    df = pd.DataFrame(records)

    # タイムスタンプをパース（パーティション用）
    year = process_date.strftime("%Y")
    month = process_date.strftime("%m")
    day = process_date.strftime("%d")

    # Parquetに変換（メモリ上）
    parquet_buffer = df.to_parquet(index=False, engine="pyarrow")

    # S3にアップロード（パーティション構造）
    output_key = f"parquet/{log_type}/year={year}/month={month}/day={day}/data.parquet"

    s3_client.put_object(
        Bucket=output_bucket,
        Key=output_key,
        Body=parquet_buffer,
        ContentType="application/octet-stream",
    )

    print(f"✓ Saved Parquet: s3://{output_bucket}/{output_key}")
    print(f"  Records: {len(records)}, Size: {len(parquet_buffer)} bytes")

    return output_key


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
                records, summary = parse_access_log(content)
                log_type = "access"
            elif "app" in key.lower():
                records, summary = parse_app_log(content)
                log_type = "app"
            else:
                print(f"Unknown log type: {key}")
                continue

            # 処理日時
            process_date = datetime.utcnow()
            timestamp = process_date.strftime("%Y%m%d_%H%M%S")

            # 出力バケット
            output_bucket = os.environ.get("OUTPUT_BUCKET")

            # 1. JSON形式で集計結果を保存（Phase 1互換）
            summary["log_type"] = log_type
            summary["source_file"] = key
            summary["processed_at"] = process_date.isoformat()

            json_key = f"json/{log_type}/{timestamp}_{log_type}_summary.json"
            s3_client.put_object(
                Bucket=output_bucket,
                Key=json_key,
                Body=json.dumps(summary, indent=2, ensure_ascii=False),
                ContentType="application/json",
            )
            print(f"✓ Saved JSON: s3://{output_bucket}/{json_key}")

            # 2. Parquet形式で詳細データを保存（Phase 2: Athena用）
            parquet_key = save_as_parquet(
                records, output_bucket, log_type, process_date
            )

            print(f"✓ Processing completed for {key}")

        except Exception as e:
            print(f"Error processing {key}: {str(e)}")
            raise

    return {"statusCode": 200, "body": json.dumps("Log processing completed")}


# ローカルテスト用
if __name__ == "__main__":
    os.environ["OUTPUT_BUCKET"] = "test-output-bucket"

    # アクセスログのテスト
    print("\n=== Testing Access Log Parsing ===")
    with open("../../sample-data/access.log", "r") as f:
        content = f.read()
        records, summary = parse_access_log(content)
        print(f"Records: {len(records)}")
        print(f"Summary: {json.dumps(summary, indent=2)}")

        # DataFrame確認
        df = pd.DataFrame(records)
        print(f"\nDataFrame shape: {df.shape}")
        print(df.head())

    # アプリログのテスト
    print("\n=== Testing App Log Parsing ===")
    with open("../../sample-data/app.log", "r") as f:
        content = f.read()
        records, summary = parse_app_log(content)
        print(f"Records: {len(records)}")
        print(f"Summary: {json.dumps(summary, indent=2)}")

        # DataFrame確認
        df = pd.DataFrame(records)
        print(f"\nDataFrame shape: {df.shape}")
        print(df.head())
