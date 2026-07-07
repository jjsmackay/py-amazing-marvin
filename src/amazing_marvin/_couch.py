"""CouchDB Mango selector construction for Marvin's document schema.

Pure helpers — no I/O. The client owns the HTTP; this module owns the
Marvin-schema knowledge (``db`` discriminators, field names, selector shapes).
All documents share one database and are discriminated by their ``db`` field:
``Tasks``, ``Categories``, ``RecurringTasks``, ``SavedItems``, ``PlannerItems``.
"""

from __future__ import annotations

import datetime
import re
from typing import Any

#: Single-field Mango JSON indexes the query helpers rely on.
COUCH_INDEXES: dict[str, list[str]] = {
    "idx-db": ["db"],
    "idx-done": ["done"],
    "idx-day": ["day"],
    "idx-labelIds": ["labelIds"],
    "idx-parentId": ["parentId"],
}

DayLike = str | datetime.date


def day_str(day: DayLike) -> str:
    """Normalise a date or ``YYYY-MM-DD`` string to the string form."""
    if isinstance(day, datetime.date):
        return day.isoformat()
    return day


def regex_contains(text: str) -> dict[str, str]:
    """Case-insensitive substring match with regex metacharacters escaped."""
    return {"$regex": "(?i)" + re.escape(text)}


def due_by_condition(due_by: DayLike) -> dict[str, Any]:
    """``dueDate`` on or before the day, excluding null/missing.

    CouchDB collation sorts ``null`` before strings, so a bare ``$lte`` would
    match tasks with no due date; ``$gt: null`` excludes them.
    """
    return {"$gt": None, "$lte": day_str(due_by)}


def build_task_selector(
    *,
    title_contains: str | None = None,
    done: bool | None = None,
    day: DayLike | None = None,
    day_range: tuple[DayLike, DayLike] | None = None,
    due_by: DayLike | None = None,
    parent_id: str | None = None,
    label_id: str | None = None,
) -> dict[str, Any]:
    """Build a Mango selector over Task documents; filters AND together.

    Always constrains ``db == "Tasks"`` so RecurringTasks generator documents
    never match — results are actionable task instances only.

    Raises ``ValueError`` if both ``day`` and ``day_range`` are given — they
    both constrain the ``day`` field, so passing both is a caller mistake.
    """
    if day is not None and day_range is not None:
        raise ValueError("Pass either day or day_range, not both.")
    selector: dict[str, Any] = {"db": "Tasks"}
    if title_contains is not None:
        selector["title"] = regex_contains(title_contains)
    if done is not None:
        selector["done"] = done
    if day is not None:
        selector["day"] = day_str(day)
    if day_range is not None:
        start, end = day_range
        selector["day"] = {"$gte": day_str(start), "$lte": day_str(end)}
    if due_by is not None:
        selector["dueDate"] = due_by_condition(due_by)
    if parent_id is not None:
        selector["parentId"] = parent_id
    if label_id is not None:
        selector["labelIds"] = {"$elemMatch": {"$eq": label_id}}
    return selector
