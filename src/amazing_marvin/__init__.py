"""py-amazing-marvin — async Python client for the Amazing Marvin API."""

from amazing_marvin.client import MarvinClient
from amazing_marvin.exceptions import (
    MarvinAPIError,
    MarvinAuthError,
    MarvinCouchError,
    MarvinNotFoundError,
    MarvinRateLimitError,
)
from amazing_marvin.models import (
    AccountProfile,
    CalendarEvent,
    Category,
    Goal,
    GoalSection,
    Habit,
    Kudos,
    Label,
    MarvinDocument,
    Reminder,
    Subtask,
    Task,
    TimeBlock,
    TimeTrack,
    TrackingResult,
)

__all__ = [
    "MarvinClient",
    "MarvinAPIError",
    "MarvinAuthError",
    "MarvinRateLimitError",
    "MarvinNotFoundError",
    "MarvinCouchError",
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
