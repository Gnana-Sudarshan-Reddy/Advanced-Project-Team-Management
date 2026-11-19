"""Recurring task materialization for the background worker."""

import calendar
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.models import Task
from app.models.enums import TaskStatus
from app.services.task_history import record_task_history


def _next_date(value: date, pattern: str) -> date:
    if pattern == "daily":
        return value + timedelta(days=1)
    if pattern == "weekly":
        return value + timedelta(days=7)
    month = value.month % 12 + 1
    year = value.year + (value.month // 12)
    return date(year, month, min(value.day, calendar.monthrange(year, month)[1]))


def materialize_due_recurring_tasks(db: Session, today: date | None = None) -> int:
    """Create one next occurrence for each recurring task that is due."""
    today = today or date.today()
    tasks = db.query(Task).filter(
        Task.is_recurring.is_(True), Task.recurrence_pattern.is_not(None),
        Task.recurrence_next_date.is_not(None), Task.recurrence_next_date <= today,
    ).all()
    created = 0
    for task in tasks:
        occurrence_date = task.recurrence_next_date
        next_date = _next_date(occurrence_date, task.recurrence_pattern)
        occurrence = Task(
            title=task.title, description=task.description, status=TaskStatus.TODO.value,
            priority=task.priority, due_date=occurrence_date, start_date=occurrence_date,
            estimated_date=task.estimated_date, estimated_hours=task.estimated_hours,
            is_recurring=True, recurrence_pattern=task.recurrence_pattern,
            recurrence_next_date=next_date, project_id=task.project_id,
            assignee_id=task.assignee_id, created_by_id=task.created_by_id,
            updated_by_id=task.created_by_id, milestone_id=task.milestone_id,
        )
        db.add(occurrence)
        db.flush()
        task.recurrence_next_date = next_date
        record_task_history(db, occurrence.id, task.created_by, "created", {"recurrence_of": task.id},
                            "Recurring task occurrence created")
        created += 1
    db.commit()
    return created
