"""Timesheet business logic: aggregation, submission and approval."""

from datetime import date, datetime, timedelta, timezone

from app.core.exceptions import AppError, ConflictError, ForbiddenError, NotFoundError
from app.models import TimeEntry, Timesheet, User
from app.models.enums import TimesheetStatus
from app.services.access import get_user_or_404


def _week_start(d: date) -> date:
    """Return the Monday of the week containing d."""
    return d - timedelta(days=d.weekday())


def get_or_create_timesheet(db, user: User, week_start: date) -> Timesheet:
    """Return the existing timesheet for a user/week or create a draft."""
    timesheet = db.query(Timesheet).filter(
        Timesheet.user_id == user.id, Timesheet.week_start_date == week_start
    ).first()
    if not timesheet:
        timesheet = Timesheet(user_id=user.id, week_start_date=week_start, status=TimesheetStatus.DRAFT.value)
        db.add(timesheet)
        db.flush()
    return timesheet


def submit_timesheet(db, user: User, week_start: date) -> Timesheet:
    """Submit a draft timesheet for manager approval."""
    timesheet = get_or_create_timesheet(db, user, week_start)
    if timesheet.status != TimesheetStatus.DRAFT.value:
        raise ConflictError("Only draft timesheets can be submitted", 409, "not_draft")
    total = _total_hours_for_week(db, user.id, week_start)
    timesheet.status = TimesheetStatus.SUBMITTED.value
    timesheet.total_hours = total
    timesheet.submitted_at = datetime.now(timezone.utc)
    db.flush()
    return timesheet


def approve_timesheet(db, timesheet_id: int, manager: User, approve: bool) -> Timesheet:
    """Approve or reject a submitted timesheet (managers/admins only)."""
    timesheet = db.get(Timesheet, timesheet_id)
    if not timesheet:
        raise NotFoundError("Timesheet not found")
    if timesheet.status != TimesheetStatus.SUBMITTED.value:
        raise ConflictError("Only submitted timesheets can be approved or rejected", 409, "not_submitted")
    timesheet.status = TimesheetStatus.APPROVED.value if approve else TimesheetStatus.REJECTED.value
    timesheet.approved_by_id = manager.id
    timesheet.approved_at = datetime.now(timezone.utc)
    db.flush()
    return timesheet


def _total_hours_for_week(db, user_id: int, week_start: date) -> float:
    week_end = week_start + timedelta(days=6)
    rows = db.query(TimeEntry).filter(
        TimeEntry.user_id == user_id,
        TimeEntry.is_running == False,  # noqa: E712
        TimeEntry.start_time >= week_start,
        TimeEntry.start_time <= week_end,
    ).all()
    return round(sum((r.duration_minutes or 0) for r in rows) / 60, 2)