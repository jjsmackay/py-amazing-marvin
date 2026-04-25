"""Internal asyncio-based rate limiter for the Amazing Marvin API."""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timedelta, timezone

from amazing_marvin.exceptions import MarvinRateLimitError

BURST_INTERVAL = 3.0
DAILY_CAP = 1440


def _local_date(tz_offset: int) -> str:
    """Return the local date as YYYY-MM-DD given tz_offset in minutes east of UTC."""
    return (datetime.now(timezone.utc) + timedelta(minutes=tz_offset)).date().isoformat()


class _Throttler:
    """Enforces Marvin's 1-req/3-s burst and 1440/day limits across coroutines."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._last_request_at: float = 0.0
        self._daily_count: int = 0
        self._daily_date: str = ""

    async def acquire(self, tz_offset: int = 0) -> None:
        async with self._lock:
            today = _local_date(tz_offset)
            if today != self._daily_date:
                self._daily_count = 0
                self._daily_date = today
            if self._daily_count >= DAILY_CAP:
                raise MarvinRateLimitError(
                    "Daily request cap (1440) reached",
                    daily_cap_exceeded=True,
                )
            wait = max(0.0, self._last_request_at + BURST_INTERVAL - time.monotonic())
            if wait > 0:
                await asyncio.sleep(wait)
            self._last_request_at = time.monotonic()
            self._daily_count += 1
