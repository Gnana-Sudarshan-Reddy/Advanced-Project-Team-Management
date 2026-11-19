"""Validation and response schemas for timesheets."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import TimesheetStatus
from app.schemas.user import UserBrief


class TimesheetBase(BaseModel):
    """Fields shared by timesheet creation and details."""

    week_start_date: date
    status: TimesheetStatus = TimesheetStatus.DRAFT
    total_hours: float = Field(default=0, ge=0)


class TimesheetCreate(TimesheetBase):
    """Input for creating a timesheet."""


class TimesheetUpdate(BaseModel):
    """Optional fields accepted when changing a timesheet."""

    status: TimesheetStatus | None = None
    total_hours: float | None = Field(default=None, ge=0)


class TimesheetOut(TimesheetBase):
    """Timesheet fields returned by the API."""

    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    submitted_at: datetime | None
    approved_by_id: int | None
    approved_at: datetime | None
    created_at: datetime
    updated_at: datetime
    user: UserBrief | None
    approved_by: UserBrief | None


class TimesheetSubmit(BaseModel):
    """Request to submit a draft timesheet."""


class TimesheetApprove(BaseModel):
    """Request to approve or reject a timesheet."""

    approve: bool