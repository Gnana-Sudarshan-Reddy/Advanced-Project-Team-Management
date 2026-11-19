"""SQLAlchemy model for project approval requests."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import ApprovalStatus
from app.models.mixins import utcnow


class ProjectApproval(Base):
    """A request for a Project Manager to approve or reject completed project work."""

    __tablename__ = "project_approvals"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    task_id: Mapped[int | None] = mapped_column(ForeignKey("tasks.id", ondelete="SET NULL"), index=True, default=None)
    submitted_by_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    status: Mapped[str] = mapped_column(String(20), default=ApprovalStatus.PENDING.value, index=True)
    reviewer_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), default=None)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    comments: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    project = relationship("Project", back_populates="approvals")
    task = relationship("Task")
    submitted_by = relationship("User", foreign_keys=[submitted_by_id], lazy="joined")
    reviewer = relationship("User", foreign_keys=[reviewer_id], lazy="joined")