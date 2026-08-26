"""モックが記録した kwargs を実 SDK のシグネチャに突き合わせるヘルパー。

Anthropic クライアントを丸ごとモックするテストは、SDK の破壊的変更を
検出できない。実際 anthropic 0.43.0 → 1.0.0 で `temperature` が
messages.create() から削除されたが、モックはそれを黙って受け入れ、
全テストが通ったまま本番だけが TypeError で落ちる状態だった。
"""

import inspect

from anthropic.resources.messages import Messages


def assert_matches_sdk_signature(call_kwargs: dict) -> None:
    """kwargs が anthropic.messages.create の実シグネチャに適合することを検証する。"""
    inspect.signature(Messages.create).bind_partial(None, **call_kwargs)
