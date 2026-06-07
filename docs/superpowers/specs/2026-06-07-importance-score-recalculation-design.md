# importance_score 再計算の仕組み 設計書

作成日: 2026-06-07

## 目的

importance_score のスコアリングロジックを改善・変更しやすくするため、**ロジックを変えた際に既存の summaries 行を再計算（再採点）できる基盤**を作る。スコアの版を `scoring_version` で管理し、古い版で採点された行だけを差分で再計算する。

関連分析: [2026-06-06-summary-notification-logic-analysis.md](2026-06-06-summary-notification-logic-analysis.md)

## 方針（確定事項）

| 項目 | 決定 |
|------|------|
| 今回のスコープ | スコアロジックの中身改善より先に「再計算の仕組み」を作る |
| 再計算の範囲 | importance_score のみ（summary/tags は再生成しない・score-only 呼び出し） |
| 対象選定 | `scoring_version` で差分再計算（古い版の行だけ） |
| トリガー | 専用エンドポイント `POST /recalculate`（手動）。settings 上限件数ずつ処理し数回叩く |
| 閾値未満時 | スコア更新のみ（summaries から削除しない・notify 側フィルタも追加しない） |
| スコアリング基準の置き場所 | `summarizer.py` の共有ヘルパに集約し collect/recalculate 両経路で共用 |
| 版定数 | `summarizer.SCORING_VERSION`（初期値 1） |
| モデル | 現状の Claude Haiku 4.5 を踏襲（score-only） |

## コストの見積もり（参考）

score-only は入力 ~1,500 トークン/件・出力 ~20 トークン/件。Haiku 4.5（概算 入力$1 / 出力$5 per 1M）で 200 件あたり **約 $0.3〜0.4**。コスト制約は実質ない。律速は逐次 API 呼び出しの処理時間のため、per-run 上限（`recalculate_limit`）で区切る。

## アーキテクチャ

```
┌─ POST /recalculate（手動・実験用）────────────────────────────┐
│  get_outdated_summaries(SCORING_VERSION, limit)               │
│    （summaries ⋈ raw_articles で本文取得、版が古い行を limit 件）│
│  各行 → score_article(title, content, keywords)               │
│    → update_summary_score(article_id, score, SCORING_VERSION) │
└──────────────────────────────────────────────────────────────┘

collect 側: 新規 summary 保存時に scoring_version = SCORING_VERSION を付与
```

### スコアリング基準の一元化

要約とスコアは分離しない（collect は要約+タグ+スコアを1呼び出しで生成）。そのため**スコア基準が collect の結合プロンプトと recalculate の score-only プロンプトの2か所に現れる**。これを共有ヘルパ `_build_scoring_criteria(keywords)` に集約し、両プロンプトが同じ基準文字列を埋め込む。スコアロジックを変えるときはこのヘルパを編集し `SCORING_VERSION` を +1 する。これで collect（新着）と recalculate（既存）が一貫して新ロジックになる。

## コンポーネントと変更内容

### summarizer.py

- `SCORING_VERSION = 1` を定義。
- `_build_scoring_criteria(keywords: list[str]) -> str`: importance_score の判定基準（ルーブリック + keywords の使い方）を組み立てて返す共有ヘルパ。現行の判定基準文（「キーワードに関連するほど高く / 複数該当でさらに高く / 無関係なら0.1以下」）をこのヘルパに移す。
- `summarize_article(...)`: 既存の結合プロンプト内のスコア基準部分を `_build_scoring_criteria(keywords)` の呼び出しに置き換える（挙動は現状維持）。
- 新規 `score_article(title: str, content: str, api_key: str, keywords: list[str] | None = None) -> float | None`:
  - `_build_scoring_criteria` を使ったスコア専用のシステムプロンプトで Claude Haiku 4.5 を呼ぶ。
  - 出力は `{"importance_score": 0.0〜1.0}` のみ。JSON をパースして float を返す。失敗時は None。
  - 本文は既存同様 `content[:3000]` に切り詰め。

### bq_client.py

- 新規 `get_outdated_summaries(version: int, limit: int) -> list[dict]`:
  - `summaries` を `raw_articles` と LEFT JOIN し本文を取得。`WHERE s.scoring_version IS NULL OR s.scoring_version < @version`、`LIMIT @limit`。
  - 返す dict: `article_id`, `title`, `content`（raw_articles 由来・NULL あり得る）, `source`。
  - `version` / `limit` はパラメータ化（ScalarQueryParameter INT64）。
- 新規 `update_summary_score(article_id: str, importance_score: float, scoring_version: int) -> None`:
  - DML `UPDATE summaries SET importance_score=@score, scoring_version=@ver WHERE article_id=@aid`。全パラメータ化。
  - 例外は送出する（呼び出し側 `_run_recalculate` が1件ずつ try/except で握り、失敗行は次回繰り越し）。

### infra/bigquery.tf

- summaries の schema に NULLABLE 列を追加:
  ```hcl
  { name = "scoring_version", type = "INT64", mode = "NULLABLE" },
  ```
- NULLABLE 列追加は BigQuery の非破壊スキーマ更新（テーブル再作成なし）。既存行は NULL = 旧版扱いで再計算対象になる。

### main.py

- import に `SCORING_VERSION` と `score_article` を追加（既存の summarize_article import を拡張）。
- 新規 `_run_recalculate(triggered_by: str = "manual") -> int`:
  1. config から keywords / settings を読む。`recalculate_limit = int(settings.get("general", {}).get("recalculate_limit", _DEFAULT_RECALCULATE_LIMIT))`
  2. `rows = bq.get_outdated_summaries(SCORING_VERSION, recalculate_limit)`
  3. 各 row:
     - `score = score_article(title=row["title"], content=row.get("content") or "", api_key=ANTHROPIC_API_KEY, keywords=keywords)`
     - `score is None` ならスキップ（error_count++）
     - そうでなければ `bq.update_summary_score(row["article_id"], score, SCORING_VERSION)`、成功カウント++（個別 try/except、失敗は次回繰り越し）
  4. 再計算成功件数を返す。finally で pipeline_logs 保存（`triggered_by`、既存スキーマで記録）。
- 定数 `_DEFAULT_RECALCULATE_LIMIT = 50` を追加。
- collect 側（`_run_collect`）の summary dict 構築箇所に `"scoring_version": SCORING_VERSION` を追加し、新規行が現行版で記録されるようにする。
- 新規エンドポイント:
  ```python
  @app.post("/recalculate", response_model=PipelineResponse)
  async def recalculate():
      n = await asyncio.to_thread(_run_recalculate)
      return PipelineResponse(status="ok", notified=n)
  ```

### settings シート

- `general/recalculate_limit`（1回の再計算で処理する最大件数、既定 50）を追加。

## データフロー（`/recalculate`）

```
get_outdated_summaries(SCORING_VERSION, limit)
   summaries ⋈ raw_articles（content 取得）
   WHERE scoring_version IS NULL OR scoring_version < SCORING_VERSION
   LIMIT limit
        │
   各行: score_article(title, content, keywords)  ← _build_scoring_criteria を使用
        │  None ならスキップ（error_count++）
        ▼
   update_summary_score(article_id, score, SCORING_VERSION)  ← DML UPDATE
        │  1件ずつ try/except、失敗は次回繰り越し
        ▼
   成功件数を返す
```

## エラー処理 / エッジケース

- **本文が NULL（raw_articles）**: タイトルのみで再採点（`content or ""`）。元々 content 無しで採点された記事と整合。
- **score_article が None（API/パース失敗）**: その行はスキップし scoring_version 据え置き → 次回 `/recalculate` で再試行。
- **update_summary_score 失敗**: 1件ずつ try/except で握り、その行は版据え置き → 次回繰り越し。
- **streaming buffer 制約**: recalc が対象にするのは過去 collect で挿入された古い行のみ（collect 直後の新規行は現行版で対象外）なので UPDATE が buffer に当たらない。
- **既存行（scoring_version=NULL）**: 初回 `/recalculate` で全件が現行版 1 に揃う。ロジック未変更でも再採点されるが安価。気になる場合は実行しなければよい（手動トリガーのため暴発しない）。
- **閾値未満化**: スコア更新のみ。summaries からは削除せず、notify 側フィルタも追加しない（決定通り）。未通知行は importance 降順の各カテゴリ上位 max_notify から自然に外れて後回しになる。

## テスト

- `summarizer`: `score_article` がスコアを float で返す / コードブロック除去 / 失敗時 None。`_build_scoring_criteria` が keywords を含む基準文字列を返す。`summarize_article` が引き続きスコアを返す（共有ヘルパ移行後の回帰確認）。
- `bq_client`: `get_outdated_summaries` のクエリ条件（scoring_version IS NULL OR < @version、JOIN raw_articles、LIMIT）と返却。`update_summary_score` の UPDATE DML 生成。
- main.py は import 不可のため単体テストなし（構文 + import + 全テスト緑 + grep で検証）。

## 環境変数 / ドキュメント

- CLAUDE.md / README を更新:
  - エンドポイント一覧に `POST /recalculate`（手動・スコア再計算）
  - settings に `general/recalculate_limit`（既定50）
  - summaries の `scoring_version` 列
  - 運用手順: スコアロジック変更 → `SCORING_VERSION` を +1 → デプロイ → `/recalculate` を古い版が無くなるまで数回叩く

## 非対象（YAGNI）

- スコアリングロジック自体の改善（ルーブリック高度化・多軸スコア・モデル変更）。本設計は「再計算の仕組み」のみ。中身の改善は本基盤の上で別途実験する。
- 要約（summary/tags）の再生成
- 再計算の自動スケジューラ化
- 閾値未満行の削除 / notify 側の閾値フィルタ
- scoring_version 別の A/B 比較や履歴保持（上書き更新のみ）
