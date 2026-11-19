"""Validation and response schemas for task attachments."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.user import UserBrief


class TaskAttachmentOut(BaseModel):
    """Attachment fields returned by the API."""

    model_config = ConfigDict(from_attributes=True)
    id: int
    task_id: int
    uploaded_by_id: int
    filename: str
    file_path: str
    file_size: int | None
    content_type: str | None
    created_at: datetime
    uploaded_by: UserBrief | None


class TaskAttachmentUpload(BaseModel):
    """Metadata returned after a file upload."""

    task_id: int
    filename: str
    file_path: str
    file_size: int | None
    content_type: str | None