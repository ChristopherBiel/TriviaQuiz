import time
from backend.utils.rate_limit import RateLimiter


def test_allows_under_limit():
    rl = RateLimiter(max_calls=3, window_seconds=60)
    assert rl.check_and_record("key") is True
    assert rl.check_and_record("key") is True
    assert rl.check_and_record("key") is True


def test_blocks_over_limit():
    rl = RateLimiter(max_calls=2, window_seconds=60)
    assert rl.check_and_record("key") is True
    assert rl.check_and_record("key") is True
    assert rl.check_and_record("key") is False


def test_separate_keys():
    rl = RateLimiter(max_calls=1, window_seconds=60)
    assert rl.check_and_record("a") is True
    assert rl.check_and_record("b") is True
    assert rl.check_and_record("a") is False


def test_remaining():
    rl = RateLimiter(max_calls=3, window_seconds=60)
    assert rl.remaining("key") == 3
    rl.record("key")
    assert rl.remaining("key") == 2


def test_window_expiry():
    rl = RateLimiter(max_calls=1, window_seconds=1)
    assert rl.check_and_record("key") is True
    assert rl.check_and_record("key") is False
    time.sleep(1.1)
    assert rl.check_and_record("key") is True


def test_is_allowed_does_not_consume():
    rl = RateLimiter(max_calls=1, window_seconds=60)
    assert rl.is_allowed("key") is True
    assert rl.is_allowed("key") is True  # still true — not consumed
    rl.record("key")
    assert rl.is_allowed("key") is False
