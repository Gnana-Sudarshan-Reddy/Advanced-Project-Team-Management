"""SQLAlchemy model for calendar events (deadlines, milestones, meetings)."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import utcnow


class CalendarEvent(Base):
    """A scheduled event shown on the project calendar."""

    __tablename__ = "calendar_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    event_type: Mapped[str] = mapped_column(String(30), index=True)  # task_deadline, milestone, meeting, custom
    start_datetime: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    end_datetime: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True, default=None)
    task_id: Mapped[int | None] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), index=True, default=None)
    milestone_id: Mapped[int | None] = mapped_column(ForeignKey("project_milestones.id", ondelete="CASCADE"), index=True, default=None)
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    project = relationship("Project", back_populates="calendar_events")
    task = relationship("Task")
    milestone = relationship("ProjectMilestone")
    created_by = relationship("User", lazy="joined")