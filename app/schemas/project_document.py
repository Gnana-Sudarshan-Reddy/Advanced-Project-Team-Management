"""Validation schemas for project documents."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.user import UserBrief


class ProjectDocumentCreate(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    file_path: str = Field(min_length=1, max_length=500)
    file_size: int | None = None
    content_type: str | None = Field(default=None, max_length=100)
    description: str | None = Field(default=None, max_length=2000)


class ProjectDocumentOut(ProjectDocumentCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_id: int
    uploaded_by_id: int
    created_at: datetime
    uploaded_by: UserBrief | None
