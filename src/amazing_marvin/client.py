"""Amazing Marvin async HTTP client."""

from __future__ import annotations

import json as _json
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

import aiohttp

from amazing_marvin._throttle import _Throttler
from amazing_marvin.exceptions import (
    MarvinAPIError,
    MarvinAuthError,
    MarvinNotFoundError,
    MarvinRateLimitError,
)
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

_BASE_URL = "https://serv.amazingmarvin.com/api"


class MarvinClient:
    """Async client for the Amazing Marvin API.

    Args:
        api_token: Read-only API token (X-API-Token header).
        full_access_token: Full-access token (X-Full-Access-Token header).
        tz_offset: Minutes east of UTC, matching Marvin's convention. Default 0 (UTC).
        throttle: When True, enforce 1-req/3-s burst and 1440/day limits automatically.
        session: Externally owned aiohttp.ClientSession. If None, a session is created
                 on __aenter__ and closed on __aexit__.
    """

    def __init__(
        self,
        *,
        api_token: str | None = None,
        full_access_token: str | None = None,
        tz_offset: int = 0,
        throttle: bool = False,
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        self._api_token = api_token
        self._full_access_token = full_access_token
        self._tz_offset = tz_offset
        self._throttler: _Throttler | None = _Throttler() if throttle else None
        self._session = session
        self._owns_session = session is None

    async def __aenter__(self) -> "MarvinClient":
        if self._owns_session:
            self._session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._owns_session and self._session is not None:
            await self._session.close()
            self._session = None

    def _active_tz(self, tz_override: int | None) -> int:
        return tz_override if tz_override is not None else self._tz_offset

    def _today_date(self, tz_offset: int) -> str:
        utc_now = datetime.now(timezone.utc).replace(tzinfo=None)
        return (utc_now + timedelta(minutes=tz_offset)).date().isoformat()

    async def _request(
        self,
        method: str,
        path: str,
        *,
        auth: Literal["api", "full"],
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        tz_override: int | None = None,
    ) -> Any:
        if self._session is None:
            raise MarvinAPIError(
                "Client has no session. Use 'async with MarvinClient(...) as client:' "
                "or pass session= at construction."
            )

        # Pre-flight auth check
        if auth == "api" and not self._api_token:
            raise MarvinAuthError(
                "This method requires an API token (X-API-Token). "
                "Pass api_token= when constructing MarvinClient.",
                required_token="api",
            )
        if auth == "full" and not self._full_access_token:
            raise MarvinAuthError(
                "This method requires a full-access token (X-Full-Access-Token). "
                "Pass full_access_token= when constructing MarvinClient.",
                required_token="full",
            )

        # Throttle if enabled
        active_tz = self._active_tz(tz_override)
        if self._throttler is not None:
            await self._throttler.acquire(active_tz)

        # Build headers
        req_headers: dict[str, str] = headers.copy() if headers else {}
        if auth == "api":
            req_headers["X-API-Token"] = self._api_token or ""
        else:
            req_headers["X-Full-Access-Token"] = self._full_access_token or ""

        url = f"{_BASE_URL}{path}"
        try:
            async with self._session.request(
                method, url, json=json, params=params, headers=req_headers
            ) as resp:
                if resp.status in (401, 403):
                    raise MarvinAuthError(
                        f"Authentication failed (HTTP {resp.status})",
                        status=resp.status,
                        required_token=auth,
                    )
                if resp.status == 404:
                    raise MarvinNotFoundError(
                        "Resource not found (HTTP 404)",
                        status=404,
                    )
                if resp.status == 429:
                    retry_after: float | None = None
                    raw_ra = resp.headers.get("Retry-After")
                    if raw_ra is not None:
                        try:
                            retry_after = float(raw_ra)
                        except ValueError:
                            pass
                    raise MarvinRateLimitError(
                        "Rate limit exceeded (HTTP 429)",
                        status=429,
                        retry_after=retry_after,
                        daily_cap_exceeded=False,
                    )
                if resp.status >= 500:
                    try:
                        cause: BaseException | None = aiohttp.ClientResponseError(
                            resp.request_info,
                            resp.history,
                            status=resp.status,
                        )
                    except Exception:
                        cause = None
                    raise MarvinAPIError(
                        f"Server error (HTTP {resp.status})",
                        status=resp.status,
                        cause=cause,
                    )
                # Parse JSON
                content_type = resp.headers.get("Content-Type", "")
                if "application/json" in content_type or resp.status == 200:
                    try:
                        return await resp.json(content_type=None)
                    except (_json.JSONDecodeError, aiohttp.ContentTypeError):
                        raw = await resp.read()
                        raise MarvinAPIError(
                            "Response is not valid JSON",
                            status=resp.status,
                            raw_body=raw,
                        )
                return await resp.json(content_type=None)
        except MarvinAPIError:
            raise
        except aiohttp.ClientError as exc:
            raise MarvinAPIError(
                f"Network error: {exc}",
                cause=exc,
            ) from exc

    # ------------------------------------------------------------------ #
    # Test & Health
    # ------------------------------------------------------------------ #

    async def test_credentials(self) -> bool:
        """POST /test — verify API token is valid.

        Auth: api_token required.
        Returns True if credentials are valid.
        Raises MarvinAuthError on 401/403.
        """
        result = await self._request("POST", "/test", auth="api")
        return result == "OK" or result is True

    # ------------------------------------------------------------------ #
    # Tasks
    # ------------------------------------------------------------------ #

    async def get_today_items(self, *, tz_offset: int | None = None) -> list[Task]:
        """GET /todayItems — tasks and projects scheduled for today.

        Auth: api_token required.
        Args:
            tz_offset: Override client timezone for this call. Sent as X-Date header.
        """
        active_tz = self._active_tz(tz_offset)
        today = self._today_date(active_tz)
        data = await self._request(
            "GET", "/todayItems", auth="api", headers={"X-Date": today}
        )
        return [Task.from_dict(t) for t in (data or [])]

    async def get_due_items(
        self, *, by: str | None = None, tz_offset: int | None = None
    ) -> list[Task]:
        """GET /dueItems — open tasks/projects due on or before a date.

        Auth: api_token required.
        Args:
            by: Due date as "YYYY-MM-DD". Defaults to today in the active timezone.
            tz_offset: Override client timezone for this call.
        """
        active_tz = self._active_tz(tz_offset)
        by_date = by or self._today_date(active_tz)
        data = await self._request("GET", "/dueItems", auth="api", params={"by": by_date})
        return [Task.from_dict(t) for t in (data or [])]

    async def get_children(self, parent_id: str) -> list[Task]:
        """GET /children — open tasks and projects with given parentId.

        Auth: api_token required.
        Experimental: Only returns open (not done) items.
        """
        data = await self._request(
            "GET", "/children", auth="api", params={"parentId": parent_id}
        )
        return [Task.from_dict(t) for t in (data or [])]

    async def add_task(
        self,
        title: str,
        *,
        done: bool = False,
        day: str | None = None,
        parent_id: str | None = None,
        label_ids: list[str] | None = None,
        due_date: str | None = None,
        first_scheduled: str | None = None,
        rank: int | None = None,
        daily_section: str | None = None,
        bonus_section: str | None = None,
        custom_section: str | None = None,
        time_block_section: str | None = None,
        note: str | None = None,
        time_estimate: int | None = None,
        is_reward: bool = False,
        is_starred: int | None = None,
        is_frogged: int | None = None,
        planned_week: str | None = None,
        planned_month: str | None = None,
        reward_points: float | None = None,
        reward_id: str | None = None,
        backburner: bool = False,
        review_date: str | None = None,
        item_snooze_time: int | None = None,
        perma_snooze_time: str | None = None,
        auto_complete: bool = True,
        tz_offset: int | None = None,
    ) -> Task:
        """POST /addTask — create a new task.

        Auth: api_token required.
        Args:
            title: Task title. Supports autocompletion syntax unless auto_complete=False.
            auto_complete: Set False to disable Marvin's title autocompletion.
            tz_offset: Override timezone for day-boundary scheduling.
        """
        active_tz = self._active_tz(tz_offset)
        body: dict[str, Any] = {"title": title, "timeZoneOffset": active_tz}
        if done:
            body["done"] = done
        if day is not None:
            body["day"] = day
        if parent_id is not None:
            body["parentId"] = parent_id
        if label_ids is not None:
            body["labelIds"] = label_ids
        if due_date is not None:
            body["dueDate"] = due_date
        if first_scheduled is not None:
            body["firstScheduled"] = first_scheduled
        if rank is not None:
            body["rank"] = rank
        if daily_section is not None:
            body["dailySection"] = daily_section
        if bonus_section is not None:
            body["bonusSection"] = bonus_section
        if custom_section is not None:
            body["customSection"] = custom_section
        if time_block_section is not None:
            body["timeBlockSection"] = time_block_section
        if note is not None:
            body["note"] = note
        if time_estimate is not None:
            body["timeEstimate"] = time_estimate
        if is_reward:
            body["isReward"] = is_reward
        if is_starred is not None:
            body["isStarred"] = is_starred
        if is_frogged is not None:
            body["isFrogged"] = is_frogged
        if planned_week is not None:
            body["plannedWeek"] = planned_week
        if planned_month is not None:
            body["plannedMonth"] = planned_month
        if reward_points is not None:
            body["rewardPoints"] = reward_points
        if reward_id is not None:
            body["rewardId"] = reward_id
        if backburner:
            body["backburner"] = backburner
        if review_date is not None:
            body["reviewDate"] = review_date
        if item_snooze_time is not None:
            body["itemSnoozeTime"] = item_snooze_time
        if perma_snooze_time is not None:
            body["permaSnoozeTime"] = perma_snooze_time
        hdrs = {} if auto_complete else {"X-Auto-Complete": "false"}
        data = await self._request("POST", "/addTask", auth="api", json=body, headers=hdrs)
        return Task.from_dict(data)

    async def mark_done(
        self,
        item_id: str,
        done: bool = True,
        *,
        tz_offset: int | None = None,
    ) -> Task:
        """POST /markDone — mark a task or subtask done or undone.

        Auth: api_token required.
        Experimental: Several recurring-task edge cases are not yet implemented
            server-side. The library surfaces whatever the server returns.
        Args:
            item_id: ID of the task or subtask to mark.
            done: True to mark done, False to undo.
            tz_offset: Override timezone (affects which day is recorded as completion).
        """
        active_tz = self._active_tz(tz_offset)
        body: dict[str, Any] = {"itemId": item_id, "timeZoneOffset": active_tz}
        if not done:
            body["done"] = False
        data = await self._request("POST", "/markDone", auth="api", json=body)
        return Task.from_dict(data)

    # ------------------------------------------------------------------ #
    # Projects
    # ------------------------------------------------------------------ #

    async def add_project(
        self,
        title: str,
        *,
        done: bool = False,
        day: str | None = None,
        parent_id: str | None = None,
        label_ids: list[str] | None = None,
        due_date: str | None = None,
        first_scheduled: str | None = None,
        rank: int | None = None,
        daily_section: str | None = None,
        bonus_section: str | None = None,
        custom_section: str | None = None,
        time_block_section: str | None = None,
        note: str | None = None,
        time_estimate: int | None = None,
        is_reward: bool = False,
        priority: str | None = None,
        is_frogged: int | None = None,
        planned_week: str | None = None,
        planned_month: str | None = None,
        reward_points: float | None = None,
        reward_id: str | None = None,
        backburner: bool = False,
        review_date: str | None = None,
        item_snooze_time: int | None = None,
        perma_snooze_time: str | None = None,
        auto_complete: bool = True,
        tz_offset: int | None = None,
    ) -> Category:
        """POST /addProject — create a new project.

        Auth: api_token required.
        Returns: Created Category with type="project", _id, and _rev.
        """
        active_tz = self._active_tz(tz_offset)
        body: dict[str, Any] = {"title": title, "timeZoneOffset": active_tz}
        if done:
            body["done"] = done
        if day is not None:
            body["day"] = day
        if parent_id is not None:
            body["parentId"] = parent_id
        if label_ids is not None:
            body["labelIds"] = label_ids
        if due_date is not None:
            body["dueDate"] = due_date
        if first_scheduled is not None:
            body["firstScheduled"] = first_scheduled
        if rank is not None:
            body["rank"] = rank
        if daily_section is not None:
            body["dailySection"] = daily_section
        if bonus_section is not None:
            body["bonusSection"] = bonus_section
        if custom_section is not None:
            body["customSection"] = custom_section
        if time_block_section is not None:
            body["timeBlockSection"] = time_block_section
        if note is not None:
            body["note"] = note
        if time_estimate is not None:
            body["timeEstimate"] = time_estimate
        if is_reward:
            body["isReward"] = is_reward
        if priority is not None:
            body["priority"] = priority
        if is_frogged is not None:
            body["isFrogged"] = is_frogged
        if planned_week is not None:
            body["plannedWeek"] = planned_week
        if planned_month is not None:
            body["plannedMonth"] = planned_month
        if reward_points is not None:
            body["rewardPoints"] = reward_points
        if reward_id is not None:
            body["rewardId"] = reward_id
        if backburner:
            body["backburner"] = backburner
        if review_date is not None:
            body["reviewDate"] = review_date
        if item_snooze_time is not None:
            body["itemSnoozeTime"] = item_snooze_time
        if perma_snooze_time is not None:
            body["permaSnoozeTime"] = perma_snooze_time
        hdrs = {} if auto_complete else {"X-Auto-Complete": "false"}
        data = await self._request("POST", "/addProject", auth="api", json=body, headers=hdrs)
        return Category.from_dict(data)

    # ------------------------------------------------------------------ #
    # Categories & Labels
    # ------------------------------------------------------------------ #

    async def get_categories(self) -> list[Category]:
        """GET /categories — all categories (and projects) in the account.

        Auth: api_token required.
        """
        data = await self._request("GET", "/categories", auth="api")
        return [Category.from_dict(c) for c in (data or [])]

    async def get_labels(self) -> list[Label]:
        """GET /labels — all labels in sort order.

        Auth: api_token required.
        """
        data = await self._request("GET", "/labels", auth="api")
        return [Label.from_dict(lb) for lb in (data or [])]

    # ------------------------------------------------------------------ #
    # Calendar Events
    # ------------------------------------------------------------------ #

    async def add_event(
        self,
        title: str,
        start: str,
        *,
        note: str | None = None,
        length: int | None = None,
    ) -> CalendarEvent:
        """POST /addEvent — create a calendar event.

        Auth: api_token required.
        Experimental: Calendar sync happens on the Marvin client. The event will
            only be synced to your calendar provider if Marvin is running on a device.
        Args:
            start: ISO 8601 datetime string, e.g. "2024-01-15T09:00:00.000Z".
            length: Duration in milliseconds.
        """
        body: dict[str, Any] = {"title": title, "start": start}
        if note is not None:
            body["note"] = note
        if length is not None:
            body["length"] = length
        data = await self._request("POST", "/addEvent", auth="api", json=body)
        return CalendarEvent.from_dict(data)

    async def get_today_time_blocks(self, *, tz_offset: int | None = None) -> list[TimeBlock]:
        """GET /todayTimeBlocks — time blocks scheduled for today.

        Auth: api_token required.
        Experimental.
        """
        active_tz = self._active_tz(tz_offset)
        today = self._today_date(active_tz)
        data = await self._request(
            "GET", "/todayTimeBlocks", auth="api", headers={"X-Date": today}
        )
        return [TimeBlock.from_dict(tb) for tb in (data or [])]

    # ------------------------------------------------------------------ #
    # Time Tracking
    # ------------------------------------------------------------------ #

    async def start_tracking(self, task_id: str) -> TrackingResult:
        """POST /track with action="START" — begin time tracking a task.

        Auth: api_token required.
        """
        data = await self._request(
            "POST", "/track", auth="api", json={"taskId": task_id, "action": "START"}
        )
        return TrackingResult.from_dict(data or {})

    async def stop_tracking(self, task_id: str) -> TrackingResult:
        """POST /track with action="STOP" — stop time tracking a task.

        Auth: api_token required.
        """
        data = await self._request(
            "POST", "/track", auth="api", json={"taskId": task_id, "action": "STOP"}
        )
        return TrackingResult.from_dict(data or {})

    async def get_time_tracks(self, task_ids: list[str]) -> list[TimeTrack]:
        """POST /tracks — retrieve time track data for up to 100 tasks.

        Auth: api_token required.
        Args:
            task_ids: List of task IDs (max 100).
        """
        data = await self._request("POST", "/tracks", auth="api", json={"taskIds": task_ids})
        return [TimeTrack.from_dict(tt) for tt in (data or [])]

    async def get_tracked_item(self) -> Task | None:
        """GET /trackedItem — the task currently being time tracked.

        Auth: api_token required.
        Returns None if no task is currently being tracked.
        """
        data = await self._request("GET", "/trackedItem", auth="api")
        if not data:
            return None
        return Task.from_dict(data)

    # ------------------------------------------------------------------ #
    # Rewards
    # ------------------------------------------------------------------ #

    async def claim_reward_points(
        self,
        points: float,
        *,
        item_id: str | None = None,
        date: str | None = None,
    ) -> AccountProfile:
        """POST /claimRewardPoints — claim reward points.

        Auth: api_token required.
        Args:
            points: Number of points to claim.
            item_id: Task ID or "MANUAL".
            date: Date string "YYYY-MM-DD". Defaults to today in the active timezone.
        Returns: Updated AccountProfile.
        """
        body: dict[str, Any] = {"points": points, "op": "CLAIM"}
        if item_id is not None:
            body["itemId"] = item_id
        if date is not None:
            body["date"] = date
        data = await self._request("POST", "/claimRewardPoints", auth="api", json=body)
        return AccountProfile.from_dict(data)

    async def unclaim_reward_points(
        self,
        *,
        item_id: str,
        date: str | None = None,
    ) -> AccountProfile:
        """POST /unclaimRewardPoints — reverse a reward claim.

        Auth: api_token required.
        """
        body: dict[str, Any] = {"itemId": item_id, "op": "UNCLAIM"}
        if date is not None:
            body["date"] = date
        data = await self._request("POST", "/unclaimRewardPoints", auth="api", json=body)
        return AccountProfile.from_dict(data)

    async def spend_reward_points(
        self,
        points: float,
        *,
        date: str | None = None,
    ) -> AccountProfile:
        """POST /spendRewardPoints — spend reward points on a reward.

        Auth: api_token required.
        """
        body: dict[str, Any] = {"points": points, "op": "SPEND"}
        if date is not None:
            body["date"] = date
        data = await self._request("POST", "/spendRewardPoints", auth="api", json=body)
        return AccountProfile.from_dict(data)

    async def reset_reward_points(self) -> AccountProfile:
        """POST /resetRewardPoints — permanently reset all reward points to zero.

        Auth: full_access_token required.
        Warning: Deletes all earn/spend history. Irreversible.
        """
        data = await self._request("POST", "/resetRewardPoints", auth="full")
        return AccountProfile.from_dict(data)

    # ------------------------------------------------------------------ #
    # Kudos & Account
    # ------------------------------------------------------------------ #

    async def get_kudos(self) -> Kudos:
        """GET /kudos — Marvin kudos level and progress.

        Auth: api_token required.
        """
        data = await self._request("GET", "/kudos", auth="api")
        return Kudos.from_dict(data)

    async def get_me(self) -> AccountProfile:
        """GET /me — account profile information.

        Auth: api_token required.
        """
        data = await self._request("GET", "/me", auth="api")
        return AccountProfile.from_dict(data)

    # ------------------------------------------------------------------ #
    # Goals
    # ------------------------------------------------------------------ #

    async def get_goals(self) -> list[Goal]:
        """GET /goals — all goals with sections and check-in data.

        Auth: api_token required.
        """
        data = await self._request("GET", "/goals", auth="api")
        return [Goal.from_dict(g) for g in (data or [])]

    # ------------------------------------------------------------------ #
    # Habits
    # ------------------------------------------------------------------ #

    async def get_habits(self) -> list[Habit]:
        """GET /habits — all habits with full history.

        Auth: api_token required.
        Experimental.
        """
        data = await self._request("GET", "/habits", auth="api")
        return [Habit.from_dict(h) for h in (data or [])]

    async def get_habits_raw(self) -> list[Habit]:
        """GET /habits?raw=1 — all habit objects in raw database format.

        Auth: full_access_token required.
        Experimental.
        """
        data = await self._request("GET", "/habits", auth="full", params={"raw": "1"})
        return [Habit.from_dict(h) for h in (data or [])]

    async def get_habit(self, habit_id: str) -> Habit:
        """GET /habit — single habit with full history.

        Auth: api_token required.
        Experimental.
        """
        data = await self._request("GET", "/habit", auth="api", params={"id": habit_id})
        return Habit.from_dict(data)

    async def update_habit(
        self,
        habit_id: str,
        *,
        time: int | None = None,
        value: float | None = None,
        undo: bool = False,
        history: list[int] | None = None,
        update_db: bool = True,
    ) -> Any:
        """POST /updateHabit — record, undo, or rewrite habit history.

        Auth: api_token required.
        Experimental.
        Args:
            habit_id: ID of the habit to update.
            time: Unix ms timestamp for the record (record mode).
            value: Recorded value (for numeric habits).
            undo: If True, undo the last recording (undo mode).
            history: Full history array [time, val, ...] to rewrite (rewrite mode).
            update_db: Whether server updates the Habit document in CouchDB.
        Returns: The new habit value (type varies by habit recordType).
        Note: Exactly one of (time), (undo=True), or (history) should be provided.
        """
        body: dict[str, Any] = {"habitId": habit_id, "updateDB": update_db}
        if undo:
            body["op"] = "UNDO"
        elif history is not None:
            body["op"] = "REWRITE"
            body["history"] = history
        else:
            body["op"] = "RECORD"
            if time is not None:
                body["time"] = time
            if value is not None:
                body["value"] = value
        return await self._request("POST", "/updateHabit", auth="api", json=body)

    # ------------------------------------------------------------------ #
    # Reminders
    # ------------------------------------------------------------------ #

    async def get_reminders(self) -> list[Reminder]:
        """GET /reminders — all scheduled server-side reminders.

        Auth: full_access_token required.
        Note: Only for push notification reminders.
        """
        data = await self._request("GET", "/reminders", auth="full")
        return [Reminder.from_dict(r) for r in (data or [])]

    async def set_reminders(self, reminders: list[Reminder]) -> bool:
        """POST /reminder/set — schedule one or more reminders.

        Auth: api_token required.
        Returns: True on success.
        """
        body = {"reminders": [r.to_dict() for r in reminders]}
        result = await self._request("POST", "/reminder/set", auth="api", json=body)
        return result == "OK" or result is True

    async def delete_reminders(self, reminder_ids: list[str]) -> bool:
        """POST /reminder/delete — delete one or more reminders.

        Auth: api_token required.
        Returns: True on success.
        """
        body = {"reminderIds": reminder_ids}
        result = await self._request("POST", "/reminder/delete", auth="api", json=body)
        return result == "OK" or result is True

    async def delete_all_reminders(self) -> bool:
        """POST /reminder/deleteAll — delete all server-side reminders.

        Auth: full_access_token required.
        Returns: True on success.
        """
        result = await self._request("POST", "/reminder/deleteAll", auth="full")
        return result == "OK" or result is True

    # ------------------------------------------------------------------ #
    # Document Access (raw CouchDB)
    # ------------------------------------------------------------------ #

    async def get_doc(self, doc_id: str) -> MarvinDocument:
        """GET /doc — read any document from the CouchDB database by ID.

        Auth: full_access_token required.
        Experimental.
        Note: The document shape varies by type. MarvinDocument.data contains
            all fields beyond _id and _rev.
        Warning: Editing ProfileItems can cause Marvin to crash on startup if
            the document is given an invalid shape.
        """
        data = await self._request("GET", "/doc", auth="full", params={"id": doc_id})
        return MarvinDocument.from_dict(data)

    async def create_doc(self, data: dict[str, Any]) -> MarvinDocument:
        """POST /doc/create — create a new document directly in the database.

        Auth: full_access_token required.
        Experimental.
        Args:
            data: Document fields. Should include 'db' and 'createdAt'.
        Warning: Creating invalid documents may cause Marvin to crash.
        """
        result = await self._request("POST", "/doc/create", auth="full", json=data)
        return MarvinDocument.from_dict(result)

    async def update_doc(
        self,
        item_id: str,
        setters: list[dict[str, Any]],
    ) -> MarvinDocument:
        """POST /doc/update — update fields on any document using setters.

        Auth: full_access_token required.
        Experimental.
        Args:
            item_id: The document's _id.
            setters: List of {"key": str, "val": Any} dicts.
        Warning: Wrong document shape may cause Marvin to crash on startup.
        """
        body = {"itemId": item_id, "setters": setters}
        result = await self._request("POST", "/doc/update", auth="full", json=body)
        return MarvinDocument.from_dict(result)

    async def delete_doc(self, item_id: str) -> bool:
        """POST /doc/delete — permanently delete a document.

        Auth: full_access_token required.
        Experimental.
        Warning: Deletion is permanent.
        Returns: True on success.
        """
        result = await self._request("POST", "/doc/delete", auth="full", json={"itemId": item_id})
        return result == "OK" or result is True
