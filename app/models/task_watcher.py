"""SQLAlchemy model for users watching/following a task."""

from sqlalchemy import ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin


class TaskWatcher(Base, TimestampMixin):
    """A user who receives updates when a task they follow changes."""

    __tablename__ = "task_watchers"
    __table_args__ = (UniqueConstraint("task_id", "user_id", name="uq_task_watcher"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    task = relationship("Task", back_populates="watchers")
    user = relationship("User", lazy="joined")