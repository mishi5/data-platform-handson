"""release_notes モジュール（Google Cloud リリースノートの日付単位の本文取得）のテスト。"""

from unittest.mock import MagicMock

from collector.release_notes import (
    extract_section,
    fetch_release_note,
    is_release_notes_url,
)

_URL = "https://docs.cloud.google.com/bigquery/docs/release-notes#September_24_2026"

# 実ページ（docs.cloud.google.com/bigquery/docs/release-notes）の構造を縮めたもの
_PAGE = """
<html><body>
<section class="intro"><p>To get the latest product updates delivered to you,
add the URL of this page to your feed reader.</p></section>
<section class="releases">
<h2 id="September_24_2026" data-text="September 24, 2026">September 24, 2026</h2>
    <div class="devsite-release-note">
      <span class="devsite-label devsite-label-release-feature">Feature</span>
      <div><p>The <strong>Query results</strong> table now keeps
the row numbers visible.</p></div>
    </div>
    <div class="devsite-release-note">
      <span class="devsite-label devsite-label-release-change">Change</span>
      <div><p>Quota for jobs&#39; metadata was raised.</p></div>
    </div>
<h2 id="September_22_2026" data-text="September 22, 2026">September 22, 2026</h2>
    <div class="devsite-release-note">
      <span class="devsite-label devsite-label-release-feature">Feature</span>
      <div><p>You can now publish a BigQuery data agent.</p></div>
    </div>
</section>
<footer>Last updated 2026-09-24</footer>
</body></html>
"""


def test_is_release_notes_url_true():
    assert is_release_notes_url(_URL)


def test_is_release_notes_url_true_for_legacy_host():
    assert is_release_notes_url(
        "https://cloud.google.com/dataform/docs/release-notes#August_1_2026"
    )


def test_is_release_notes_url_false_without_fragment():
    # アンカーが無いとページ全体になり日付単位の記事として扱えない
    assert not is_release_notes_url(
        "https://docs.cloud.google.com/bigquery/docs/release-notes"
    )


def test_is_release_notes_url_false_for_other_page():
    assert not is_release_notes_url(
        "https://cloud.google.com/blog/products/data-analytics/x#section"
    )


def test_is_release_notes_url_false_for_other_host():
    assert not is_release_notes_url("https://example.com/docs/release-notes#May_1")


def test_extract_section_returns_only_that_day():
    text = extract_section(_PAGE, "September_24_2026")
    assert text is not None
    assert "row numbers visible" in text
    assert "Quota for jobs' metadata" in text
    assert "Feature" in text and "Change" in text
    # 次の日付・ページ外の要素は含めない
    assert "data agent" not in text
    assert "September 22" not in text
    assert "feed reader" not in text


def test_extract_section_last_day_stops_at_section_end():
    text = extract_section(_PAGE, "September_22_2026")
    assert text is not None
    assert "data agent" in text
    assert "Last updated" not in text


def test_extract_section_missing_anchor_returns_none():
    assert extract_section(_PAGE, "January_1_2020") is None


def test_fetch_release_note_returns_section(mocker):
    resp = MagicMock()
    resp.text = _PAGE
    resp.raise_for_status.return_value = None
    mock_get = mocker.patch("collector.release_notes.requests.get", return_value=resp)

    text, ok = fetch_release_note(_URL)

    assert ok is True
    assert text is not None and "row numbers visible" in text
    # ページの取得はアンカーを除いた URL で、タイムアウト付き
    assert mock_get.call_args.args[0] == (
        "https://docs.cloud.google.com/bigquery/docs/release-notes"
    )
    assert mock_get.call_args.kwargs.get("timeout") is not None


def test_fetch_release_note_missing_anchor_is_skip(mocker):
    # アンカーが消えた（ページの改訂など）場合は再取得しても戻らないのでスキップ
    resp = MagicMock()
    resp.text = _PAGE
    resp.raise_for_status.return_value = None
    mocker.patch("collector.release_notes.requests.get", return_value=resp)

    text, ok = fetch_release_note(
        "https://docs.cloud.google.com/bigquery/docs/release-notes#January_1_2020"
    )
    assert (text, ok) == (None, True)


def test_fetch_release_note_network_error_is_retry(mocker):
    mocker.patch(
        "collector.release_notes.requests.get", side_effect=Exception("timeout")
    )
    text, ok = fetch_release_note(_URL)
    assert (text, ok) == (None, False)
