"""Validation and response schemas for subtasks (self-referential tasks)."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import TaskPriority, TaskStatus
from app.schemas.user import UserBrief


class SubtaskBase(BaseModel):
    """Fields shared by subtask creation and details."""

    title: str = Field(min_length=3, max_length=200)
    description: str | None = Field(default=None, max_length=10000)
    status: TaskStatus = TaskStatus.TODO
    priority: TaskPriority = TaskPriority.MEDIUM
    due_date: date | None = None


class SubtaskCreate(SubtaskBase):
    """Input for creating a subtask under a parent task."""


class SubtaskUpdate(BaseModel):
    """Optional fields accepted when changing a subtask."""

    title: str | None = Field(default=None, min_length=3, max_length=200)
    description: str | None = Field(default=None, max_length=10000)
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    due_date: date | None = None


class SubtaskOut(SubtaskBase):
    """Subtask fields returned by the API."""

    model_config = ConfigDict(from_attributes=True)
    id: int
    task_id: int
    assignee: UserBrief | None
    created_at: datetime
    updated_at: datetime