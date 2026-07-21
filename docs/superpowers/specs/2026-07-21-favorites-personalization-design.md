# favorites タグによるスコアリングのパーソナライズ 設計書

- 日付: 2026-07-21
- 対象 Issue: [#17](https://github.com/mishi5/data-platform-handson/issues/17)
- ステータス: 承認済み

## 背景・課題

Slack の ⭐ ボタンで `favorites` テーブルにユーザーの好みデータが貯まっているが、
importance_score の採点には活用されていない。関心の明示的な入力は Google Sheets の
keywords シートのみで、実際に「読んで気に入った」という暗黙のフィードバックが
キュレーション精度に反映されない。

## 目的

お気に入り履歴から「よく favorite しているタグ」を抽出し、採点基準への加点ヒント
として動的に反映するフィードバックループを作る。使うほどキュレーションが育つ。

## 検討した代替案

| 案 | 内容 | 判断 |
|---|---|---|
| A. タグ頻度ベース（採用） | favorites × summaries のタグ頻度上位N個を基準に追記 | 実装が単純・追加コストゼロ（タグは要約時に生成済み） |
| B. 事例ベース (few-shot) | お気に入り記事タイトルを「気に入った例」としてプロンプトに入れる | 表現力は高いがプロンプト肥大・採点の揺れ・コスト増 |
| C. 両方 | A + B | 精度は期待できるがチューニング変数が増えすぎる |

## 設計

### データフロー

1. `_run_collect` / `_run_recalculate` / `_run_resummarize` の開始時に
   `bq.get_favorite_tag_counts(limit)` を1回だけ呼ぶ。
2. SQL: `favorites` と `summaries` を article_id で JOIN し `UNNEST(tags)` で展開、
   タグごとの出現数を集計。**出現2回以上**のみを対象に出現数降順で上位 `limit` 件を返す。
   - 出現2回以上の条件は、1記事だけの偶発タグへの過適合を防ぐため。
     お気に入りが貯まるまでは自然にパーソナライズなしで動作する。
3. 取得タグを `summarize_article` / `score_article` / `score_slide_relevance` に
   `favorite_tags` 引数として渡す。
4. `_build_scoring_criteria(keywords, favorite_tags)` が「ユーザーが過去にお気に入り
   した記事に多いトピック（該当すれば加点）」セクションを追記する。
   keywords（明示的関心）と favorites 由来タグ（暗黙的関心）が並ぶ構成。

### 設定（settings シート）

- `general / personalize_top_tags`: 反映するタグ数。未設定は 5、`0` で無効。
  無効時は BigQuery クエリ自体をスキップする。

### SCORING_VERSION の扱い

変更しない。keywords シートの編集が版を上げない既存前例と同じく、これは
「採点ロジック」ではなく「ヒント入力」の変化であるため。favorites が増えても
/recalculate のトリガーにはならない。

### エラー処理

タグ取得（BigQuery）に失敗しても空リストで続行し、パーソナライズなしの通常採点に
フォールバックする。パイプラインは止めない（warning ログのみ）。

### テスト

- `bq_client.get_favorite_tag_counts`: SQL 構造（JOIN・UNNEST・HAVING・LIMIT
  パラメータ）と戻り値の形。
- `_build_scoring_criteria`: favorite_tags 指定時にセクションが追記されること、
  空リスト時は既存出力と同一であること。
- `_run_collect`: favorite_tags が summarize に渡ること、`personalize_top_tags=0`
  で BQ を呼ばないこと、タグ取得失敗時も収集が続行すること。

### 変更ファイル

- `news_pipeline/collector/bq_client.py`: `get_favorite_tag_counts` 追加
- `news_pipeline/collector/summarizer.py`: `_build_scoring_criteria` 拡張・
  各関数に `favorite_tags` 引数追加
- `news_pipeline/collector/main.py`: 設定読み出し・タグ取得・受け渡し
- `news_pipeline/tests/`: test_bq_client / test_summarizer / test_main
- `CLAUDE.md`: settings 項目と挙動の追記
