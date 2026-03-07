from google.cloud import bigquery

DATASET = "tech_news"


class BQClient:
    def __init__(self, project: str):
        self.client = bigquery.Client(project=project)
        self.project = project

    def get_existing_urls(self) -> set[str]:
        """raw_articles に保存済みの URL セットを返す（dedup 用）。"""
        query = f"SELECT url FROM `{self.project}.{DATASET}.raw_articles`"
        rows = self.client.query(query).result()
        return {row.url for row in rows}

    def insert_raw_articles(self, articles: list[dict]) -> None:
        table_id = f"{self.project}.{DATASET}.raw_articles"
        errors = self.client.insert_rows_json(table_id, articles)
        if errors:
            print(f"[bq_client] insert_raw_articles errors: {errors}")

    def insert_summaries(self, summaries: list[dict]) -> None:
        table_id = f"{self.project}.{DATASET}.summaries"
        errors = self.client.insert_rows_json(table_id, summaries)
        if errors:
            print(f"[bq_client] insert_summaries errors: {errors}")
