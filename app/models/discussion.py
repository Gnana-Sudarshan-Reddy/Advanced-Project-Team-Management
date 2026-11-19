"""SQLAlchemy models for project-level discussion boards and replies."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import utcnow


class ProjectDiscussion(Base):
    """A discussion thread within a project."""

    __tablename__ = "project_discussions"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(Text)
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    project = relationship("Project", back_populates="discussions")
    created_by = relationship("User", lazy="joined")
    replies = relationship("DiscussionReply", back_populates="discussion", cascade="all, delete-orphan", passive_deletes=True)


class DiscussionReply(Base):
    """A reply to a project discussion, optionally nested under another reply."""

    __tablename__ = "discussion_replies"

    id: Mapped[int] = mapped_column(primary_key=True)
    discussion_id: Mapped[int] = mapped_column(ForeignKey("project_discussions.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    parent_reply_id: Mapped[int | None] = mapped_column(ForeignKey("discussion_replies.id", ondelete="CASCADE"), index=True, default=None)
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    discussion = relationship("ProjectDiscussion", back_populates="replies")
    user = relationship("User", lazy="joined")
    parent_reply = relationship("DiscussionReply", remote_side=[id], back_populates="replies")
    replies = relationship("DiscussionReply", back_populates="parent_reply")
    reactions = relationship("CommentReaction", back_populates="discussion_reply", cascade="all, delete-orphan", passive_deletes=True)