"""Tests for model dataclasses — FR-017 (typed models, unknown-field discard)."""

from __future__ import annotations

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


def test_task_from_dict_basic():
    data = {"_id": "t1", "title": "Buy milk", "done": False, "day": "2026-04-25"}
    task = Task.from_dict(data)
    assert task._id == "t1"
    assert task.title == "Buy milk"
    assert task.done is False
    assert task.day == "2026-04-25"


def test_task_camelcase_mapping():
    data = {
        "_id": "t2",
        "parentId": "cat1",
        "labelIds": ["l1", "l2"],
        "dueDate": "2026-05-01",
        "isStarred": 2,
        "isFrogged": 1,
        "recurringTaskId": "rec123",
        "marvinPoints": 10,
    }
    task = Task.from_dict(data)
    assert task.parent_id == "cat1"
    assert task.label_ids == ["l1", "l2"]
    assert task.due_date == "2026-05-01"
    assert task.is_starred == 2
    assert task.is_frogged == 1
    assert task.recurring_task_id == "rec123"
    assert task.marvin_points == 10


def test_task_unknown_fields_silently_discarded():
    data = {
        "_id": "t3",
        "title": "Workout",
        "unknownFieldFromFuture": "ignored",
        "anotherNewField": 42,
    }
    task = Task.from_dict(data)
    assert task._id == "t3"
    assert task.title == "Workout"
    assert not hasattr(task, "unknownFieldFromFuture")


def test_task_default_collections():
    task = Task.from_dict({"_id": "t4"})
    assert task.subtasks == {}
    assert task.label_ids == []
    assert task.times == []
    assert task.depends_on == {}


def test_task_subtasks_nested():
    data = {
        "_id": "parent",
        "subtasks": {
            "sub1": {"_id": "sub1", "title": "Take meds", "done": False},
            "sub2": {"_id": "sub2", "title": "Drink coffee", "done": True},
        },
    }
    task = Task.from_dict(data)
    assert len(task.subtasks) == 2
    assert isinstance(task.subtasks["sub1"], Subtask)
    assert task.subtasks["sub1"].title == "Take meds"
    assert task.subtasks["sub2"].done is True


def test_subtask_from_dict():
    s = Subtask.from_dict({"_id": "s1", "title": "Sub", "done": True, "rank": 5})
    assert s._id == "s1"
    assert s.done is True
    assert s.rank == 5


def test_subtask_unknown_fields_discarded():
    s = Subtask.from_dict({"_id": "s2", "title": "Sub", "newField": "x"})
    assert s._id == "s2"
    assert not hasattr(s, "newField")


def test_category_from_dict():
    data = {"_id": "cat1", "title": "Work", "type": "category", "parentId": "root"}
    cat = Category.from_dict(data)
    assert cat._id == "cat1"
    assert cat.parent_id == "root"
    assert cat.type == "category"


def test_category_unknown_fields_discarded():
    data = {"_id": "cat2", "title": "Home", "novelApiField": True}
    cat = Category.from_dict(data)
    assert cat._id == "cat2"
    assert not hasattr(cat, "novelApiField")


def test_label_from_dict():
    data = {"_id": "lb1", "title": "Urgent", "color": "#ff0000", "isAction": True}
    lb = Label.from_dict(data)
    assert lb._id == "lb1"
    assert lb.color == "#ff0000"
    assert lb.is_action is True


def test_calendar_event_from_dict():
    data = {"_id": "ev1", "title": "Standup", "start": "2026-04-25T09:00:00Z"}
    ev = CalendarEvent.from_dict(data)
    assert ev._id == "ev1"
    assert ev.start == "2026-04-25T09:00:00Z"
    assert ev.is_all_day is False


def test_time_block_from_dict():
    data = {"_id": "tb1", "title": "Morning", "date": "2026-04-25", "time": "09:00"}
    tb = TimeBlock.from_dict(data)
    assert tb._id == "tb1"
    assert tb.time == "09:00"


def test_tracking_result_from_dict():
    data = {"startId": "t1", "startTimes": [1700000000000], "issues": []}
    tr = TrackingResult.from_dict(data)
    assert tr.start_id == "t1"
    assert tr.start_times == [1700000000000]
    assert tr.issues == []


def test_time_track_from_dict():
    data = {"taskId": "t1", "times": [1700000000000, 1700010000000]}
    tt = TimeTrack.from_dict(data)
    assert tt.task_id == "t1"
    assert len(tt.times) == 2


def test_kudos_from_dict():
    data = {"kudos": 50, "level": 3, "kudosRemaining": 100}
    k = Kudos.from_dict(data)
    assert k.kudos == 50
    assert k.level == 3
    assert k.kudos_remaining == 100


def test_account_profile_from_dict():
    data = {
        "userId": "u1",
        "email": "test@example.com",
        "marvinPoints": 500,
        "rewardPointsEarned": 10.5,
    }
    p = AccountProfile.from_dict(data)
    assert p.user_id == "u1"
    assert p.email == "test@example.com"
    assert p.marvin_points == 500
    assert p.reward_points_earned == 10.5


def test_reminder_from_dict():
    data = {
        "reminderId": "r1",
        "time": 1700000000,
        "title": "Take meds",
        "type": "T",
        "autoSnooze": True,
    }
    r = Reminder.from_dict(data)
    assert r.reminder_id == "r1"
    assert r.time == 1700000000
    assert r.auto_snooze is True


def test_reminder_to_dict():
    r = Reminder(reminder_id="r1", time=1700000000, title="Take meds", auto_snooze=True)
    d = r.to_dict()
    assert d["reminderId"] == "r1"
    assert d["time"] == 1700000000
    assert d["autoSnooze"] is True
    assert "reminder_id" not in d


def test_goal_section_from_dict():
    data = {"_id": "gs1", "title": "Q1 milestones"}
    gs = GoalSection.from_dict(data)
    assert gs._id == "gs1"
    assert gs.title == "Q1 milestones"


def test_goal_from_dict_with_sections():
    data = {
        "_id": "g1",
        "title": "Lose weight",
        "status": "active",
        "sections": [{"_id": "gs1", "title": "Phase 1"}],
    }
    g = Goal.from_dict(data)
    assert g._id == "g1"
    assert g.status == "active"
    assert len(g.sections) == 1
    assert isinstance(g.sections[0], GoalSection)


def test_habit_from_dict():
    data = {
        "_id": "h1",
        "title": "Meditate",
        "isPositive": True,
        "recordType": "boolean",
        "history": [1700000000000, 1, 1700086400000, 1],
    }
    h = Habit.from_dict(data)
    assert h._id == "h1"
    assert h.is_positive is True
    assert h.record_type == "boolean"
    assert len(h.history) == 4


def test_marvin_document_from_dict():
    data = {"_id": "doc1", "_rev": "1-abc", "db": "Habits", "title": "My doc"}
    doc = MarvinDocument.from_dict(data)
    assert doc.id == "doc1"
    assert doc.rev == "1-abc"
    assert doc.data == {"db": "Habits", "title": "My doc"}


def test_marvin_document_no_rev():
    data = {"_id": "doc2", "db": "Tasks"}
    doc = MarvinDocument.from_dict(data)
    assert doc.id == "doc2"
    assert doc.rev is None
    assert doc.data == {"db": "Tasks"}
