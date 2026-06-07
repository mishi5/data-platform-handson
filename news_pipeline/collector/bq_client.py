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

    def get_existing_summary_ids(self) -> set[str]:
        """summaries に保存済みの article_id セットを返す（dedup 用）。"""
        query = f"SELECT DISTINCT article_id FROM `{self.project}.{DATASET}.summaries`"
        rows = self.client.query(query).result()
        return {row.article_id for row in rows}

    def get_unnotified_summaries(self) -> list[dict]:
        """notification_log に記録されていないサマリーを返す（未通知分）。article_id 重複は最高スコアの1件に絞る。"""
        query = (
            f"SELECT s.* FROM ("
            f"  SELECT *, ROW_NUMBER() OVER (PARTITION BY article_id ORDER BY importance_score DESC) AS _rn"
            f"  FROM `{self.project}.{DATASET}.summaries`"
            f") s"
            f" LEFT JOIN `{self.project}.{DATASET}.notification_log` n"
            f" ON s.article_id = n.article_id"
            f" WHERE n.article_id IS NULL AND s._rn = 1"
            f" ORDER BY s.importance_score DESC"
        )
        rows = self.client.query(query).result()
        # _rn は内部用カラムなので除外
        return [{k: v for k, v in dict(row).items() if k != "_rn"} for row in rows]

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

    def get_pending_articles(self, max_retries: int) -> list[dict]:
        """本文未取得（content_status='pending'）かつリトライ上限未満の記事を返す。"""
        query = (
            f"SELECT article_id, url, title, source, retry_count"
            f" FROM `{self.project}.{DATASET}.raw_articles`"
            f" WHERE content_status = 'pending' AND retry_count < @max_retries"
        )
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("max_retries", "INT64", max_retries)
            ]
        )
        rows = self.client.query(query, job_config=job_config).result()
        return [dict(row) for row in rows]

    def update_article_content(
        self,
        article_id: str,
        content: str | None,
        content_status: str,
        retry_count: int,
    ) -> None:
        """pending 記事の本文・ステータス・retry_count を DML UPDATE で更新する。

        streaming buffer 制約等で UPDATE が失敗しても送出せずログのみ。
        その記事は pending のまま残り、次回実行（buffer flush 後）で再試行される。
        """
        query = (
            f"UPDATE `{self.project}.{DATASET}.raw_articles`"
            f" SET content = @content, content_status = @status, retry_count = @retry"
            f" WHERE article_id = @aid"
        )
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("content", "STRING", content),
                bigquery.ScalarQueryParameter("status", "STRING", content_status),
                bigquery.ScalarQueryParameter("retry", "INT64", retry_count),
                bigquery.ScalarQueryParameter("aid", "STRING", article_id),
            ]
        )
        try:
            self.client.query(query, job_config=job_config).result()
        except Exception as e:
            logger.warning(
                "[bq_client] update_article_content skipped for %s: %s", article_id, e
            )

    def insert_summaries(self, summaries: list[dict]) -> None:
        """Claude 生成サマリーを summaries テーブルに挿入する。"""
        table_id = f"{self.project}.{DATASET}.summaries"
        errors = self.client.insert_rows_json(table_id, summaries)
        if errors:
            logger.error("[bq_client] insert_summaries errors: %s", errors)
            raise RuntimeError(f"BigQuery insert_summaries failed: {errors}")

    def get_outdated_summaries(self, version: int, limit: int) -> list[dict]:
        """scoring_version が古い（NULL含む）summaries を本文付きで返す。"""
        query = (
            f"SELECT s.article_id, s.title, r.content, s.source"
            f" FROM `{self.project}.{DATASET}.summaries` s"
            f" LEFT JOIN `{self.project}.{DATASET}.raw_articles` r"
            f" ON s.article_id = r.article_id"
            f" WHERE (s.scoring_version IS NULL OR s.scoring_version < @version)"
            f" LIMIT @limit"
        )
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("version", "INT64", version),
                bigquery.ScalarQueryParameter("limit", "INT64", limit),
            ]
        )
        rows = self.client.query(query, job_config=job_config).result()
        return [dict(row) for row in rows]

    def update_summary_score(
        self, article_id: str, importance_score: float, scoring_version: int
    ) -> None:
        """summaries の importance_score と scoring_version を DML UPDATE で更新する。

        例外は送出する（呼び出し側が1件ずつ握って次回繰り越し）。
        """
        query = (
            f"UPDATE `{self.project}.{DATASET}.summaries`"
            f" SET importance_score = @score, scoring_version = @ver"
            f" WHERE article_id = @aid"
        )
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("score", "FLOAT64", importance_score),
                bigquery.ScalarQueryParameter("ver", "INT64", scoring_version),
                bigquery.ScalarQueryParameter("aid", "STRING", article_id),
            ]
        )
        self.client.query(query, job_config=job_config).result()

    def get_deepdive(self, article_id: str) -> str | None:
        """既存の深堀り結果を取得。なければ None。"""
        query = (
            f"SELECT deepdive_text FROM `{self.project}.{DATASET}.deepdives`"
            f" WHERE article_id = '{article_id}'"
            f" LIMIT 1"
        )
        rows = list(self.client.query(query).result())
        if not rows:
            return None
        return rows[0].deepdive_text

    def insert_deepdive(self, article_id: str, text: str) -> None:
        """深堀り結果を deepdives テーブルに保存する。"""
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        table_id = f"{self.project}.{DATASET}.deepdives"
        errors = self.client.insert_rows_json(
            table_id,
            [{"article_id": article_id, "deepdive_text": text, "created_at": now}],
        )
        if errors:
            logger.error("[bq_client] insert_deepdive errors: %s", errors)
            raise RuntimeError(f"BigQuery deepdives insert failed: {errors}")

    def get_article_by_id(self, article_id_prefix: str) -> dict | None:
        """先頭8文字のIDプレフィックスで記事を取得。summaries + raw_articles を JOIN。"""
        query = (
            f"SELECT s.article_id, s.title, s.url, r.content"
            f" FROM `{self.project}.{DATASET}.summaries` s"
            f" JOIN `{self.project}.{DATASET}.raw_articles` r ON s.article_id = r.article_id"
            f" WHERE s.article_id LIKE '{article_id_prefix}%'"
            f" LIMIT 1"
        )
        rows = list(self.client.query(query).result())
        if not rows:
            return None
        return dict(rows[0])

    def get_top_undived_article(self) -> dict | None:
        """深堀り未実施の記事の中でimportance_score最上位のものを返す。"""
        query = (
            f"SELECT s.article_id, s.title, s.url, r.content"
            f" FROM `{self.project}.{DATASET}.summaries` s"
            f" JOIN `{self.project}.{DATASET}.raw_articles` r ON s.article_id = r.article_id"
            f" LEFT JOIN `{self.project}.{DATASET}.deepdives` d ON s.article_id = d.article_id"
            f" WHERE d.article_id IS NULL"
            f" ORDER BY s.importance_score DESC"
            f" LIMIT 1"
        )
        rows = list(self.client.query(query).result())
        if not rows:
            return None
        return dict(rows[0])

    def get_favorites(self) -> list[dict]:
        """お気に入り記事一覧を返す（summariesと結合）。"""
        query = (
            f"SELECT f.article_id, f.favorited_at, s.title, s.url, s.source"
            f" FROM `{self.project}.{DATASET}.favorites` f"
            f" LEFT JOIN `{self.project}.{DATASET}.summaries` s ON f.article_id = s.article_id"
            f" ORDER BY f.favorited_at DESC"
        )
        rows = list(self.client.query(query).result())
        return [dict(row) for row in rows]

    def delete_favorite(self, article_id: str) -> None:
        """お気に入りから記事を削除する。"""
        query = (
            f"DELETE FROM `{self.project}.{DATASET}.favorites`"
            f" WHERE article_id = '{article_id}'"
        )
        self.client.query(query).result()
        logger.info("[bq_client] deleted favorite article_id=%s", article_id)

    def insert_favorite(self, article_id: str) -> None:
        """記事をお気に入りテーブルに追加する。"""
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        table_id = f"{self.project}.{DATASET}.favorites"
        errors = self.client.insert_rows_json(
            table_id, [{"article_id": article_id, "favorited_at": now}]
        )
        if errors:
            logger.error("[bq_client] insert_favorite errors: %s", errors)
            raise RuntimeError(f"BigQuery favorites insert failed: {errors}")

    def is_favorited(self, article_id: str) -> bool:
        """記事がすでにお気に入り済みか確認する。"""
        query = (
            f"SELECT 1 FROM `{self.project}.{DATASET}.favorites`"
            f" WHERE article_id = '{article_id}'"
            f" LIMIT 1"
        )
        rows = list(self.client.query(query).result())
        return len(rows) > 0

    def insert_pipeline_log(self, log: dict) -> None:
        """パイプライン実行ログを pipeline_logs テーブルに挿入する。"""
        table_id = f"{self.project}.{DATASET}.pipeline_logs"
        errors = self.client.insert_rows_json(table_id, [log])
        if errors:
            logger.error("[bq_client] insert_pipeline_log errors: %s", errors)
            raise RuntimeError(f"BigQuery pipeline_logs insert failed: {errors}")
