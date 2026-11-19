"""SQLAlchemy model for time spent on tasks."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import utcnow


class TimeEntry(Base):
    """A record of time spent (or in-progress timer) on a task by a team member."""

    __tablename__ = "time_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_minutes: Mapped[int | None] = mapped_column(Integer)
    description: Mapped[str | None] = mapped_column(Text)
    is_running: Mapped[bool] = mapped_column(default=False)

    task = relationship("Task", back_populates="time_entries")
    user = relationship("User", lazy="joined")