"""BigQuery への読み書きを担当するモジュール。データセット: tech_news。"""
import logging
from google.cloud import bigquery

logger = logging.getLogger(__name__)

DATASET = "tech_news"


class BQClient:
    def __init__(self, project: str):
        """BigQuery クライアントを初期化する。"""
        self.client = bigquery.Client(project=project)
        self.project = project

    def get_existing_urls(self) -> set[str]:
        """raw_articles に保存済みの URL セットを返す（dedup 用）。"""
        query = f"SELECT url FROM `{self.project}.{DATASET}.raw_articles`"
        rows = self.client.query(query).result()
        return {row.url for row in rows}

    def get_unnotified_summaries(self) -> list[dict]:
        """notification_log に記録されていないサマリーを返す（未通知分）。"""
        query = (
            f"SELECT s.* FROM `{self.project}.{DATASET}.summaries` s"
            f" LEFT JOIN `{self.project}.{DATASET}.notification_log` n"
            f" ON s.article_id = n.article_id"
            f" WHERE n.article_id IS NULL"
            f" ORDER BY s.importance_score DESC"
        )
        rows = self.client.query(query).result()
        return [dict(row) for row in rows]

    def mark_summaries_notified(self, article_ids: list[str]) -> None:
        """通知済み article_id を notification_log にストリーミング挿入する。"""
        if not article_ids:
            return
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        rows = [{"article_id": aid, "notified_at": now} for aid in article_ids]
        table_id = f"{self.project}.{DATASET}.notification_log"
        errors = self.client.insert_rows_json(table_id, rows)
        if errors:
            logger.error("[bq_client] mark_summaries_notified errors: %s", errors)
            raise RuntimeError(f"BigQuery notification_log insert failed: {errors}")

    def insert_raw_articles(self, articles: list[dict]) -> None:
        """記事メタデータと本文を raw_articles テーブルに挿入する。"""
        table_id = f"{self.project}.{DATASET}.raw_articles"
        errors = self.client.insert_rows_json(table_id, articles)
        if errors:
            logger.error("[bq_client] insert_raw_articles errors: %s", errors)
            raise RuntimeError(f"BigQuery insert_raw_articles failed: {errors}")

    def insert_summaries(self, summaries: list[dict]) -> None:
        """Claude 生成サマリーを summaries テーブルに挿入する。"""
        table_id = f"{self.project}.{DATASET}.summaries"
        errors = self.client.insert_rows_json(table_id, summaries)
        if errors:
            logger.error("[bq_client] insert_summaries errors: %s", errors)
            raise RuntimeError(f"BigQuery insert_summaries failed: {errors}")

    def insert_pipeline_log(self, log: dict) -> None:
        """パイプライン実行ログを pipeline_logs テーブルに挿入する。"""
        table_id = f"{self.project}.{DATASET}.pipeline_logs"
        errors = self.client.insert_rows_json(table_id, [log])
        if errors:
            logger.error("[bq_client] insert_pipeline_log errors: %s", errors)
            raise RuntimeError(f"BigQuery pipeline_logs insert failed: {errors}")
