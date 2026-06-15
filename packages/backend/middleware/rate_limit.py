"""Simple in-memory rate limiting."""
from __future__ import annotations

import time
from collections import defaultdict


class RateLimiter:
    def __init__(self, max_calls: int = 60, period: float = 60.0) -> None:
        self._max_calls = max_calls
        self._period = period
        self._calls: dict[str, list[float]] = defaultdict(list)

    def is_allowed(self, key: str) -> bool:
        now = time.monotonic()
        window_start = now - self._period
        self._calls[key] = [t for t in self._calls[key] if t > window_start]
        if len(self._calls[key]) >= self._max_calls:
            return False
        self._calls[key].append(now)
        return True
