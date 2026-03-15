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
        """notified_at IS NULL のサマリーを返す（未通知分）。"""
        query = (
            f"SELECT * FROM `{self.project}.{DATASET}.summaries`"
            " WHERE notified_at IS NULL"
            " ORDER BY importance_score DESC"
        )
        rows = self.client.query(query).result()
        return [dict(row) for row in rows]

    def mark_summaries_notified(self, article_ids: list[str]) -> None:
        """指定した article_id の notified_at を現在時刻に更新する。"""
        if not article_ids:
            return
        ids_str = ", ".join(f"'{aid}'" for aid in article_ids)
        query = (
            f"UPDATE `{self.project}.{DATASET}.summaries`"
            f" SET notified_at = CURRENT_TIMESTAMP()"
            f" WHERE article_id IN ({ids_str})"
        )
        self.client.query(query).result()

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
