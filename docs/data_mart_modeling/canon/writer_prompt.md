あなたはデータマート設計シリーズ（全11回）の1回分を執筆する。読者はデータエンジニア本人1名。

## 最初に読むもの（この順で、全部）
1. `docs/data_mart_modeling/canon/style.md` — 文体・節構成・HTML 骨格・自己チェック
2. `docs/data_mart_modeling/canon/domain.md` — 題材の正典（テーブル・列・ID・固定判断）。ここに無い名前は使わない
3. `docs/data_mart_modeling/canon/references.md` — 文献。自分の回に割り当てられた記事を **WebFetch で実際に読む**
4. `docs/data_mart_modeling/briefs/NN.md` — この章の要件。**節ごとの必須内容・図・演習はこれが正本**
5. 図を描く回だけ: `~/.claude/skills/svg-diagram/SKILL.md`（`references/examples.md` も）

## やること
- ブリーフの必須内容を全て入れた HTML を `docs/data_mart_modeling/html/NN_<slug>.html` に書く（ファイル名はブリーフ指定）
- SQL / YAML は BigQuery + dbt で実際に動く形。架空の関数・オプションを使わない。迷ったら dbt docs を WebFetch で確認
- 図がある回: `python3 ~/.claude/skills/svg-diagram/scripts/check_svg.py <html>` を実行し **0 errors** にする。warning も可能な限り消す
- 書き終えたら style.md の「出力前の自己チェック」を1項目ずつ実際に確認する（grep で正典に無いテーブル名が無いか等）
- 報告を `docs/data_mart_modeling/reports/NN_report.md` に書く。内容: 完了した節の一覧 / 読んだ文献と引用した要点 / check_svg の結果 / 正典への変更提案（あれば）/ 迷った判断とその理由 / 未達事項

## 禁止
- サブエージェントを起動しない
- 正典に無いテーブル名・列名・ID を作らない（必要なら report に提案を書き、本文では正典の範囲で書く）
- 他の回の HTML を読まない（一貫性は正典が担保する）
- 手元の基盤（dbt_logs_analysis / news_pipeline）への言及は第8節だけ
- family-share への公開・git commit をしない

## 返答
最後にチャットへ返すのは次の4行だけ（report 本文を貼らない）:
STATUS: DONE | DONE_WITH_CONCERNS | BLOCKED
FILE: <html パス>
SVG: <check_svg の結果 1行、図が無い回は "n/a">
CONCERNS: <1行、無ければ none>
