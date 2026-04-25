"""Tests for FR-009/010/011/012 — rate limiter (T022)."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from aioresponses import aioresponses

from amazing_marvin._throttle import BURST_INTERVAL, DAILY_CAP, _Throttler, _local_date
from amazing_marvin.client import MarvinClient
from amazing_marvin.exceptions import MarvinRateLimitError

BASE = "https://serv.amazingmarvin.com/api"


@pytest.fixture
def mock_responses():
    with aioresponses() as m:
        yield m


# ---------------------------------------------------------------------------
# Burst enforcement
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_burst_enforcement_sleeps_between_calls():
    """5 sequential acquire() calls each sleep (burst interval enforced between requests).

    acquire() reads time.monotonic() twice: once to compute wait, once to stamp last_request_at.
    We supply values so every wait computation yields wait > 0.
    """
    throttler = _Throttler()
    # 10 values: pairs of (wait_read, stamp_read) for each of the 5 calls
    # Each wait_read is just below last_stamp + BURST_INTERVAL, ensuring wait > 0
    mono_sequence = [
        0.0, 3.1,    # call 0: wait=0+3-0=3>0, stamp=3.1
        4.0, 7.2,    # call 1: wait=3.1+3-4.0=2.1>0, stamp=7.2
        8.0, 11.3,   # call 2: wait=7.2+3-8.0=2.2>0, stamp=11.3
        12.0, 15.4,  # call 3: wait=11.3+3-12.0=2.3>0, stamp=15.4
        16.0, 19.5,  # call 4: wait=15.4+3-16.0=2.4>0, stamp=19.5
    ]
    mono_iter = iter(mono_sequence)

    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        with patch("time.monotonic", side_effect=lambda: next(mono_iter)):
            for _ in range(5):
                await throttler.acquire(0)

    assert mock_sleep.call_count == 5


@pytest.mark.asyncio
async def test_burst_first_call_free_when_no_prior_request():
    """When _last_request_at=0 and monotonic is well past BURST_INTERVAL, no sleep on first call."""
    throttler = _Throttler()
    # Simulate that we're 10 seconds in — last_request was at 0, now is 10
    # wait = 0.0 + 3.0 - 10.0 = -7.0 -> max(0, -7) = 0 -> no sleep
    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        with patch("time.monotonic", return_value=10.0):
            await throttler.acquire(0)
    mock_sleep.assert_not_called()


# ---------------------------------------------------------------------------
# Daily cap
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_daily_cap_raises_after_1440():
    """After 1440 acquire() calls, the 1441st raises MarvinRateLimitError(daily_cap_exceeded=True)."""
    throttler = _Throttler()
    # Patch monotonic to advance time so no burst sleeping interferes
    counter = [0]

    def monotonic_side():
        val = counter[0] * BURST_INTERVAL + 100.0
        counter[0] += 1
        return val

    with patch("time.monotonic", side_effect=monotonic_side):
        with patch("asyncio.sleep", new_callable=AsyncMock):
            for _ in range(DAILY_CAP):
                await throttler.acquire(0)

            with pytest.raises(MarvinRateLimitError) as exc_info:
                await throttler.acquire(0)

    assert exc_info.value.daily_cap_exceeded is True


# ---------------------------------------------------------------------------
# Daily rollover
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_daily_rollover_resets_counter():
    """After 1440 calls on one date, changing the date resets the counter."""
    throttler = _Throttler()
    counter = [0]

    def monotonic_side():
        val = counter[0] * BURST_INTERVAL + 100.0
        counter[0] += 1
        return val

    with patch("time.monotonic", side_effect=monotonic_side):
        with patch("asyncio.sleep", new_callable=AsyncMock):
            # Fill up day "2026-04-25"
            with patch("amazing_marvin._throttle._local_date", return_value="2026-04-25"):
                for _ in range(DAILY_CAP):
                    await throttler.acquire(0)
                # 1441st on same day should fail
                with pytest.raises(MarvinRateLimitError):
                    await throttler.acquire(0)

            # Now change date to "2026-04-26" — counter should reset
            with patch("amazing_marvin._throttle._local_date", return_value="2026-04-26"):
                # Should succeed without error
                await throttler.acquire(0)

    assert throttler._daily_count == 1
    assert throttler._daily_date == "2026-04-26"


# ---------------------------------------------------------------------------
# Concurrent safety
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_concurrent_acquires_run_sequentially():
    """5 concurrent acquire() calls complete sequentially (each gets the lock)."""
    throttler = _Throttler()
    order: list[int] = []
    counter = [0]

    def monotonic_side():
        val = counter[0] * BURST_INTERVAL + 100.0
        counter[0] += 1
        return val

    async def acquire_and_record(i: int) -> None:
        await throttler.acquire(0)
        order.append(i)

    with patch("time.monotonic", side_effect=monotonic_side):
        with patch("asyncio.sleep", new_callable=AsyncMock):
            await asyncio.gather(*[acquire_and_record(i) for i in range(5)])

    # All 5 completed
    assert len(order) == 5
    # Daily count advanced by 5
    assert throttler._daily_count == 5


# ---------------------------------------------------------------------------
# throttle=False — 429 raises immediately without sleeping
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_throttle_false_429_raises_immediately(mock_responses):
    """throttle=False: a 429 response raises MarvinRateLimitError(retry_after=5.0) immediately."""
    mock_responses.post(f"{BASE}/test", status=429, headers={"Retry-After": "5"})

    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        async with MarvinClient(api_token="tok", throttle=False) as client:
            with pytest.raises(MarvinRateLimitError) as exc_info:
                await client.test_credentials()

    assert exc_info.value.retry_after == 5.0
    mock_sleep.assert_not_called()
