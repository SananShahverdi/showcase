import time

from ocw_smart_scraper.utils import RateLimiter


def test_rate_limiter_enforces_interval() -> None:
    limiter = RateLimiter(5)  # 0.2s interval
    start = time.time()
    limiter.wait()
    limiter.wait()
    assert time.time() - start >= 0.2
