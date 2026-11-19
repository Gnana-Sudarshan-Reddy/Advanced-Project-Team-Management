"""Validation and response schemas for project approvals."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ApprovalStatus
from app.schemas.user import UserBrief


class ProjectApprovalBase(BaseModel):
    """Fields shared by approval creation and details."""

    task_id: int | None = None
    comments: str | None = Field(default=None, max_length=2000)


class ProjectApprovalCreate(ProjectApprovalBase):
    """Input for requesting a project approval."""


class ProjectApprovalUpdate(BaseModel):
    """Fields a reviewer submits when approving or rejecting."""

    status: ApprovalStatus
    comments: str | None = Field(default=None, max_length=2000)


class ProjectApprovalOut(ProjectApprovalBase):
    """Approval fields returned by the API."""

    model_config = ConfigDict(from_attributes=True)
    id: int
    project_id: int
    submitted_by_id: int
    status: ApprovalStatus
    reviewer_id: int | None
    reviewed_at: datetime | None
    created_at: datetime
    submitted_by: UserBrief | None
    reviewer: UserBrief | None