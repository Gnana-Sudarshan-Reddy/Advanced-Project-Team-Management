"""SQLAlchemy model for user notifications."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import NotificationType
from app.models.mixins import utcnow


class Notification(Base):
    """A notification delivered to a user, with read/unread tracking."""

    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    message: Mapped[str] = mapped_column(Text)
    type: Mapped[str] = mapped_column(String(40), index=True)
    related_entity_type: Mapped[str | None] = mapped_column(String(50), default=None)
    related_entity_id: Mapped[int | None] = mapped_column(Integer, default=None, index=True)
    is_read: Mapped[bool] = mapped_column(default=False, index=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

    user = relationship("User", lazy="joined")


class NotificationPreference(Base):
    """Persistent per-user notification preferences."""

    __tablename__ = "notification_preferences"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True)
    email_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    push_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    task_assigned: Mapped[bool] = mapped_column(Boolean, default=True)
    deadline_approaching: Mapped[bool] = mapped_column(Boolean, default=True)
    mention: Mapped[bool] = mapped_column(Boolean, default=True)
    comment_added: Mapped[bool] = mapped_column(Boolean, default=True)
    approval_requested: Mapped[bool] = mapped_column(Boolean, default=True)

    user = relationship("User", back_populates="notification_preference")
