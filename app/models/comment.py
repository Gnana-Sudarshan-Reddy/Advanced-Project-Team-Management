"""SQLAlchemy model for comments attached to tasks."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import utcnow


class TaskComment(Base):
    """A message written by a user on a task."""

    __tablename__ = "task_comments"

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    parent_comment_id: Mapped[int | None] = mapped_column(ForeignKey("task_comments.id", ondelete="CASCADE"), index=True, default=None)
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    task = relationship("Task", back_populates="comments")
    user = relationship("User", lazy="joined")
    parent_comment = relationship("TaskComment", remote_side=[id], back_populates="replies")
    replies = relationship("TaskComment", back_populates="parent_comment")
    reactions = relationship("CommentReaction", back_populates="task_comment", cascade="all, delete-orphan", passive_deletes=True)