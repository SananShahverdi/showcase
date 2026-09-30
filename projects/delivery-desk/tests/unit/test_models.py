from datetime import date

import pytest
from pydantic import ValidationError

from delivery_desk.api.app import TaskEdit, TaskFields


def test_task_fields_apply_defaults_and_trim_text():
    task = TaskFields(title="  Ship search  ")
    assert task.title == "Ship search"
    assert (task.project, task.status, task.priority, task.due_date) == ("General", "backlog", "medium", None)


@pytest.mark.parametrize("payload", [
    {"title": "   "},
    {"title": "x" * 161},
    {"title": "Task", "status": "blocked"},
    {"title": "Task", "priority": "urgent"},
    {"title": "Task", "due_date": "not-a-date"},
    {"title": "Task", "owner": "unknown field"},
])
def test_task_fields_reject_invalid_input(payload):
    with pytest.raises(ValidationError):
        TaskFields(**payload)


def test_edit_requires_a_version_and_forbids_nulling_required_fields():
    with pytest.raises(ValidationError):
        TaskEdit(title="No version")
    with pytest.raises(ValidationError):
        TaskEdit(version=0)
    for field in ("title", "project", "status", "priority"):
        with pytest.raises(ValidationError):
            TaskEdit(version=1, **{field: None})


def test_edit_can_clear_the_due_date_and_only_dumps_sent_fields():
    edit = TaskEdit(version=3, due_date=None)
    assert edit.model_dump(exclude_unset=True) == {"version": 3, "due_date": None}
    assert TaskEdit(version=1, due_date="2026-10-01").due_date == date(2026, 10, 1)
