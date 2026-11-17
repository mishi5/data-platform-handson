"""scripts/digest/assemble.py のテスト。"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts", "digest"))

import assemble


def test_svg_head_scopes_every_selector_and_marker():
    head = assemble.svg_head("dg-a")

    assert 'id="dg-a-a"' in head and 'id="dg-a-af"' in head
    assert "url(#dg-a-a)" in head
    assert ":root{" not in head  # 色トークンをページ全体に漏らさない
    assert "prefers-color-scheme:dark" in head
    assert ':root[data-theme="dark"] #dg-a' in head
    assert ':root[data-theme="light"] #dg-a' in head


def test_assemble_expands_heads_and_list():
    src = '<svg id="dg-a"><!--SVG-HEAD:dg-a--></svg><svg id="dg-b"><!--SVG-HEAD:dg-b--></svg><!--LIST-->'

    out = assemble.assemble(src, "<ul>LIST</ul>")

    assert "<!--" not in out
    assert "#dg-b .box" in out
    assert "<ul>LIST</ul>" in out


def test_head_without_matching_svg_is_rejected():
    with pytest.raises(ValueError, match="dg-x"):
        assemble.assemble('<svg id="dg-a"><!--SVG-HEAD:dg-x--></svg>', None)


def test_duplicate_head_id_is_rejected():
    src = '<svg id="dg-a"><!--SVG-HEAD:dg-a--></svg><svg id="dg-a"><!--SVG-HEAD:dg-a--></svg>'
    with pytest.raises(ValueError, match="重複"):
        assemble.assemble(src, None)


def test_list_placeholder_without_fragment_is_rejected():
    with pytest.raises(ValueError, match="LIST"):
        assemble.assemble("<p><!--LIST--></p>", None)
