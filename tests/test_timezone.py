"""Tests for FR-013/014/015 and SC-007 — timezone handling (T014 + T038)."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from aioresponses import aioresponses
from yarl import URL

from amazing_marvin.client import MarvinClient

BASE = "https://serv.amazingmarvin.com/api"


@pytest.fixture
def mock_responses():
    with aioresponses() as m:
        yield m


def _make_utc_datetime(year, month, day, hour, minute, second=0):
    """Helper to build a UTC-aware datetime."""
    return datetime(year, month, day, hour, minute, second, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Basic UTC (tz_offset=0)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_today_items_utc_sends_today_date(mock_responses):
    """get_today_items() with tz_offset=0 sends today's UTC date as X-Date header."""
    # Fix UTC "now" to 2026-04-25 12:00:00 UTC
    fixed_utc = _make_utc_datetime(2026, 4, 25, 12, 0)
    mock_responses.get(f"{BASE}/todayItems", payload=[])

    with patch("amazing_marvin._throttle.datetime") as mock_dt:
        mock_dt.now.return_value = fixed_utc
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)

        async with MarvinClient(api_token="tok", tz_offset=0) as client:
            await client.get_today_items()

    calls = list(mock_responses.requests.get(("GET", URL(f"{BASE}/todayItems")), []))
    assert len(calls) == 1
    sent_headers = calls[0].kwargs.get("headers", {})
    assert sent_headers.get("X-Date") == "2026-04-25"


# ---------------------------------------------------------------------------
# Negative offset — previous day at 23:30 UTC
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_today_items_negative_offset_previous_day(mock_responses):
    """get_today_items(tz_offset=-300) sends previous day when UTC time is 23:30."""
    # 23:30 UTC + (-300 min) = 23:30 - 5:00 = 18:30 local — still 2026-04-24 locally
    fixed_utc = _make_utc_datetime(2026, 4, 25, 23, 30)
    mock_responses.get(f"{BASE}/todayItems", payload=[])

    with patch("amazing_marvin._throttle.datetime") as mock_dt:
        mock_dt.now.return_value = fixed_utc
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)

        async with MarvinClient(api_token="tok") as client:
            await client.get_today_items(tz_offset=-300)

    calls = list(mock_responses.requests.get(("GET", URL(f"{BASE}/todayItems")), []))
    sent_headers = calls[0].kwargs.get("headers", {})
    assert sent_headers.get("X-Date") == "2026-04-25"  # 23:30 - 300min = 18:30, still Apr 25


@pytest.mark.asyncio
async def test_get_today_items_negative_offset_crosses_midnight(mock_responses):
    """tz_offset=-300 at 02:30 UTC means local time is previous day (Apr 24)."""
    # 02:30 UTC + (-300 min) = 02:30 - 5:00 = -2:30 = previous day 21:30 local
    fixed_utc = _make_utc_datetime(2026, 4, 25, 2, 30)
    mock_responses.get(f"{BASE}/todayItems", payload=[])

    with patch("amazing_marvin._throttle.datetime") as mock_dt:
        mock_dt.now.return_value = fixed_utc
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)

        async with MarvinClient(api_token="tok") as client:
            await client.get_today_items(tz_offset=-300)

    calls = list(mock_responses.requests.get(("GET", URL(f"{BASE}/todayItems")), []))
    sent_headers = calls[0].kwargs.get("headers", {})
    assert sent_headers.get("X-Date") == "2026-04-24"  # 02:30 - 300min = previous day


# ---------------------------------------------------------------------------
# Per-call override does NOT mutate client._tz_offset
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_per_call_tz_override_does_not_mutate_client(mock_responses):
    """Per-call tz_offset override does NOT mutate client._tz_offset."""
    mock_responses.get(f"{BASE}/todayItems", payload=[])

    async with MarvinClient(api_token="tok", tz_offset=0) as client:
        original_tz = client._tz_offset
        await client.get_today_items(tz_offset=330)
        assert client._tz_offset == original_tz == 0


# ---------------------------------------------------------------------------
# Positive offset — next day when UTC time is 23:00
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_today_items_positive_offset_next_day(mock_responses):
    """get_today_items(tz_offset=840) sends NEXT day when UTC time is 23:00."""
    # 23:00 UTC + 840 min (14h) = 37:00 = next day 13:00 local
    fixed_utc = _make_utc_datetime(2026, 4, 25, 23, 0)
    mock_responses.get(f"{BASE}/todayItems", payload=[])

    with patch("amazing_marvin._throttle.datetime") as mock_dt:
        mock_dt.now.return_value = fixed_utc
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)

        async with MarvinClient(api_token="tok") as client:
            await client.get_today_items(tz_offset=840)

    calls = list(mock_responses.requests.get(("GET", URL(f"{BASE}/todayItems")), []))
    sent_headers = calls[0].kwargs.get("headers", {})
    assert sent_headers.get("X-Date") == "2026-04-26"


# ---------------------------------------------------------------------------
# SC-007: Parametrised — midnight boundary flip
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "tz_offset,utc_hour,utc_minute,expected_date",
    [
        # tz_offset=-720 (UTC-12): local = UTC - 720min
        # At 23:59 UTC (T-1s of local midnight for UTC+12), local is still Apr 24
        (-720, 11, 59, "2026-04-24"),  # 11:59 UTC - 720min = -0:01 = Apr 24 23:59
        (-720, 12, 1, "2026-04-25"),   # 12:01 UTC - 720min = 00:01 local = Apr 25
        # tz_offset=-300 (UTC-5): local = UTC - 300min
        (-300, 4, 59, "2026-04-24"),   # 04:59 UTC - 300min = -0:01 = Apr 24 23:59
        (-300, 5, 1, "2026-04-25"),    # 05:01 UTC - 300min = 00:01 = Apr 25
        # tz_offset=0 (UTC): local = UTC
        (0, 23, 59, "2026-04-25"),     # 23:59 UTC = Apr 25
        (0, 0, 1, "2026-04-25"),       # 00:01 UTC = Apr 25
        # tz_offset=330 (UTC+5:30): local = UTC + 330min
        (330, 18, 29, "2026-04-25"),   # 18:29 + 330min = 23:59 = Apr 25
        (330, 18, 31, "2026-04-26"),   # 18:31 + 330min = 00:01 = Apr 26
        # tz_offset=540 (UTC+9): local = UTC + 540min
        (540, 14, 59, "2026-04-25"),   # 14:59 + 540min = 23:59 = Apr 25
        (540, 15, 1, "2026-04-26"),    # 15:01 + 540min = 00:01 = Apr 26
        # tz_offset=840 (UTC+14): local = UTC + 840min
        (840, 9, 59, "2026-04-25"),    # 09:59 + 840min = 23:59 = Apr 25
        (840, 10, 1, "2026-04-26"),    # 10:01 + 840min = 00:01 = Apr 26
    ],
)
async def test_sc007_midnight_boundary_flip(
    mock_responses, tz_offset, utc_hour, utc_minute, expected_date
):
    """SC-007: At T-1s and T+1s of local midnight, 'today' flips correctly."""
    fixed_utc = _make_utc_datetime(2026, 4, 25, utc_hour, utc_minute)
    mock_responses.get(f"{BASE}/todayItems", payload=[])

    with patch("amazing_marvin._throttle.datetime") as mock_dt:
        mock_dt.now.return_value = fixed_utc
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)

        async with MarvinClient(api_token="tok") as client:
            await client.get_today_items(tz_offset=tz_offset)

    calls = list(mock_responses.requests.get(("GET", URL(f"{BASE}/todayItems")), []))
    sent_headers = calls[0].kwargs.get("headers", {})
    assert sent_headers.get("X-Date") == expected_date, (
        f"tz_offset={tz_offset}, UTC={utc_hour:02d}:{utc_minute:02d} "
        f"-> expected {expected_date}, got {sent_headers.get('X-Date')}"
    )
