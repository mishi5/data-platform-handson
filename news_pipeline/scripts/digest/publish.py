"""ダイジェスト HTML を family-share に上げて Slack に通知する。

  uv run python scripts/digest/publish.py --html digest.html \
      --title "週次ダイジェスト 2026-08-30" [--content-id ID] [--slack] [--dry-run]

family-share は IAP 配下なので、gcloud でサービスアカウントを impersonate して
IDトークンを取る。--content-id を渡すと上書き（URL は変わらず、直近10世代を保持）。

Slack 通知はアップロード成功後にのみ行う。失敗した URL を通知しないため。
"""

import argparse
import os
import subprocess
import sys

import requests
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

SERVICE_URL = "https://family-share-76mm33owba-an.a.run.app"
SERVICE_ACCOUNT = "family-share-api@family-share-2607.iam.gserviceaccount.com"
AUDIENCE = "87908050213-v3c1a429pegd2je8gnta95fv1c73hk25.apps.googleusercontent.com"
_TIMEOUT = 60


def get_id_token() -> str:
    """IAP 用のIDトークンを取得する。失敗は例外にする（後続が必ず失敗するため）。"""
    cmd = [
        "gcloud",
        "auth",
        "print-identity-token",
        f"--impersonate-service-account={SERVICE_ACCOUNT}",
        f"--audiences={AUDIENCE}",
        "--include-email",
    ]
    # returncode を自分で判定するので check=False を明示する
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"failed to get ID token: {proc.stderr.strip()}")
    return proc.stdout.strip()


def upload_html(token: str, html_path: str, title: str, content_id: str | None) -> dict:
    """HTML をアップロードする。content_id があれば上書き、なければ新規。"""
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    if content_id:
        url = f"{SERVICE_URL}/api/content/{content_id}/upload"
        data = None
    else:
        url = f"{SERVICE_URL}/api/upload"
        data = {"title": title}

    with open(html_path, "rb") as f:
        files = {"file": (os.path.basename(html_path), f, "text/html")}
        resp = requests.post(
            url, headers=headers, files=files, data=data, timeout=_TIMEOUT
        )

    if resp.status_code not in (200, 201):
        raise RuntimeError(
            f"upload failed: {resp.status_code} {getattr(resp, 'text', '')[:200]}"
        )
    return resp.json()


def notify_slack(webhook_url: str, title: str, url: str, headlines: list[str]) -> None:
    """ダイジェストの公開を Slack に通知する。"""
    lines = "\n".join(f"• {h}" for h in headlines)
    payload = {
        "blocks": [
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*📰 {title}*\n<{url}|資料を開く>"},
            },
            {"type": "section", "text": {"type": "mrkdwn", "text": lines}},
        ]
    }
    resp = requests.post(webhook_url, json=payload, timeout=30)
    if resp.status_code != 200:
        raise RuntimeError(f"slack notify failed: {resp.status_code}")


def run(
    html_path: str,
    title: str,
    content_id: str | None,
    slack: bool,
    dry_run: bool,
    webhook_url: str | None,
    headlines: list[str] | None = None,
) -> int:
    if not os.path.exists(html_path):
        print(f"file not found: {html_path}", file=sys.stderr)
        return 1

    if dry_run:
        action = (
            f"上書き(content_id={content_id})" if content_id else "新規アップロード"
        )
        print(f"[dry-run] {action}: {html_path} (title={title!r})")
        print(f"[dry-run] Slack 通知: {'あり' if slack else 'なし'}")
        return 0

    try:
        token = get_id_token()
        result = upload_html(token, html_path, title, content_id)
    except Exception as e:
        print(f"アップロードに失敗しました: {e}", file=sys.stderr)
        return 1

    url = result.get("url", "")
    print(f"アップロード成功: {url}")
    print(f"content_id: {result.get('id', '')}")

    if not slack:
        return 0

    if not webhook_url:
        print("SLACK_WEBHOOK_URL が未設定のため通知をスキップしました", file=sys.stderr)
        return 1
    try:
        notify_slack(webhook_url, title, url, headlines or [])
    except Exception as e:
        print(f"Slack 通知に失敗しました: {e}", file=sys.stderr)
        return 1
    print("Slack に通知しました")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--html", required=True, help="アップロードする HTML のパス")
    parser.add_argument("--title", required=True)
    parser.add_argument("--content-id", default=None, help="指定すると上書き")
    parser.add_argument("--slack", action="store_true", help="Slack に通知する")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--headline",
        action="append",
        default=[],
        help="Slack に載せる見出し（複数指定可）",
    )
    args = parser.parse_args()

    return run(
        html_path=args.html,
        title=args.title,
        content_id=args.content_id,
        slack=args.slack,
        dry_run=args.dry_run,
        webhook_url=os.environ.get("SLACK_WEBHOOK_URL"),
        headlines=args.headline,
    )


if __name__ == "__main__":
    raise SystemExit(main())
