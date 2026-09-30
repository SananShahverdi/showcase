"""Utility helpers for the OCW Smart Scraper."""

from __future__ import annotations

import threading
import time


class RateLimiter:
    """Simple token bucket rate limiter for polite scraping."""

    def __init__(self, calls_per_second: float) -> None:
        self.interval = 1.0 / max(calls_per_second, 0.1)
        self._lock = threading.Lock()
        self._last_call = 0.0

    def wait(self) -> None:
        with self._lock:
            now = time.time()
            elapsed = now - self._last_call
            if elapsed < self.interval:
                time.sleep(self.interval - elapsed)
            self._last_call = time.time()
