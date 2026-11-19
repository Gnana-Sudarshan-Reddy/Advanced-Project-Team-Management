"""Endpoints for calendar events (deadlines, milestones, meetings)."""

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_permission
from app.core.exceptions import AppError, NotFoundError
from app.core.permissions import Perm
from app.db.session import get_db
from app.models import CalendarEvent, Project, Task, User
from app.schemas.calendar_event import (
    CalendarEventCreate, CalendarEventOut, CalendarEventUpdate,
)
from app.services.access import _load_accessible_task, ensure_project_access
from app.services.activity import log_activity

router = APIRouter(prefix="/calendar-events", tags=["Calendar"])


@router.post("", response_model=CalendarEventOut, status_code=201)
def create_calendar_event(payload: CalendarEventCreate, db: Session = Depends(get_db),
                          user: User = Depends(require_permission(Perm.CALENDAR_MANAGE))):
    """Create a calendar event linked to a project/task/milestone."""
    if payload.end_datetime and payload.end_datetime <= payload.start_datetime:
        raise AppError("end_datetime must be after start_datetime", 422, "invalid_range")
    project = None
    if payload.project_id:
        project = ensure_project_access(db, user, payload.project_id)
    elif payload.task_id:
        task, project = _load_accessible_task(db, user, payload.task_id)
    elif payload.milestone_id:
        from app.models import ProjectMilestone
        milestone = db.get(ProjectMilestone, payload.milestone_id)
        if not milestone:
            raise NotFoundError("Milestone not found")
        project = ensure_project_access(db, user, milestone.project_id)
    event = CalendarEvent(**payload.model_dump(), created_by_id=user.id)
    db.add(event)
    if payload.task_id and payload.event_type == "task_deadline":
        task = db.get(Task, payload.task_id)
        if task:
            task.due_date = payload.start_datetime.date()
    db.flush()
    log_activity(db, user, "calendar_event.created",
                 project_id=(project.id if project else None),
                 details={"event_id": event.id, "title": event.title})
    db.commit()
    db.refresh(event)
    return event


@router.get("", response_model=list[CalendarEventOut])
def list_calendar_events(
    project_id: int | None = Query(None),
    start: datetime | None = Query(None),
    end: datetime | None = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List calendar events, optionally filtered by project and date range."""
    query = db.query(CalendarEvent)
    if project_id is not None:
        ensure_project_access(db, user, project_id)
        query = query.filter(CalendarEvent.project_id == project_id)
    else:
        # non-admin: only events on accessible projects
        from app.core.permissions import RoleName
        if user.role.name != RoleName.ADMIN.value:
            from app.services.access import accessible_project_ids
            query = query.filter(CalendarEvent.project_id.in_(accessible_project_ids(user)))
    if start:
        query = query.filter(CalendarEvent.start_datetime >= start)
    if end:
        query = query.filter(CalendarEvent.start_datetime <= end)
    return query.order_by(CalendarEvent.start_datetime.asc()).all()


@router.get("/{event_id}", response_model=CalendarEventOut)
def get_calendar_event(event_id: int, db: Session = Depends(get_db),
                       user: User = Depends(get_current_user)):
    """Return one calendar event after checking project access."""
    event = db.get(CalendarEvent, event_id)
    if not event:
        raise NotFoundError("Calendar event not found")
    if event.project_id:
        ensure_project_access(db, user, event.project_id)
    return event


@router.patch("/{event_id}", response_model=CalendarEventOut)
def update_calendar_event(event_id: int, payload: CalendarEventUpdate, db: Session = Depends(get_db),
                          user: User = Depends(require_permission(Perm.CALENDAR_MANAGE))):
    """Update a calendar event (supports dragging deadlines on the calendar)."""
    event = db.get(CalendarEvent, event_id)
    if not event:
        raise NotFoundError("Calendar event not found")
    if event.project_id:
        ensure_project_access(db, user, event.project_id)
    data = payload.model_dump(exclude_unset=True, exclude_none=True)
    if "end_datetime" in data and data["end_datetime"] and "start_datetime" in data and data["start_datetime"]:
        if data["end_datetime"] <= data["start_datetime"]:
            raise AppError("end_datetime must be after start_datetime", 422, "invalid_range")
    from app.services.utils import apply_changes
    changes = apply_changes(event, data)
    if event.task_id and event.event_type == "task_deadline" and "start_datetime" in data:
        task = db.get(Task, event.task_id)
        if task:
            task.due_date = event.start_datetime.date()
    if changes:
        log_activity(db, user, "calendar_event.updated",
                     project_id=event.project_id, details={"event_id": event_id, **changes})
    db.commit()
    db.refresh(event)
    return event


@router.delete("/{event_id}", status_code=204)
def delete_calendar_event(event_id: int, db: Session = Depends(get_db),
                          user: User = Depends(require_permission(Perm.CALENDAR_MANAGE))):
    """Delete a calendar event."""
    event = db.get(CalendarEvent, event_id)
    if not event:
        raise NotFoundError("Calendar event not found")
    if event.project_id:
        ensure_project_access(db, user, event.project_id)
    db.delete(event)
    db.commit()
    return None
