"""Tests for FR-018/019 — endpoint coverage and model parsing (T025)."""

from __future__ import annotations

import pytest
from aioresponses import aioresponses

from amazing_marvin.client import MarvinClient
from amazing_marvin.models import (
    AccountProfile,
    CalendarEvent,
    Category,
    Goal,
    Habit,
    Kudos,
    Label,
    MarvinDocument,
    Reminder,
    Task,
    TimeBlock,
    TimeTrack,
    TrackingResult,
)

BASE = "https://serv.amazingmarvin.com/api"

# ---------------------------------------------------------------------------
# Sample payloads
# ---------------------------------------------------------------------------

TASK_PAYLOAD = {"_id": "t1", "title": "Test task", "done": False}
CATEGORY_PAYLOAD = {"_id": "cat1", "title": "Work", "type": "project"}
LABEL_PAYLOAD = {"_id": "lb1", "title": "Urgent"}
EVENT_PAYLOAD = {"_id": "ev1", "title": "Meeting", "start": "2026-04-25T09:00:00Z"}
TIME_BLOCK_PAYLOAD = {"_id": "tb1", "title": "Morning", "date": "2026-04-25", "time": "09:00"}
TRACKING_PAYLOAD = {"startId": "t1", "startTimes": [1700000000000]}
TIME_TRACK_PAYLOAD = {"taskId": "t1", "times": [1700000000000, 1700010000000]}
KUDOS_PAYLOAD = {"kudos": 50, "level": 3, "kudosRemaining": 100}
PROFILE_PAYLOAD = {"userId": "u1", "email": "user@example.com"}
GOAL_PAYLOAD = {"_id": "g1", "title": "Get fit", "sections": []}
HABIT_PAYLOAD = {"_id": "h1", "title": "Meditate"}
REMINDER_PAYLOAD = {"reminderId": "r1", "time": 1700000000, "title": "Take meds"}
DOC_PAYLOAD = {"_id": "doc1", "_rev": "1-abc", "db": "Tasks"}


@pytest.fixture
def mock_responses():
    with aioresponses() as m:
        yield m


# ---------------------------------------------------------------------------
# Test & Health
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_test_credentials(mock_responses):
    """POST /test — returns True when server responds OK."""
    mock_responses.post(f"{BASE}/test", payload="OK")
    async with MarvinClient(api_token="tok") as client:
        result = await client.test_credentials()
    assert result is True


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_today_items(mock_responses):
    """GET /todayItems — returns list[Task]."""
    mock_responses.get(f"{BASE}/todayItems", payload=[TASK_PAYLOAD])
    async with MarvinClient(api_token="tok") as client:
        tasks = await client.get_today_items()
    assert len(tasks) == 1
    assert isinstance(tasks[0], Task)
    assert tasks[0]._id == "t1"


@pytest.mark.asyncio
async def test_get_due_items(mock_responses):
    """GET /dueItems — returns list[Task]."""
    from datetime import datetime, timezone, timedelta
    today = (datetime.now(timezone.utc) + timedelta(minutes=0)).date().isoformat()
    mock_responses.get(f"{BASE}/dueItems?by={today}", payload=[TASK_PAYLOAD])
    async with MarvinClient(api_token="tok") as client:
        tasks = await client.get_due_items()
    assert len(tasks) == 1
    assert isinstance(tasks[0], Task)


@pytest.mark.asyncio
async def test_get_children(mock_responses):
    """GET /children — returns list[Task] with parentId param."""
    mock_responses.get(f"{BASE}/children?parentId=cat1", payload=[TASK_PAYLOAD])
    async with MarvinClient(api_token="tok") as client:
        tasks = await client.get_children("cat1")
    assert len(tasks) == 1
    assert isinstance(tasks[0], Task)


@pytest.mark.asyncio
async def test_add_task_with_auto_complete(mock_responses):
    """POST /addTask — default auto_complete=True, no X-Auto-Complete header."""
    mock_responses.post(f"{BASE}/addTask", payload=TASK_PAYLOAD)
    async with MarvinClient(api_token="tok") as client:
        task = await client.add_task("Buy milk")
    assert isinstance(task, Task)
    assert task._id == "t1"


@pytest.mark.asyncio
async def test_add_task_without_auto_complete(mock_responses):
    """POST /addTask — auto_complete=False sends X-Auto-Complete: false header."""
    mock_responses.post(f"{BASE}/addTask", payload=TASK_PAYLOAD)
    async with MarvinClient(api_token="tok") as client:
        task = await client.add_task("Buy milk", auto_complete=False)
    assert isinstance(task, Task)


@pytest.mark.asyncio
async def test_mark_done(mock_responses):
    """POST /markDone — returns Task."""
    done_payload = {**TASK_PAYLOAD, "done": True}
    mock_responses.post(f"{BASE}/markDone", payload=done_payload)
    async with MarvinClient(api_token="tok") as client:
        task = await client.mark_done("t1")
    assert isinstance(task, Task)
    assert task.done is True


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_add_project(mock_responses):
    """POST /addProject — returns Category."""
    mock_responses.post(f"{BASE}/addProject", payload=CATEGORY_PAYLOAD)
    async with MarvinClient(api_token="tok") as client:
        cat = await client.add_project("My Project")
    assert isinstance(cat, Category)
    assert cat._id == "cat1"


# ---------------------------------------------------------------------------
# Categories & Labels
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_categories(mock_responses):
    """GET /categories — returns list[Category]."""
    mock_responses.get(f"{BASE}/categories", payload=[CATEGORY_PAYLOAD])
    async with MarvinClient(api_token="tok") as client:
        cats = await client.get_categories()
    assert len(cats) == 1
    assert isinstance(cats[0], Category)


@pytest.mark.asyncio
async def test_get_labels(mock_responses):
    """GET /labels — returns list[Label]."""
    mock_responses.get(f"{BASE}/labels", payload=[LABEL_PAYLOAD])
    async with MarvinClient(api_token="tok") as client:
        labels = await client.get_labels()
    assert len(labels) == 1
    assert isinstance(labels[0], Label)


# ---------------------------------------------------------------------------
# Calendar Events & Time Blocks
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_add_event(mock_responses):
    """POST /addEvent — returns CalendarEvent."""
    mock_responses.post(f"{BASE}/addEvent", payload=EVENT_PAYLOAD)
    async with MarvinClient(api_token="tok") as client:
        event = await client.add_event("Meeting", "2026-04-25T09:00:00Z")
    assert isinstance(event, CalendarEvent)
    assert event._id == "ev1"


@pytest.mark.asyncio
async def test_get_today_time_blocks(mock_responses):
    """GET /todayTimeBlocks — returns list[TimeBlock]."""
    mock_responses.get(f"{BASE}/todayTimeBlocks", payload=[TIME_BLOCK_PAYLOAD])
    async with MarvinClient(api_token="tok") as client:
        blocks = await client.get_today_time_blocks()
    assert len(blocks) == 1
    assert isinstance(blocks[0], TimeBlock)


# ---------------------------------------------------------------------------
# Time Tracking
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_start_tracking(mock_responses):
    """POST /track (START) — returns TrackingResult."""
    mock_responses.post(f"{BASE}/track", payload=TRACKING_PAYLOAD)
    async with MarvinClient(api_token="tok") as client:
        result = await client.start_tracking("t1")
    assert isinstance(result, TrackingResult)
    assert result.start_id == "t1"


@pytest.mark.asyncio
async def test_stop_tracking(mock_responses):
    """POST /track (STOP) — returns TrackingResult."""
    stop_payload = {"stopId": "t1", "stopTimes": [1700010000000]}
    mock_responses.post(f"{BASE}/track", payload=stop_payload)
    async with MarvinClient(api_token="tok") as client:
        result = await client.stop_tracking("t1")
    assert isinstance(result, TrackingResult)


@pytest.mark.asyncio
async def test_get_time_tracks(mock_responses):
    """POST /tracks — returns list[TimeTrack]."""
    mock_responses.post(f"{BASE}/tracks", payload=[TIME_TRACK_PAYLOAD])
    async with MarvinClient(api_token="tok") as client:
        tracks = await client.get_time_tracks(["t1"])
    assert len(tracks) == 1
    assert isinstance(tracks[0], TimeTrack)
    assert tracks[0].task_id == "t1"


@pytest.mark.asyncio
async def test_get_tracked_item_returns_task(mock_responses):
    """GET /trackedItem — returns Task when tracking."""
    mock_responses.get(f"{BASE}/trackedItem", payload=TASK_PAYLOAD)
    async with MarvinClient(api_token="tok") as client:
        task = await client.get_tracked_item()
    assert isinstance(task, Task)


@pytest.mark.asyncio
async def test_get_tracked_item_returns_none_when_not_tracking(mock_responses):
    """GET /trackedItem — returns None when nothing is tracked."""
    mock_responses.get(f"{BASE}/trackedItem", payload=None)
    async with MarvinClient(api_token="tok") as client:
        task = await client.get_tracked_item()
    assert task is None


# ---------------------------------------------------------------------------
# Kudos & Account
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_kudos(mock_responses):
    """GET /kudos — returns Kudos."""
    mock_responses.get(f"{BASE}/kudos", payload=KUDOS_PAYLOAD)
    async with MarvinClient(api_token="tok") as client:
        kudos = await client.get_kudos()
    assert isinstance(kudos, Kudos)
    assert kudos.kudos == 50


@pytest.mark.asyncio
async def test_get_me(mock_responses):
    """GET /me — returns AccountProfile."""
    mock_responses.get(f"{BASE}/me", payload=PROFILE_PAYLOAD)
    async with MarvinClient(api_token="tok") as client:
        profile = await client.get_me()
    assert isinstance(profile, AccountProfile)
    assert profile.user_id == "u1"


# ---------------------------------------------------------------------------
# Goals
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_goals(mock_responses):
    """GET /goals — returns list[Goal]."""
    mock_responses.get(f"{BASE}/goals", payload=[GOAL_PAYLOAD])
    async with MarvinClient(api_token="tok") as client:
        goals = await client.get_goals()
    assert len(goals) == 1
    assert isinstance(goals[0], Goal)


# ---------------------------------------------------------------------------
# Habits
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_habits(mock_responses):
    """GET /habits — returns list[Habit] (api_token)."""
    mock_responses.get(f"{BASE}/habits", payload=[HABIT_PAYLOAD])
    async with MarvinClient(api_token="tok") as client:
        habits = await client.get_habits()
    assert len(habits) == 1
    assert isinstance(habits[0], Habit)


@pytest.mark.asyncio
async def test_get_habit(mock_responses):
    """GET /habit — returns single Habit."""
    mock_responses.get(f"{BASE}/habit?id=h1", payload=HABIT_PAYLOAD)
    async with MarvinClient(api_token="tok") as client:
        habit = await client.get_habit("h1")
    assert isinstance(habit, Habit)
    assert habit._id == "h1"


@pytest.mark.asyncio
async def test_update_habit(mock_responses):
    """POST /updateHabit — returns raw value."""
    mock_responses.post(f"{BASE}/updateHabit", payload=1)
    async with MarvinClient(api_token="tok") as client:
        result = await client.update_habit("h1", time=1700000000000)
    assert result == 1


@pytest.mark.asyncio
async def test_get_habits_raw(mock_responses):
    """GET /habits?raw=1 — returns list[Habit] (full_access_token)."""
    mock_responses.get(f"{BASE}/habits?raw=1", payload=[HABIT_PAYLOAD])
    async with MarvinClient(api_token="tok", full_access_token="full-tok") as client:
        habits = await client.get_habits_raw()
    assert len(habits) == 1
    assert isinstance(habits[0], Habit)


# ---------------------------------------------------------------------------
# Rewards
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_claim_reward_points(mock_responses):
    """POST /claimRewardPoints — returns AccountProfile."""
    mock_responses.post(f"{BASE}/claimRewardPoints", payload=PROFILE_PAYLOAD)
    async with MarvinClient(api_token="tok") as client:
        profile = await client.claim_reward_points(10.0)
    assert isinstance(profile, AccountProfile)


@pytest.mark.asyncio
async def test_unclaim_reward_points(mock_responses):
    """POST /unclaimRewardPoints — returns AccountProfile."""
    mock_responses.post(f"{BASE}/unclaimRewardPoints", payload=PROFILE_PAYLOAD)
    async with MarvinClient(api_token="tok") as client:
        profile = await client.unclaim_reward_points(item_id="t1")
    assert isinstance(profile, AccountProfile)


@pytest.mark.asyncio
async def test_spend_reward_points(mock_responses):
    """POST /spendRewardPoints — returns AccountProfile."""
    mock_responses.post(f"{BASE}/spendRewardPoints", payload=PROFILE_PAYLOAD)
    async with MarvinClient(api_token="tok") as client:
        profile = await client.spend_reward_points(5.0)
    assert isinstance(profile, AccountProfile)


@pytest.mark.asyncio
async def test_reset_reward_points(mock_responses):
    """POST /resetRewardPoints — full_access_token required, returns AccountProfile."""
    mock_responses.post(f"{BASE}/resetRewardPoints", payload=PROFILE_PAYLOAD)
    async with MarvinClient(api_token="tok", full_access_token="full-tok") as client:
        profile = await client.reset_reward_points()
    assert isinstance(profile, AccountProfile)


# ---------------------------------------------------------------------------
# Reminders
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_reminders(mock_responses):
    """GET /reminders — full_access_token required, returns list[Reminder]."""
    mock_responses.get(f"{BASE}/reminders", payload=[REMINDER_PAYLOAD])
    async with MarvinClient(api_token="tok", full_access_token="full-tok") as client:
        reminders = await client.get_reminders()
    assert len(reminders) == 1
    assert isinstance(reminders[0], Reminder)


@pytest.mark.asyncio
async def test_set_reminders(mock_responses):
    """POST /reminder/set — returns True."""
    mock_responses.post(f"{BASE}/reminder/set", payload="OK")
    reminder = Reminder(reminder_id="r1", time=1700000000)
    async with MarvinClient(api_token="tok") as client:
        result = await client.set_reminders([reminder])
    assert result is True


@pytest.mark.asyncio
async def test_delete_reminders(mock_responses):
    """POST /reminder/delete — returns True."""
    mock_responses.post(f"{BASE}/reminder/delete", payload="OK")
    async with MarvinClient(api_token="tok") as client:
        result = await client.delete_reminders(["r1"])
    assert result is True


@pytest.mark.asyncio
async def test_delete_all_reminders(mock_responses):
    """POST /reminder/deleteAll — full_access_token required, returns True."""
    mock_responses.post(f"{BASE}/reminder/deleteAll", payload="OK")
    async with MarvinClient(api_token="tok", full_access_token="full-tok") as client:
        result = await client.delete_all_reminders()
    assert result is True


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_doc(mock_responses):
    """GET /doc — full_access_token required, returns MarvinDocument."""
    mock_responses.get(f"{BASE}/doc?id=doc1", payload=DOC_PAYLOAD)
    async with MarvinClient(api_token="tok", full_access_token="full-tok") as client:
        doc = await client.get_doc("doc1")
    assert isinstance(doc, MarvinDocument)
    assert doc.id == "doc1"


@pytest.mark.asyncio
async def test_create_doc(mock_responses):
    """POST /doc/create — full_access_token required, returns MarvinDocument."""
    mock_responses.post(f"{BASE}/doc/create", payload=DOC_PAYLOAD)
    async with MarvinClient(api_token="tok", full_access_token="full-tok") as client:
        doc = await client.create_doc({"db": "Tasks", "createdAt": 1700000000000})
    assert isinstance(doc, MarvinDocument)


@pytest.mark.asyncio
async def test_update_doc(mock_responses):
    """POST /doc/update — full_access_token required, returns MarvinDocument."""
    mock_responses.post(f"{BASE}/doc/update", payload=DOC_PAYLOAD)
    setters = [{"key": "title", "val": "Updated"}]
    async with MarvinClient(api_token="tok", full_access_token="full-tok") as client:
        doc = await client.update_doc("doc1", setters)
    assert isinstance(doc, MarvinDocument)


@pytest.mark.asyncio
async def test_delete_doc(mock_responses):
    """POST /doc/delete — full_access_token required, returns True."""
    mock_responses.post(f"{BASE}/doc/delete", payload="OK")
    async with MarvinClient(api_token="tok", full_access_token="full-tok") as client:
        result = await client.delete_doc("doc1")
    assert result is True


# ---------------------------------------------------------------------------
# Auth header assertions
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_api_token_auth_header_sent(mock_responses):
    """api_token method sends X-API-Token header."""
    mock_responses.post(f"{BASE}/test", payload="OK")
    async with MarvinClient(api_token="my-secret-token") as client:
        await client.test_credentials()
    from yarl import URL
    calls = list(mock_responses.requests.get(("POST", URL(f"{BASE}/test")), []))
    assert calls[0].kwargs["headers"]["X-API-Token"] == "my-secret-token"


@pytest.mark.asyncio
async def test_full_access_token_auth_header_sent(mock_responses):
    """full_access_token method sends X-Full-Access-Token header."""
    mock_responses.get(f"{BASE}/reminders", payload=[])
    async with MarvinClient(api_token="api-tok", full_access_token="full-secret") as client:
        await client.get_reminders()
    from yarl import URL
    calls = list(mock_responses.requests.get(("GET", URL(f"{BASE}/reminders")), []))
    assert calls[0].kwargs["headers"]["X-Full-Access-Token"] == "full-secret"


# ---------------------------------------------------------------------------
# Experimental docstring assertion
# ---------------------------------------------------------------------------


def test_experimental_docstrings():
    """'Experimental' appears in the docstring of each experimental method."""
    experimental_methods = [
        "get_children",
        "mark_done",
        "add_event",
        "get_today_time_blocks",
        "get_habits",
        "get_habits_raw",
        "get_habit",
        "update_habit",
        "get_doc",
        "create_doc",
        "update_doc",
        "delete_doc",
    ]
    for method_name in experimental_methods:
        method = getattr(MarvinClient, method_name)
        docstring = method.__doc__ or ""
        assert "Experimental" in docstring, (
            f"Expected 'Experimental' in {method_name}.__doc__, got: {docstring!r}"
        )
