"""Claude API を使って記事を要約・採点するモジュール。

- summarize_article: 要約(summary)+タグ(tags)+重要度(importance_score) を1回で生成
- score_article: 重要度スコアのみを再計算（/recalculate 用）
スコア判定基準は _build_scoring_criteria に集約し両者で共用する。
スコアロジックを変えたら SCORING_VERSION を +1 すること。

出力は tool use（tool_choice で強制）による structured output で受け取る。
プロンプトで「JSONのみ返せ」と指示してパースする方式はモデルが余計な文を
返すと落ちるため使わない。採点の一貫性のため temperature=0 を明示する。
"""

import logging
import re

import anthropic
from anthropic.types import ToolUseBlock

logger = logging.getLogger(__name__)

# スコアロジックの版。_build_scoring_criteria を変えたら +1 する。
SCORING_VERSION = 2

_MODEL = "claude-haiku-4-5-20251001"

# 要約・採点に渡す本文の最大文字数。長い技術記事は結論が後半にあることが
# 多いため、切り詰めすぎると価値を取りこぼす（Haiku なので費用影響は小さい）。
_MAX_CONTENT_CHARS = 8000

_SUMMARY_PROMPT_TEMPLATE = """あなたはデータエンジニアリングの技術ニュースを要約するアシスタントです。
記事を読んで record_summary ツールで要約・タグ・重要度を記録してください。

summary は箇条書きで3〜5項目の技術ポイント（日本語・改行区切り）にしてください。
tags は英語・小文字・単語はスペース区切りで統一してください（日本語記事でも英語で付ける。
例: data governance, vector search, dbt）。

{scoring_criteria}"""

_SCORE_PROMPT_TEMPLATE = """あなたはデータエンジニアリングの技術ニュースの重要度を評価するアシスタントです。
記事を読んで record_score ツールで重要度スコアを記録してください。

{scoring_criteria}"""


_SLIDE_PREFILTER_PROMPT_TEMPLATE = """あなたはデータエンジニアリングのスライド資料を、全文(PDF)を読む前にざっくり選別するアシスタントです。
スライドのタイトルと短い説明だけから、データエンジニアにとって読む価値がありそうかを 0.0〜1.0 で見積もり、record_relevance ツールで記録してください。

{scoring_criteria}

重要: 説明が空・極端に短い等で情報が少ない場合は判断を保留し、高め(0.6以上)に倒してください（PDFを読めば価値があるかもしれず、取りこぼしを避けるため）。"""


_SUMMARY_TOOL = {
    "name": "record_summary",
    "description": "記事の要約・タグ・重要度スコアを記録する",
    "input_schema": {
        "type": "object",
        "properties": {
            "summary": {
                "type": "string",
                "description": "箇条書き3〜5項目の技術ポイント（日本語・改行区切り）",
            },
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": (
                    "記事の技術トピックを表す英語小文字のタグ"
                    "（例: data governance, dbt）。日本語記事でも英語で付ける"
                ),
            },
            "importance_score": {
                "type": "number",
                "description": "重要度スコア（0.0〜1.0）",
            },
        },
        "required": ["summary", "tags", "importance_score"],
    },
}

_SCORE_TOOL = {
    "name": "record_score",
    "description": "記事の重要度スコアを記録する",
    "input_schema": {
        "type": "object",
        "properties": {
            "importance_score": {
                "type": "number",
                "description": "重要度スコア（0.0〜1.0）",
            },
        },
        "required": ["importance_score"],
    },
}

_RELEVANCE_TOOL = {
    "name": "record_relevance",
    "description": "スライドの関連度スコアを記録する",
    "input_schema": {
        "type": "object",
        "properties": {
            "relevance_score": {
                "type": "number",
                "description": "関連度スコア（0.0〜1.0）",
            },
        },
        "required": ["relevance_score"],
    },
}


def _build_scoring_criteria(
    keywords: list[str], favorite_tags: list[str] | None = None
) -> str:
    """importance_score の判定基準を組み立てる。summarize / score_article で共用。

    主軸は「データエンジニアにとって読む価値があるか」の総合判断。
    keyword は興味分野のヒント（加点）で、無くても価値があれば相応に高くする。
    favorite_tags はお気に入り履歴由来の暗黙的な関心（加点ヒント）。
    """
    if keywords:
        items = "\n".join(f"  - {kw}" for kw in keywords)
    else:
        items = "  （キーワード未設定のため、データエンジニアリング全般を対象とする）"
    criteria = (
        "importance_score は「データエンジニアにとって読む価値があるか」を総合的に判断して付ける。\n"
        "\n"
        "高くすべき記事（価値が高い）：\n"
        "- 実務で使える具体的な知見（設計・運用ノウハウ、how-to、トラブル対応）\n"
        "- 技術的な深さ・考察（アーキテクチャ議論、仕組みの深掘り、トレードオフ分析）\n"
        "- 大規模・本番環境の実例（実サービスの事例、失敗談やスケールの教訓）\n"
        "\n"
        "低くすべき記事（価値が低い）：\n"
        "- 宣伝・PR・製品の単なる紹介（マーケティング目的）\n"
        "- 中身が薄い・短い（具体性がなく表面的）\n"
        "\n"
        "次のキーワードは特に関心の高いトピックのヒント。該当すれば加点するが、"
        "キーワードに無くても上記の価値があれば相応に高くする：\n"
        f"{items}\n"
        "\n"
        "スコアの目安：\n"
        "- 0.8〜1.0: 実務に直接役立つ深い技術記事、本番事例の濃い知見\n"
        "- 0.5前後: 有用だが一般的、または部分的に価値がある\n"
        "- 0.3以下: 宣伝・PR、中身が薄い、データエンジニアにほぼ無関係"
    )
    if favorite_tags:
        tag_items = "\n".join(f"  - {t}" for t in favorite_tags)
        criteria += (
            "\n\n"
            "また、次はユーザーが過去にお気に入りした記事に多いトピック。"
            "該当する記事は関心が高い可能性があるため加点のヒントにする：\n"
            f"{tag_items}"
        )
    return criteria


def _build_system_prompt(
    keywords: list[str], favorite_tags: list[str] | None = None
) -> str:
    """要約+タグ+スコア用のシステムプロンプト。"""
    return _SUMMARY_PROMPT_TEMPLATE.format(
        scoring_criteria=_build_scoring_criteria(keywords, favorite_tags)
    )


def _build_score_only_prompt(
    keywords: list[str], favorite_tags: list[str] | None = None
) -> str:
    """スコアのみ用のシステムプロンプト。"""
    return _SCORE_PROMPT_TEMPLATE.format(
        scoring_criteria=_build_scoring_criteria(keywords, favorite_tags)
    )


def _normalize_tag(tag: str) -> str:
    """タグの機械正規化: 小文字化・アンダースコア→スペース・トリム。

    プロンプトで英語小文字を指示しているが、モデル出力の揺れ
    （大文字・アンダースコア区切り）を保存前に吸収する。
    """
    return tag.lower().replace("_", " ").strip()


# 前後がクォート・カッコでないリテラル `\n` だけにマッチする
_LITERAL_NEWLINE_RE = re.compile(r"""(?<!['"`「『（(\[{])\\n(?!['"`」』）)\]}])""")


def _unescape_literal_newlines(text: str) -> str:
    """summary 中のリテラル `\\n`（バックスラッシュ+n の2文字）を実改行に直す。

    tool use の出力でモデルが改行の一部を二重エスケープすることがあり、
    そのまま保存すると Slack 通知に「\\n」がそのまま表示される。
    ただし記事が改行文字そのものを話題にしている場合（`'\\n'` や `「\\n」` の
    ようにクォート・カッコで囲まれている場合）は意味を壊すので置換しない。
    """
    return _LITERAL_NEWLINE_RE.sub("\n", text)


def _call_tool(
    system_prompt: str,
    user_content: str,
    tool: dict,
    api_key: str,
    max_tokens: int,
) -> dict | None:
    """tool_choice で指定ツールを強制呼び出しし、その入力（dict）を返す。"""
    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model=_MODEL,
        max_tokens=max_tokens,
        temperature=0,
        system=system_prompt,
        tools=[tool],
        tool_choice={"type": "tool", "name": tool["name"]},
        messages=[{"role": "user", "content": user_content}],
    )
    block = next(
        (b for b in message.content if isinstance(b, ToolUseBlock)),
        None,
    )
    if block is None:
        return None
    return dict(block.input)


def summarize_article(
    title: str,
    content: str,
    api_key: str,
    keywords: list[str] | None = None,
    favorite_tags: list[str] | None = None,
) -> dict | None:
    """Claude で記事を要約する。失敗時は None。keywords に基づいて importance_score を判定する。"""
    try:
        result = _call_tool(
            system_prompt=_build_system_prompt(keywords or [], favorite_tags),
            user_content=f"タイトル: {title}\n\n本文:\n{content[:_MAX_CONTENT_CHARS]}",
            tool=_SUMMARY_TOOL,
            api_key=api_key,
            max_tokens=1024,
        )
        if result is None:
            return None
        if isinstance(result.get("summary"), list):
            result["summary"] = "\n".join(result["summary"])
        if isinstance(result.get("summary"), str):
            result["summary"] = _unescape_literal_newlines(result["summary"])
        if isinstance(result.get("tags"), list):
            normalized: list[str] = []
            for t in result["tags"]:
                if not isinstance(t, str):
                    continue
                nt = _normalize_tag(t)
                if nt and nt not in normalized:
                    normalized.append(nt)
            result["tags"] = normalized
        return result
    except Exception as e:
        logger.error("[summarizer] failed: %s", e)
        return None


def score_slide_relevance(
    title: str,
    description: str,
    api_key: str,
    keywords: list[str] | None = None,
    favorite_tags: list[str] | None = None,
) -> float | None:
    """スライド(Speaker Deck)の PDF を読む前に、title+description だけで関連度を見積もる。

    PDFビジョン書き起こし(高コスト)の前段フィルタ用。失敗時は None（呼び出し側は
    None を「判定不能＝通す」として扱う）。情報が少ない場合は高めのスコアを返す。
    """
    system_prompt = _SLIDE_PREFILTER_PROMPT_TEMPLATE.format(
        scoring_criteria=_build_scoring_criteria(keywords or [], favorite_tags)
    )
    try:
        result = _call_tool(
            system_prompt=system_prompt,
            user_content=f"タイトル: {title}\n\n説明:\n{(description or '')[:500]}",
            tool=_RELEVANCE_TOOL,
            api_key=api_key,
            max_tokens=128,
        )
        if result is None or result.get("relevance_score") is None:
            return None
        return float(result["relevance_score"])
    except Exception as e:
        logger.error("[summarizer] slide prefilter failed: %s", e)
        return None


def score_article(
    title: str,
    content: str,
    api_key: str,
    keywords: list[str] | None = None,
    favorite_tags: list[str] | None = None,
) -> float | None:
    """記事の importance_score のみを再計算する。失敗時は None。"""
    try:
        result = _call_tool(
            system_prompt=_build_score_only_prompt(keywords or [], favorite_tags),
            user_content=f"タイトル: {title}\n\n本文:\n{content[:_MAX_CONTENT_CHARS]}",
            tool=_SCORE_TOOL,
            api_key=api_key,
            max_tokens=128,
        )
        if result is None or result.get("importance_score") is None:
            return None
        return float(result["importance_score"])
    except Exception as e:
        logger.error("[summarizer] score failed: %s", e)
        return None
