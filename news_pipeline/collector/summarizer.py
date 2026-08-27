"""Claude API を使って記事を要約・採点するモジュール。

- summarize_article: 要約(summary)+タグ(tags)+重要度(importance_score) を1回で生成
- score_article: 重要度スコアのみを再計算（/recalculate 用）
スコア判定基準は _build_scoring_criteria に集約し両者で共用する。
スコアロジックを変えたら SCORING_VERSION を +1 すること。

出力は tool use（tool_choice で強制）による structured output で受け取る。
プロンプトで「JSONのみ返せ」と指示してパースする方式はモデルが余計な文を
返すと落ちるため使わない。採点の一貫性のため temperature=0 を明示する
（SDK 1.x で messages.create の引数から外れたため extra_body で送る）。
"""

import logging
import re

import anthropic
from anthropic.types import ToolUseBlock

logger = logging.getLogger(__name__)

# スコアロジックの版。_build_scoring_criteria を変えたら +1 する。
SCORING_VERSION = 3

# クレジット枯渇・支出上限の到達を示す 400 のメッセージ断片。これらはリトライしても
# 回復しないので、バッチ処理は次の記事に進まず即座に中断する必要がある。
_QUOTA_MARKERS = ("credit balance is too low", "usage limits")


class QuotaExceededError(Exception):
    """API のクレジット枯渇・利用上限到達。

    通常の失敗（None を返して次の記事へ）と違い、後続も必ず失敗するため
    バッチ全体を中断させる目的で送出する。
    """


def _is_quota_error(error: Exception) -> bool:
    """例外がクレジット枯渇・上限到達によるものかを判定する。"""
    if not isinstance(error, anthropic.APIStatusError):
        return False
    text = str(error)
    body = getattr(error, "body", None)
    if isinstance(body, dict):
        message = body.get("error", {})
        if isinstance(message, dict):
            text = f"{text} {message.get('message', '')}"
    lowered = text.lower()
    return any(marker in lowered for marker in _QUOTA_MARKERS)

_MODEL = "claude-haiku-4-5"

# _MODEL の単価（$ / 100万トークン）。予算カウンタの積算に使う。
_INPUT_USD_PER_MTOK = 1.0
_OUTPUT_USD_PER_MTOK = 5.0


class CostTracker:
    """1回のバッチで使った API コストを積算し、予算超過を判定する。

    Anthropic は支出上限の残量を API で公開していない（レスポンスヘッダーの
    anthropic-ratelimit-* は分あたりのスループット枠であって支出枠ではない）。
    そこで実 usage から自前で積算し、バッチが暴走的に使い切るのを防ぐ。
    budget_usd が None / 0 なら無制限（従来どおりの挙動）。
    """

    def __init__(self, budget_usd: float | None = None):
        self.budget_usd = float(budget_usd) if budget_usd else None
        self.spent_usd = 0.0

    def add(self, input_tokens: int, output_tokens: int) -> None:
        self.spent_usd += (
            input_tokens * _INPUT_USD_PER_MTOK
            + output_tokens * _OUTPUT_USD_PER_MTOK
        ) / 1_000_000

    def exceeded(self) -> bool:
        return self.budget_usd is not None and self.spent_usd >= self.budget_usd

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
            "relevance_score": {
                "type": "number",
                "description": "データ／データ基盤との関連度（0.0〜1.0）",
            },
        },
        "required": ["summary", "tags", "importance_score", "relevance_score"],
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
            "relevance_score": {
                "type": "number",
                "description": "データ／データ基盤との関連度（0.0〜1.0）",
            },
        },
        "required": ["importance_score", "relevance_score"],
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


_DOMAIN_DEFINITION = """このパイプラインの対象領域は「データエンジニアリング／データ基盤」である。
relevance_score は、その記事の内容が対象領域にどれだけ関わるかを 0.0〜1.0 で表す。

対象（relevance が高い）：
- データウェアハウス／レイクハウス（BigQuery, Snowflake, Databricks, Redshift, Iceberg, Delta Lake）
- ETL/ELT・データパイプライン・ワークフロー（dbt, Dataform, Airflow, Dagster, Fivetran, Spark）
- ストリーミング・CDC（Kafka, Flink, Debezium）
- データ品質・データガバナンス・データカタログ・メタデータ・リネージ
- BI・可視化・セマンティックレイヤー・メトリクス定義（Looker, Tableau, Omni）
- データ基盤の上での AI/LLM 活用（RAG のためのデータ基盤、ベクトル検索、semantic model、
  データ基盤そのものの開発・運用への AI 適用）
- MLOps のうちデータ側（特徴量ストア、学習データのパイプライン）

対象外（relevance が低い）：
- 汎用のクラウド運用・IAM・権限管理・セキュリティ・認証
- ネットワーク運用・サーバ運用・インフラ運用一般
- 開発環境やローカルツールの Tips（SSH、シェル、エディタ、パッケージ管理、認証情報の保管）
- データ基盤に紐づかない開発プロセス論・AI コーディング論・組織論
- 汎用の Web／アプリ／ゲーム開発

判定の原理：AI・Terraform/IaC・クラウドといった「技法」が登場するかどうかではなく、
その技法の適用対象がデータ／データ基盤かどうかで判断する。技法が同じでも適用対象が違えば
判定は逆になる。

対比例：
- 「Claude Code で Snowflake + dbt プロジェクトを AI 駆動で開発する」→ 適用対象がデータ基盤 → 0.8
- 「AI 駆動開発で仕様はどこまで書くべきか（一般のソフトウェア開発の話）」→ 適用対象が一般の開発 → 0.1
- 「GitHub Copilot で社内コーディング規約のレビューを自動化する」→ 適用対象が一般の開発 → 0.1
- 「AI に任せたレガシーシステムのモダナイズで仕様の移行漏れに気づけない理由」→ 適用対象が一般の開発 → 0.1
- 「dbt のモデルを Terraform で管理する」→ 適用対象がデータ基盤 → 0.8
- 「IAM Policy Autopilot が Terraform の plan ファイルをサポート」→ 適用対象が権限管理 → 0.1
- 「NOC サーバチームで実践したネットワーク構成の SSoT・IaC の取り組み」→ 適用対象がネットワーク運用 → 0.1
- 「WSL2 から 1Password の SSH エージェントを使う」→ 開発環境の Tips → 0.0"""


def _build_domain_definition() -> str:
    """対象領域（データ基盤）の定義。relevance_score の判定基準として3経路で共有する。"""
    return _DOMAIN_DEFINITION


def _build_keyword_hint(keywords: list[str]) -> str:
    """関心キーワードのヒント文。"""
    if keywords:
        items = "\n".join(f"  - {kw}" for kw in keywords)
    else:
        items = "  （キーワード未設定のため、データエンジニアリング全般を対象とする）"
    return (
        "次のキーワードは特に関心の高いトピックのヒント。該当すれば加点するが、"
        "キーワードに無くても対象領域の価値があれば相応に高くする：\n"
        f"{items}"
    )


def _build_favorite_hint(favorite_tags: list[str] | None) -> str:
    """お気に入り履歴由来のタグヒント文。無ければ空文字。"""
    if not favorite_tags:
        return ""
    tag_items = "\n".join(f"  - {t}" for t in favorite_tags)
    return (
        "\n\n"
        "また、次はユーザーが過去にお気に入りした記事に多いトピック。"
        "該当する記事は関心が高い可能性があるため加点のヒントにする：\n"
        f"{tag_items}"
    )


def _build_relevance_criteria(
    keywords: list[str], favorite_tags: list[str] | None = None
) -> str:
    """relevance_score のみの判定基準。スライドの1次フィルタ用。

    importance_score の目安を混ぜると2つのスコア定義が1つのプロンプトに同居して
    混線するため、ドメイン定義とヒントだけで構成する。
    """
    return (
        f"{_build_domain_definition()}\n\n"
        f"{_build_keyword_hint(keywords)}"
        f"{_build_favorite_hint(favorite_tags)}"
    )


def _build_scoring_criteria(
    keywords: list[str], favorite_tags: list[str] | None = None
) -> str:
    """importance_score / relevance_score の判定基準。summarize / score_article で共用。

    relevance_score は対象領域（データ基盤）との関連度、importance_score は
    「データエンジニアにとって読む価値があるか」の総合判断。関連度が低い記事は
    内容が良質でも importance を高くしない。
    keyword は興味分野のヒント（加点）、favorite_tags はお気に入り履歴由来の
    暗黙的な関心（加点ヒント）。
    """
    criteria = (
        f"{_build_domain_definition()}\n"
        "\n"
        "importance_score は「データエンジニアにとって読む価値があるか」を総合的に判断して付ける。\n"
        "対象領域の記事であることが前提で、relevance_score が低い記事は内容が良質でも "
        "importance_score を高くしない。\n"
        "\n"
        "高くすべき記事（価値が高い）：\n"
        "- 実務で使える具体的な知見（設計・運用ノウハウ、how-to、トラブル対応）\n"
        "- 技術的な深さ・考察（アーキテクチャ議論、仕組みの深掘り、トレードオフ分析）\n"
        "- 大規模・本番環境の実例（実サービスの事例、失敗談やスケールの教訓）\n"
        "\n"
        "低くすべき記事（価値が低い）：\n"
        "- 対象領域外（relevance_score が低い）\n"
        "- 宣伝・PR・製品の単なる紹介（マーケティング目的）\n"
        "- 中身が薄い・短い（具体性がなく表面的）\n"
        "\n"
        f"{_build_keyword_hint(keywords)}\n"
        "\n"
        "スコアの目安：\n"
        "- 0.8〜1.0: 実務に直接役立つ深い技術記事、本番事例の濃い知見\n"
        "- 0.5前後: 有用だが一般的、または部分的に価値がある\n"
        "- 0.3以下: 対象領域外、宣伝・PR、中身が薄い"
    )
    criteria += _build_favorite_hint(favorite_tags)
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


def _as_float(value) -> float | None:
    """スコア値を float に正規化する。欠落・非数値は None（＝判定不能）。

    None は呼び出し側で「ゲートを通す」側にフォールバックさせるため、
    0.0 に丸めずそのまま None を返す。
    """
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


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
    tracker: "CostTracker | None" = None,
) -> dict | None:
    """tool_choice で指定ツールを強制呼び出しし、その入力（dict）を返す。"""
    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model=_MODEL,
        max_tokens=max_tokens,
        # temperature は SDK 1.x の signature から削除されたが Haiku 4.5 は
        # まだ受け付ける。採点の一貫性のために extra_body で送り続ける。
        extra_body={"temperature": 0},
        system=system_prompt,
        tools=[tool],
        tool_choice={"type": "tool", "name": tool["name"]},
        messages=[{"role": "user", "content": user_content}],
    )
    if tracker is not None:
        usage = getattr(message, "usage", None)
        if usage is not None:
            tracker.add(
                input_tokens=getattr(usage, "input_tokens", 0) or 0,
                output_tokens=getattr(usage, "output_tokens", 0) or 0,
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
    tracker: CostTracker | None = None,
) -> dict | None:
    """Claude で記事を要約する。失敗時は None。keywords に基づいて importance_score を判定する。"""
    try:
        result = _call_tool(
            system_prompt=_build_system_prompt(keywords or [], favorite_tags),
            user_content=f"タイトル: {title}\n\n本文:\n{content[:_MAX_CONTENT_CHARS]}",
            tool=_SUMMARY_TOOL,
            api_key=api_key,
            max_tokens=1024,
            tracker=tracker,
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
        result["relevance_score"] = _as_float(result.get("relevance_score"))
        return result
    except Exception as e:
        if _is_quota_error(e):
            raise QuotaExceededError(str(e)) from e
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
        scoring_criteria=_build_relevance_criteria(keywords or [], favorite_tags)
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
        if _is_quota_error(e):
            raise QuotaExceededError(str(e)) from e
        logger.error("[summarizer] slide prefilter failed: %s", e)
        return None


def score_article(
    title: str,
    content: str,
    api_key: str,
    keywords: list[str] | None = None,
    favorite_tags: list[str] | None = None,
    tracker: CostTracker | None = None,
) -> dict | None:
    """記事のスコアを再計算する。失敗時は None。

    {"importance_score": float, "relevance_score": float | None} を返す。
    relevance_score が None なのはモデルが返さなかった場合で、呼び出し側は
    「判定不能＝ゲートを通す」として扱う（取りこぼし防止）。
    """
    try:
        result = _call_tool(
            system_prompt=_build_score_only_prompt(keywords or [], favorite_tags),
            user_content=f"タイトル: {title}\n\n本文:\n{content[:_MAX_CONTENT_CHARS]}",
            tool=_SCORE_TOOL,
            api_key=api_key,
            max_tokens=128,
            tracker=tracker,
        )
        if result is None or result.get("importance_score") is None:
            return None
        return {
            "importance_score": float(result["importance_score"]),
            "relevance_score": _as_float(result.get("relevance_score")),
        }
    except Exception as e:
        if _is_quota_error(e):
            raise QuotaExceededError(str(e)) from e
        logger.error("[summarizer] score failed: %s", e)
        return None
