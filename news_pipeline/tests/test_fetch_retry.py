from collector.fetch_retry import next_fetch_state


def test_success_keeps_retry_count_and_sets_ok():
    assert next_fetch_state(ok=True, retry_count=0, max_retries=3) == ("ok", 0)


def test_success_on_pending_article_sets_ok():
    assert next_fetch_state(ok=True, retry_count=2, max_retries=3) == ("ok", 2)


def test_first_failure_becomes_pending():
    assert next_fetch_state(ok=False, retry_count=0, max_retries=3) == ("pending", 1)


def test_failure_below_max_stays_pending():
    assert next_fetch_state(ok=False, retry_count=1, max_retries=3) == ("pending", 2)


def test_failure_reaching_max_becomes_failed():
    assert next_fetch_state(ok=False, retry_count=2, max_retries=3) == ("failed", 3)


def test_failure_at_max_one_becomes_failed_immediately():
    assert next_fetch_state(ok=False, retry_count=0, max_retries=1) == ("failed", 1)
