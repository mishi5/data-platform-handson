# 07 star か One Big Table か — 再レビュー（修正ラウンド 1 の検証）

対象: `docs/data_mart_modeling/html/07_star_vs_obt.html`
初回レビュー: `review/07_review.md`（Critical 3 / Important 7 / Minor 7）／執筆者の対応報告: `reports/07_report.md` 末尾

レビュー担当は初回とは別。報告は鵜呑みにせず、17 件すべて HTML の該当箇所を読んで判定した。
裁定済みの 3 点（`obt_page_view` は「この節だけの仮定」明示で可 / `int_scout_keyed` は命名規約に沿うので可 / `INFORMATION_SCHEMA` のプロジェクト修飾省略は可）は前提として扱う。

---

## 1. 初回指摘 17 件の判定

| # | 指摘 | 判定 | 根拠（現在の HTML） |
|---|---|---|---|
| C1 | Type1 `UPDATE` に `AND is_current` が付いている | **ADDRESSED** | L88–91 の SQL から `AND is_current` が消え、コメントは `-- star: C002 の SCD2 版すべて（現時点で 2 行）`。L86 に「`is_current` で絞らず**その自然キーの全 SCD2 版を揃えて上書きする**（Type 6, DT#15）」＋ `C002` が 2 行ある理由。正典（`C002` は 2026-05-01 に `employee_size_band` 変化＝2 行）と一致 |
| C2 | §8 の `mart_url_performance_incremental` 記述が事実と違う | **ADDRESSED** | L587 が「`date` に `partition_by` を持つ（`cluster_by` は無い）」に修正。`dbt_logs_analysis/models/marts/mart_url_performance_incremental.sql` L6–9 の `partition_by={'field':'date','data_type':'date'}`・`cluster_by` 不在と一致。増分境界の引用 `DATE(request_timestamp) > (SELECT MAX(date) FROM {{ this }})` も同ファイル L21 の原文どおり。上流 `stg_access_logs` が view であることも `dbt_project.yml`（`staging: +materialized: view`）と一致 |
| C3 | 「このビュー自体のスキャンは課金されない」が誤り | **ADDRESSED** | L485 が「オンデマンド課金では処理バイトが 10 MB 未満でも 1 回あたり最低 10 MB が課金され、しかも結果がキャッシュされないので回すたびに課金される」に差し替え済み |
| I1 | Fowler が消えている | **ADDRESSED** | `p.meta`（L44）に `Fowler (Coalesce 2020)`、§4 の軸ボックス（L167）が講演の主張として記述、参照文献 L597 に YouTube URL、Discourse は L175 の「関連議論」＋ L598 に降格。主張の帰属も正しい（下記 §2 で外部照合） |
| I2 | Manifesto「3 点に尽きる」 | **ADDRESSED** | L143 が「Manifesto（1997）が挙げる強みのうち、この回で使うのは 3 点」、L144 で対称性・標準技法・集約ナビゲーションを補い「そのどれもが意味の側の主張」と結んでいる |
| I3 | §6 判断基準表が非排他・§7(a)/§8 の引き当てと矛盾 | **ADDRESSED**（ただし副作用あり → NI1） | L511–520 で `#` 列追加・具体→一般の並べ替え・4 行目を「1 億以上（更新頻度を問わず）」にして穴を塞いだ。BI ツール行（3/4/5）は組合せに漏れがない。§7(a) は 4 行目（L533）、§8 は 1 行目（L586）で、どちらも第一一致で正しく引ける |
| I4 | snowflake の結合数が自己矛盾 | **ADDRESSED** | L68 が `3（…1 段増える）` に修正。L78 に `dim_agency` は縮約ディメンションで雪片化とは別物、という注記 |
| I5 | `obt_page_view` が正典外 | **ADDRESSED** | L94–95 に「正典に無い。`fct_page_view` を企業属性込みで非正規化したと仮定した、この節だけの『やってはいけない設計』の例」。裁定条件を満たす |
| I6 | 図の数値が実測でないのに図中でそう見える | **ADDRESSED** | L308 に 3 行目の注記「数値は題材上の想定値（実測ではない）。自分の表の実値は §5(d) の dry-run で取る。」、`<desc>`（L228）末尾にも「数値は題材上の想定値。」。`viewBox` 400→424・背景 `rect` 424 も整合（ゾーン下端 344、注記 y=408 で収まる） |
| I7 | `require_partition_filter` 下で落ちるテストの説明が不完全 | **NOT ADDRESSED** | 本文（L452）は「`unique` と `relationships`」に限定され、`not_null` の但し書き（L463）も入った。しかし**差し替えた修正例（L456–461）が dbt では機能しない**。詳細は NI1（新規 Critical） |
| M1 | 1 段落 3 文までの違反 9 箇所 | **ADDRESSED** | 全 `<p>` を機械集計。4 文以上は L567 の `(1)…(2)…` 列挙 1 箇所のみで、報告どおり |
| M2 | §8 の aside が「3〜5 行」を超える | **NOT ADDRESSED** | L585–590 は 4 段落・約 480 字（900px 幅で 10 行前後）。C2 の書き直しで内容が増えたぶん、初回時点より短くなっていない。報告も超過を認めている |
| M3 | 「2013 年以降に失効した」の年が根拠不明 | **ADDRESSED** | L149「列指向 DWH が標準になった時点で失効した」 |
| M4 | §7(a) の config の対象が読めない | **ADDRESSED** | L537 に `-- models/marts/fct_page_view.sql（OBT ではなくファクト本体の config）` |
| M5 | `agg_company_rating_daily` がページビューと無関係 | **ADDRESSED** | L535「`agg_company_rating_daily` と同じ形の『企業 × 日粒度の閲覧集約』」＋「正典には無いので、作るなら正典への追加が要る」 |
| M6 | `<caption style="...">` が骨格に無い | **ADDRESSED** | L50 が `<h3>この回で固定する判断</h3>`。HTML 内にインラインスタイル付き `caption` は無し |
| M7 | Fivetran のストレージに star 全体の値を足す | **ADDRESSED** | L196「ファクト `store_sales` 単体は 29,778 MB（4 つのディメンションを足した star 全体でも 29,905 MB）」 |

**集計: ADDRESSED 15 / NOT ADDRESSED 2（I7・M2）**

---

## 2. 修正で新たに入った箇所の検証

| 検証項目 | 結果 |
|---|---|
| Fowler 講演の帰属（L167） | **正しい**。講演の存在・演題・登壇者（Dave Fowler / Chartio / Coalesce 2020）を外部で確認。「star schema を捨て、結合可能な列を全て結合した大きな非正規化テーブルを 1 本作り、その上にビューでマートを切る」「根拠はストレージコストが当時ほど高くない」は、Hightouch の同講演要約（"ditching the star schema and just building denormalized big tables… join all joinable fields… making views over this table" / "storage not costing as much… one of the motives behind the Star Schema"）と一致する。L168–169 の「性能の技法は捨てる／意味の技法は残す」は Fowler の発言としてではなく**この回の整理**として書かれており、帰属の歪みは無い |
| L172 のビューの記述 | **正しい**。BigQuery の論理ビューは実行のたびに下のテーブルをスキャンするので、ワイドテーブル＋ビューではスキャン量は減らない。だから OBT を `materialized='table'` にする、という接続も C3（`INFORMATION_SCHEMA` の課金）と整合。マテリアライズド・ビューの「外部結合や一部の集計に制約がある」も事実（`canon/references.md` に BQ MV 行が追加されているので、URL を参照文献に足す余地はある。必須ではない） |
| L485 の `INFORMATION_SCHEMA` 課金 | **正しい**（最低 10 MB・キャッシュ無し） |
| §8 と実ファイルの突き合わせ | **一致**。`partition_by` あり／`cluster_by` なし／増分境界の式／上流が view であること、いずれも `mart_url_performance_incremental.sql`・`dbt_project.yml`・`sources.yml`（`data-platform-handson-1223.logs_database.access`）と合う。生テーブルのパーティション有無はリポジトリ内に定義が無く（Glue クローラ経由の外部定義）、「パーティション無し」は repo からは検証できない前提である点だけ留意 |
| 図の数値の扱い | **可**。可視要素（L308）と `<desc>` の両方に「題材上の想定値（実測ではない）」。accent の位置は初回の裁定どおり変更なし。`check_svg.py` → `0 errors, 0 warnings` |
| `fct_scout` の config（L316–324） | **dbt docs どおり**。`partition_by` は `{'field':'sent_date','data_type':'date','granularity':'day'}` で DATE 列（正典 §4「`partition_by` はこの DATE 列に張る」に一致）、`cluster_by` はリスト、`require_partition_filter` は `partition_by` の外側のトップレベル config（OBT 側 L357 のみ）。`SELECT` に `audit_key` を含む点も更新後の正典に追随 |
| 正典外テーブル名 | `obt_page_view`（I5 で仮定と明示）と `int_scout_keyed`（`int_<entity>_<verb>` 規約に沿う）の 2 件のみ。いずれも裁定済み |
| HTML 体裁 | `<h2>` は 1〜8 ＋ 参照文献の 9 個、`<table>` 7 個すべてが `.table-wrap` 内、`<pre><code>` 内に生の `<` 無し（`&lt;` エスケープ漏れ無し）、URL は全て `canon/references.md` 内 |

---

## 3. 新規指摘（修正差分の範囲）

### 新規 Critical

**NI1. I7 の修正例（モデル単位の `+where`）は dbt では効かない — L456–461**

```yaml
models:
  - name: obt_scout_funnel
    config:
      # このモデルのテストは全て直近パーティションに限定する
      +where: "sent_date >= DATE_SUB(CURRENT_DATE('Asia/Tokyo'), INTERVAL 7 DAY)"
```

dbt の `where` はテスト（data test）のコンフィグであり、**モデルの `config:` に書いてもそのモデルに付いた generic test には伝播しない**。設定できるのは (1) 各テストの `config:`、(2) generic test マクロ内の `{{ config(where=...) }}`、(3) `dbt_project.yml` の `data_tests:` 配下（`+` 前置）の 3 箇所だけである。さらに `+` 前置は `dbt_project.yml` 専用で、プロパティ（schema）yml の `config:` では使わない。つまりこの例は**前置記号も置き場所も誤り**で、写した読者は `dbt test` が落ちたまま原因を掴めない。直前の L452 で「`unique` と `relationships` が落ちる」と問題提起した直後の解決策なので、記事の中で最も参照される箇所でもある。

修正案（どちらか、または両方）:

```yaml
    columns:
      - name: scout_id
        tests:
          - unique:
              config:
                where: "sent_date >= DATE_SUB(CURRENT_DATE('Asia/Tokyo'), INTERVAL 7 DAY)"
      - name: scout_sender_key
        tests:
          - relationships:
              to: ref('dim_scout_sender')
              field: scout_sender_key
              config:
                where: "sent_date >= DATE_SUB(CURRENT_DATE('Asia/Tokyo'), INTERVAL 7 DAY)"
```

書き漏らしを防ぐ「まとめて掛ける」形を見せたいなら、置き場所は `dbt_project.yml` になる:

```yaml
# dbt_project.yml
data_tests:
  dbt_logs_analysis:   # プロジェクト名。marts 配下だけに絞るならディレクトリを 1 段足す
    +where: "sent_date >= DATE_SUB(CURRENT_DATE('Asia/Tokyo'), INTERVAL 7 DAY)"
```

ただし後者はプロジェクト全体（またはディレクトリ配下全部）に効くので、`sent_date` を持たないモデルのテストまで壊す。本文で「モデル単位でまとめる方法は dbt には無い。テスト単位に書くか、`dbt_project.yml` でディレクトリ単位に掛けるかの二択」と 1 文添えるのが正確。

### 新規 Important

**NI2. §1 の「OBT を正本にする条件」と §6 の表が食い違い、`自分 × star 未所持 × 1000 万行以上` に該当行が無い — L57 / L512・L519**

§6 を I3 に沿って並べ替えた結果、1 行目と 8 行目に条件が付いた（1 行目「star をまだ持っていない・1000 万未満」、8 行目「star が既にある」）。これで §1 の固定判断表（L57）と噛み合わなくなっている。

- §1: 「OBT を正本にする条件 = 利用者が自分 1 人・**1 億未満**・Type1 上書きが**起きない**、の 3 つが同時に成り立つときだけ」
- §6 1 行目: 「利用者 1〜2 名・star をまだ持っていない・**1000 万未満**・更新頻度は**問わない**」

行数の閾値（1 億 / 1000 万）も Type1 の扱い（起きない / 問わない）も違うので、同じ「OBT のみ」という結論に 2 つの異なる条件が並ぶ。さらに「自分 1 人・star をまだ持っていない・5000 万行」を L523 の読み方（上から第一一致）で当てると、1 行目は行数で外れ、8 行目は「star が既にある」で外れ、2〜7 行目は利用者が違う（6 行目「アナリスト（SQL を書く・少人数）」に読めるかは曖昧）。**表に穴が残っている。**

修正案: §6 を正とし、§1 L57 を「§6 の 1 行目に当たるときだけ（単発の分析・PoC・star をまだ持っていない・1000 万行未満）。詳細は 6 節」に短縮して閾値の二重定義をやめる。そのうえで §6 8 行目の利用者を「自分（SQL を書く）」に戻し、条件「star が既にある」は理由列へ移すと穴が閉じる（star をまだ持っていない自分 1 人・1000 万行以上は「star のまま」＝作ってから判断、で筋が通る）。

### 新規 Minor

- **NM1. §8 の `mart_url_performance` を「OBT」と呼ぶのは、この記事自身の定義と合わない（L586）。** §7(b)（L551）は OBT を「ファクト 1 行に全ディメンション属性を付けた表」と定義し、粒度が 1 行 = 1 企業の `agg_company_entity` を OBT から外している。`mart_url_performance` の粒度は `url_path × date` の集約なので、同じ理屈で OBT ではない。「star を持たない集約マート」と書けば §6 1 行目の引き当ても壊れない。
- **NM2. §8 が規約の「3〜5 行」を超えたまま（M2）。** C2 の書き直しで密度が上がったのは妥当なので、`news_pipeline` の 1 段落（L589）を 1 文に詰めるか、チュートリアルの種（L588）を 1 行に圧縮する。
- **NM3. Fowler の要約が Hightouch 経由であることが読み取れない（L167）。** 講演本体（動画）を直接引いたのか二次資料からかで確度が違う。参照文献に YouTube と Hightouch 2 が並んでいるので実害は小さいが、report 側に取得元を明記しておくと次回以降の検証が速い。

---

## 4. 総合判定

**REVISE**

- 初回 17 件: ADDRESSED 15 / NOT ADDRESSED 2（I7・M2）
- 新規: Critical 1（NI1: モデル単位 `+where` は効かない）／ Important 1（NI2: §1 と §6 の条件不整合と表の穴）／ Minor 3

Critical 3 件のうち C1・C2・C3 はいずれも実ファイル・実仕様に当たり直したうえで正しく直っている（特に C2 は `mart_url_performance_incremental.sql` を読んで結論ごと組み直しており、初回指摘より内容が良くなっている）。I1 の Fowler 復帰も帰属が正しい。残るのは **I7 の修正が dbt の仕様を外していること 1 点**で、ここだけ直せば通る。NI2 は表の並べ替えに伴う副作用なので、L57 の 1 行と §6 8 行目の条件文の調整で閉じる。
