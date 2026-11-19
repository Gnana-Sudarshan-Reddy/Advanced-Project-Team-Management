"""SQLAlchemy model for work items that belong to a project."""

from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import TaskPriority, TaskStatus
from app.models.mixins import TimestampMixin


class Task(Base, TimestampMixin):
    """A project work item with status, priority, dates, and optional assignee."""

    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200), index=True)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default=TaskStatus.TODO.value, index=True)
    priority: Mapped[str] = mapped_column(String(20), default=TaskPriority.MEDIUM.value, index=True)
    due_date: Mapped[date | None] = mapped_column(Date, index=True)
    start_date: Mapped[date | None] = mapped_column(Date, index=True)
    estimated_date: Mapped[date | None] = mapped_column(Date)
    estimated_hours: Mapped[float | None] = mapped_column(default=None)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_recurring: Mapped[bool] = mapped_column(default=False)
    recurrence_pattern: Mapped[str | None] = mapped_column(String(20))  # daily, weekly, monthly

    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    assignee_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    updated_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    parent_task_id: Mapped[int | None] = mapped_column(ForeignKey("tasks.id", ondelete="SET NULL"), index=True)
    milestone_id: Mapped[int | None] = mapped_column(ForeignKey("project_milestones.id", ondelete="SET NULL"), index=True, default=None)

    project = relationship("Project", back_populates="tasks")
    milestone = relationship("ProjectMilestone", back_populates="tasks")
    assignee = relationship("User", foreign_keys=[assignee_id], lazy="selectin")
    created_by = relationship("User", foreign_keys=[created_by_id], lazy="selectin")
    updated_by = relationship("User", foreign_keys=[updated_by_id], lazy="selectin")
    parent_task = relationship("Task", remote_side=[id], back_populates="subtasks_orm")
    subtasks_orm = relationship("Task", foreign_keys=[parent_task_id], back_populates="parent_task")
    comments = relationship("TaskComment", back_populates="task", cascade="all, delete-orphan", passive_deletes=True)
    attachments = relationship("TaskAttachment", back_populates="task", cascade="all, delete-orphan", passive_deletes=True)
    watchers = relationship("TaskWatcher", back_populates="task", cascade="all, delete-orphan", passive_deletes=True)
    checklists = relationship("TaskChecklist", back_populates="task", cascade="all, delete-orphan", passive_deletes=True)
    time_entries = relationship("TimeEntry", back_populates="task", cascade="all, delete-orphan", passive_deletes=True)
    # dependencies where THIS task is the dependent (task depends on these)
    dependencies_as_dependent = relationship("TaskDependency", foreign_keys="TaskDependency.task_id",
                                             back_populates="task", cascade="all, delete-orphan", passive_deletes=True)
    # dependencies where THIS task is the prerequisite (others depend on this)
    dependencies_as_prerequisite = relationship("TaskDependency", foreign_keys="TaskDependency.depends_on_task_id",
                                                back_populates="depends_on_task", cascade="all, delete-orphan", passive_deletes=True)
