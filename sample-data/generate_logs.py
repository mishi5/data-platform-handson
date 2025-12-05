#!/usr/bin/env python3
"""
サンプルログ生成スクリプト
Webアクセスログ(Nginx形式)とアプリケーションログ(JSON形式)を生成
"""

import json
import random
from datetime import datetime, timedelta

# サンプルデータ
URLS = [
    "/",
    "/products",
    "/products/123",
    "/cart",
    "/checkout",
    "/api/users",
    "/api/products",
    "/search",
    "/about",
    "/contact",
]

STATUS_CODES = [200, 200, 200, 200, 201, 304, 400, 404, 500]
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15",
]

ACTIONS = ["page_view", "button_click", "form_submit", "api_call", "error"]
LOG_LEVELS = ["INFO", "INFO", "INFO", "WARNING", "ERROR"]


def generate_access_log(count=100):
    """Nginx形式のアクセスログを生成"""
    logs = []
    base_time = datetime.now() - timedelta(hours=1)

    for i in range(count):
        timestamp = base_time + timedelta(seconds=i * 10)
        ip = f"{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}"
        method = "GET" if random.random() > 0.2 else "POST"
        url = random.choice(URLS)
        status = random.choice(STATUS_CODES)
        size = random.randint(100, 50000)
        response_time = round(random.uniform(0.01, 2.0), 3)
        user_agent = random.choice(USER_AGENTS)

        # Nginx combined log format
        log = (
            f"{ip} - - [{timestamp.strftime('%d/%b/%Y:%H:%M:%S +0900')}] "
            f'"{method} {url} HTTP/1.1" {status} {size} "-" "{user_agent}" '
            f"rt={response_time}"
        )
        logs.append(log)

    return "\n".join(logs)


def generate_app_log(count=100):
    """JSON形式のアプリケーションログを生成"""
    logs = []
    base_time = datetime.now() - timedelta(hours=1)

    for i in range(count):
        timestamp = base_time + timedelta(seconds=i * 10)

        log_entry = {
            "timestamp": timestamp.isoformat(),
            "level": random.choice(LOG_LEVELS),
            "action": random.choice(ACTIONS),
            "user_id": f"user_{random.randint(1000, 9999)}",
            "session_id": f"sess_{random.randint(100000, 999999)}",
            "message": f"User performed {random.choice(ACTIONS)}",
            "duration_ms": random.randint(10, 1000),
            "metadata": {
                "ip": f"{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}",
                "endpoint": random.choice(URLS),
            },
        }

        # エラーの場合は追加情報を付与
        if log_entry["level"] == "ERROR":
            log_entry["error"] = {
                "type": random.choice(
                    ["DatabaseError", "ValidationError", "TimeoutError"]
                ),
                "message": "An error occurred during processing",
            }

        logs.append(json.dumps(log_entry))

    return "\n".join(logs)


if __name__ == "__main__":
    # アクセスログ生成
    access_logs = generate_access_log(200)
    with open("access.log", "w") as f:
        f.write(access_logs)
    print("✓ access.log generated (200 entries)")

    # アプリケーションログ生成
    app_logs = generate_app_log(200)
    with open("app.log", "w") as f:
        f.write(app_logs)
    print("✓ app.log generated (200 entries)")
