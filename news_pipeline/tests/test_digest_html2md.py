"""scripts/digest/html2md.py のテスト。"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts", "digest"))

import html2md


def test_extract_skips_svg_nav_pre_and_generated_list():
    html = """
    <nav><ol><li>目次</li></ol></nav>
    <p>本文<strong>強調</strong>と<code>id</code>。</p>
    <svg><text>図のラベル</text></svg>
    <pre><code>x = 1</code></pre>
    <h2 class="section" id="others">その他の記事</h2>
    <ul class="brief"><li>一覧の記事</li></ul>
    """

    md = html2md.extract(html)

    assert "本文**強調**と`id`。" in md
    for absent in ("目次", "図のラベル", "x = 1", "一覧の記事", "その他の記事"):
        assert absent not in md


def test_extract_keeps_headings_lists_and_tables():
    html = """
    <h3>要点</h3>
    <ul><li>一つ目<ul><li>入れ子</li></ul></li><li>二つ目</li></ul>
    <table><tr><th>列A</th><th>列B</th></tr><tr><td>1</td><td>2</td></tr></table>
    """

    md = html2md.extract(html)

    assert "### 要点" in md
    assert "- 一つ目" in md
    assert "  - 入れ子" in md
    assert "- 二つ目" in md
    assert "| 列A | 列B |\n| 1 | 2 |" in md


def test_extract_decodes_entities():
    md = html2md.extract("<p>A &amp; B &gt; C</p>")

    assert "A & B > C" in md
