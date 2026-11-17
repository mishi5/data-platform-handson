"""ダイジェストの原稿 HTML から、推敲の対象になる本文を Markdown に書き出す。

  uv run python scripts/digest/html2md.py --src digest_src.html --out original.md

yomiyasu（日本語の推敲スキル）の lint / check は Markdown・テキストを読むので、
原稿 HTML から自分で書いた本文だけを取り出して渡す。次は推敲の対象にしない:

  * 図（<svg>）・目次（<nav>）・コード（<pre>）・<style> / <head>
  * 「その他の記事」以降（list_view.py が要約から機械的に作った一覧）

強調（<strong>）は **…**、<code> は `…`、表は | 区切りの行にする。推敲は原稿 HTML を
直接直し、直したらもう一度書き出して検査に渡す（Markdown から HTML へは戻さない）。
"""

import argparse
import re
import sys
from html.parser import HTMLParser

_SKIP_TAGS = {"svg", "nav", "pre", "style", "head"}
# この見出しから後ろは機械生成の一覧なので推敲しない
_LIST_SECTION_MARK = '<h2 class="section" id="others">'


def _squash(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


class _Extractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.lines: list[str] = []
        self.skip = 0
        self.buf = ""
        self.prefix = ""
        self.cells: list[str] | None = None
        self.list_depth = 0

    def _flush(self) -> None:
        text = _squash(self.buf)
        if text:
            self.lines.append(self.prefix + text)
        self.buf = ""
        self.prefix = ""

    def handle_starttag(self, tag, attrs):
        if tag in _SKIP_TAGS:
            self.skip += 1
            return
        if self.skip:
            return
        if tag in ("p", "h1", "h2", "h3", "li", "tr"):
            self._flush()
        if tag in ("h1", "h2", "h3"):
            self.prefix = "#" * int(tag[1]) + " "
        elif tag == "li":
            self.prefix = "  " * max(self.list_depth - 1, 0) + "- "
        elif tag in ("ul", "ol"):
            self._flush()
            self.list_depth += 1
        elif tag == "tr":
            self.cells = []
        elif tag in ("td", "th"):
            self.buf = ""
        elif tag == "strong":
            self.buf += "**"
        elif tag == "code":
            self.buf += "`"

    def handle_endtag(self, tag):
        if tag in _SKIP_TAGS:
            self.skip -= 1
            return
        if self.skip:
            return
        if tag in ("td", "th") and self.cells is not None:
            self.cells.append(_squash(self.buf))
            self.buf = ""
        elif tag == "tr" and self.cells is not None:
            self.lines.append("| " + " | ".join(self.cells) + " |")
            self.cells = None
        elif tag in ("p", "h1", "h2", "h3", "li"):
            self._flush()
        elif tag in ("ul", "ol"):
            self._flush()
            self.list_depth -= 1
        elif tag == "strong":
            self.buf += "**"
        elif tag == "code":
            self.buf += "`"

    def handle_data(self, data):
        if not self.skip:
            self.buf += data


def extract(html: str) -> str:
    """原稿 HTML から推敲対象の本文を Markdown で返す。"""
    cut = html.find(_LIST_SECTION_MARK)
    if cut >= 0:
        html = html[:cut]
    parser = _Extractor()
    parser.feed(html)
    parser.close()
    parser._flush()

    out: list[str] = []
    for line in parser.lines:
        # 見出しと表の前に空行を入れる（表の行どうしは続ける）
        if line.startswith(("#", "|")) and out and not out[-1].startswith("|"):
            out.append("")
        out.append(line)
    return "\n".join(out) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--src", required=True, help="原稿 HTML")
    parser.add_argument("--out", required=True, help="書き出す Markdown")
    args = parser.parse_args()

    with open(args.src, encoding="utf-8") as f:
        md = extract(f.read())
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"{args.out} に本文を書き出しました（{len(md)} 文字）", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
