"""Validation and response schemas for comment reactions."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.user import UserBrief


class CommentReactionCreate(BaseModel):
    """Input for adding a reaction to a comment or reply."""

    task_comment_id: int | None = None
    discussion_reply_id: int | None = None
    reaction: str = Field(min_length=1, max_length=20)


class CommentReactionOut(BaseModel):
    """Reaction fields returned by the API."""

    model_config = ConfigDict(from_attributes=True)
    id: int
    task_comment_id: int | None
    discussion_reply_id: int | None
    user_id: int
    reaction: str
    created_at: datetime
    user: UserBrief | None