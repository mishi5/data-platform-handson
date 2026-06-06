"""本文取得の結果から次の (content_status, retry_count) を決める純粋関数。

重い依存を持たず単体テストしやすい。content_status は "ok" / "pending" / "failed"。
"""


def next_fetch_state(ok: bool, retry_count: int, max_retries: int) -> tuple[str, int]:
    """本文取得結果から次状態を決める。

    ok=True  … 取得成功 → ("ok", retry_count)（カウント据え置き、本文の有無は問わない）
    ok=False … 失敗 → カウント +1。max 以上なら ("failed", n+1)、未満なら ("pending", n+1)
    """
    if ok:
        return "ok", retry_count
    new_count = retry_count + 1
    if new_count >= max_retries:
        return "failed", new_count
    return "pending", new_count
