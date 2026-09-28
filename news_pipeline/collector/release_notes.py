"""Google Cloud のリリースノートを日付単位の記事として扱うモジュール。

リリースノートのフィード（例: cloud.google.com/feeds/bigquery-release-notes.xml）は
1日1エントリで、リンクは同じページ内のアンカー違い
（…/bigquery/docs/release-notes#September_24_2026）になっている。

- URL 正規化で fragment を落とすと全エントリが同じ URL になり dedup で消えるため、
  rss_fetcher はこの URL に限って fragment を残す（is_release_notes_url で判定）。
- ページ全体を trafilatura に渡すと数か月分が本文になるため、アンカーの <h2> から
  次の <h2> までの区間（＝その日の分）だけをテキストにして返す。
"""

import logging
import re
from urllib.parse import urlsplit, urlunsplit

import lxml.html
import requests

logger = logging.getLogger(__name__)

_HOSTS = {"cloud.google.com", "docs.cloud.google.com"}

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}


def is_release_notes_url(url: str) -> bool:
    """Google Cloud のリリースノートの日付アンカー付き URL か。"""
    parts = urlsplit(url)
    return (
        parts.hostname in _HOSTS
        and parts.path.rstrip("/").endswith("/release-notes")
        and bool(parts.fragment)
    )


def extract_section(html: str, anchor: str) -> str | None:
    """ページ HTML から id=anchor の <h2> 以降、次の <h2> までをテキストにする。

    アンカーが無ければ None。項目ごとに「種別: 本文」の1段落にする。
    """
    start = re.search(rf'<h2[^>]*\bid="{re.escape(anchor)}"', html)
    if not start:
        return None
    body_start = html.find(">", start.end()) + 1
    rest = html[body_start:]
    end = re.search(r"<h2[\s>]|</section>", rest)
    fragment = rest[: end.start()] if end else rest
    # 先頭の <h2> 見出し（日付）の閉じタグまでを飛ばす
    fragment = fragment.split("</h2>", 1)[-1]
    if not fragment.strip():
        return None

    root = lxml.html.fragment_fromstring(fragment, create_parent="div")
    paragraphs = []
    for note in root.find_class("devsite-release-note"):
        labels = note.find_class("devsite-label")
        label = labels[0].text_content().strip() if labels else ""
        for lb in labels:
            lb.drop_tree()
        body = _squash(note.text_content())
        if body:
            paragraphs.append(f"{label}: {body}" if label else body)
    if not paragraphs:
        # 構造が変わった場合もテキストだけは返す
        text = _squash(root.text_content())
        return text or None
    return "\n\n".join(paragraphs)


def _squash(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def fetch_release_note(url: str) -> tuple[str | None, bool]:
    """リリースノートの URL から、その日の分の本文を取得する。

    戻り値は article_parser.fetch_content と同じ (text, ok)。
    アンカーがページに無い（改訂で消えた等）場合は再取得しても戻らないので
    (None, True) のスキップ、通信エラーは (None, False) で pending に回す。
    """
    parts = urlsplit(url)
    page_url = urlunsplit((parts.scheme, parts.netloc, parts.path, parts.query, ""))
    try:
        response = requests.get(page_url, headers=_HEADERS, timeout=30)
        response.raise_for_status()
    except Exception as e:
        logger.warning("[release_notes] failed to fetch %s: %s", page_url, e)
        return None, False
    text = extract_section(response.text, parts.fragment)
    if text is None:
        logger.warning("[release_notes] anchor not found: %s", url)
    return text, True
