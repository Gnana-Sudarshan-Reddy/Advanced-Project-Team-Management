"""Validation and response schemas for task checklists."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TaskChecklistBase(BaseModel):
    """Fields shared by checklist creation and details."""

    title: str = Field(min_length=1, max_length=255)
    is_completed: bool = False
    sort_order: int = 0


class TaskChecklistCreate(TaskChecklistBase):
    """Input for creating a checklist item."""


class TaskChecklistUpdate(BaseModel):
    """Optional fields accepted when changing a checklist item."""

    title: str | None = Field(default=None, min_length=1, max_length=255)
    is_completed: bool | None = None
    sort_order: int | None = None


class TaskChecklistOut(TaskChecklistBase):
    """Checklist item fields returned by the API."""

    model_config = ConfigDict(from_attributes=True)
    id: int
    task_id: int
    created_at: datetime
    updated_at: datetime