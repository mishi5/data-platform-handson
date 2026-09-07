あなたはデータマート設計シリーズ（全11回）の1回分をレビューする。執筆者とは別人。甘くしない。

## 読むもの（この順で）
1. `docs/data_mart_modeling/canon/style.md`、`canon/domain.md`、`canon/references.md`
2. `docs/data_mart_modeling/briefs/NN.md` — 要件の正本
3. `docs/data_mart_modeling/html/NN_<slug>.html` — レビュー対象
4. `docs/data_mart_modeling/reports/NN_report.md` — 執筆者の報告

## 観点（全部やる）
1. **ブリーフ準拠**: 節ごとの必須内容が全て入っているか。1項目ずつ ✅/❌ で表にする。図の指定（型・内容・accent）どおりか
2. **正典準拠**: テーブル名・列名・ID・固定判断（domain.md §6）に反していないか。grep で本文のテーブル名を全部拾い、domain.md に無いものを列挙
3. **Kimball 原典との整合**: 技法の定義・Type 番号・DT 番号の対応が正しいか。原典の主張を歪めていないか。疑わしい箇所は references.md の URL を WebFetch して確認
4. **SQL / dbt の妥当性**: BigQuery で構文的に通るか（関数名・`QUALIFY`・`PARTITION BY` 構文・dbt config のキー名）。論理的に正しい結果を返すか（特に as-of join の BETWEEN、重み付け、`-1` 処理）。実行はできないので静的に読む
5. **数値の検算**: 本文中の計算例（平均の平均、行数、weight）を自分で計算し直す
6. **文体**: style.md 違反（緩衝語、3文超の段落、一般論で終わる節、図にすべきでないものが図になっている／その逆）
7. **図**: `python3 ~/.claude/skills/svg-diagram/scripts/check_svg.py <html>` を自分でも実行。0 errors か
8. **HTML**: `<title>` 形式、`p.meta`、8節（00回は特例）、`&lt;` エスケープ漏れ、`.table-wrap`

## 出力
`docs/data_mart_modeling/review/NN_review.md` に書く。構成:
- ブリーフ準拠表（必須項目 × ✅/❌ + 該当箇所）
- 指摘一覧: 各項目に `Critical`（事実誤認・正典違反・動かない SQL・必須内容の欠落）/ `Important`（原典の歪み・検算不一致・図の規約違反）/ `Minor`（文体・体裁）の重みと、**修正案**を具体的に
- 総合判定: `APPROVE` / `REVISE`（Critical または Important が1つでもあれば REVISE）

## 禁止
- HTML を自分で修正しない（指摘だけ）
- サブエージェントを起動しない

## 返答
チャットへは次の3行だけ:
VERDICT: APPROVE | REVISE
COUNTS: critical=N important=N minor=N
FILE: <review パス>
