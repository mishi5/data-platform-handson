"""記事URLからユーザー識別子を抽出し、ブロック対象か判定するモジュール。"""

from urllib.parse import urlparse


def extract_user(url: str, location: str) -> str | None:
    """URL からユーザー識別子を抽出する。抽出できなければ None。

    location:
      "" / "path1"      -> パス第1セグメント（Zenn / Qiita / note）
      "subdomain"       -> ホスト名の先頭ラベル（はてなブログ等）
      "path2","path3".. -> パスの N 番目セグメント（1始まり）
    """
    parsed = urlparse(url)
    loc = (location or "path1").strip().lower()

    if loc == "subdomain":
        host = parsed.hostname or ""
        label = host.split(".")[0]
        return label or None

    if loc.startswith("path"):
        suffix = loc[len("path") :]
        index = int(suffix) if suffix.isdigit() else 1
        segments = [s for s in parsed.path.split("/") if s]
        if 1 <= index <= len(segments):
            return segments[index - 1]
        return None

    return None


def is_blocked(url: str, users: set[str], location: str) -> bool:
    """URL から抽出したユーザーが users に完全一致で含まれれば True。"""
    if not users:
        return False
    user = extract_user(url, location)
    return user is not None and user in users
