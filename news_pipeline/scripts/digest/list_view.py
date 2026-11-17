"""fetch_articles.py の一覧 JSON を、選定用の表示と資料用の HTML 断片に変換する。

  選定用（スコア順の1行表示。深掘り候補を選ぶとき）:
      uv run python scripts/digest/list_view.py rank --list list.json [--top 60]
  資料用（深掘り以外をテーマ別にまとめた <h3>＋<ul class="brief"> の断片）:
      uv run python scripts/digest/list_view.py html --list list.json \
          --exclude id1,id2 --out list_frag.html

一覧 JSON をそのまま読むと 100 件超で数十 KB になり、選定の判断材料が埋もれる。
rank は判断に要る列（スコア・id・出典・タイトル・タグ）だけを1行に並べる。

テーマ分けはタグと出典による機械的な振り分け。BigQuery だけは出典かタイトルで
判定する（他社の記事も連携先として bigquery タグを持つことが多く、タグで判定すると
Databricks の事例などが BigQuery 欄に入るため）。
"""

import argparse
import html
import json
import sys

# (テーマ名, タグ・タイトルに含まれていればそのテーマにするキーワード)。上から順に判定する。
# 最後のテーマはどれにも当たらなかった記事の受け皿。
BIGQUERY_THEME = "BigQuery・Google Cloud"
THEMES: list[tuple[str, list[str]]] = [
    (
        "セマンティックレイヤー・オントロジー・AIエージェント",
        [
            "semantic",
            "ontology",
            "ai agent",
            "agent",
            "genie",
            "cortex",
            "coco",
            "cowork",
            "llm",
            "rag",
            "ai readiness",
            "mcp",
        ],
    ),
    (
        "テーブルフォーマット・データ共有（Iceberg / Delta / OpenSharing）",
        ["iceberg", "delta", "opensharing", "data sharing", "lakehouse"],
    ),
    (
        "パイプライン・ストリーミング・CDC",
        [
            "cdc",
            "streaming",
            "kafka",
            "kinesis",
            "airflow",
            "data pipeline",
            "spark",
            "flink",
            "etl",
            "glue",
            "firehose",
        ],
    ),
    ("DWH運用・コスト・モデリング", []),
]
_BIGQUERY_SOURCE_WORDS = ("bigquery",)
_BIGQUERY_TITLE_WORDS = ("bigquery", "gemini", "bigframes", "dataform", "looker")


def score(article: dict) -> float:
    """選定の並び順。fetch_articles の ORDER BY と同じ（relevance NULL は 1.0 扱い）。"""
    imp = article.get("importance_score") or 0.0
    rel = article.get("relevance_score")
    return imp * (1.0 if rel is None else rel)


def classify(article: dict) -> str:
    """記事をテーマに振り分ける。"""
    source = (article.get("source") or "").lower()
    title = (article.get("title") or "").lower()
    if any(w in source for w in _BIGQUERY_SOURCE_WORDS) or any(
        w in title for w in _BIGQUERY_TITLE_WORDS
    ):
        return BIGQUERY_THEME
    haystack = " ".join(article.get("tags") or []).lower() + " " + title
    for name, words in THEMES[:-1]:
        if any(w in haystack for w in words):
            return name
    return THEMES[-1][0]


def theme_order() -> list[str]:
    return [BIGQUERY_THEME] + [name for name, _ in THEMES]


def summary_lines(article: dict, limit: int) -> list[str]:
    """要約を行に分け、行頭の記号を除いて先頭 limit 行を返す。"""
    lines = []
    for line in (article.get("summary") or "").splitlines():
        line = line.strip().lstrip("•・-*").strip()
        if line:
            lines.append(line)
    return lines[:limit]


def format_rank(articles: list[dict], top: int | None = None) -> str:
    """選定用の1行表示。id は先頭12桁（--ids には全桁が要るので rank の後で引き直す）。"""
    rows = sorted(articles, key=score, reverse=True)
    if top:
        rows = rows[:top]
    out = []
    for a in rows:
        tags = ",".join(a.get("tags") or [])
        out.append(
            f"{score(a):.2f} {a.get('article_id', '')[:12]} [{a.get('source', '')}] "
            f"{a.get('title', '')} | {tags}"
        )
    return "\n".join(out)


def resolve_ids(
    articles: list[dict], prefixes: list[str]
) -> tuple[list[str], list[str]]:
    """rank に出る12桁の接頭辞から完全な article_id を引く。(解決できた id, 解決できなかった接頭辞)。

    接頭辞が複数の記事に一致した場合も「解決できなかった」に入れる（取り違えを防ぐ）。
    """
    resolved, unresolved = [], []
    for p in prefixes:
        hits = [
            a["article_id"] for a in articles if a.get("article_id", "").startswith(p)
        ]
        if len(hits) == 1:
            resolved.append(hits[0])
        else:
            unresolved.append(p)
    return resolved, unresolved


def build_html(articles: list[dict], exclude: set[str], summary_limit: int = 2) -> str:
    """深掘り以外の記事をテーマ別の HTML 断片にする。テーマ内はスコア順。"""
    groups: dict[str, list[dict]] = {name: [] for name in theme_order()}
    for a in articles:
        if a.get("article_id") in exclude:
            continue
        groups[classify(a)].append(a)

    esc = html.escape
    out = []
    for name in theme_order():
        items = sorted(groups[name], key=score, reverse=True)
        if not items:
            continue
        out.append(
            f'<h3 class="theme">{esc(name)} <span class="cnt">{len(items)} 件</span></h3>'
        )
        out.append('<ul class="brief">')
        for a in items:
            points = "".join(
                f'<span class="pt">{esc(line)}</span>'
                for line in summary_lines(a, summary_limit)
            )
            tags = "".join(
                f'<span class="tag">{esc(t)}</span>' for t in (a.get("tags") or [])[:4]
            )
            out.append(
                f'  <li><a href="{esc(a.get("url", ""))}">{esc(a.get("title", ""))}</a> '
                f'<span class="src">{esc(a.get("source", ""))}</span><br>{points}<br>{tags}</li>'
            )
        out.append("</ul>")
    return "\n".join(out)


def _load(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_rank = sub.add_parser("rank", help="選定用にスコア順の1行表示を出す")
    p_rank.add_argument("--list", required=True)
    p_rank.add_argument("--top", type=int, default=None)

    p_ids = sub.add_parser(
        "ids", help="rank の12桁 id から完全な id をカンマ区切りで出す"
    )
    p_ids.add_argument("--list", required=True)
    p_ids.add_argument("prefixes", help="カンマ区切りの id 接頭辞")

    p_html = sub.add_parser("html", help="深掘り以外の記事のテーマ別 HTML 断片を出す")
    p_html.add_argument("--list", required=True)
    p_html.add_argument(
        "--exclude", default="", help="深掘りに選んだ article_id（カンマ区切り）"
    )
    p_html.add_argument("--out", required=True)

    args = parser.parse_args()
    articles = _load(args.list)

    if args.cmd == "rank":
        print(f"{len(articles)} 件（score = importance × relevance）")
        print(format_rank(articles, args.top))
        return 0

    if args.cmd == "ids":
        prefixes = [p.strip() for p in args.prefixes.split(",") if p.strip()]
        resolved, unresolved = resolve_ids(articles, prefixes)
        if unresolved:
            print(f"一意に解決できない接頭辞: {', '.join(unresolved)}", file=sys.stderr)
            return 1
        print(",".join(resolved))
        return 0

    exclude = {i.strip() for i in args.exclude.split(",") if i.strip()}
    unknown = exclude - {a.get("article_id") for a in articles}
    if unknown:
        # 接頭辞のまま渡すと除外されず、深掘り記事が一覧にも重複して載る
        print(
            f"--exclude に一覧に無い id があります: {', '.join(sorted(unknown))}",
            file=sys.stderr,
        )
        return 1
    fragment = build_html(articles, exclude)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(fragment)
    counts = {}
    for a in articles:
        if a.get("article_id") not in exclude:
            counts[classify(a)] = counts.get(classify(a), 0) + 1
    print(
        f"{len(articles) - len(exclude)} 件を {args.out} に出力しました",
        file=sys.stderr,
    )
    for name in theme_order():
        if counts.get(name):
            print(f"  {name}: {counts[name]}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
