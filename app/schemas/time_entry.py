"""Validation and response schemas for time entries."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.user import UserBrief


class TimeEntryBase(BaseModel):
    """Fields shared by time entry creation and details."""

    description: str | None = Field(default=None, max_length=1000)


class TimeEntryCreate(TimeEntryBase):
    """Input for starting a timer or recording manual time."""

    start_time: datetime | None = None
    end_time: datetime | None = None
    is_running: bool = False


class TimeEntryUpdate(BaseModel):
    """Optional fields accepted when changing a time entry."""

    description: str | None = Field(default=None, max_length=1000)
    end_time: datetime | None = None
    duration_minutes: int | None = Field(default=None, ge=0)
    is_running: bool | None = None


class TimeEntryOut(TimeEntryBase):
    """Time entry fields returned by the API."""

    model_config = ConfigDict(from_attributes=True)
    id: int
    task_id: int
    user_id: int
    start_time: datetime
    end_time: datetime | None
    duration_minutes: int | None
    is_running: bool
    created_at: datetime
    updated_at: datetime
    user: UserBrief | None