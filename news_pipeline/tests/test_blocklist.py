from collector.blocklist import extract_user, is_blocked


def test_extract_user_path1_default_empty_location():
    url = "https://zenn.dev/web_benriya/articles/abc"
    assert extract_user(url, "") == "web_benriya"


def test_extract_user_path1_explicit():
    url = "https://zenn.dev/web_benriya/articles/abc"
    assert extract_user(url, "path1") == "web_benriya"


def test_extract_user_subdomain():
    url = "https://taro.hatenablog.com/entry/2026/06/18/foo"
    assert extract_user(url, "subdomain") == "taro"


def test_extract_user_path2():
    url = "https://example.com/tech/author_x/posts/1"
    assert extract_user(url, "path2") == "author_x"


def test_extract_user_missing_segment_returns_none():
    assert extract_user("https://zenn.dev/", "path1") is None
    assert extract_user("https://zenn.dev/onlyone", "path2") is None


def test_extract_user_unknown_location_returns_none():
    assert extract_user("https://zenn.dev/web_benriya/x", "bogus") is None


def test_is_blocked_exact_match():
    url = "https://zenn.dev/web_benriya/articles/abc"
    assert is_blocked(url, {"web_benriya"}, "path1") is True


def test_is_blocked_no_partial_match():
    # web_benriya2 は別ユーザー: 部分一致で誤ブロックしない
    url = "https://zenn.dev/web_benriya2/articles/abc"
    assert is_blocked(url, {"web_benriya"}, "path1") is False


def test_is_blocked_empty_users():
    url = "https://zenn.dev/web_benriya/articles/abc"
    assert is_blocked(url, set(), "path1") is False


def test_is_blocked_extract_none():
    assert is_blocked("https://zenn.dev/", {"web_benriya"}, "path1") is False
