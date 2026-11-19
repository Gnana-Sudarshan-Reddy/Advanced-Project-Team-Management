"""Task history recording helpers."""

from sqlalchemy.orm import Session

from app.models import TaskHistory, User


def record_task_history(db: Session, task_id: int, user: User | None, action: str,
                        changes: dict | None = None, summary: str | None = None) -> None:
    """Add an immutable task history row to the current transaction."""
    db.add(TaskHistory(task_id=task_id, changed_by_id=user.id if user else None,
                       action=action, changes=changes, summary=summary))
