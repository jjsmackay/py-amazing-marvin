"""SC-001 — ergonomics check: minimal HA borrowed-session flow (T039)."""

from __future__ import annotations

import aiohttp
import pytest
from aioresponses import aioresponses

from amazing_marvin.client import MarvinClient

BASE = "https://serv.amazingmarvin.com/api"

TASK_PAYLOAD = {"_id": "task1", "title": "Morning standup", "done": False}
DONE_PAYLOAD = {"_id": "sub1", "title": "Sub-task", "done": True}


@pytest.mark.asyncio
async def test_ha_borrowed_session_flow():
    """Minimal HA integration flow: pass session, call get_today_items + mark_done."""
    with aioresponses() as m:
        m.get(f"{BASE}/todayItems", payload=[TASK_PAYLOAD])
        m.post(f"{BASE}/markDone", payload=DONE_PAYLOAD)

        async with aiohttp.ClientSession() as session:
            client = MarvinClient(api_token="ha-api-token", session=session)
            tasks = await client.get_today_items()
            done_task = await client.mark_done("sub1")

        assert len(tasks) == 1
        assert tasks[0]._id == "task1"
        assert done_task.done is True
