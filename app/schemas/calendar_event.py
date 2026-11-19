"""Validation and response schemas for calendar events."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CalendarEventBase(BaseModel):
    """Fields shared by calendar event creation and details."""

    title: str = Field(min_length=3, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    event_type: str = Field(min_length=1, max_length=30)
    start_datetime: datetime
    end_datetime: datetime | None = None
    project_id: int | None = None
    task_id: int | None = None
    milestone_id: int | None = None


class CalendarEventCreate(CalendarEventBase):
    """Input for creating a calendar event."""


class CalendarEventUpdate(BaseModel):
    """Optional fields accepted when changing a calendar event."""

    title: str | None = Field(default=None, min_length=3, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    event_type: str | None = Field(default=None, min_length=1, max_length=30)
    start_datetime: datetime | None = None
    end_datetime: datetime | None = None
    project_id: int | None = None
    task_id: int | None = None
    milestone_id: int | None = None


class CalendarEventOut(CalendarEventBase):
    """Calendar event fields returned by the API."""

    model_config = ConfigDict(from_attributes=True)
    id: int
    created_by_id: int
    created_at: datetime