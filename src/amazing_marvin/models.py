"""Typed dataclass models for the Amazing Marvin API."""

from __future__ import annotations

import re
from dataclasses import dataclass, field, fields
from functools import lru_cache
from typing import Any, Callable, Optional, TypeVar

_T = TypeVar("_T")

_CAMEL_RE_1 = re.compile(r"([A-Z]+)([A-Z][a-z])")
_CAMEL_RE_2 = re.compile(r"([a-z0-9])([A-Z])")


@lru_cache(maxsize=512)
def _camel_to_snake(name: str) -> str:
    if name.startswith("_"):
        return name
    s = _CAMEL_RE_1.sub(r"\1_\2", name)
    s = _CAMEL_RE_2.sub(r"\1_\2", s)
    return s.lower()


@lru_cache(maxsize=None)
def _field_names(cls: type) -> frozenset[str]:
    return frozenset(f.name for f in fields(cls))


def _from_dict(
    cls: type[_T],
    data: dict[str, Any],
    converters: dict[str, Callable[[Any], Any]] | None = None,
) -> _T:
    known = _field_names(cls)  # type: ignore[arg-type]
    converted: dict[str, Any] = {}
    for k, v in data.items():
        snake = _camel_to_snake(k)
        if snake not in known:
            continue
        if converters and snake in converters:
            converted[snake] = converters[snake](v)
        else:
            converted[snake] = v
    return cls(**converted)


@dataclass
class Subtask:
    _id: str
    title: str
    done: bool = False
    rank: int = 0
    time_estimate: Optional[int] = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Subtask":
        return _from_dict(cls, data)


@dataclass
class Task:
    _id: str
    _rev: Optional[str] = None
    title: str = ""
    done: bool = False
    day: Optional[str] = None
    parent_id: Optional[str] = None
    subtasks: dict[str, Subtask] = field(default_factory=dict)
    label_ids: list[str] = field(default_factory=list)
    due_date: Optional[str] = None
    first_scheduled: Optional[str] = None
    planned_week: Optional[str] = None
    planned_month: Optional[str] = None
    sprint_id: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    review_date: Optional[str] = None
    time_estimate: Optional[int] = None
    duration: Optional[int] = None
    times: list[int] = field(default_factory=list)
    first_tracked: Optional[int] = None
    done_at: Optional[int] = None
    completed_at: Optional[int] = None
    created_at: Optional[int] = None
    updated_at: Optional[int] = None
    worked_on_at: Optional[int] = None
    marvin_points: Optional[int] = None
    reward_points: Optional[float] = None
    reward_id: Optional[str] = None
    is_reward: bool = False
    is_starred: Optional[int] = None
    is_frogged: Optional[int] = None
    recurring: bool = False
    recurring_task_id: Optional[str] = None
    echo: bool = False
    echo_id: Optional[str] = None
    is_pinned: bool = False
    pin_id: Optional[str] = None
    daily_section: Optional[str] = None
    bonus_section: Optional[str] = None
    custom_section: Optional[str] = None
    time_block_section: Optional[str] = None
    rank: Optional[int] = None
    master_rank: Optional[int] = None
    note: Optional[str] = None
    email: Optional[str] = None
    link: Optional[str] = None
    backburner: bool = False
    item_snooze_time: Optional[int] = None
    perma_snooze_time: Optional[str] = None
    cal_id: Optional[str] = None
    cal_url: Optional[str] = None
    etag: Optional[str] = None
    cal_data: Optional[str] = None
    db: str = "Tasks"
    on_board: bool = False
    imported: bool = False
    generated_at: Optional[int] = None
    echoed_at: Optional[int] = None
    deleted_at: Optional[int] = None
    restored_at: Optional[int] = None
    depends_on: dict[str, bool] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Task":
        return _from_dict(
            cls,
            data,
            converters={
                "subtasks": lambda v: (
                    {sid: Subtask.from_dict(sub) for sid, sub in v.items()}
                    if isinstance(v, dict)
                    else v
                ),
            },
        )


@dataclass
class Category:
    _id: str
    title: str
    type: str = "category"
    _rev: Optional[str] = None
    parent_id: Optional[str] = None
    db: str = "Categories"
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
    color: Optional[str] = None
    icon: Optional[str] = None
    note: Optional[str] = None
    priority: Optional[str] = None
    label_ids: list[str] = field(default_factory=list)
    time_estimate: Optional[int] = None
    marvin_points: Optional[int] = None
    is_frogged: Optional[int] = None
    review_date: Optional[str] = None
    rank: Optional[int] = None
    day_rank: Optional[int] = None
    worked_on_at: Optional[int] = None
    updated_at: Optional[int] = None
    recurring: bool = False
    recurring_task_id: Optional[str] = None
    echo: bool = False
    backburner: bool = False
    item_snooze_time: Optional[int] = None
    perma_snooze_time: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Category":
        return _from_dict(cls, data)


@dataclass
class Label:
    _id: str
    title: str
    color: Optional[str] = None
    icon: Optional[str] = None
    group_id: Optional[str] = None
    created_at: Optional[int] = None
    show_as: Optional[str] = None
    is_action: bool = False
    is_hidden: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Label":
        return _from_dict(cls, data)


@dataclass
class CalendarEvent:
    _id: str
    title: str
    start: str
    _rev: Optional[str] = None
    is_all_day: bool = False
    length: Optional[int] = None
    note: Optional[str] = None
    parent_id: Optional[str] = None
    label_ids: list[str] = field(default_factory=list)
    cal_id: Optional[str] = None
    cal_url: Optional[str] = None
    etag: Optional[str] = None
    cal_data: Optional[str] = None
    hidden: bool = False
    time_zone_fix: Optional[int] = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CalendarEvent":
        return _from_dict(cls, data)


@dataclass
class TimeBlock:
    _id: str
    title: str
    date: str
    time: str
    duration: Optional[str] = None
    _rev: Optional[str] = None
    is_section: bool = True
    note: Optional[str] = None
    cal_id: Optional[str] = None
    cal_url: Optional[str] = None
    etag: Optional[str] = None
    cal_data: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TimeBlock":
        return _from_dict(cls, data)


@dataclass
class TrackingResult:
    start_id: Optional[str] = None
    start_times: list[int] = field(default_factory=list)
    stop_id: Optional[str] = None
    stop_times: list[int] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TrackingResult":
        return _from_dict(cls, data)


@dataclass
class TimeTrack:
    task_id: str
    times: list[int] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TimeTrack":
        return _from_dict(cls, data)


@dataclass
class Kudos:
    kudos: int = 0
    level: int = 1
    kudos_remaining: int = 0

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Kudos":
        return _from_dict(cls, data)


@dataclass
class AccountProfile:
    user_id: str = ""
    email: str = ""
    parent_email: Optional[str] = None
    email_confirmed: bool = False
    billing_period: Optional[str] = None
    paid_through: Optional[str] = None
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
    tracking: Optional[str] = None
    tracking_since: Optional[int] = None
    current_version: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AccountProfile":
        return _from_dict(cls, data)


@dataclass
class Reminder:
    reminder_id: str
    time: int
    title: str = ""
    offset: int = -1
    type: str = "T"
    snooze: int = 0
    auto_snooze: bool = False
    can_track: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Reminder":
        return _from_dict(cls, data)

    def to_dict(self) -> dict[str, Any]:
        return {
            "reminderId": self.reminder_id,
            "time": self.time,
            "title": self.title,
            "offset": self.offset,
            "type": self.type,
            "snooze": self.snooze,
            "autoSnooze": self.auto_snooze,
            "canTrack": self.can_track,
        }


@dataclass
class GoalSection:
    _id: str
    title: str = ""
    note: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GoalSection":
        return _from_dict(cls, data)


@dataclass
class Goal:
    _id: str
    title: str
    _rev: Optional[str] = None
    note: Optional[str] = None
    status: Optional[str] = None
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

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Goal":
        return _from_dict(
            cls,
            data,
            converters={
                "sections": lambda v: (
                    [GoalSection.from_dict(s) for s in v] if isinstance(v, list) else v
                ),
            },
        )


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
    period: Optional[str] = None
    target: Optional[int] = None
    is_positive: bool = True
    record_type: Optional[str] = None
    show_in_day_view: bool = False
    show_in_calendar: bool = False
    show_after_success: bool = True
    show_after_record: bool = True
    done: bool = False
    history: list[int] = field(default_factory=list)
    dismissed: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Habit":
        return _from_dict(cls, data)


@dataclass
class MarvinDocument:
    id: str
    rev: Optional[str] = None
    data: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MarvinDocument":
        d = dict(data)
        doc_id = d.pop("_id", "")
        rev = d.pop("_rev", None)
        return cls(id=doc_id, rev=rev, data=d)
