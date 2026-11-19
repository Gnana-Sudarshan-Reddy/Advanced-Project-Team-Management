"""Validation and response schemas for project discussions and replies."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.user import UserBrief


class DiscussionBase(BaseModel):
    """Fields shared by discussion creation and details."""

    title: str = Field(min_length=3, max_length=200)
    content: str = Field(min_length=1, max_length=10000)


class DiscussionCreate(DiscussionBase):
    """Input for creating a project discussion."""


class DiscussionUpdate(BaseModel):
    """Optional fields accepted when changing a discussion."""

    title: str | None = Field(default=None, min_length=3, max_length=200)
    content: str | None = Field(default=None, min_length=1, max_length=10000)


class DiscussionOut(DiscussionBase):
    """Discussion fields returned by the API."""

    model_config = ConfigDict(from_attributes=True)
    id: int
    project_id: int
    created_by_id: int
    created_at: datetime
    updated_at: datetime
    created_by: UserBrief | None


class DiscussionReplyBase(BaseModel):
    """Fields shared by discussion reply creation and details."""

    content: str = Field(min_length=1, max_length=10000)
    parent_reply_id: int | None = None


class DiscussionReplyCreate(DiscussionReplyBase):
    """Input for creating a discussion reply."""


class DiscussionReplyOut(DiscussionReplyBase):
    """Discussion reply fields returned by the API."""

    model_config = ConfigDict(from_attributes=True)
    id: int
    discussion_id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    user: UserBrief | None