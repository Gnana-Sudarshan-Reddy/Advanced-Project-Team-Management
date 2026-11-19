"""Validation and response schemas for task dependencies."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TaskDependencyCreate(BaseModel):
    """Input for creating a task dependency."""

    task_id: int = Field(gt=0)
    depends_on_task_id: int = Field(gt=0)


class TaskDependencyOut(BaseModel):
    """Dependency fields returned by the API."""

    model_config = ConfigDict(from_attributes=True)
    id: int
    task_id: int
    depends_on_task_id: int
    created_at: datetime