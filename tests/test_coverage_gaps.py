"""Tests targeting coverage gaps in client.py — optional params, throttle integration."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from aioresponses import aioresponses

from amazing_marvin.client import MarvinClient
from amazing_marvin.exceptions import MarvinRateLimitError

BASE = "https://serv.amazingmarvin.com/api"

TASK_PAYLOAD = {"_id": "t1", "title": "Test", "done": False}
CATEGORY_PAYLOAD = {"_id": "cat1", "title": "Work", "type": "project"}
EVENT_PAYLOAD = {"_id": "ev1", "title": "Meeting", "start": "2026-04-25T09:00:00Z"}
PROFILE_PAYLOAD = {"userId": "u1", "email": "user@example.com"}


@pytest.fixture
def mock_responses():
    with aioresponses() as m:
        yield m


# ---------------------------------------------------------------------------
# add_task — optional params coverage (lines 290-336)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_add_task_all_optional_params(mock_responses):
    """add_task with every optional param set — covers the body-building branches."""
    mock_responses.post(f"{BASE}/addTask", payload=TASK_PAYLOAD)
    async with MarvinClient(api_token="tok") as client:
        task = await client.add_task(
            "Buy milk",
            done=True,
            day="2026-04-25",
            parent_id="cat1",
            label_ids=["lb1"],
            due_date="2026-05-01",
            first_scheduled="2026-04-25",
            rank=3,
            daily_section="Morning",
            bonus_section="Bonus",
            custom_section="Custom",
            time_block_section="Block",
            note="Don't forget",
            time_estimate=1800000,
            is_reward=True,
            is_starred=2,
            is_frogged=1,
            planned_week="2026-W17",
            planned_month="2026-04",
            reward_points=5.0,
            reward_id="rwd1",
            backburner=True,
            review_date="2026-05-01",
            item_snooze_time=30,
            perma_snooze_time="09:00",
            auto_complete=False,
        )
    assert task._id == "t1"


# ---------------------------------------------------------------------------
# add_project — optional params coverage (lines 408-454)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_add_project_all_optional_params(mock_responses):
    """add_project with every optional param set — covers the body-building branches."""
    mock_responses.post(f"{BASE}/addProject", payload=CATEGORY_PAYLOAD)
    async with MarvinClient(api_token="tok") as client:
        cat = await client.add_project(
            "Big Project",
            done=True,
            day="2026-04-25",
            parent_id="cat0",
            label_ids=["lb1"],
            due_date="2026-06-01",
            first_scheduled="2026-04-25",
            rank=1,
            daily_section="Morning",
            bonus_section="Bonus",
            custom_section="Custom",
            time_block_section="Block",
            note="Important",
            time_estimate=3600000,
            is_reward=True,
            priority="high",
            is_frogged=1,
            planned_week="2026-W17",
            planned_month="2026-04",
            reward_points=10.0,
            reward_id="rwd2",
            backburner=True,
            review_date="2026-06-01",
            item_snooze_time=15,
            perma_snooze_time="10:00",
            auto_complete=False,
        )
    assert cat._id == "cat1"


# ---------------------------------------------------------------------------
# mark_done — done=False branch (line 361)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mark_done_undo(mock_responses):
    """mark_done(done=False) adds done=False to request body."""
    mock_responses.post(f"{BASE}/markDone", payload=TASK_PAYLOAD)
    async with MarvinClient(api_token="tok") as client:
        task = await client.mark_done("t1", done=False)
    assert task._id == "t1"


# ---------------------------------------------------------------------------
# add_event — optional note and length (lines 502, 504)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_add_event_with_note_and_length(mock_responses):
    """add_event with note and length — covers optional param branches."""
    mock_responses.post(f"{BASE}/addEvent", payload=EVENT_PAYLOAD)
    async with MarvinClient(api_token="tok") as client:
        ev = await client.add_event(
            "Standup", "2026-04-25T09:00:00Z", note="Daily sync", length=1800000
        )
    assert ev._id == "ev1"


# ---------------------------------------------------------------------------
# claim/unclaim/spend — optional date branches (lines 588, 590, 606, 622)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_claim_reward_points_with_item_and_date(mock_responses):
    """claim_reward_points with item_id and date — covers optional branches."""
    mock_responses.post(f"{BASE}/claimRewardPoints", payload=PROFILE_PAYLOAD)
    async with MarvinClient(api_token="tok") as client:
        profile = await client.claim_reward_points(5.0, item_id="t1", date="2026-04-25")
    assert profile.user_id == "u1"


@pytest.mark.asyncio
async def test_unclaim_reward_points_with_date(mock_responses):
    """unclaim_reward_points with date — covers optional branch."""
    mock_responses.post(f"{BASE}/unclaimRewardPoints", payload=PROFILE_PAYLOAD)
    async with MarvinClient(api_token="tok") as client:
        profile = await client.unclaim_reward_points(item_id="t1", date="2026-04-25")
    assert profile.user_id == "u1"


@pytest.mark.asyncio
async def test_spend_reward_points_with_date(mock_responses):
    """spend_reward_points with date — covers optional branch."""
    mock_responses.post(f"{BASE}/spendRewardPoints", payload=PROFILE_PAYLOAD)
    async with MarvinClient(api_token="tok") as client:
        profile = await client.spend_reward_points(3.0, date="2026-04-25")
    assert profile.user_id == "u1"


# ---------------------------------------------------------------------------
# update_habit — undo, history, time+value branches (lines 724, 726-727, 733)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_habit_undo(mock_responses):
    """update_habit with undo=True — covers the UNDO branch (line 724)."""
    mock_responses.post(f"{BASE}/updateHabit", payload=1)
    async with MarvinClient(api_token="tok") as client:
        result = await client.update_habit("h1", undo=True)
    assert result == 1


@pytest.mark.asyncio
async def test_update_habit_history_rewrite(mock_responses):
    """update_habit with history — covers REWRITE branch (lines 726-727)."""
    mock_responses.post(f"{BASE}/updateHabit", payload=1)
    async with MarvinClient(api_token="tok") as client:
        result = await client.update_habit("h1", history=[1700000000000, 1])
    assert result == 1


@pytest.mark.asyncio
async def test_update_habit_with_time_and_value(mock_responses):
    """update_habit with time and value — covers RECORD branch with time+value (line 733)."""
    mock_responses.post(f"{BASE}/updateHabit", payload=5)
    async with MarvinClient(api_token="tok") as client:
        result = await client.update_habit("h1", time=1700000000000, value=5)
    assert result == 5


# ---------------------------------------------------------------------------
# Throttle integration — _request calls throttler when throttle=True (line 116)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_throttle_integration_in_request(mock_responses):
    """When throttle=True, _request calls throttler.acquire before dispatching."""
    mock_responses.get(f"{BASE}/todayItems", payload=[])
    with patch("amazing_marvin._throttle._Throttler.acquire", new_callable=AsyncMock) as mock_acq:
        async with MarvinClient(api_token="tok", throttle=True) as client:
            await client.get_today_items()
        mock_acq.assert_called_once()


# ---------------------------------------------------------------------------
# Retry-After — non-numeric value falls back to None (lines 147-148)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_retry_after_non_numeric_value(mock_responses):
    """429 with non-numeric Retry-After header sets retry_after=None."""
    mock_responses.get(
        f"{BASE}/todayItems",
        status=429,
        headers={"Retry-After": "Wed, 01 Jan 2026 00:00:00 GMT"},
        payload={},
    )
    async with MarvinClient(api_token="tok") as client:
        with pytest.raises(MarvinRateLimitError) as exc_info:
            await client.get_today_items()
    assert exc_info.value.retry_after is None
    assert exc_info.value.daily_cap_exceeded is False
