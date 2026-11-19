"""Endpoints for weekly timesheets and their approval workflow."""

from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_permission
from app.core.exceptions import AppError, NotFoundError
from app.core.permissions import Perm, RoleName
from app.db.session import get_db
from app.models import Timesheet, User
from app.models.enums import TimesheetStatus
from app.schemas.timesheet import (
    TimesheetApprove, TimesheetCreate, TimesheetOut, TimesheetSubmit, TimesheetUpdate,
)
from app.services.access import get_user_or_404
from app.services.activity import log_activity
from app.services.timesheet import approve_timesheet, get_or_create_timesheet, submit_timesheet

router = APIRouter(prefix="/timesheets", tags=["Timesheets"])


@router.post("", response_model=TimesheetOut, status_code=201)
def create_timesheet(payload: TimesheetCreate, db: Session = Depends(get_db),
                     user: User = Depends(require_permission(Perm.TIME_TRACKING))):
    """Create or get the draft timesheet for a user/week."""
    get_user_or_404(db, user.id)
    timesheet = get_or_create_timesheet(db, user, payload.week_start_date)
    return timesheet


@router.get("/me", response_model=list[TimesheetOut])
def my_timesheets(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """List the current user's timesheets."""
    return db.query(Timesheet).filter(Timesheet.user_id == user.id).order_by(Timesheet.week_start_date.desc()).all()


@router.get("/me/{week_start_date}", response_model=TimesheetOut)
def my_timesheet(week_start_date: date, db: Session = Depends(get_db),
                 user: User = Depends(get_current_user)):
    """Return the current user's timesheet for a given week."""
    timesheet = get_or_create_timesheet(db, user, week_start_date)
    return timesheet


@router.post("/me/{week_start_date}/submit", response_model=TimesheetOut)
def submit_my_timesheet(week_start_date: date, payload: TimesheetSubmit, db: Session = Depends(get_db),
                        user: User = Depends(require_permission(Perm.TIME_TRACKING))):
    """Submit a draft timesheet for approval."""
    timesheet = submit_timesheet(db, user, week_start_date)
    db.commit()
    db.refresh(timesheet)
    return timesheet


@router.get("", response_model=list[TimesheetOut])
def list_timesheets(db: Session = Depends(get_db), user: User = Depends(require_permission(Perm.TIMESHEETS_MANAGE))):
    """List all timesheets (managers/admins)."""
    return db.query(Timesheet).order_by(Timesheet.week_start_date.desc()).all()


@router.patch("/{timesheet_id}/approve", response_model=TimesheetOut)
def approve_timesheet_route(timesheet_id: int, payload: TimesheetApprove, db: Session = Depends(get_db),
                            manager: User = Depends(require_permission(Perm.TIMESHEETS_MANAGE))):
    """Approve or reject a submitted timesheet."""
    timesheet = approve_timesheet(db, timesheet_id, manager, payload.approve)
    db.commit()
    db.refresh(timesheet)
    return timesheet


@router.get("/{timesheet_id}", response_model=TimesheetOut)
def get_timesheet(timesheet_id: int, db: Session = Depends(get_db),
                  user: User = Depends(get_current_user)):
    """Return one timesheet (owner or manager/admin)."""
    timesheet = db.get(Timesheet, timesheet_id)
    if not timesheet:
        raise NotFoundError("Timesheet not found")
    if timesheet.user_id != user.id and user.role.name not in (RoleName.ADMIN.value, RoleName.PROJECT_MANAGER.value):
        from app.core.exceptions import ForbiddenError
        raise ForbiddenError("You can only view your own timesheets")
    return timesheet