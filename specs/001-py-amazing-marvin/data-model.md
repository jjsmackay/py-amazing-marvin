# Data Model: py-amazing-marvin

**Phase 1 output** | Sourced from: wiki `Marvin-Data-Types.md` and `Marvin-API.md`

All models are Python `@dataclass` classes in `src/amazing_marvin/models.py`. Fields use `Optional[T]` for nullable/optional API fields and `= None` defaults. All models expose a `from_dict(data: dict[str, Any]) -> Self` class method that silently discards unknown keys.

---

## Subtask

Embedded within `Task.subtasks` (dict keyed by subtask ID).

```python
@dataclass
class Subtask:
    _id: str
    title: str
    done: bool = False
    rank: int = 0
    time_estimate: Optional[int] = None   # ms
    # reminder fields omitted (rarely needed at this level)
```

**Relationships**: Lives inside `Task.subtasks: dict[str, Subtask]`.
**Lifecycle**: Created/updated as part of the parent Task document.

---

## Task

The primary Marvin work unit. Returned by most read endpoints and all task-mutation endpoints.

```python
@dataclass
class Task:
    # Identity
    _id: str
    _rev: Optional[str] = None

    # Core fields (commonly used by HA integration)
    title: str = ""
    done: bool = False
    day: Optional[str] = None            # "YYYY-MM-DD" or "unassigned"
    parent_id: Optional[str] = None      # field: parentId

    # Subtasks (dict from _id -> Subtask)
    subtasks: dict[str, Subtask] = field(default_factory=dict)

    # Labels
    label_ids: list[str] = field(default_factory=list)  # field: labelIds

    # Scheduling
    due_date: Optional[str] = None       # "YYYY-MM-DD"
    first_scheduled: Optional[str] = None
    planned_week: Optional[str] = None
    planned_month: Optional[str] = None
    sprint_id: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    review_date: Optional[str] = None

    # Timing
    time_estimate: Optional[int] = None  # ms
    duration: Optional[int] = None       # ms, set when done
    times: list[int] = field(default_factory=list)  # [start, stop, start, stop, ...]
    first_tracked: Optional[int] = None
    done_at: Optional[int] = None
    completed_at: Optional[int] = None
    created_at: Optional[int] = None
    updated_at: Optional[int] = None
    worked_on_at: Optional[int] = None

    # Gamification
    marvin_points: Optional[int] = None
    reward_points: Optional[float] = None
    reward_id: Optional[str] = None
    is_reward: bool = False
    is_starred: Optional[int] = None     # 1=yellow, 2=orange, 3=red, or True (legacy)
    is_frogged: Optional[int] = None     # 1=normal, 2=baby, 3=monster

    # Recurrence
    recurring: bool = False
    recurring_task_id: Optional[str] = None
    echo: bool = False
    echo_id: Optional[str] = None
    is_pinned: bool = False
    pin_id: Optional[str] = None

    # Sections / structure
    daily_section: Optional[str] = None
    bonus_section: Optional[str] = None
    custom_section: Optional[str] = None
    time_block_section: Optional[str] = None
    rank: Optional[int] = None
    master_rank: Optional[int] = None

    # Notes / content
    note: Optional[str] = None
    email: Optional[str] = None
    link: Optional[str] = None
    backburner: bool = False

    # Snooze
    item_snooze_time: Optional[int] = None
    perma_snooze_time: Optional[str] = None

    # Calendar
    cal_id: Optional[str] = None
    cal_url: Optional[str] = None
    etag: Optional[str] = None
    cal_data: Optional[str] = None

    # Metadata
    db: str = "Tasks"
    on_board: bool = False
    imported: bool = False
    generated_at: Optional[int] = None
    echoed_at: Optional[int] = None
    deleted_at: Optional[int] = None
    restored_at: Optional[int] = None
    depends_on: dict[str, bool] = field(default_factory=dict)
```

**Note on field naming**: JSON uses camelCase (`parentId`, `labelIds`, etc.); the `from_dict` classmethod maps these to Python snake_case attributes. The `_id` and `_rev` fields are kept as-is (conventional CouchDB names).

---

## Category / Project

Both categories and projects share the same data structure (`db="Categories"`). Projects are identified by `type="project"`.

```python
@dataclass
class Category:
    _id: str
    title: str
    type: str = "category"               # "category" or "project"
    _rev: Optional[str] = None
    parent_id: Optional[str] = None      # "root" for top-level categories
    db: str = "Categories"

    # Scheduling (projects only)
    day: Optional[str] = None
    due_date: Optional[str] = None
    first_scheduled: Optional[str] = None
    planned_week: Optional[str] = None
    planned_month: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    sprint_id: Optional[str] = None
    done: bool = False
    done_date: Optional[str] = None

    # Appearance
    color: Optional[str] = None
    icon: Optional[str] = None
    note: Optional[str] = None
    priority: Optional[str] = None       # "low", "mid", "high" (projects only)

    # Labels / gamification
    label_ids: list[str] = field(default_factory=list)
    time_estimate: Optional[int] = None
    marvin_points: Optional[int] = None
    is_frogged: Optional[int] = None
    review_date: Optional[str] = None
    rank: Optional[int] = None
    day_rank: Optional[int] = None
    worked_on_at: Optional[int] = None
    updated_at: Optional[int] = None

    # Recurrence
    recurring: bool = False
    recurring_task_id: Optional[str] = None
    echo: bool = False

    backburner: bool = False
    item_snooze_time: Optional[int] = None
    perma_snooze_time: Optional[str] = None
```

---

## Label

```python
@dataclass
class Label:
    _id: str
    title: str
    color: Optional[str] = None
    icon: Optional[str] = None
    group_id: Optional[str] = None
    created_at: Optional[int] = None
    show_as: Optional[str] = None        # "text", "icon", "both"
    is_action: bool = False
    is_hidden: bool = False
```

---

## CalendarEvent

```python
@dataclass
class CalendarEvent:
    _id: str
    title: str
    start: str                           # ISO 8601 string
    _rev: Optional[str] = None
    is_all_day: bool = False
    length: Optional[int] = None         # ms
    note: Optional[str] = None
    parent_id: Optional[str] = None
    label_ids: list[str] = field(default_factory=list)
    cal_id: Optional[str] = None
    cal_url: Optional[str] = None
    etag: Optional[str] = None
    cal_data: Optional[str] = None
    hidden: bool = False
    time_zone_fix: Optional[int] = None
```

---

## TimeBlock

```python
@dataclass
class TimeBlock:
    _id: str
    title: str
    date: str                            # "YYYY-MM-DD"
    time: str                            # "HH:mm"
    duration: Optional[str] = None       # minutes as string
    _rev: Optional[str] = None
    is_section: bool = True
    note: Optional[str] = None
    cal_id: Optional[str] = None
    cal_url: Optional[str] = None
    etag: Optional[str] = None
    cal_data: Optional[str] = None
```

---

## TrackingResult

Returned by `POST /track`.

```python
@dataclass
class TrackingResult:
    start_id: Optional[str] = None      # task ID that started tracking
    start_times: list[int] = field(default_factory=list)
    stop_id: Optional[str] = None       # task ID that was stopped
    stop_times: list[int] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)
```

---

## TimeTrack

One element of the `POST /tracks` response array.

```python
@dataclass
class TimeTrack:
    task_id: str
    times: list[int] = field(default_factory=list)  # [start, stop, start, stop, ...]
```

---

## Kudos

```python
@dataclass
class Kudos:
    kudos: int = 0
    level: int = 1
    kudos_remaining: int = 0
```

---

## AccountProfile

From `GET /me` and returned by reward-points endpoints.

```python
@dataclass
class AccountProfile:
    user_id: str = ""
    email: str = ""
    parent_email: Optional[str] = None
    email_confirmed: bool = False
    billing_period: Optional[str] = None  # "TRIAL", "MONTH", "YEAR", "ONCE", "PAID"
    paid_through: Optional[str] = None   # RFC3339 timestamp

    marvin_points: int = 0
    next_multiplier: int = 1
    reward_points_earned: float = 0.0
    reward_points_spent: float = 0.0
    reward_points_earned_today: float = 0.0
    reward_points_spent_today: float = 0.0
    reward_points_last_date: Optional[str] = None

    tomatoes: int = 0
    tomatoes_today: int = 0
    tomato_time: int = 0
    tomato_time_today: int = 0
    tomato_date: Optional[str] = None

    default_snooze: int = 0
    default_auto_snooze: bool = False
    default_offset: int = 0

    tracking: Optional[str] = None      # task ID currently tracked
    tracking_since: Optional[int] = None
    current_version: Optional[str] = None
```

---

## Reminder

```python
@dataclass
class Reminder:
    reminder_id: str                     # field: reminderId
    time: int                            # unix seconds
    title: str = ""
    offset: int = -1                     # minutes ahead; -1 = use default
    type: str = "T"                      # "T", "M", "DT", "DP", "t"
    snooze: int = 0
    auto_snooze: bool = False
    can_track: bool = False
```

---

## Goal

```python
@dataclass
class GoalSection:
    _id: str
    title: str = ""
    note: Optional[str] = None

@dataclass
class Goal:
    _id: str
    title: str
    _rev: Optional[str] = None
    note: Optional[str] = None
    status: Optional[str] = None         # "backburner", "pending", "active", "done"
    parent_id: Optional[str] = None
    color: Optional[str] = None
    due_date: Optional[str] = None
    has_end: bool = False
    is_starred: Optional[int] = None
    label_ids: list[str] = field(default_factory=list)
    sections: list[GoalSection] = field(default_factory=list)
    task_progress: bool = False
    committed: bool = False
    importance: Optional[int] = None
    difficulty: Optional[int] = None
    hide_in_day_view: bool = False
    check_in: bool = False
    check_in_weeks: Optional[int] = None
    last_check_in: Optional[str] = None
    started_at: Optional[int] = None
```

---

## Habit

```python
@dataclass
class Habit:
    _id: str
    title: str
    _rev: Optional[str] = None
    note: Optional[str] = None
    color: Optional[str] = None
    parent_id: Optional[str] = None
    label_ids: list[str] = field(default_factory=list)
    is_starred: Optional[int] = None
    is_frogged: Optional[int] = None
    time_estimate: Optional[int] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    units: Optional[str] = None
    period: Optional[str] = None         # "day", "week", "month", "quarter", "year"
    target: Optional[int] = None
    is_positive: bool = True
    record_type: Optional[str] = None   # "boolean", "number"
    show_in_day_view: bool = False
    show_in_calendar: bool = False
    show_after_success: bool = True
    show_after_record: bool = True
    done: bool = False
    history: list[int] = field(default_factory=list)  # [time, val, time, val, ...]
    dismissed: Optional[str] = None
```

---

## MarvinDocument

Wrapper for raw document endpoints (`/doc`, `/doc/create`, `/doc/update`).

```python
@dataclass
class MarvinDocument:
    id: str                              # field: _id
    rev: Optional[str] = None           # field: _rev
    data: dict[str, Any] = field(default_factory=dict)  # all other fields

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "MarvinDocument":
        doc_id = d.pop("_id", "")
        rev = d.pop("_rev", None)
        return cls(id=doc_id, rev=rev, data=d)
```

**Note**: `data` is intentionally `dict[str, Any]` because the Marvin doc schema varies by document type. This is the one place where `Any` appears in the public API, with explicit justification: the schema is dynamic and defined by the caller.

---

## Entity Relationships

```
Category  ←──parentId──  Category        (infinite nesting)
Category  ←──parentId──  Project
Category  ←──parentId──  Task
Project   ←──parentId──  Task
Task      ──subtasks──►  Subtask         (embedded)
Task      ──labelIds──►  Label[]
Goal      ──sections──►  GoalSection[]
Task      ──g_in_GOALID──► Goal          (goal membership via dynamic fields)
Task      ──recurringTaskId──► RecurringTask
```

---

## Field Naming Conventions

| JSON camelCase | Python snake_case |
|---|---|
| `parentId` | `parent_id` |
| `labelIds` | `label_ids` |
| `timeEstimate` | `time_estimate` |
| `dueDate` | `due_date` |
| `isStarred` | `is_starred` |
| `isFrogged` | `is_frogged` |
| `recurringTaskId` | `recurring_task_id` |
| `reminderId` | `reminder_id` |
| `marvinPoints` | `marvin_points` |
| `rewardPoints` | `reward_points` |
| `startId` (track) | `start_id` |
| `stopId` (track) | `stop_id` |

The `from_dict` method handles the conversion. CouchDB fields `_id` and `_rev` remain unchanged.
