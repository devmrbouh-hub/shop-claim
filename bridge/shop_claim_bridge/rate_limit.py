"""Simple in-memory rate limiter for Bridge HTTP."""

from __future__ import annotations

import time
from collections import defaultdict


class RateLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, list[float]] = defaultdict(list)

    def allow(self, key: str, *, max_events: int, window_sec: float) -> bool:
        now = time.monotonic()
        window_start = now - window_sec
        hits = [t for t in self._hits[key] if t >= window_start]
        if len(hits) >= max_events:
            self._hits[key] = hits
            return False
        hits.append(now)
        self._hits[key] = hits
        return True

    def reset(self) -> None:
        self._hits.clear()


rate_limiter = RateLimiter()
