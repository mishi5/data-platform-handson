"""note のハッシュタグに付いた記事を非公式 API から取得するモジュール。

note のハッシュタグ RSS は最新25件しか返さず、1日1回の収集では取りこぼす。
一覧 API（/api/v3/hashtags/{tag}/notes）は order=new でページ送りできるので、
lookback_days 日前の記事に到達するまで遡って取得する。

非公式 API のため、依存は記事一覧の取得だけに限定する。本文は記事ページから
article_parser（trafilatura）で取得する。認証が必要なエンドポイントは使わず、
リクエスト間に待ちを入れて低頻度に保つ。

戻り値は rss_fetcher.fetch_articles と同じ形の dict。一覧 API の body（本文冒頭
240字）を description に入れ、1次フィルタ（Jev）の入力にする。origin="note_tag"
は main の1次フィルタがタグ経路の記事を見分けるための一時情報で、description と
同様に raw_articles 保存前に除去される。
"""

import logging
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

import requests
from rss_fetcher import _HEADERS, _make_article_id, _normalize_url

logger = logging.getLogger(__name__)

_API_URL = "https://note.com/api/v3/hashtags/{tag}/notes"
_TIMEOUT_SECONDS = 30
_REQUEST_INTERVAL_SECONDS = 1.0

ORIGIN = "note_tag"


def source_name(tag: str) -> str:
    """タグ経路の記事の source 名。config_loader も category・ブロックの登録に使う。"""
    return f"note #{tag}"


def _to_article(note: dict, tag: str, collected_at: str) -> dict:
    url = _normalize_url(f"https://note.com/{note['user']['urlname']}/n/{note['key']}")
    return {
        "article_id": _make_article_id(url),
        "title": note.get("name") or "",
        "url": url,
        "source": source_name(tag),
        "published_at": note.get("publish_at"),
        "collected_at": collected_at,
        "description": note.get("body") or "",
        "origin": ORIGIN,
    }


def _is_target(note: dict) -> bool:
    # 有料記事は trafilatura で無料部分しか取れず要約の質が下がる。
    # TextNote 以外（画像・つぶやき・動画）は本文が無い。
    return note.get("type") == "TextNote" and not note.get("price")


def fetch_articles(tags: list[str], lookback_days: int, max_pages: int) -> list[dict]:
    """タグごとに新着を lookback_days 日前まで遡って取得する。

    タグ単位で失敗を隔離し、失敗したタグはそれまでの取得分だけ返して次のタグへ進む。
    """
    results: list[dict] = []
    since = datetime.now(timezone.utc) - timedelta(days=lookback_days)
    collected_at = datetime.now(timezone.utc).isoformat()
    requested = False

    for tag in tags:
        fetched = skipped = pages = 0
        try:
            for page in range(1, max_pages + 1):
                if requested:
                    time.sleep(_REQUEST_INTERVAL_SECONDS)
                requested = True
                response = requests.get(
                    _API_URL.format(tag=quote(tag, safe="")),
                    params={"order": "new", "page": page},
                    headers=_HEADERS,
                    timeout=_TIMEOUT_SECONDS,
                )
                response.raise_for_status()
                data = response.json()["data"]
                notes = data["notes"]
                pages += 1

                reached_old = False
                for note in notes:
                    if datetime.fromisoformat(note["publish_at"]) < since:
                        reached_old = True
                        break
                    if not _is_target(note):
                        skipped += 1
                        continue
                    results.append(_to_article(note, tag, collected_at))
                    fetched += 1

                if reached_old or not notes or data.get("is_last_page"):
                    break
        except Exception as e:
            logger.warning(
                "[note_fetcher] #%s failed on page %d: %s", tag, pages + 1, e
            )
        logger.info(
            "[note_fetcher] #%s: %d notes (%d pages, skipped %d paid/non-text)",
            tag,
            fetched,
            pages,
            skipped,
        )

    return results
