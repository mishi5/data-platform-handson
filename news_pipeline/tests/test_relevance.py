"""relevance.judge_relevance（TypeSafe Jev による関連度判定）のテスト。"""

import inspect
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "collector"))

from typesafe_sdk import TypeSafeClient  # noqa: E402

from collector import relevance  # noqa: E402


@pytest.fixture(autouse=True)
def _clear_client_cache():
    relevance._client.cache_clear()
    yield
    relevance._client.cache_clear()


def _response(noul: float) -> MagicMock:
    res = MagicMock()
    res.answers = {"data_platform": MagicMock(noul=noul)}
    return res


@patch("collector.relevance.TypeSafeClient")
def test_returns_noul_probability(mock_client_cls):
    mock_client_cls.return_value.system_one.return_value = _response(0.93)

    assert relevance.judge_relevance("dbt の増分モデル", "本文", "key") == 0.93


@patch("collector.relevance.TypeSafeClient")
def test_call_matches_sdk_signature(mock_client_cls):
    """モックは SDK の破壊的変更を検出できないため、記録した引数を実シグネチャに当てる。"""
    mock_client_cls.return_value.system_one.return_value = _response(0.5)

    relevance.judge_relevance("T", "body", "key")

    init_kwargs = mock_client_cls.call_args.kwargs
    inspect.signature(TypeSafeClient.__init__).bind(None, **init_kwargs)
    call = mock_client_cls.return_value.system_one.call_args
    inspect.signature(TypeSafeClient.system_one).bind(None, *call.args, **call.kwargs)
    assert init_kwargs["model"] == relevance.MODEL


@patch("collector.relevance.TypeSafeClient")
def test_body_is_truncated(mock_client_cls):
    """長い本文は無関係な文脈で判定がぶれるので冒頭だけ渡す。"""
    mock_client_cls.return_value.system_one.return_value = _response(0.5)

    relevance.judge_relevance("T", "あ" * 10000, "key")

    state = mock_client_cls.return_value.system_one.call_args.args[0]
    assert len(state["body"]) == relevance._MAX_BODY_CHARS


def test_state_without_body_uses_title_only():
    """スライドの1次フィルタは description が空のことが多く、タイトルだけで判定する。"""
    assert relevance.build_state("Title", "") == {"title": "Title"}


@patch("collector.relevance.TypeSafeClient")
def test_failure_returns_none(mock_client_cls):
    """失敗は None（呼び出し側で判定不能＝通す）。例外で収集全体を止めない。"""
    mock_client_cls.return_value.system_one.side_effect = RuntimeError("503")

    assert relevance.judge_relevance("T", "body", "key") is None


@patch("collector.relevance.TypeSafeClient")
def test_client_is_reused(mock_client_cls):
    mock_client_cls.return_value.system_one.return_value = _response(0.5)

    relevance.judge_relevance("T1", "b", "key")
    relevance.judge_relevance("T2", "b", "key")

    assert mock_client_cls.call_count == 1
