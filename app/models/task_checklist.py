"""SQLAlchemy model for checklists attached to tasks."""

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin


class TaskChecklist(Base, TimestampMixin):
    """A checklist item belonging to a task."""

    __tablename__ = "task_checklists"

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    is_completed: Mapped[bool] = mapped_column(default=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    task = relationship("Task", back_populates="checklists")