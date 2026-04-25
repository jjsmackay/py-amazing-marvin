# Contract: Public API — MarvinClient

**File**: `src/amazing_marvin/client.py`
**Exported from**: `src/amazing_marvin/__init__.py` as `MarvinClient`

All methods are `async`. All parameters beyond the first positional (where present) are keyword-only unless noted. `tz_offset` on any method overrides the client-level default for that call only.

---

## Constructor & Lifecycle

```python
class MarvinClient:
    def __init__(
        self,
        *,
        api_token: str | None = None,
        full_access_token: str | None = None,
        tz_offset: int = 0,
        throttle: bool = False,
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        """Create a Marvin API client.

        Args:
            api_token: Read-only API token (X-API-Token).
            full_access_token: Full-access token (X-Full-Access-Token).
            tz_offset: Minutes east of UTC, matching Marvin's convention. Default 0 (UTC).
            throttle: When True, enforce the 1-req/3-s burst and 1440/day limits
                      automatically. Raises MarvinRateLimitError if daily cap reached.
            session: Externally owned aiohttp.ClientSession. If None, a session is
                     created on __aenter__ and closed on __aexit__.
        """

    async def __aenter__(self) -> "MarvinClient": ...
    async def __aexit__(self, *args: Any) -> None: ...
```

---

## Test & Health

```python
    async def test_credentials(self) -> bool:
        """POST /test — verify API token is valid.

        Auth: api_token required.
        Returns True if credentials are valid.
        Raises MarvinAuthError on 401/403.
        """
```

---

## Tasks

```python
    async def get_today_items(
        self,
        *,
        tz_offset: int | None = None,
    ) -> list[Task]:
        """GET /todayItems — tasks and projects scheduled for today.

        Auth: api_token required.
        Args:
            tz_offset: Override client timezone for this call. Sent as X-Date header.
        """

    async def get_due_items(
        self,
        *,
        by: str | None = None,
        tz_offset: int | None = None,
    ) -> list[Task]:
        """GET /dueItems — open tasks/projects due on or before a date.

        Auth: api_token required.
        Args:
            by: Due date as "YYYY-MM-DD". Defaults to today in the active timezone.
            tz_offset: Override client timezone for this call.
        """

    async def get_children(self, parent_id: str) -> list[Task]:
        """GET /children — open tasks and projects with given parentId.

        Auth: api_token required.
        Experimental.
        Note: Only returns open (not done) items.
        """

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
            auto_complete: Set False to disable Marvin's title autocompletion
                           (sends X-Auto-Complete: false header).
            tz_offset: Override timezone for day-boundary scheduling.
        Returns: Created Task with _id and _rev.
        """

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
            server-side (see research.md §9 for details). The library surfaces
            whatever the server returns.
        Args:
            item_id: ID of the task or subtask to mark.
            done: True to mark done, False to undo.
            tz_offset: Override timezone (affects which day is recorded as completion).
        """
```

---

## Projects

```python
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
```

---

## Categories & Labels

```python
    async def get_categories(self) -> list[Category]:
        """GET /categories — all categories (and projects) in the account.

        Auth: api_token required.
        """

    async def get_labels(self) -> list[Label]:
        """GET /labels — all labels in sort order.

        Auth: api_token required.
        """
```

---

## Calendar Events

```python
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

    async def get_today_time_blocks(
        self,
        *,
        tz_offset: int | None = None,
    ) -> list[TimeBlock]:
        """GET /todayTimeBlocks — time blocks scheduled for today.

        Auth: api_token required.
        Experimental.
        """
```

---

## Time Tracking

```python
    async def start_tracking(self, task_id: str) -> TrackingResult:
        """POST /track with action="START" — begin time tracking a task.

        Auth: api_token required.
        Note: Caller is responsible for updating task.times and task.duration
            after stopping (see research.md §9).
        """

    async def stop_tracking(self, task_id: str) -> TrackingResult:
        """POST /track with action="STOP" — stop time tracking a task.

        Auth: api_token required.
        """

    async def get_time_tracks(
        self,
        task_ids: list[str],
    ) -> list[TimeTrack]:
        """POST /tracks — retrieve source-of-truth time track data for up to 100 tasks.

        Auth: api_token required.
        Args:
            task_ids: List of task IDs (max 100).
        """

    async def get_tracked_item(self) -> Task | None:
        """GET /trackedItem — the task currently being time tracked.

        Auth: api_token required.
        Returns None if no task is currently being tracked.
        """
```

---

## Rewards

```python
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
            item_id: Task ID or "MANUAL". Determines how many points for unclaim.
            date: Date string "YYYY-MM-DD" for tracking. Defaults to today (tz_offset).
        Returns: Updated AccountProfile.
        """

    async def unclaim_reward_points(
        self,
        *,
        item_id: str,
        date: str | None = None,
    ) -> AccountProfile:
        """POST /unclaimRewardPoints — reverse a reward claim.

        Auth: api_token required.
        """

    async def spend_reward_points(
        self,
        points: float,
        *,
        date: str | None = None,
    ) -> AccountProfile:
        """POST /spendRewardPoints — spend reward points on a reward.

        Auth: api_token required.
        """

    async def reset_reward_points(self) -> AccountProfile:
        """POST /resetRewardPoints — permanently reset all reward points to zero.

        Auth: full_access_token required.
        Warning: Deletes all earn/spend history. Irreversible.
        """
```

---

## Kudos & Account

```python
    async def get_kudos(self) -> Kudos:
        """GET /kudos — Marvin kudos level and progress.

        Auth: api_token required.
        """

    async def get_me(self) -> AccountProfile:
        """GET /me — account profile information.

        Auth: api_token required.
        """
```

---

## Goals

```python
    async def get_goals(self) -> list[Goal]:
        """GET /goals — all goals with sections and check-in data.

        Auth: api_token required.
        """
```

---

## Habits

```python
    async def get_habits(self) -> list[Habit]:
        """GET /habits — all habits with full history.

        Auth: api_token required.
        Experimental.
        """

    async def get_habits_raw(self) -> list[Habit]:
        """GET /habits?raw=1 — all habit objects in raw database format.

        Auth: full_access_token required.
        Experimental.
        """

    async def get_habit(self, habit_id: str) -> Habit:
        """GET /habit — single habit with full history.

        Auth: api_token required.
        Experimental.
        """

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
```

---

## Reminders

```python
    async def get_reminders(self) -> list[Reminder]:
        """GET /reminders — all scheduled server-side reminders.

        Auth: full_access_token required.
        Note: Only for push notification reminders. Not needed if cloud sync is disabled.
        """

    async def set_reminders(self, reminders: list[Reminder]) -> bool:
        """POST /reminder/set — schedule one or more reminders.

        Auth: api_token required.
        Note: Caller is also responsible for updating the corresponding Task's
            reminder fields to keep the Marvin UI accurate.
        Returns: True on success.
        """

    async def delete_reminders(self, reminder_ids: list[str]) -> bool:
        """POST /reminder/delete — delete one or more reminders.

        Auth: api_token required.
        Returns: True on success.
        """

    async def delete_all_reminders(self) -> bool:
        """POST /reminder/deleteAll — delete all server-side reminders.

        Auth: full_access_token required.
        Returns: True on success.
        """
```

---

## Document Access (raw CouchDB)

```python
    async def get_doc(self, doc_id: str) -> MarvinDocument:
        """GET /doc — read any document from the CouchDB database by ID.

        Auth: full_access_token required.
        Experimental.
        Note: The document shape varies by type. MarvinDocument.data contains
            all fields beyond _id and _rev.
        Warning: Editing ProfileItems can cause Marvin to crash on startup if
            the document is given an invalid shape.
        """

    async def create_doc(self, data: dict[str, Any]) -> MarvinDocument:
        """POST /doc/create — create a new document directly in the database.

        Auth: full_access_token required.
        Experimental.
        Args:
            data: Document fields. Should include 'db' and 'createdAt' for
                  correct display. '_id' is optional (server generates if absent).
        Warning: Creating invalid documents may cause Marvin to crash.
        """

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
            setters: List of {"key": str, "val": Any} dicts. Use
                     "fieldUpdates.FIELD" keys for conflict-safe updates.
        Example:
            setters=[
                {"key": "done", "val": True},
                {"key": "fieldUpdates.done", "val": 1700000000000},
                {"key": "updatedAt", "val": 1700000000000},
            ]
        Warning: Wrong document shape may cause Marvin to crash on startup.
        """

    async def delete_doc(self, item_id: str) -> bool:
        """POST /doc/delete — permanently delete a document.

        Auth: full_access_token required.
        Experimental.
        Warning: Deletion is permanent. Marvin Trash is client-side only and
            does not apply to documents deleted via this API.
        Returns: True on success.
        """
```

---

## Public Exports (`__init__.py`)

```python
from amazing_marvin.client import MarvinClient
from amazing_marvin.exceptions import (
    MarvinAPIError,
    MarvinAuthError,
    MarvinRateLimitError,
    MarvinNotFoundError,
)
from amazing_marvin.models import (
    Task,
    Subtask,
    Category,
    Label,
    CalendarEvent,
    TimeBlock,
    TrackingResult,
    TimeTrack,
    Kudos,
    AccountProfile,
    Reminder,
    Goal,
    GoalSection,
    Habit,
    MarvinDocument,
)

__all__ = [
    "MarvinClient",
    "MarvinAPIError",
    "MarvinAuthError",
    "MarvinRateLimitError",
    "MarvinNotFoundError",
    "Task",
    "Subtask",
    "Category",
    "Label",
    "CalendarEvent",
    "TimeBlock",
    "TrackingResult",
    "TimeTrack",
    "Kudos",
    "AccountProfile",
    "Reminder",
    "Goal",
    "GoalSection",
    "Habit",
    "MarvinDocument",
]
```
