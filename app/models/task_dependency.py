"""SQLAlchemy model for task dependencies (predecessor/successor links)."""

from sqlalchemy import ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin


class TaskDependency(Base, TimestampMixin):
    """Declares that one task (task) depends on another (depends_on_task) being completed first."""

    __tablename__ = "task_dependencies"

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), index=True)
    depends_on_task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), index=True)

    __table_args__ = (
        UniqueConstraint("task_id", "depends_on_task_id", name="uq_task_dependency"),
    )

    task = relationship("Task", foreign_keys=[task_id], back_populates="dependencies_as_dependent")
    depends_on_task = relationship("Task", foreign_keys=[depends_on_task_id], back_populates="dependencies_as_prerequisite")
