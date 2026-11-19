"""SQLAlchemy model for project milestones."""

from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import MilestoneStatus
from app.models.mixins import TimestampMixin


class ProjectMilestone(Base, TimestampMixin):
    """A milestone that groups tasks and marks a significant point in a project."""

    __tablename__ = "project_milestones"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(150), index=True)
    description: Mapped[str | None] = mapped_column(Text)
    due_date: Mapped[date | None] = mapped_column(Date, index=True)
    status: Mapped[str] = mapped_column(String(20), default=MilestoneStatus.UPCOMING.value, index=True)
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    project = relationship("Project", back_populates="milestones")
    created_by = relationship("User", lazy="joined")
    tasks = relationship("Task", back_populates="milestone")