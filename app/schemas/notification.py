"""Validation and response schemas for notifications."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import NotificationType


class NotificationOut(BaseModel):
    """Notification fields returned by the API."""

    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    title: str
    message: str
    type: str
    related_entity_type: str | None
    related_entity_id: int | None
    is_read: bool
    read_at: datetime | None
    created_at: datetime


class NotificationPreference(BaseModel):
    """User notification preferences."""

    email_enabled: bool = True
    push_enabled: bool = True
    task_assigned: bool = True
    deadline_approaching: bool = True
    mention: bool = True
    comment_added: bool = True
    approval_requested: bool = True