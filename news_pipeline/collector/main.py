"""
news_pipeline メインモジュール。

FastAPI サーバーとして起動し、以下のエンドポイントを提供する:
  POST /collect       - Cloud Scheduler からの収集トリガー（RSS取得〜要約〜保存）
  POST /notify        - Cloud Scheduler からの通知トリガー（未通知サマリーを通知）
  POST /slack         - Slack スラッシュコマンド（/news-update）からの手動通知トリガー
  POST /slack/deepdive - Slack スラッシュコマンド（/news-deepdive）からの深堀りトリガー

収集処理は _run_collect()、通知処理は _run_notify() に分離されており、
Slack エンドポイントではタイムアウト対策として BackgroundTasks で実行する。
"""

import asyncio
import hashlib
import hmac
import json
import logging
import os
import time
import urllib.parse

from article_parser import fetch_content
from blocklist import is_blocked
from bq_client import BQClient
from categorizer import (
    category_label,
    category_limit,
    group_by_category,
    order_categories,
)
from config_loader import load_config
from deepdiver import deepdive_article
from dotenv import load_dotenv
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request
from fetch_retry import next_fetch_state
from notifier import (
    format_favorites_blocks,
    send_error_notification,
    send_no_news_notification,
    send_slack_notification,
)
from pydantic import BaseModel
from rss_fetcher import fetch_articles
from speakerdeck import is_speakerdeck_url
from summarizer import (
    SCORING_VERSION,
    _as_float,
    score_article,
    score_slide_relevance,
    summarize_article,
)

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

PROJECT_ID = os.environ["GCP_PROJECT_ID"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
SLACK_WEBHOOK_URL = os.environ["SLACK_WEBHOOK_URL"]
SLACK_SIGNING_SECRET = os.environ.get("SLACK_SIGNING_SECRET", "")

# max_summarize: 1実行で要約する記事の最大件数（Google Sheetsのsettingsシートから取得）
_DEFAULT_MAX_SUMMARIZE = 10
# settings シートの general から取得するデフォルト値
_DEFAULT_IMPORTANCE_THRESHOLD = 0.65
# relevance_threshold: データ基盤との関連度の下限。良質でも対象領域外の記事を落とす。
# モデルは 0.5 のような丸い値を出しやすいため、境界をその上にずらして 0.5 を落とす。
_DEFAULT_RELEVANCE_THRESHOLD = 0.55
_DEFAULT_MAX_CONTENT_RETRIES = 3
_DEFAULT_RECALCULATE_LIMIT = 50
# resummarize: 要約漏れ記事（本文ありで summaries 無し）の復旧バッチ設定
_DEFAULT_RESUMMARIZE_LIMIT = 50
_DEFAULT_RESUMMARIZE_DAYS = 7
# slide_prefilter_threshold: Speaker Deck の PDF を取得する前に title+description で
# 関連度を見積もり、この値未満なら PDF をスキップする。description が空で title 中心の
# 判定になりやすく辛めに出るうえ、採点基準にドメイン定義が入って更に辛くなったため、
# 取りこぼし防止を優先して低めに設定する（filtered は終端で再取得されない）。
_DEFAULT_SLIDE_PREFILTER_THRESHOLD = 0.2
# personalize_top_tags: お気に入り記事のタグ頻度上位N個を採点の加点ヒントに使う。
# 0 で無効（BigQuery クエリ自体をスキップ）。
_DEFAULT_PERSONALIZE_TOP_TAGS = 5


class PipelineResponse(BaseModel):
    status: str
    notified: int


class SlackResponse(BaseModel):
    response_type: str
    text: str


def _post_to_response_url(response_url: str, text: str) -> None:
    """Slack の response_url に遅延応答を POST する。"""
    import requests as _requests

    try:
        _requests.post(
            response_url,
            json={"response_type": "in_channel", "text": text},
            timeout=10,
        )
    except Exception as e:
        logger.error("[deepdive] failed to post to response_url: %s", e)


async def verify_slack(request: Request) -> None:
    """Slack署名を検証するDependency。失敗時は HTTPException(403)。"""
    if not SLACK_SIGNING_SECRET:
        return
    timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
    try:
        if abs(time.time() - int(timestamp)) > 300:
            raise HTTPException(status_code=403, detail="invalid signature")
    except ValueError:
        raise HTTPException(status_code=403, detail="invalid signature")
    body = await request.body()
    sig_basestring = f"v0:{timestamp}:{body.decode()}"
    expected = (
        "v0="
        + hmac.new(
            SLACK_SIGNING_SECRET.encode(), sig_basestring.encode(), hashlib.sha256
        ).hexdigest()
    )
    if not hmac.compare_digest(expected, request.headers.get("X-Slack-Signature", "")):
        raise HTTPException(status_code=403, detail="invalid signature")


def passes_thresholds(
    summary: dict, importance_threshold: float, relevance_threshold: float
) -> bool:
    """サマリーが通知対象かを判定する。

    importance（読む価値）と relevance（データ基盤との関連度）の2軸ゲート。
    relevance が判定不能（None・非数値・キー欠落）の場合は通す。モデルが
    relevance を返さなかっただけで良記事を落とすと取りこぼしになるため。
    """
    importance = _as_float(summary.get("importance_score"))
    if importance is None or importance < importance_threshold:
        return False
    relevance = _as_float(summary.get("relevance_score"))
    if relevance is not None and relevance < relevance_threshold:
        return False
    return True


def _load_favorite_tags(bq: BQClient, general: dict) -> list[str]:
    """お気に入り由来の関心タグを取得する（採点のパーソナライズ用）。

    personalize_top_tags=0 なら無効（クエリ自体をスキップ）。取得失敗時は
    空リストで続行し、パーソナライズなしの通常採点にフォールバックする。
    """
    limit = int(general.get("personalize_top_tags", _DEFAULT_PERSONALIZE_TOP_TAGS))
    if limit <= 0:
        return []
    try:
        tags = bq.get_favorite_tag_counts(limit)
        if tags:
            logger.info("[personalize] favorite tags: %s", tags)
        return tags
    except Exception as e:
        logger.warning("[personalize] failed to load favorite tags: %s", e)
        return []


def _filter_blocked(items: list[dict], feed_blocks: dict) -> list[dict]:
    """url/source を持つ dict のリストから、ブロック対象ユーザーの記事を除外する。"""
    kept = []
    for item in items:
        block = feed_blocks.get(item["source"], {})
        if is_blocked(
            item["url"], block.get("users", set()), block.get("location", "path1")
        ):
            continue
        kept.append(item)
    return kept


def _run_collect(triggered_by: str = "scheduler") -> int:
    """収集パイプライン。RSS取得〜要約〜summaries保存。新着要約件数を返す。"""
    import uuid
    from datetime import datetime, timezone

    run_id = str(uuid.uuid4())
    started_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    log: dict = {
        "run_id": run_id,
        "triggered_by": triggered_by,
        "started_at": started_at,
        "finished_at": None,
        "articles_fetched": 0,
        "new_articles": 0,
        "summaries_generated": 0,
        "notified_count": 0,
        "error_count": 0,
        "status": "success",
        "error_message": None,
        "keywords": [],
    }

    config = load_config()
    feeds: dict[str, str] = config.get("feeds", {})
    keywords: list[str] = config.get("keywords", [])
    feed_blocks: dict = config.get("feed_blocks", {})
    settings: dict = config.get("settings", {})
    general: dict = settings.get("general", {})
    max_summarize: int = int(general.get("max_summarize", _DEFAULT_MAX_SUMMARIZE))
    importance_threshold: float = float(
        general.get("importance_threshold", _DEFAULT_IMPORTANCE_THRESHOLD)
    )
    relevance_threshold: float = float(
        general.get("relevance_threshold", _DEFAULT_RELEVANCE_THRESHOLD)
    )
    max_content_retries: int = int(
        general.get("max_content_retries", _DEFAULT_MAX_CONTENT_RETRIES)
    )
    slide_prefilter_threshold: float = float(
        general.get("slide_prefilter_threshold", _DEFAULT_SLIDE_PREFILTER_THRESHOLD)
    )
    log["keywords"] = keywords

    bq = BQClient(project=PROJECT_ID)

    try:
        # 0. 設定ガード。Sheets 読み込み失敗（load_config が {} を返す）や feeds 空を
        #    「新着0件の成功」として黙って完了させず、エラーとして観測可能にする。
        if not feeds:
            raise RuntimeError(
                "feeds is empty: Google Sheets の設定読み込みに失敗した可能性"
            )

        # 0.5. お気に入り由来の関心タグ（採点のパーソナライズ用。失敗しても続行）
        favorite_tags = _load_favorite_tags(bq, general)

        # 1. RSS 取得
        articles = fetch_articles(feeds)
        log["articles_fetched"] = len(articles)
        logger.info("[collect] fetched %d articles from RSS", len(articles))

        # 1.5. ブロックユーザーの記事を除外
        before_block = len(articles)
        articles = _filter_blocked(articles, feed_blocks)
        if before_block != len(articles):
            logger.info(
                "[collect] blocked %d articles by feed block list",
                before_block - len(articles),
            )

        # 2. dedup（raw_articles ベース + 同一実行内）→ 全新着を保持（切り捨てない）
        #    同じURLが複数フィードに載ることがあるため、実行内でも重複を排除する
        existing_urls = bq.get_existing_urls()
        new_articles = []
        seen_urls: set[str] = set()
        for a in articles:
            if a["url"] in existing_urls or a["url"] in seen_urls:
                continue
            seen_urls.add(a["url"])
            new_articles.append(a)
        log["new_articles"] = len(new_articles)
        logger.info("[collect] %d new articles", len(new_articles))

        # 2.5. Speaker Deck の1次フィルタ（PDF取得前に title+description で関連度判定）。
        #      高コストな PDF ビジョン書き起こしの前に明らかな無関係を除外する。
        #      判定不能（None）や閾値以上は通す（取りこぼし防止）。弾いた記事は
        #      raw_articles に content_status='filtered' で記録し再取得しない。
        survivors: list[dict] = []
        prefiltered = 0
        for a in new_articles:
            if is_speakerdeck_url(a["url"]):
                score = score_slide_relevance(
                    title=a["title"],
                    description=a.get("description", ""),
                    api_key=ANTHROPIC_API_KEY,
                    keywords=keywords,
                    favorite_tags=favorite_tags,
                )
                if score is not None and score < slide_prefilter_threshold:
                    a["content"] = None
                    a["content_status"] = "filtered"
                    a["retry_count"] = 0
                    prefiltered += 1
                    continue
            survivors.append(a)
        if prefiltered:
            logger.info(
                "[collect] slide prefilter skipped %d slides (threshold=%.2f)",
                prefiltered,
                slide_prefilter_threshold,
            )

        # to_summarize: この実行で本文取得に成功した記事（繰り越し + 新着）
        to_summarize: list[dict] = []

        # 3. 繰り越し（pending）を優先処理。古い順・最大 max_summarize 件まで。
        #    max_summarize は「繰り越し + 新着」合算の1実行バジェット。
        pending = bq.get_pending_articles(max_content_retries, limit=max_summarize)
        logger.info(
            "[collect] %d carried-over (pending) articles to process", len(pending)
        )
        for p in pending:
            text, ok = fetch_content(p["url"], ANTHROPIC_API_KEY)
            status, retry = next_fetch_state(
                ok, int(p.get("retry_count", 0)), max_content_retries
            )
            bq.update_article_content(p["article_id"], text, status, retry)
            if status == "ok" and text:
                to_summarize.append(
                    {
                        "article_id": p["article_id"],
                        "title": p["title"],
                        "url": p["url"],
                        "source": p["source"],
                        "content": text,
                    }
                )

        # 4. 残りバジェットで新着を処理。超過分は破棄せず pending として繰り越す。
        remaining = max(0, max_summarize - len(to_summarize))
        to_fetch_now = survivors[:remaining]
        deferred = survivors[remaining:]
        if deferred:
            logger.info(
                "[collect] %d new articles deferred to next run (budget=%d)",
                len(deferred),
                max_summarize,
            )

        # 4a. 今回処理する新着の本文取得（UA付き・1回）
        for article in to_fetch_now:
            text, ok = fetch_content(article["url"], ANTHROPIC_API_KEY)
            status, retry = next_fetch_state(ok, 0, max_content_retries)
            article["content"] = text
            article["content_status"] = status
            article["retry_count"] = retry
            if status == "ok" and text:
                to_summarize.append(article)

        # 4b. 繰り越す新着は本文未取得の pending として保存（次回の繰り越し処理で拾う）
        for article in deferred:
            article["content"] = None
            article["content_status"] = "pending"
            article["retry_count"] = 0

        # 5. 要約生成（本文取得に成功した記事のみ）
        summaries = []
        for article in to_summarize:
            try:
                result = summarize_article(
                    title=article["title"],
                    content=article["content"] or "",
                    api_key=ANTHROPIC_API_KEY,
                    keywords=keywords,
                    favorite_tags=favorite_tags,
                )
            except Exception as e:
                logger.warning(
                    "[collect] summarize failed for %s: %s", article["url"], e
                )
                log["error_count"] += 1
                continue
            if result:
                summaries.append(
                    {
                        "article_id": article["article_id"],
                        "title": article["title"],
                        "url": article["url"],
                        "source": article["source"],
                        "scoring_version": SCORING_VERSION,
                        **result,
                    }
                )

        # 6. importance / relevance の2軸ゲート
        relevant_summaries = [
            s
            for s in summaries
            if passes_thresholds(s, importance_threshold, relevance_threshold)
        ]
        log["summaries_generated"] = len(relevant_summaries)
        logger.info(
            "[collect] %d relevant summaries "
            "(importance >= %.2f and relevance >= %.2f)",
            len(relevant_summaries),
            importance_threshold,
            relevance_threshold,
        )

        # 6.5. ゲートを通らなかった記事は content_status='summarized'（終端）にする。
        #      放置すると
        #      「本文あり・summaries無し」の orphan として /resummarize が無駄に
        #      再要約してしまうため。新着は保存前に dict を書き換え（streaming buffer
        #      直後の DML UPDATE は失敗するため）、繰り越し由来の既存行は DML でマーク。
        below_ids = {
            s["article_id"]
            for s in summaries
            if not passes_thresholds(s, importance_threshold, relevance_threshold)
        }
        if below_ids:
            for article in to_fetch_now:
                if article["article_id"] in below_ids:
                    article["content_status"] = "summarized"
            for p in pending:
                if p["article_id"] in below_ids:
                    bq.mark_article_summarized(p["article_id"])
            logger.info(
                "[collect] marked %d below-threshold articles as summarized",
                len(below_ids),
            )

        # 7. raw_articles 保存（全新着＝取りこぼしゼロ。filtered も記録し再取得を防ぐ）
        if new_articles:
            # description は1次フィルタ用の一時情報。スキーマ外なので保存前に除去。
            for a in new_articles:
                a.pop("description", None)
            bq.insert_raw_articles(new_articles)
            logger.info("[collect] saved %d to raw_articles", len(new_articles))

        # 8. summaries 保存（article_id 重複を排除）
        if relevant_summaries:
            existing_summary_ids = bq.get_existing_summary_ids()
            relevant_summaries = [
                s
                for s in relevant_summaries
                if s["article_id"] not in existing_summary_ids
            ]
        if relevant_summaries:
            bq.insert_summaries(relevant_summaries)
            logger.info("[collect] saved %d summaries", len(relevant_summaries))

        return log["summaries_generated"]

    except Exception as e:
        log["status"] = "error"
        log["error_message"] = str(e)
        logger.error("[collect] pipeline error: %s", e)
        send_error_notification(SLACK_WEBHOOK_URL, "collect", str(e))
        raise

    finally:
        log["finished_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        try:
            bq.insert_pipeline_log(log)
            logger.info("[collect] saved pipeline log run_id=%s", run_id)
        except Exception as e:
            logger.error("[collect] failed to save pipeline log: %s", e)


def _run_notify(triggered_by: str = "scheduler") -> int:
    """通知パイプライン。未通知サマリーをカテゴリ別に Slack 通知。通知件数を返す。"""
    import uuid
    from datetime import datetime, timezone

    run_id = str(uuid.uuid4())
    started_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    log: dict = {
        "run_id": run_id,
        "triggered_by": triggered_by,
        "started_at": started_at,
        "finished_at": None,
        "articles_fetched": 0,
        "new_articles": 0,
        "summaries_generated": 0,
        "notified_count": 0,
        "error_count": 0,
        "status": "success",
        "error_message": None,
        "keywords": [],
    }

    config = load_config()
    settings: dict = config.get("settings", {})
    general: dict = settings.get("general", {})
    importance_threshold: float = float(
        general.get("importance_threshold", _DEFAULT_IMPORTANCE_THRESHOLD)
    )
    relevance_threshold: float = float(
        general.get("relevance_threshold", _DEFAULT_RELEVANCE_THRESHOLD)
    )
    feed_categories: dict[str, str] = config.get("feed_categories", {})
    feed_blocks: dict = config.get("feed_blocks", {})

    bq = BQClient(project=PROJECT_ID)

    try:
        # 0. 設定ガード。設定なしで進むとブロックリスト・カテゴリ設定が
        #    適用されないまま通知してしまうため、エラーとして観測可能にする。
        if not config:
            raise RuntimeError(
                "config is empty: Google Sheets の設定読み込みに失敗した可能性"
            )

        # 9. 未通知サマリーを取得（importance / relevance の2軸ゲート付き）
        unnotified = bq.get_unnotified_summaries(
            importance_threshold, relevance_threshold
        )
        logger.info("[notify] %d unnotified summaries in BQ", len(unnotified))

        # 9.5. ブロックユーザーの記事を除外（保存済み記事も通知しない）
        before_block = len(unnotified)
        unnotified = _filter_blocked(unnotified, feed_blocks)
        if before_block != len(unnotified):
            logger.info(
                "[notify] blocked %d summaries by feed block list",
                before_block - len(unnotified),
            )

        if not unnotified:
            send_no_news_notification(SLACK_WEBHOOK_URL, "新着記事はありませんでした。")
            return 0

        # 10. カテゴリ別にグルーピングし、カテゴリごとに通知
        groups = group_by_category(unnotified, feed_categories)
        notified_ids: list[str] = []
        for category in order_categories(list(groups.keys()), settings):
            items = sorted(
                groups[category],
                key=lambda x: x.get("importance_score", 0),
                reverse=True,
            )
            top = items[: category_limit(category, settings)]
            if not top:
                continue
            sent = send_slack_notification(
                top, SLACK_WEBHOOK_URL, header=category_label(category, settings)
            )
            if not sent:
                # 送信失敗分は通知済みマークせず、次回 /notify で再送する
                log["error_count"] += 1
                logger.warning(
                    "[notify] slack send failed for category '%s'; "
                    "left unnotified for retry",
                    category,
                )
                continue
            notified_ids.extend(a["article_id"] for a in top)
            logger.info(
                "[notify] notified %d articles in category '%s'", len(top), category
            )

        if not notified_ids:
            # 送信失敗によるゼロ件では「新着なし」と誤通知しない
            if log["error_count"] == 0:
                send_no_news_notification(
                    SLACK_WEBHOOK_URL, "新着記事はありませんでした。"
                )
            return 0

        # 11. 通知済みマーク（全カテゴリの和集合）
        bq.mark_summaries_notified(notified_ids)
        logger.info("[notify] marked %d summaries as notified", len(notified_ids))

        log["notified_count"] = len(notified_ids)
        return len(notified_ids)

    except Exception as e:
        log["status"] = "error"
        log["error_message"] = str(e)
        logger.error("[notify] pipeline error: %s", e)
        send_error_notification(SLACK_WEBHOOK_URL, "notify", str(e))
        raise

    finally:
        log["finished_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        try:
            bq.insert_pipeline_log(log)
            logger.info("[notify] saved pipeline log run_id=%s", run_id)
        except Exception as e:
            logger.error("[notify] failed to save pipeline log: %s", e)


def _run_recalculate(triggered_by: str = "manual") -> int:
    """既存 summaries のスコアを現行 SCORING_VERSION で再計算する。成功件数を返す。

    importance_score と relevance_score の両方を更新する。行は削除しないため、
    閾値割れした行は通知クエリ側のゲート（get_unnotified_summaries）で落とす。
    """
    import uuid
    from datetime import datetime, timezone

    run_id = str(uuid.uuid4())
    started_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    log: dict = {
        "run_id": run_id,
        "triggered_by": triggered_by,
        "started_at": started_at,
        "finished_at": None,
        "articles_fetched": 0,
        "new_articles": 0,
        "summaries_generated": 0,
        "notified_count": 0,
        "error_count": 0,
        "status": "success",
        "error_message": None,
        "keywords": [],
    }

    config = load_config()
    keywords: list[str] = config.get("keywords", [])
    settings: dict = config.get("settings", {})
    general: dict = settings.get("general", {})
    recalculate_limit: int = int(
        general.get("recalculate_limit", _DEFAULT_RECALCULATE_LIMIT)
    )
    log["keywords"] = keywords

    bq = BQClient(project=PROJECT_ID)

    try:
        favorite_tags = _load_favorite_tags(bq, general)

        rows = bq.get_outdated_summaries(SCORING_VERSION, recalculate_limit)
        logger.info(
            "[recalculate] %d outdated summaries (version < %d)",
            len(rows),
            SCORING_VERSION,
        )

        recalculated = 0
        for row in rows:
            scores = score_article(
                title=row["title"],
                content=row.get("content") or "",
                api_key=ANTHROPIC_API_KEY,
                keywords=keywords,
                favorite_tags=favorite_tags,
            )
            if scores is None:
                log["error_count"] += 1
                continue
            try:
                bq.update_summary_score(
                    row["article_id"],
                    scores["importance_score"],
                    SCORING_VERSION,
                    relevance_score=scores.get("relevance_score"),
                )
                recalculated += 1
            except Exception as e:
                logger.warning(
                    "[recalculate] update failed for %s: %s", row["article_id"], e
                )
                log["error_count"] += 1

        log["summaries_generated"] = recalculated
        logger.info("[recalculate] recalculated %d summaries", recalculated)
        return recalculated

    except Exception as e:
        log["status"] = "error"
        log["error_message"] = str(e)
        logger.error("[recalculate] error: %s", e)
        send_error_notification(SLACK_WEBHOOK_URL, "recalculate", str(e))
        raise

    finally:
        log["finished_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        try:
            bq.insert_pipeline_log(log)
            logger.info("[recalculate] saved pipeline log run_id=%s", run_id)
        except Exception as e:
            logger.error("[recalculate] failed to save pipeline log: %s", e)


def _run_resummarize(triggered_by: str = "manual") -> int:
    """本文ありで summaries が無い記事（orphan）を再要約する。復旧（summaries挿入）件数を返す。

    要約失敗（クレジット枯渇等）で取り残された記事を救済する手動バッチ。閾値超えは
    summaries に保存し通常の未通知フローで通知される。閾値未満は content_status='summarized'
    にマークして以降の対象から除外する（冪等化）。
    """
    import uuid
    from datetime import datetime, timezone

    run_id = str(uuid.uuid4())
    started_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    log: dict = {
        "run_id": run_id,
        "triggered_by": triggered_by,
        "started_at": started_at,
        "finished_at": None,
        "articles_fetched": 0,
        "new_articles": 0,
        "summaries_generated": 0,
        "notified_count": 0,
        "error_count": 0,
        "status": "success",
        "error_message": None,
        "keywords": [],
    }

    config = load_config()
    keywords: list[str] = config.get("keywords", [])
    settings: dict = config.get("settings", {})
    general: dict = settings.get("general", {})
    importance_threshold: float = float(
        general.get("importance_threshold", _DEFAULT_IMPORTANCE_THRESHOLD)
    )
    relevance_threshold: float = float(
        general.get("relevance_threshold", _DEFAULT_RELEVANCE_THRESHOLD)
    )
    resummarize_limit: int = int(
        general.get("resummarize_limit", _DEFAULT_RESUMMARIZE_LIMIT)
    )
    resummarize_days: int = int(
        general.get("resummarize_days", _DEFAULT_RESUMMARIZE_DAYS)
    )
    log["keywords"] = keywords

    bq = BQClient(project=PROJECT_ID)

    try:
        favorite_tags = _load_favorite_tags(bq, general)

        orphans = bq.get_unsummarized_articles(resummarize_days, resummarize_limit)
        logger.info(
            "[resummarize] %d unsummarized articles (within %d days)",
            len(orphans),
            resummarize_days,
        )

        recovered = 0
        for a in orphans:
            try:
                result = summarize_article(
                    title=a["title"],
                    content=a.get("content") or "",
                    api_key=ANTHROPIC_API_KEY,
                    keywords=keywords,
                    favorite_tags=favorite_tags,
                )
            except Exception as e:
                logger.warning("[resummarize] summarize failed for %s: %s", a["url"], e)
                log["error_count"] += 1
                continue
            if not result:
                log["error_count"] += 1
                continue

            if passes_thresholds(result, importance_threshold, relevance_threshold):
                bq.insert_summaries(
                    [
                        {
                            "article_id": a["article_id"],
                            "title": a["title"],
                            "url": a["url"],
                            "source": a["source"],
                            "scoring_version": SCORING_VERSION,
                            **result,
                        }
                    ]
                )
                recovered += 1
            else:
                # 閾値未満は終端状態にして以降の対象から外す（冪等化）
                bq.mark_article_summarized(a["article_id"])

        log["summaries_generated"] = recovered
        logger.info("[resummarize] recovered %d summaries", recovered)
        return recovered

    except Exception as e:
        log["status"] = "error"
        log["error_message"] = str(e)
        logger.error("[resummarize] error: %s", e)
        send_error_notification(SLACK_WEBHOOK_URL, "resummarize", str(e))
        raise

    finally:
        log["finished_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        try:
            bq.insert_pipeline_log(log)
            logger.info("[resummarize] saved pipeline log run_id=%s", run_id)
        except Exception as e:
            logger.error("[resummarize] failed to save pipeline log: %s", e)


def _run_deepdive(article_id_prefix: str, response_url: str) -> None:
    """深堀り処理。完了後に response_url へ結果を POST する。"""
    bq = BQClient(project=PROJECT_ID)

    # 1. 対象記事を取得
    if article_id_prefix:
        article = bq.get_article_by_id(article_id_prefix)
        if not article:
            _post_to_response_url(
                response_url, f"ID `{article_id_prefix}` の記事が見つかりませんでした。"
            )
            return
    else:
        article = bq.get_top_undived_article()
        if not article:
            _post_to_response_url(response_url, "深堀り対象の記事がありません。")
            return

    title = article["title"]
    url = article["url"]
    article_id = article["article_id"]

    # 2. キャッシュ確認
    cached = bq.get_deepdive(article_id)
    if cached:
        logger.info("[deepdive] cache hit for %s", article_id)
        _post_to_response_url(
            response_url, f"*[深堀り] {title}*\n\n{cached}\n\n🔗 <{url}|元記事を読む>"
        )
        return

    # 3. 深堀り生成
    logger.info("[deepdive] generating for %s", article_id)
    text = deepdive_article(
        title=title,
        content=article.get("content") or "",
        api_key=ANTHROPIC_API_KEY,
    )
    if not text:
        _post_to_response_url(
            response_url,
            "深堀り生成に失敗しました。しばらく経ってから再試行してください。",
        )
        return

    # 4. キャッシュ保存
    try:
        bq.insert_deepdive(article_id, text)
    except Exception as e:
        logger.error("[deepdive] failed to cache deepdive: %s", e)

    # 5. 結果を送信
    _post_to_response_url(
        response_url, f"*[深堀り] {title}*\n\n{text}\n\n🔗 <{url}|元記事を読む>"
    )
    logger.info("[deepdive] completed for %s", article_id)


@app.post("/collect", response_model=PipelineResponse)
async def collect():
    """Cloud Scheduler からの収集トリガー。収集〜要約を同期実行する。"""
    summarized = await asyncio.to_thread(_run_collect)
    return PipelineResponse(status="ok", notified=summarized)


@app.post("/notify", response_model=PipelineResponse)
async def notify():
    """Cloud Scheduler からの通知トリガー。未通知サマリーを通知する。"""
    notified = await asyncio.to_thread(_run_notify)
    return PipelineResponse(status="ok", notified=notified)


@app.post("/recalculate", response_model=PipelineResponse)
async def recalculate():
    """importance_score を現行ロジックで再計算する手動エンドポイント。"""
    n = await asyncio.to_thread(_run_recalculate)
    return PipelineResponse(status="ok", notified=n)


@app.post("/resummarize", response_model=PipelineResponse)
async def resummarize():
    """本文ありで summaries が無い記事を再要約し復旧する手動エンドポイント。"""
    n = await asyncio.to_thread(_run_resummarize)
    return PipelineResponse(status="ok", notified=n)


@app.post("/slack", response_model=SlackResponse)
async def slack_command(
    background_tasks: BackgroundTasks,
    _: None = Depends(verify_slack),
):
    """Slack スラッシュコマンド（/news-update）のエンドポイント。"""
    background_tasks.add_task(_run_notify, "slack_command")
    return SlackResponse(
        response_type="in_channel",
        text=":hourglass: 未通知ニュースを送信中です...",
    )


@app.post("/slack/actions")
async def slack_actions(
    request: Request,
    background_tasks: BackgroundTasks,
    _: None = Depends(verify_slack),
):
    """Slack インタラクティブコンポーネント（ボタン押下など）のエンドポイント。"""
    # Form(...)を使わず手動パース（verify_slackがbodyを先に読んでキャッシュするため）
    body = await request.body()
    form_data = urllib.parse.parse_qs(body.decode())
    payload_str = form_data.get("payload", [""])[0]
    data = json.loads(payload_str)
    actions = data.get("actions", [])
    if not actions:
        return {}

    action = actions[0]
    action_id = action.get("action_id", "")

    if action_id == "add_favorite":
        article_id = action.get("value", "")
        bq = BQClient(project=PROJECT_ID)
        if bq.is_favorited(article_id):
            return {"response_type": "ephemeral", "text": "すでにお気に入り済みです。"}
        bq.insert_favorite(article_id)
        logger.info("[favorite] added article_id=%s", article_id)
        return {"response_type": "ephemeral", "text": "⭐ お気に入りに追加しました！"}

    if action_id == "remove_favorite":
        article_id = action.get("value", "")
        bq = BQClient(project=PROJECT_ID)
        bq.delete_favorite(article_id)
        logger.info("[favorite] removed article_id=%s", article_id)
        return {"response_type": "ephemeral", "text": "🗑️ お気に入りから削除しました。"}

    if action_id == "deepdive_article":
        article_id = action.get("value", "")
        response_url = data.get("response_url", "")
        background_tasks.add_task(_run_deepdive, article_id, response_url)
        return {
            "response_type": "ephemeral",
            "text": ":mag: 深堀り中です。しばらくお待ちください...",
        }

    return {}


def _run_show_favorites(response_url: str) -> None:
    """お気に入り一覧を取得して response_url に POST する。"""
    import requests as _requests

    bq = BQClient(project=PROJECT_ID)
    favorites = bq.get_favorites()
    if not favorites:
        _post_to_response_url(response_url, "お気に入り記事はありません。")
        return
    blocks = format_favorites_blocks(favorites)
    try:
        _requests.post(
            response_url,
            json={"response_type": "ephemeral", "blocks": blocks},
            timeout=10,
        )
    except Exception as e:
        logger.error("[favorites] failed to post to response_url: %s", e)


@app.post("/slack/favorites", response_model=SlackResponse)
async def slack_favorites(
    request: Request,
    background_tasks: BackgroundTasks,
    _: None = Depends(verify_slack),
):
    """Slack スラッシュコマンド（/news-favorites）のエンドポイント。"""
    body = await request.body()
    form_data = urllib.parse.parse_qs(body.decode())
    response_url = form_data.get("response_url", [""])[0]
    background_tasks.add_task(_run_show_favorites, response_url)
    return SlackResponse(
        response_type="ephemeral", text=":hourglass: お気に入り一覧を取得中..."
    )


@app.post("/slack/deepdive", response_model=SlackResponse)
async def slack_deepdive(
    request: Request,
    background_tasks: BackgroundTasks,
    _: None = Depends(verify_slack),
):
    """Slack スラッシュコマンド（/news-deepdive）のエンドポイント。"""
    body = await request.body()
    form_data = urllib.parse.parse_qs(body.decode())
    article_id_prefix = form_data.get("text", [""])[0].strip()
    response_url = form_data.get("response_url", [""])[0]
    background_tasks.add_task(_run_deepdive, article_id_prefix, response_url)
    msg = (
        f"ID `{article_id_prefix}` の記事を深堀り中です..."
        if article_id_prefix
        else "最新記事を深堀り中です..."
    )
    return SlackResponse(response_type="in_channel", text=f":mag: {msg}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)
