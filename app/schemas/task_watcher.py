"""Validation and response schemas for task watchers."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.user import UserBrief


class TaskWatcherCreate(BaseModel):
    """Input for adding a watcher to a task."""

    user_id: int


class TaskWatcherOut(BaseModel):
    """Watcher fields returned by the API."""

    model_config = ConfigDict(from_attributes=True)
    id: int
    task_id: int
    user_id: int
    created_at: datetime
    user: UserBrief | None