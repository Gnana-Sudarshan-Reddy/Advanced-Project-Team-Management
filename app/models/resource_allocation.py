"""SQLAlchemy model for resource allocation across projects."""

from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin


class ResourceAllocation(Base, TimestampMixin):
    """Allocates a percentage of a user's capacity to a project over a date range."""

    __tablename__ = "resource_allocations"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    allocation_percent: Mapped[int] = mapped_column(Integer, default=100)
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)

    project = relationship("Project", back_populates="resource_allocations")
    user = relationship("User", lazy="joined")