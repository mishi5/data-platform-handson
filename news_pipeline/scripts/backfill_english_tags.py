"""summaries.tags の既存データを英語小文字タグに統一する一回性メンテナンススクリプト。

タグは自由生成だったため日本語/英語・大文字小文字・アンダースコアの表記ゆれが
混在している。本スクリプトは:

1. summaries から日本語を含む distinct タグを抽出
2. Claude (Haiku, temperature=0, tool use) でバッチ翻訳して日→英マッピングを作成
3. 1回の UPDATE DML で全行の tags を変換
   - 日本語タグ: マッピングで英語化
   - 全タグ共通: 小文字化・アンダースコア→スペース・トリム・配列内 dedup
4. 前後の統計を表示

streaming buffer 制約があるため、直近 (~90分) に挿入された summaries が
ある時間帯には実行しないこと（DML が失敗する）。

実行:
    cd news_pipeline
    uv run python scripts/backfill_english_tags.py --dry-run   # マッピング確認のみ
    uv run python scripts/backfill_english_tags.py             # 実行
"""

import argparse
import os
import sys

import anthropic
from anthropic.types import ToolUseBlock
from dotenv import load_dotenv
from google.cloud import bigquery

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

PROJECT_ID = os.environ["GCP_PROJECT_ID"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
DATASET = "tech_news"
MODEL = "claude-haiku-4-5-20251001"
BATCH_SIZE = 100

_JA_REGEX = r"[぀-ヿ㐀-䶿一-鿿]"

_TRANSLATE_TOOL = {
    "name": "record_translations",
    "description": "タグの日本語→英語対訳を記録する",
    "input_schema": {
        "type": "object",
        "properties": {
            "mappings": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "original": {"type": "string"},
                        "english": {"type": "string"},
                    },
                    "required": ["original", "english"],
                },
            }
        },
        "required": ["mappings"],
    },
}

_SYSTEM_PROMPT = """あなたはデータエンジニアリング記事のタグを英語に統一するアシスタントです。
与えられた日本語（または日英混在）のタグそれぞれを、簡潔な英語小文字のタグに翻訳し、
record_translations ツールで全件記録してください。

ルール:
- 出力は英語・小文字・単語はスペース区切り（例: data governance, vector search）
- 業界で確立した用語に合わせる（データガバナンス→data governance、メタデータ→metadata、
  生成AI→generative ai、自然言語処理→natural language processing、BI ツール→bi tool）
- 製品名・固有名詞は一般的な英語表記の小文字（メルカリ→mercari、Java ランタイム→java runtime）
- 意訳せず、タグとして自然な最短の英語にする
- 入力の全タグを漏れなく記録する（original は入力をそのまま返す）"""


def normalize(tag: str) -> str:
    """機械正規化: 小文字化・アンダースコア→スペース・トリム。"""
    return tag.lower().replace("_", " ").strip()


def fetch_japanese_tags(client: bigquery.Client) -> list[str]:
    query = (
        f"SELECT DISTINCT tag"
        f" FROM `{PROJECT_ID}.{DATASET}.summaries`, UNNEST(tags) AS tag"
        f" WHERE REGEXP_CONTAINS(tag, r'{_JA_REGEX}')"
        f" ORDER BY tag"
    )
    return [row.tag for row in client.query(query).result()]


def translate_batch(client: anthropic.Anthropic, tags: list[str]) -> dict[str, str]:
    tag_list = "\n".join(f"- {t}" for t in tags)
    message = client.messages.create(
        model=MODEL,
        max_tokens=8192,
        temperature=0,
        system=_SYSTEM_PROMPT,
        tools=[_TRANSLATE_TOOL],
        tool_choice={"type": "tool", "name": "record_translations"},
        messages=[{"role": "user", "content": f"タグ一覧:\n{tag_list}"}],
    )
    block = next((b for b in message.content if isinstance(b, ToolUseBlock)), None)
    if block is None:
        raise RuntimeError("no tool_use block in response")
    return {
        m["original"]: normalize(m["english"])
        for m in block.input["mappings"]
        if m.get("original") and m.get("english")
    }


def build_mapping(ja_tags: list[str]) -> dict[str, str]:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    mapping: dict[str, str] = {}
    for i in range(0, len(ja_tags), BATCH_SIZE):
        batch = ja_tags[i : i + BATCH_SIZE]
        mapping.update(translate_batch(client, batch))
        print(f"  translated {min(i + BATCH_SIZE, len(ja_tags))}/{len(ja_tags)}")
    missing = [t for t in ja_tags if t not in mapping]
    if missing:
        print(f"WARNING: {len(missing)} tags missing from translation, kept as-is:")
        for t in missing:
            print(f"  - {t}")
    return mapping


def count_japanese_tags(client: bigquery.Client) -> int:
    query = (
        f"SELECT COUNT(*) AS cnt"
        f" FROM `{PROJECT_ID}.{DATASET}.summaries`, UNNEST(tags) AS tag"
        f" WHERE REGEXP_CONTAINS(tag, r'{_JA_REGEX}')"
    )
    return list(client.query(query).result())[0].cnt


def apply_update(client: bigquery.Client, mapping: dict[str, str]) -> int:
    query = (
        f"UPDATE `{PROJECT_ID}.{DATASET}.summaries` s"
        f" SET tags = ARRAY("
        f"   SELECT DISTINCT COALESCE("
        f"     (SELECT m.en FROM UNNEST(@mapping) m WHERE m.ja = t),"
        f"     TRIM(REPLACE(LOWER(t), '_', ' '))"
        f"   )"
        f"   FROM UNNEST(s.tags) AS t"
        f" )"
        f" WHERE EXISTS ("
        f"   SELECT 1 FROM UNNEST(s.tags) AS t"
        f"   WHERE REGEXP_CONTAINS(t, r'{_JA_REGEX}')"
        f"      OR t != TRIM(REPLACE(LOWER(t), '_', ' '))"
        f" )"
    )
    params = bigquery.ArrayQueryParameter(
        "mapping",
        "STRUCT",
        [
            bigquery.StructQueryParameter(
                None,
                bigquery.ScalarQueryParameter("ja", "STRING", ja),
                bigquery.ScalarQueryParameter("en", "STRING", en),
            )
            for ja, en in mapping.items()
        ],
    )
    job = client.query(
        query, job_config=bigquery.QueryJobConfig(query_parameters=[params])
    )
    job.result()
    return job.num_dml_affected_rows or 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="マッピング作成と表示のみ（UPDATEしない）",
    )
    args = parser.parse_args()

    bq = bigquery.Client(project=PROJECT_ID)

    ja_tags = fetch_japanese_tags(bq)
    print(f"distinct japanese tags: {len(ja_tags)}")
    ja_count_before = count_japanese_tags(bq)
    print(f"japanese tag occurrences before: {ja_count_before}")

    mapping = build_mapping(ja_tags)
    print(f"mapping built: {len(mapping)} entries")

    if args.dry_run:
        for ja, en in sorted(mapping.items()):
            print(f"  {ja} -> {en}")
        print("dry-run: no update executed")
        return 0

    affected = apply_update(bq, mapping)
    print(f"updated rows: {affected}")

    ja_count_after = count_japanese_tags(bq)
    print(f"japanese tag occurrences after: {ja_count_after}")
    return 0 if ja_count_after == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
