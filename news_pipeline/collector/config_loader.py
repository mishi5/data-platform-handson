"""Google Sheets から設定を読み込むモジュール。"""
import logging
import os

import google.auth
import gspread
from google.auth.transport.requests import Request

logger = logging.getLogger(__name__)

SHEET_ID = os.environ.get("SHEET_ID", "")


def load_config() -> dict:
    """Google Sheets から feeds / keywords / settings を読み込む。失敗時は空 dict を返す。"""
    if not SHEET_ID:
        logger.warning("[config_loader] SHEET_ID not set, returning empty config")
        return {}
    try:
        credentials, _ = google.auth.default(
            scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
        )
        credentials.refresh(Request())
        gc = gspread.Client(auth=credentials)
        spreadsheet = gc.open_by_key(SHEET_ID)
        feeds = _load_feeds(spreadsheet)
        keywords = _load_keywords(spreadsheet)
        settings = _load_settings(spreadsheet)
        logger.info(
            "[config_loader] loaded %d feeds, %d keywords, settings=%s from Sheets",
            len(feeds),
            len(keywords),
            settings,
        )
        return {"feeds": feeds, "keywords": keywords, **settings}
    except Exception as e:
        logger.error("[config_loader] failed to load from Google Sheets: (%s) %s", type(e).__name__, e)
        return {}


def _load_feeds(spreadsheet) -> dict[str, str]:
    """feeds シートを {URL: Source Name} の dict で返す。"""
    try:
        ws = spreadsheet.worksheet("feeds")
        rows = ws.get_all_values()[1:]  # 1行目はヘッダー
        return {row[0]: row[1] for row in rows if len(row) >= 2 and row[0]}
    except Exception as e:
        logger.warning("[config_loader] failed to load feeds sheet: %s", e)
        return {}


def _load_keywords(spreadsheet) -> list[str]:
    """keywords シートをキーワードのリストで返す。"""
    try:
        ws = spreadsheet.worksheet("keywords")
        rows = ws.get_all_values()[1:]  # 1行目はヘッダー
        return [row[0].lower() for row in rows if row and row[0]]
    except Exception as e:
        logger.warning("[config_loader] failed to load keywords sheet: %s", e)
        return []


def _load_settings(spreadsheet) -> dict:
    """settings シートを {key: value} の dict で返す。数値は int 変換。"""
    try:
        ws = spreadsheet.worksheet("settings")
        rows = ws.get_all_values()[1:]  # 1行目はヘッダー
        result = {}
        for row in rows:
            if len(row) >= 2 and row[0]:
                key, val = row[0], row[1]
                try:
                    result[key] = int(val)
                except ValueError:
                    result[key] = val
        return result
    except Exception as e:
        logger.warning("[config_loader] failed to load settings sheet: %s", e)
        return {}
