"""CouchDB query capability: config guard, selectors, models, index ensure."""

from __future__ import annotations

import datetime
import json as _json
from typing import Any

import pytest
import pytest_asyncio
from aioresponses import aioresponses

from amazing_marvin import (
    Category,
    MarvinClient,
    MarvinCouchError,
    Task,
    TimeBlock,
)

COUCH_URL = "http://couchdb:5984"
FIND_URL = f"{COUCH_URL}/marvin/_find"
INDEX_URL = f"{COUCH_URL}/marvin/_index"


@pytest_asyncio.fixture
async def couch_client():
    """MarvinClient configured for couch only (no Marvin tokens needed)."""
    async with MarvinClient(
        couch_url=f"{COUCH_URL}/",  # trailing slash must be normalised
        couch_db="marvin",
        couch_user="marvin_sync",
        couch_password="sync-pass",
    ) as client:
        yield client


def _find_payload(mock: aioresponses, url: str = FIND_URL) -> dict[str, Any]:
    """Extract the JSON body of the most recent POST to ``url``."""
    requests = mock.requests[("POST", __import__("yarl").URL(url))]
    return _json.loads(_json.dumps(requests[-1].kwargs["json"]))


def _task_doc(**overrides: Any) -> dict[str, Any]:
    doc = {
        "_id": "2026-07-06_abc",
        "db": "Tasks",
        "title": "Book travel",
        "done": False,
        "day": "2026-07-06",
        "dueDate": "2026-07-08",
        "parentId": "proj-1",
        "dailySection": "Afternoon",
        "rank": 9,
    }
    doc.update(overrides)
    return doc


# ------------------------------------------------------------------ #
# Config guard
# ------------------------------------------------------------------ #


async def test_unconfigured_couch_raises_before_http():
    async with MarvinClient(api_token="t") as client:
        with pytest.raises(MarvinCouchError, match="not configured"):
            await client.find_tasks(title_contains="x")


async def test_partial_couch_auth_rejected_at_construction():
    with pytest.raises(MarvinCouchError, match="couch_user and couch_password"):
        MarvinClient(couch_url=COUCH_URL, couch_db="marvin", couch_user="only-user")


async def test_couch_methods_require_session():
    client = MarvinClient(
        couch_url=COUCH_URL, couch_db="marvin", couch_user="u", couch_password="p"
    )
    with pytest.raises(Exception, match="session"):
        await client.find_tasks()


# ------------------------------------------------------------------ #
# Low-level _find
# ------------------------------------------------------------------ #


async def test_couch_find_posts_selector_and_returns_docs(couch_client, mock_aioresponses):
    mock_aioresponses.post(
        FIND_URL, payload={"docs": [_task_doc()], "bookmark": "bm1"}
    )
    result = await couch_client.couch_find(
        {"db": "Tasks"}, fields=["_id", "title"], limit=5, skip=2, bookmark="bm0"
    )
    assert [d["_id"] for d in result["docs"]] == ["2026-07-06_abc"]
    assert result["bookmark"] == "bm1"
    payload = _find_payload(mock_aioresponses)
    assert payload["selector"] == {"db": "Tasks"}
    assert payload["fields"] == ["_id", "title"]
    assert payload["limit"] == 5
    assert payload["skip"] == 2
    assert payload["bookmark"] == "bm0"


async def test_couch_find_omits_unset_options(couch_client, mock_aioresponses):
    mock_aioresponses.post(FIND_URL, payload={"docs": []})
    await couch_client.couch_find({"db": "Tasks"})
    payload = _find_payload(mock_aioresponses)
    assert set(payload) == {"selector"}


async def test_couch_error_maps_to_exception(couch_client, mock_aioresponses):
    mock_aioresponses.post(FIND_URL, status=401, payload={"error": "unauthorized"})
    with pytest.raises(MarvinCouchError) as excinfo:
        await couch_client.couch_find({"db": "Tasks"})
    assert excinfo.value.status == 401


async def test_couch_network_error_maps_to_exception(couch_client, mock_aioresponses):
    mock_aioresponses.post(FIND_URL, exception=ConnectionError("boom"))
    with pytest.raises(MarvinCouchError, match="CouchDB request failed"):
        await couch_client.couch_find({"db": "Tasks"})


# ------------------------------------------------------------------ #
# find_tasks selector construction
# ------------------------------------------------------------------ #


async def test_find_tasks_always_constrains_db(couch_client, mock_aioresponses):
    mock_aioresponses.post(FIND_URL, payload={"docs": [_task_doc()]})
    tasks = await couch_client.find_tasks()
    assert isinstance(tasks[0], Task)
    payload = _find_payload(mock_aioresponses)
    assert payload["selector"]["db"] == "Tasks"
    assert payload["limit"] == 25


async def test_find_tasks_title_regex_case_insensitive_and_escaped(
    couch_client, mock_aioresponses
):
    mock_aioresponses.post(FIND_URL, payload={"docs": []})
    await couch_client.find_tasks(title_contains="a.b(c")
    selector = _find_payload(mock_aioresponses)["selector"]
    assert selector["title"] == {"$regex": r"(?i)a\.b\(c"}


async def test_find_tasks_filters_combine(couch_client, mock_aioresponses):
    mock_aioresponses.post(FIND_URL, payload={"docs": []})
    await couch_client.find_tasks(
        done=False,
        day=datetime.date(2026, 7, 7),
        parent_id="proj-1",
        label_id="lbl-1",
        limit=10,
    )
    payload = _find_payload(mock_aioresponses)
    selector = payload["selector"]
    assert selector["done"] is False
    assert selector["day"] == "2026-07-07"
    assert selector["parentId"] == "proj-1"
    assert selector["labelIds"] == {"$elemMatch": {"$eq": "lbl-1"}}
    assert payload["limit"] == 10


async def test_find_tasks_day_range(couch_client, mock_aioresponses):
    mock_aioresponses.post(FIND_URL, payload={"docs": []})
    await couch_client.find_tasks(
        day_range=(datetime.date(2026, 7, 1), "2026-07-31")
    )
    selector = _find_payload(mock_aioresponses)["selector"]
    assert selector["day"] == {"$gte": "2026-07-01", "$lte": "2026-07-31"}


async def test_find_tasks_due_by_excludes_null_due(couch_client, mock_aioresponses):
    mock_aioresponses.post(FIND_URL, payload={"docs": []})
    await couch_client.find_tasks(due_by="2026-07-07")
    selector = _find_payload(mock_aioresponses)["selector"]
    assert selector["dueDate"] == {"$gt": None, "$lte": "2026-07-07"}


async def test_find_tasks_maps_camel_case_to_model(couch_client, mock_aioresponses):
    mock_aioresponses.post(FIND_URL, payload={"docs": [_task_doc()]})
    (task,) = await couch_client.find_tasks()
    assert task.due_date == "2026-07-08"
    assert task.parent_id == "proj-1"
    assert task.daily_section == "Afternoon"


# ------------------------------------------------------------------ #
# High-level helpers
# ------------------------------------------------------------------ #


async def test_tasks_by_day(couch_client, mock_aioresponses):
    mock_aioresponses.post(FIND_URL, payload={"docs": [_task_doc()]})
    tasks = await couch_client.tasks_by_day(datetime.date(2026, 7, 6))
    assert isinstance(tasks[0], Task)
    selector = _find_payload(mock_aioresponses)["selector"]
    assert selector == {"db": "Tasks", "day": "2026-07-06"}


async def test_tasks_due_by(couch_client, mock_aioresponses):
    mock_aioresponses.post(FIND_URL, payload={"docs": [_task_doc()]})
    tasks = await couch_client.tasks_due_by("2026-07-07")
    assert isinstance(tasks[0], Task)
    selector = _find_payload(mock_aioresponses)["selector"]
    assert selector == {
        "db": "Tasks",
        "done": False,
        "dueDate": {"$gt": None, "$lte": "2026-07-07"},
    }


async def test_planner_items_returns_time_blocks(couch_client, mock_aioresponses):
    mock_aioresponses.post(
        FIND_URL,
        payload={
            "docs": [
                {
                    "_id": "pi-1",
                    "db": "PlannerItems",
                    "title": "Deep work",
                    "date": "2026-07-06",
                    "time": "09:00",
                    "duration": "01:30",
                }
            ]
        },
    )
    (block,) = await couch_client.planner_items("2026-07-06")
    assert isinstance(block, TimeBlock)
    assert block.time == "09:00"
    selector = _find_payload(mock_aioresponses)["selector"]
    assert selector == {"db": "PlannerItems", "date": "2026-07-06"}


async def test_recurring_generators(couch_client, mock_aioresponses):
    mock_aioresponses.post(
        FIND_URL,
        payload={"docs": [{"_id": "rt-1", "db": "RecurringTasks", "type": "daily"}]},
    )
    gens = await couch_client.recurring_generators()
    assert gens == [{"_id": "rt-1", "db": "RecurringTasks", "type": "daily"}]
    selector = _find_payload(mock_aioresponses)["selector"]
    assert selector == {"db": "RecurringTasks"}


async def test_categories_from_couch(couch_client, mock_aioresponses):
    mock_aioresponses.post(
        FIND_URL,
        payload={
            "docs": [
                {"_id": "proj-1", "db": "Categories", "title": "Home", "type": "project"}
            ]
        },
    )
    (cat,) = await couch_client.categories_from_couch()
    assert isinstance(cat, Category)
    assert cat.type == "project"
    selector = _find_payload(mock_aioresponses)["selector"]
    assert selector == {"db": "Categories"}


# ------------------------------------------------------------------ #
# Index management
# ------------------------------------------------------------------ #


async def test_ensure_couch_indexes_created_and_exists(couch_client, mock_aioresponses):
    for result in ("created", "exists", "created", "exists", "created"):
        mock_aioresponses.post(INDEX_URL, payload={"result": result, "name": "x"})
    results = await couch_client.ensure_couch_indexes()
    assert set(results) == {"idx-db", "idx-done", "idx-day", "idx-labelIds", "idx-parentId"}
    assert set(results.values()) <= {"created", "exists"}
    payload = _find_payload(mock_aioresponses, INDEX_URL)
    assert payload["index"] == {"fields": ["parentId"]}
    assert payload["type"] == "json"


async def test_pagination_via_bookmark(couch_client, mock_aioresponses):
    mock_aioresponses.post(
        FIND_URL, payload={"docs": [_task_doc()], "bookmark": "next-page"}
    )
    result = await couch_client.couch_find({"db": "Tasks"}, bookmark="prev")
    assert result["bookmark"] == "next-page"
