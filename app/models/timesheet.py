"""SQLAlchemy models for weekly timesheets and their approval workflow."""

from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import TimesheetStatus
from app.models.mixins import TimestampMixin


class Timesheet(Base, TimestampMixin):
    """A weekly timesheet for one user, aggregating their time entries."""

    __tablename__ = "timesheets"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    week_start_date: Mapped[date] = mapped_column(Date, index=True)
    status: Mapped[str] = mapped_column(String(20), default=TimesheetStatus.DRAFT.value, index=True)
    total_hours: Mapped[float] = mapped_column(Numeric(6, 2), default=0)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approved_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user = relationship("User", foreign_keys=[user_id], lazy="joined")
    approved_by = relationship("User", foreign_keys=[approved_by_id], lazy="joined")
    __table_args__ = (
        # UniqueConstraint("user_id", "week_start_date", name="uq_timesheet_user_week"),
    )
