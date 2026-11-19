"""Validation and response schemas for project milestones."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import MilestoneStatus
from app.schemas.user import UserBrief


class MilestoneBase(BaseModel):
    """Fields shared by milestone creation and details."""

    name: str = Field(min_length=3, max_length=150)
    description: str | None = Field(default=None, max_length=2000)
    due_date: date | None = None
    status: MilestoneStatus = MilestoneStatus.UPCOMING


class MilestoneCreate(MilestoneBase):
    """Input for creating a milestone."""


class MilestoneUpdate(BaseModel):
    """Optional fields accepted when changing a milestone."""

    name: str | None = Field(default=None, min_length=3, max_length=150)
    description: str | None = Field(default=None, max_length=2000)
    due_date: date | None = None
    status: MilestoneStatus | None = None


class MilestoneOut(MilestoneBase):
    """Milestone fields returned by the API."""

    model_config = ConfigDict(from_attributes=True)
    id: int
    project_id: int
    created_by_id: int | None
    created_at: datetime
    updated_at: datetime