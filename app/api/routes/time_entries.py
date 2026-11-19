"""Endpoints for time tracking (start/stop timers and manual entries)."""

from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_permission
from app.core.exceptions import NotFoundError
from app.core.permissions import Perm
from app.db.session import get_db
from app.models import Task, TimeEntry, User
from app.schemas.time_entry import TimeEntryCreate, TimeEntryOut, TimeEntryUpdate
from app.services.access import _load_accessible_task, get_user_or_404
from app.services.activity import log_activity
from app.services.time_tracking import add_manual_entry, get_running_timer, start_timer, stop_timer, task_total_time

router = APIRouter(prefix="/time-entries", tags=["Time Tracking"])


@router.post("/{task_id}/start", response_model=TimeEntryOut, status_code=201)
def start_time_timer(task_id: int, db: Session = Depends(get_db),
                     user: User = Depends(require_permission(Perm.TIME_TRACKING))):
    """Start a running timer for a task."""
    task, project = _load_accessible_task(db, user, task_id)
    entry = start_timer(db, task_id, user)
    log_activity(db, user, "time.timer_started", project_id=project.id, task_id=task.id,
                 details={"time_entry_id": entry.id})
    db.commit()
    db.refresh(entry)
    return entry


@router.post("/{task_id}/stop", response_model=TimeEntryOut)
def stop_time_timer(task_id: int, db: Session = Depends(get_db),
                    user: User = Depends(require_permission(Perm.TIME_TRACKING))):
    """Stop the running timer for a task."""
    task, project = _load_accessible_task(db, user, task_id)
    entry = stop_timer(db, task_id, user)
    log_activity(db, user, "time.timer_stopped", project_id=project.id, task_id=task.id,
                 details={"time_entry_id": entry.id, "duration_minutes": entry.duration_minutes})
    db.commit()
    db.refresh(entry)
    return entry


@router.post("/{task_id}/manual", response_model=TimeEntryOut, status_code=201)
def add_manual_time_entry(task_id: int, payload: TimeEntryCreate, db: Session = Depends(get_db),
                          user: User = Depends(require_permission(Perm.TIME_TRACKING))):
    """Manually record time spent on a task."""
    task, project = _load_accessible_task(db, user, task_id)
    start_time = payload.start_time or datetime.utcnow()
    entry = add_manual_entry(db, task_id, user, start_time, payload.end_time, payload.description)
    log_activity(db, user, "time.manual_entry", project_id=project.id, task_id=task.id,
                 details={"time_entry_id": entry.id, "duration_minutes": entry.duration_minutes})
    db.commit()
    db.refresh(entry)
    return entry


@router.get("/{task_id}", response_model=list[TimeEntryOut])
def list_time_entries(task_id: int, db: Session = Depends(get_db),
                      user: User = Depends(get_current_user)):
    """List time entries of a task."""
    task, _ = _load_accessible_task(db, user, task_id)
    return task.time_entries


@router.get("/{task_id}/running", response_model=TimeEntryOut | None)
def running_timer(task_id: int, db: Session = Depends(get_db),
                  user: User = Depends(require_permission(Perm.TIME_TRACKING))):
    """Return the user's currently running timer for a task, if any."""
    task, _ = _load_accessible_task(db, user, task_id)
    return get_running_timer(db, task_id, user)


@router.get("/{task_id}/total", response_model=dict)
def total_time(task_id: int, db: Session = Depends(get_db),
               user: User = Depends(get_current_user)):
    """Total recorded minutes for a task."""
    task, _ = _load_accessible_task(db, user, task_id)
    minutes = task_total_time(db, task_id, user)
    return {"task_id": task_id, "total_minutes": minutes, "total_hours": round(minutes / 60, 2)}


@router.patch("/{time_entry_id}", response_model=TimeEntryOut)
def update_time_entry(time_entry_id: int, payload: TimeEntryUpdate, db: Session = Depends(get_db),
                      user: User = Depends(require_permission(Perm.TIME_TRACKING))):
    """Update a time entry owned by the current user."""
    entry = db.get(TimeEntry, time_entry_id)
    if not entry:
        raise NotFoundError("Time entry not found")
    if entry.user_id != user.id:
        from app.core.exceptions import ForbiddenError
        raise ForbiddenError("You can only edit your own time entries")
    task, project = _load_accessible_task(db, user, entry.task_id)
    data = payload.model_dump(exclude_unset=True, exclude_none=True)
    from app.services.utils import apply_changes
    changes = apply_changes(entry, data)
    if changes:
        log_activity(db, user, "time.entry_updated", project_id=project.id, task_id=task.id,
                     details={"time_entry_id": time_entry_id, **changes})
    db.commit()
    db.refresh(entry)
    return entry


@router.delete("/{time_entry_id}", status_code=204)
def delete_time_entry(time_entry_id: int, db: Session = Depends(get_db),
                      user: User = Depends(require_permission(Perm.TIME_TRACKING))):
    """Delete a time entry owned by the current user."""
    entry = db.get(TimeEntry, time_entry_id)
    if not entry:
        raise NotFoundError("Time entry not found")
    if entry.user_id != user.id:
        from app.core.exceptions import ForbiddenError
        raise ForbiddenError("You can only delete your own time entries")
    task, project = _load_accessible_task(db, user, entry.task_id)
    db.delete(entry)
    db.commit()
    return None