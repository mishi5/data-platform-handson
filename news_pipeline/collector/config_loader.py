"""Google Sheets から設定を読み込むモジュール。

Sheets API は一時的に 503 を返すことがある。設定ロードの失敗は
呼び出し側の設定ガードでパイプライン全体の例外になる（＝その回の通知が
丸ごとスキップされる）ため、一時障害は指数バックオフで再試行する。
"""

import logging
import os
import time

import google.auth
import gspread
from google.auth.transport.requests import Request
from note_fetcher import source_name as note_source_name

logger = logging.getLogger(__name__)

SHEET_ID = os.environ.get("SHEET_ID", "")

# 一時障害とみなす Sheets API のステータスコード。403（権限）や 404（シート無し）
# のような恒久的な失敗は再試行しても同じなので対象外。
_RETRYABLE_CODES = frozenset({500, 502, 503, 504})
_MAX_ATTEMPTS = 3
_BACKOFF_SECONDS = 1.0


def _is_transient(error: Exception) -> bool:
    """再試行する価値のある一時障害かを判定する。"""
    if isinstance(error, (ConnectionError, TimeoutError)):
        return True
    return getattr(error, "code", None) in _RETRYABLE_CODES


def load_config() -> dict:
    """Google Sheets から feeds / keywords / settings を読み込む。失敗時は空 dict を返す。

    一時障害（5xx・接続エラー）は指数バックオフで最大 _MAX_ATTEMPTS 回試行する。
    """
    if not SHEET_ID:
        logger.warning("[config_loader] SHEET_ID not set, returning empty config")
        return {}
    for attempt in range(_MAX_ATTEMPTS):
        try:
            return _load_config_once()
        except Exception as e:
            last_attempt = attempt == _MAX_ATTEMPTS - 1
            if not _is_transient(e) or last_attempt:
                logger.error(
                    "[config_loader] failed to load from Google Sheets: (%s) %s",
                    type(e).__name__,
                    e,
                )
                return {}
            wait = _BACKOFF_SECONDS * (2**attempt)
            logger.warning(
                "[config_loader] transient error from Google Sheets "
                "(attempt %d/%d), retrying in %.1fs: (%s) %s",
                attempt + 1,
                _MAX_ATTEMPTS,
                wait,
                type(e).__name__,
                e,
            )
            time.sleep(wait)
    return {}


def _load_config_once() -> dict:
    """Sheets から1回だけ読み込む。失敗は例外のまま呼び出し側へ返す。"""
    credentials, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
    )
    credentials.refresh(Request())
    gc = gspread.Client(auth=credentials)
    spreadsheet = gc.open_by_key(SHEET_ID)
    feeds = _load_feeds(spreadsheet)
    keywords = _load_keywords(spreadsheet)
    feed_categories = _load_feed_categories(spreadsheet)
    feed_blocks = _load_feed_blocks(spreadsheet)
    settings = _load_settings(spreadsheet)
    note_tags = _load_note_tags(spreadsheet)
    _merge_note_tags(note_tags, feed_categories, feed_blocks)
    logger.info(
        "[config_loader] loaded %d feeds, %d note tags, %d keywords, "
        "%d setting groups from Sheets",
        len(feeds),
        len(note_tags),
        len(keywords),
        len(settings),
    )
    return {
        "feeds": feeds,
        "note_tags": [t["tag"] for t in note_tags],
        "keywords": keywords,
        "feed_categories": feed_categories,
        "feed_blocks": feed_blocks,
        "settings": settings,
    }


def _load_feeds(spreadsheet) -> dict[str, str]:
    """feeds シートを {URL: Source Name} の dict で返す。"""
    try:
        ws = spreadsheet.worksheet("feeds")
        rows = ws.get_all_values()[1:]  # 1行目はヘッダー
        return {row[0]: row[1] for row in rows if len(row) >= 2 and row[0]}
    except Exception as e:
        logger.warning("[config_loader] failed to load feeds sheet: %s", e)
        return {}


def _load_feed_categories(spreadsheet) -> dict[str, str]:
    """feeds シートを {Source Name: category} の dict で返す。category 列が無ければ空文字。"""
    try:
        ws = spreadsheet.worksheet("feeds")
        rows = ws.get_all_values()[1:]  # 1行目はヘッダー
        result: dict[str, str] = {}
        for row in rows:
            if len(row) >= 2 and row[1]:
                source = row[1]
                category = row[2] if len(row) >= 3 else ""
                result[source] = category
        return result
    except Exception as e:
        logger.warning("[config_loader] failed to load feed categories: %s", e)
        return {}


def _load_feed_blocks(spreadsheet) -> dict[str, dict]:
    """feeds シートを {source: {"users": set, "location": str}} で返す。

    4列目 block_users（カンマ区切り）、5列目 user_location（空欄は path1）。
    block_users が空の行は登録しない。
    """
    try:
        ws = spreadsheet.worksheet("feeds")
        rows = ws.get_all_values()[1:]  # 1行目はヘッダー
        result: dict[str, dict] = {}
        for row in rows:
            if len(row) < 4 or not row[1]:
                continue
            source = row[1]
            users = {u.strip() for u in row[3].split(",") if u.strip()}
            if not users:
                continue
            location = row[4].strip() if len(row) >= 5 and row[4].strip() else "path1"
            result[source] = {"users": users, "location": location}
        return result
    except Exception as e:
        logger.warning("[config_loader] failed to load feed blocks: %s", e)
        return {}


def _load_note_tags(spreadsheet) -> list[dict]:
    """note_tags シート（tag | category | block_users）を行ごとの dict のリストで返す。

    tag は先頭の # を除去する（書き方の揺れを吸収）。tag が空の行は読み飛ばす。
    シートが無い・読めない場合は空リスト（note のタグ経路が無いだけで RSS は続行する）。
    """
    try:
        ws = spreadsheet.worksheet("note_tags")
        rows = ws.get_all_values()[1:]  # 1行目はヘッダー
        result: list[dict] = []
        for row in rows:
            tag = row[0].strip().lstrip("#").strip() if row else ""
            if not tag:
                continue
            category = row[1].strip() if len(row) >= 2 else ""
            users_cell = row[2] if len(row) >= 3 else ""
            users = {u.strip() for u in users_cell.split(",") if u.strip()}
            result.append({"tag": tag, "category": category, "block_users": users})
        return result
    except Exception as e:
        logger.warning("[config_loader] failed to load note_tags sheet: %s", e)
        return []


def _merge_note_tags(
    note_tags: list[dict], feed_categories: dict[str, str], feed_blocks: dict[str, dict]
) -> None:
    """note のタグ経路の source 名で category・ブロックを登録する（破壊的に更新）。

    category とブロックは source 名で収集時・通知時の両方から引かれるため、
    feeds シートと同じ辞書に合流させる。feeds 側に同名 source があれば feeds を優先する。
    note の URL は note.com/<urlname>/n/<key> なので照合位置は path1 固定。
    """
    for t in note_tags:
        source = note_source_name(t["tag"])
        feed_categories.setdefault(source, t["category"])
        if t["block_users"] and source not in feed_blocks:
            feed_blocks[source] = {"users": t["block_users"], "location": "path1"}


def _load_keywords(spreadsheet) -> list[str]:
    """keywords シートをキーワードのリストで返す。"""
    try:
        ws = spreadsheet.worksheet("keywords")
        rows = ws.get_all_values()[1:]  # 1行目はヘッダー
        return [row[0].lower() for row in rows if row and row[0]]
    except Exception as e:
        logger.warning("[config_loader] failed to load keywords sheet: %s", e)
        return []


def _load_settings(spreadsheet) -> dict[str, dict]:
    """settings シートを {group: {key: value}} のネスト dict で返す。

    シートは group | key | value の3列。value は int 変換可能なら int 化する。
    group の出現順を保持する（通知順の決定に使う）。
    """
    try:
        ws = spreadsheet.worksheet("settings")
        rows = ws.get_all_values()[1:]  # 1行目はヘッダー
        result: dict = {}
        for row in rows:
            if len(row) >= 3 and row[0] and row[1]:
                group, key, val = row[0], row[1], row[2]
                try:
                    typed = int(val)
                except ValueError:
                    typed = val
                result.setdefault(group, {})[key] = typed
        return result
    except Exception as e:
        logger.warning("[config_loader] failed to load settings sheet: %s", e)
        return {}
