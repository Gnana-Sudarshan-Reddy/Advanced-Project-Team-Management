"""SQLAlchemy model for emoji reactions on comments and discussion replies."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import utcnow


class CommentReaction(Base):
    """An emoji reaction added by a user to a task comment or discussion reply."""

    __tablename__ = "comment_reactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    task_comment_id: Mapped[int | None] = mapped_column(ForeignKey("task_comments.id", ondelete="CASCADE"), index=True, default=None)
    discussion_reply_id: Mapped[int | None] = mapped_column(ForeignKey("discussion_replies.id", ondelete="CASCADE"), index=True, default=None)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    reaction: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    task_comment = relationship("TaskComment", back_populates="reactions")
    discussion_reply = relationship("DiscussionReply", back_populates="reactions")
    user = relationship("User", lazy="joined")