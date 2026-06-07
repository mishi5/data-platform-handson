# スコアロジック改善（DE価値ベース）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** importance_score の判定基準を「keyword 一致」から「データエンジニアにとっての価値（keyword は補助）+ アンカー」に変え、SCORING_VERSION を 2 に上げる。

**Architecture:** `summarizer._build_scoring_criteria` は collect の要約プロンプトと recalculate の score-only プロンプトの両方が共用する単一の基準ソース。ここを書き換えるだけで両経路が新基準になる。SCORING_VERSION を 2 にすることで /recalculate が既存行（NULL/v1）を差分で再採点対象にする。

**Tech Stack:** Python 3.12 / Anthropic（Haiku 4.5）/ pytest（`uv run pytest`）

---

## File Structure

- **Modify** `news_pipeline/collector/summarizer.py` — `_build_scoring_criteria` の本文と `SCORING_VERSION` 定数
- **Modify** `news_pipeline/tests/test_summarizer.py` — 新基準の語を検証するテスト追加

単一ファイルのロジック変更。テストは `cd news_pipeline && uv run pytest`。

---

## Task 1: 判定基準を DE 価値ベースに書き換え + SCORING_VERSION=2

**Files:**
- Modify: `news_pipeline/collector/summarizer.py`（`SCORING_VERSION` 定数 と `_build_scoring_criteria` 関数）
- Test: `news_pipeline/tests/test_summarizer.py`

着手前に `news_pipeline/collector/summarizer.py` を Read すること。現状:
- `SCORING_VERSION = 1`
- `_build_scoring_criteria(keywords)` は keyword 一致ベースの基準文を返す（keyword あり→各語列挙、なし→「キーワード未設定...」）。
- この関数は `_build_system_prompt` と `_build_score_only_prompt` が共用。

- [ ] **Step 1: Write the failing test**

`news_pipeline/tests/test_summarizer.py` の末尾に追加:

```python
def test_build_scoring_criteria_uses_de_value_axis():
    c = _build_scoring_criteria(["BigQuery"])
    # DE価値ベースの主軸とアンカーが含まれる
    assert "読む価値" in c
    assert "スコアの目安" in c
    # 高/低スコア軸の語
    assert "実務" in c
    assert "宣伝" in c


def test_scoring_version_is_2():
    from collector.summarizer import SCORING_VERSION
    assert SCORING_VERSION == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd news_pipeline && uv run pytest tests/test_summarizer.py -k "de_value or scoring_version_is_2" -v`
Expected: FAIL（現基準に「読む価値」「スコアの目安」が無い / SCORING_VERSION が 1）

- [ ] **Step 3: Implement**

`news_pipeline/collector/summarizer.py` の `SCORING_VERSION = 1` を変更:

```python
# スコアロジックの版。_build_scoring_criteria を変えたら +1 する。
SCORING_VERSION = 2
```

`_build_scoring_criteria` 関数を以下で置き換える:

```python
def _build_scoring_criteria(keywords: list[str]) -> str:
    """importance_score の判定基準を組み立てる。summarize / score_article で共用。

    主軸は「データエンジニアにとって読む価値があるか」の総合判断。
    keyword は興味分野のヒント（加点）で、無くても価値があれば相応に高くする。
    """
    if keywords:
        items = "\n".join(f"  - {kw}" for kw in keywords)
    else:
        items = "  （キーワード未設定のため、データエンジニアリング全般を対象とする）"
    return (
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd news_pipeline && uv run pytest tests/test_summarizer.py -v`
Expected: PASS（既存テスト + 新規2テスト）。特に既存の `test_build_scoring_criteria_includes_keywords`（keywords 列挙）と `test_build_scoring_criteria_no_keywords`（「キーワード未設定」）が引き続き通ること。

全体: `cd news_pipeline && uv run pytest tests/ -q`

- [ ] **Step 5: Commit**

```bash
git add news_pipeline/collector/summarizer.py news_pipeline/tests/test_summarizer.py
git commit -m "feat(summarizer): スコア基準をDE価値ベース＋アンカーに変更し SCORING_VERSION=2

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Self-Review メモ（実装者向け）

- **Spec coverage:** DE価値主軸・高/低スコア軸・keyword補助ヒント・アンカー（0.8/0.5/0.3）・SCORING_VERSION=2 — すべて Task1 で対応。
- **回帰:** keyword 列挙と「キーワード未設定」表現を維持するため既存テスト（`_build_scoring_criteria`/`_build_system_prompt` 系）は通る。`summarize_article`/`score_article` はモックJSONを返すため基準文変更の影響を受けない。
- **デプロイ（実装後の運用ステップ・別途実施）:** インフラ変更なし。Docker ビルド&デプロイのみ。デプロイ後 `/recalculate` を `scoring_version < 2` の行（NULL 約609 + v1 50 = 約659件）が無くなるまで繰り返し叩く（recalculate_limit=50 ずつ、十数回）。
