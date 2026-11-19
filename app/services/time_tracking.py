"""Time tracking business logic: start/stop timers and manual time entries."""

from datetime import datetime, timezone

from app.core.exceptions import AppError, ConflictError, ForbiddenError, NotFoundError
from app.models import Task, TimeEntry, User
from app.services.access import ensure_task_access, get_task_or_404, get_user_or_404


def start_timer(db, task_id: int, user: User, description: str | None = None) -> TimeEntry:
    """Start a running timer for a task. Fails if the user already has a running timer on that task."""
    task, _ = ensure_task_access(db, user, task_id)
    running = db.query(TimeEntry).filter(
        TimeEntry.task_id == task_id, TimeEntry.user_id == user.id, TimeEntry.is_running == True  # noqa: E712
    ).first()
    if running:
        raise ConflictError("A timer is already running for this task", 409, "timer_already_running")
    entry = TimeEntry(task_id=task_id, user_id=user.id, start_time=datetime.now(timezone.utc),
                      is_running=True, description=description)
    db.add(entry)
    db.flush()
    return entry


def stop_timer(db, task_id: int, user: User) -> TimeEntry:
    """Stop the user's running timer for a task and record elapsed duration."""
    task, _ = ensure_task_access(db, user, task_id)
    entry = db.query(TimeEntry).filter(
        TimeEntry.task_id == task_id, TimeEntry.user_id == user.id, TimeEntry.is_running == True  # noqa: E712
    ).first()
    if not entry:
        raise NotFoundError("No running timer found for this task")
    now = datetime.now(timezone.utc)
    entry.end_time = now
    entry.is_running = False
    if entry.start_time:
        entry.duration_minutes = int((now - entry.start_time).total_seconds() / 60)
    db.flush()
    return entry


def add_manual_entry(db, task_id: int, user: User, start_time: datetime, end_time: datetime,
                     description: str | None = None) -> TimeEntry:
    """Manually record time spent on a task."""
    task, _ = ensure_task_access(db, user, task_id)
    if end_time <= start_time:
        raise AppError("end_time must be after start_time", 422, "invalid_time_range")
    duration_minutes = int((end_time - start_time).total_seconds() / 60)
    entry = TimeEntry(task_id=task_id, user_id=user.id, start_time=start_time, end_time=end_time,
                      duration_minutes=duration_minutes, description=description, is_running=False)
    db.add(entry)
    db.flush()
    return entry


def get_running_timer(db, task_id: int, user: User):
    """Return the user's currently running timer for a task, if any."""
    task, _ = ensure_task_access(db, user, task_id)
    return db.query(TimeEntry).filter(
        TimeEntry.task_id == task_id, TimeEntry.user_id == user.id, TimeEntry.is_running == True  # noqa: E712
    ).first()


def task_total_time(db, task_id: int, user: User | None = None) -> int:
    """Total recorded minutes for a task, optionally filtered by user."""
    query = db.query(TimeEntry).filter(TimeEntry.task_id == task_id, TimeEntry.is_running == False)  # noqa: E712
    if user is not None:
        query = query.filter(TimeEntry.user_id == user.id)
    rows = query.all()
    return sum((r.duration_minutes or 0) for r in rows)