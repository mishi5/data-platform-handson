"""ダイジェストの原稿 HTML から公開用 HTML を組み立てる。

  uv run python scripts/digest/assemble.py --src digest_src.html \
      --list list_frag.html --out digest.html

原稿には次の2種類のプレースホルダを書く:

  <!--SVG-HEAD:dg-xx-->  図の <svg id="dg-xx"> の直後に置く。id でスコープした
                         <style>（ライト/ダーク3系統の色トークンと共通クラス）と
                         矢印の <marker> 定義に置き換える
  <!--LIST-->            list_view.py html が出した一覧の断片に置き換える

図ごとに同じ 40 行の style を手で書くと、色の直し忘れや id の前置漏れが起きる。
クラス名と色トークンは svg-diagram スキルの骨格に合わせてある。
"""

import argparse
import re
import sys

LIGHT = (
    "--paper:#fbfbfa;--ink:#22262e;--muted:#5b6472;--soft:#828b9a;"
    "--rule:rgba(34,38,46,.14);--accent:#c8571d;--tint:rgba(200,87,29,.10);"
)
DARK = (
    "--paper:#1a1d23;--ink:#e9ecf1;--muted:#a6afbd;--soft:#7f8898;"
    "--rule:rgba(233,236,241,.18);--accent:#f0894f;--tint:rgba(240,137,79,.14);"
)
_FONTS = (
    '--sans:system-ui,-apple-system,"Hiragino Sans","Noto Sans JP","Yu Gothic UI",Meiryo,sans-serif;'
    "--mono:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;"
)
# 共通クラス。.sub は日本語のサブラベル（sans 11px）、.subm は識別子・パス（mono 11px）。
# .em は accent 色の強調ラベル、.link は矢印なしの関係線、.life はシーケンス図のライフライン。
_CLASSES = """
    #{i} .bg{{fill:var(--paper)}}
    #{i} .box{{fill:var(--paper);stroke:var(--ink);stroke-width:1}}
    #{i} .box-soft{{fill:var(--paper);stroke:var(--rule);stroke-width:1}}
    #{i} .box-focal{{fill:var(--tint);stroke:var(--accent);stroke-width:1.4}}
    #{i} .zone{{fill:none;stroke:var(--rule);stroke-width:1;stroke-dasharray:4 3}}
    #{i} .life{{fill:none;stroke:var(--rule);stroke-width:1.2;stroke-dasharray:4 4}}
    #{i} .name{{fill:var(--ink);font:600 14px var(--sans)}}
    #{i} .code{{fill:var(--ink);font:600 15px var(--mono)}}
    #{i} .sub{{fill:var(--muted);font:400 11px var(--sans)}}
    #{i} .subm{{fill:var(--muted);font:400 11px var(--mono)}}
    #{i} .tag{{fill:var(--soft);font:500 10px var(--mono);letter-spacing:.12em}}
    #{i} .em{{fill:var(--accent);font:600 11px var(--sans)}}
    #{i} .lead{{fill:none;stroke:var(--muted);stroke-width:1.4;marker-end:url(#{i}-a)}}
    #{i} .lead-focal{{fill:none;stroke:var(--accent);stroke-width:1.8;marker-end:url(#{i}-af)}}
    #{i} .link{{fill:none;stroke:var(--muted);stroke-width:1.4}}
    #{i} .dash{{stroke-dasharray:5 4}}
    #{i} .mask{{fill:var(--paper)}}
    #{i} .mk{{fill:var(--muted)}} #{i} .mkf{{fill:var(--accent)}}"""

_HEAD_RE = re.compile(r"<!--SVG-HEAD:([A-Za-z][\w-]*)-->")
_LIST_MARK = "<!--LIST-->"


def svg_head(svg_id: str) -> str:
    """図1枚分の <style> と <defs> を返す。全セレクタと marker id を svg_id で前置する。"""
    i = svg_id
    return (
        "<style>\n"
        f"    #{i}{{{LIGHT}{_FONTS}}}\n"
        f"    @media (prefers-color-scheme:dark){{ #{i}{{{DARK}}} }}\n"
        f'    :root[data-theme="dark"] #{i}{{{DARK}}}\n'
        f'    :root[data-theme="light"] #{i}{{{LIGHT}}}'
        + _CLASSES.format(i=i)
        + "\n  </style>\n  <defs>\n"
        f'    <marker id="{i}-a" markerWidth="9" markerHeight="7" refX="8" refY="3.5" orient="auto">'
        '<path class="mk" d="M0,0 L9,3.5 L0,7 Z"/></marker>\n'
        f'    <marker id="{i}-af" markerWidth="9" markerHeight="7" refX="8" refY="3.5" orient="auto">'
        '<path class="mkf" d="M0,0 L9,3.5 L0,7 Z"/></marker>\n'
        "  </defs>"
    )


def assemble(src: str, list_fragment: str | None) -> str:
    """プレースホルダを展開する。不整合は例外にする（気づかずに公開しないため）。"""
    ids = _HEAD_RE.findall(src)
    dup = sorted({i for i in ids if ids.count(i) > 1})
    if dup:
        raise ValueError(f"SVG-HEAD の id が重複しています: {', '.join(dup)}")
    for i in ids:
        if f'id="{i}"' not in src:
            raise ValueError(f'SVG-HEAD:{i} に対応する <svg id="{i}"> がありません')

    out = _HEAD_RE.sub(lambda m: svg_head(m.group(1)), src)

    n_list = out.count(_LIST_MARK)
    if list_fragment is None:
        if n_list:
            raise ValueError(
                "原稿に <!--LIST--> がありますが --list が指定されていません"
            )
        return out
    if n_list != 1:
        raise ValueError(f"<!--LIST--> は1か所だけ置いてください（{n_list} か所）")
    return out.replace(_LIST_MARK, list_fragment)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--src", required=True, help="プレースホルダ入りの原稿 HTML")
    parser.add_argument("--list", default=None, help="list_view.py html の出力")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    with open(args.src, encoding="utf-8") as f:
        src = f.read()
    fragment = None
    if args.list:
        with open(args.list, encoding="utf-8") as f:
            fragment = f.read()
    try:
        html = assemble(src, fragment)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 1
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(html)
    print(
        f"{args.out} を出力しました（{len(html.encode('utf-8'))} bytes）",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
