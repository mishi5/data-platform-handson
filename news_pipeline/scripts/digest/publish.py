"""ダイジェスト HTML を family-share に上げて Slack に通知する。

  uv run python scripts/digest/publish.py --html digest.html \
      --title "週次ダイジェスト 2026-08-30" [--content-id ID] [--slack] [--dry-run]

family-share は IAP 配下なので、gcloud でサービスアカウントを impersonate して
IDトークンを取る。--content-id を渡すと上書き（URL は変わらず、直近10世代を保持）。

削除は Web UI からしかできないので、取り返しのつかない操作の手前で止めることを
優先している:

  * 同じタイトルの資料が既にあるなら新規アップロードを拒否する（--content-id を
    使うか --force-new を明示させる）
  * --slack なのに webhook URL が無い、ファイルが空・上限超過、といった「後で
    必ず失敗する条件」はアップロード前に判定する
  * Slack 通知はアップロード成功後にのみ行う（存在しない URL を通知しないため）
  * --dry-run は本番と同じ判定を通す。違いは POST しないことだけ
"""

import argparse
import json
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
# family-share の受け入れ上限
MAX_UPLOAD_BYTES = 30 * 1024 * 1024
# Slack の section ブロックの mrkdwn 上限。超えると invalid_blocks で 400 になる
SLACK_SECTION_LIMIT = 3000


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


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Accept": "application/json"}


def _json_or_raise(resp, what: str) -> dict:
    """JSON 応答を取り出す。IAP がログイン画面の HTML を返すことがある。"""
    try:
        return resp.json()
    except ValueError as e:
        body = (getattr(resp, "text", "") or "")[:200]
        raise RuntimeError(f"{what}: response is not JSON: {body}") from e


def list_contents(token: str) -> list[dict]:
    """family-share の公開済み一覧を返す。"""
    resp = requests.get(
        f"{SERVICE_URL}/api/contents", headers=_auth_headers(token), timeout=_TIMEOUT
    )
    if resp.status_code != 200:
        raise RuntimeError(f"failed to list contents: {resp.status_code}")
    return _json_or_raise(resp, "list contents").get("items", [])


def find_content_by_title(token: str, title: str) -> dict | None:
    """同じタイトルの公開済みコンテンツを返す（無ければ None）。

    完全一致で照合する。ダイジェストのタイトルは日付入りなので、一致＝同じ回の
    再アップロードとみなしてよい。
    """
    for item in list_contents(token):
        if item.get("title") == title:
            return item
    return None


def upload_html(token: str, html_path: str, title: str, content_id: str | None) -> dict:
    """HTML をアップロードする。content_id があれば上書き、なければ新規。"""
    headers = _auth_headers(token)
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
    result = _json_or_raise(resp, "upload")
    if not result.get("url"):
        raise RuntimeError(f"upload response has no url: {str(result)[:200]}")
    return result


def escape_mrkdwn(text: str) -> str:
    """Slack mrkdwn の予約文字を escape する。リンク記法を壊さないため。"""
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _section(text: str) -> dict:
    return {"type": "section", "text": {"type": "mrkdwn", "text": text}}


def build_slack_payload(title: str, url: str, headlines: list[str]) -> dict:
    """通知の Block Kit ペイロードを組み立てる。

    空文字の section は Slack が invalid_blocks で弾くので、見出しが無ければ
    ブロックごと落とす。section の mrkdwn 上限（3000）でも 400 になるため切り詰める。
    """
    head = f"*📰 {escape_mrkdwn(title)}*\n<{url}|資料を開く>"
    blocks = [_section(head[:SLACK_SECTION_LIMIT])]

    lines = [f"• {escape_mrkdwn(h)}" for h in (headlines or []) if str(h).strip()]
    body = "\n".join(lines)
    if body.strip():
        if len(body) > SLACK_SECTION_LIMIT:
            body = body[: SLACK_SECTION_LIMIT - 1] + "…"
        blocks.append(_section(body))
    return {"blocks": blocks}


def notify_slack(webhook_url: str, title: str, url: str, headlines: list[str]) -> None:
    """ダイジェストの公開を Slack に通知する。"""
    payload = build_slack_payload(title, url, headlines)
    resp = requests.post(webhook_url, json=payload, timeout=30)
    if resp.status_code != 200:
        body = (getattr(resp, "text", "") or "")[:200]
        raise RuntimeError(f"slack notify failed: {resp.status_code} {body}")


def _check_source_file(html_path: str) -> str | None:
    """アップロードして良いファイルか調べる。問題があれば理由を返す。"""
    if not os.path.exists(html_path):
        return f"file not found: {html_path}"
    size = os.path.getsize(html_path)
    if size == 0:
        return f"file is empty: {html_path}"
    if size > MAX_UPLOAD_BYTES:
        return f"file is too large ({size} bytes > {MAX_UPLOAD_BYTES}): {html_path}"
    return None


def _duplicate_message(existing: dict) -> str:
    return (
        f"同じタイトルの資料が既にあります (content_id={existing.get('id')} "
        f"url={existing.get('url')})。\n"
        f"  更新するなら: --content-id {existing.get('id')}\n"
        f"  別物として2本目を上げるなら: --force-new\n"
        f"（family-share の削除は Web UI からしかできないため、既定では止めます）"
    )


def run(
    html_path: str,
    title: str,
    content_id: str | None,
    slack: bool,
    dry_run: bool,
    webhook_url: str | None,
    headlines: list[str] | None = None,
    force_new: bool = False,
) -> int:
    problem = _check_source_file(html_path)
    if problem:
        print(problem, file=sys.stderr)
        return 1

    # 後で必ず失敗する条件は、アップロードより先に落とす。上げてから通知に失敗すると
    # 消せない資料だけが残る。
    if slack and not webhook_url:
        print(
            "SLACK_WEBHOOK_URL が未設定です（--slack を外すか .env を設定）",
            file=sys.stderr,
        )
        return 1

    token = None
    existing = None
    if content_id is None and not force_new:
        try:
            token = get_id_token()
            existing = find_content_by_title(token, title)
        except Exception as e:
            print(f"公開済み一覧の照合に失敗しました: {e}", file=sys.stderr)
            if not dry_run:
                return 1
            print("[dry-run] 重複チェックを省略しました", file=sys.stderr)
        if existing:
            print(_duplicate_message(existing), file=sys.stderr)
            return 1

    if dry_run:
        action = (
            f"上書き(content_id={content_id})" if content_id else "新規アップロード"
        )
        size = os.path.getsize(html_path)
        print(f"[dry-run] {action}: {html_path} ({size} bytes, title={title!r})")
        if slack:
            payload = build_slack_payload(
                title, f"{SERVICE_URL}/view/(新規ID)", headlines or []
            )
            print("[dry-run] Slack 通知:")
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print("[dry-run] Slack 通知: なし")
        return 0

    try:
        # 重複チェックで取得済みなら使い回す（gcloud の呼び出しは遅い）
        if token is None:
            token = get_id_token()
        result = upload_html(token, html_path, title, content_id)
    except Exception as e:
        print(f"アップロードに失敗しました: {e}", file=sys.stderr)
        return 1

    url = result["url"]
    new_id = result.get("id", "")
    print(f"アップロード成功: {url}")
    print(f"content_id: {new_id}")
    print(f"更新するときは --content-id {new_id} を付ける")

    if not slack:
        return 0

    try:
        notify_slack(webhook_url, title, url, headlines or [])
    except Exception as e:
        print(f"Slack 通知に失敗しました: {e}", file=sys.stderr)
        print("（資料は公開済み。再通知は同じ URL で手動で行う）", file=sys.stderr)
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
        "--force-new",
        action="store_true",
        help="同じタイトルが既にあっても新規として上げる",
    )
    parser.add_argument(
        "--headline",
        action="append",
        default=None,
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
        headlines=args.headline or [],
        force_new=args.force_new,
    )


if __name__ == "__main__":
    raise SystemExit(main())
