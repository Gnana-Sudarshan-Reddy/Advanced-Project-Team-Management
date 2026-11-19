"""WebSocket connection manager and in-app notification service."""

import json
import logging
import re
from datetime import date, datetime, time, timedelta, timezone
from collections import defaultdict
from typing import Dict, List, Set

from fastapi import WebSocket
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models import Notification, NotificationPreference, Task, User
from app.models.enums import TaskStatus
from app.services.access import get_user_or_404

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Tracks active WebSocket connections per user for real-time notifications."""

    def __init__(self) -> None:
        self.active_connections: Dict[int, List[WebSocket]] = defaultdict(list)

    async def connect(self, websocket: WebSocket, user_id: int) -> None:
        await websocket.accept()
        self.active_connections[user_id].append(websocket)
        logger.info("WebSocket connected for user %s", user_id)

    def disconnect(self, websocket: WebSocket, user_id: int) -> None:
        conns = self.active_connections.get(user_id, [])
        if websocket in conns:
            conns.remove(websocket)
        if not conns:
            self.active_connections.pop(user_id, None)
        logger.info("WebSocket disconnected for user %s", user_id)

    async def send_personal_message(self, message: dict, user_id: int) -> None:
        """Send a JSON message to all open connections of a user."""
        dead: List[WebSocket] = []
        for connection in list(self.active_connections.get(user_id, [])):
            try:
                await connection.send_json(message)
            except Exception:  # pragma: no cover - connection already closed
                dead.append(connection)
        for connection in dead:
            self.disconnect(connection, user_id)

    def broadcast(self, message: dict) -> None:
        """Placeholder for future broadcast logic (kept for interface symmetry)."""
        logger.debug("Broadcast (no-op): %s", message)


manager = ConnectionManager()

_PREFERENCE_FIELDS = {
    "task_assigned": "task_assigned",
    "task_reassigned": "task_assigned",
    "deadline_approaching": "deadline_approaching",
    "mention": "mention",
    "comment_added": "comment_added",
    "approval_requested": "approval_requested",
}


def create_notification(
    db: Session,
    user_id: int,
    title: str,
    message: str,
    type: str,
    *,
    related_entity_type: str | None = None,
    related_entity_id: int | None = None,
    actor: User | None = None,
) -> Notification | None:
    """Persist a notification and push it over WebSocket if the user is online."""
    user = get_user_or_404(db, user_id)
    preference = user.notification_preference
    preference_field = _PREFERENCE_FIELDS.get(type)
    if preference_field and preference is not None and not getattr(preference, preference_field):
        return None
    notification = Notification(
        user_id=user_id,
        title=title,
        message=message,
        type=type,
        related_entity_type=related_entity_type,
        related_entity_id=related_entity_id,
    )
    db.add(notification)
    db.flush()
    db.refresh(notification)

    payload = {
        "id": notification.id,
        "title": notification.title,
        "message": notification.message,
        "type": notification.type,
        "related_entity_type": notification.related_entity_type,
        "related_entity_id": notification.related_entity_id,
        "is_read": notification.is_read,
        "created_at": notification.created_at.isoformat() if notification.created_at else None,
    }
    # Fire-and-forget push; do not await here so callers stay synchronous.
    try:
        import asyncio
        asyncio.get_event_loop().create_task(manager.send_personal_message(payload, user_id))
    except RuntimeError:
        # No running event loop (e.g. in tests); skip real-time push.
        pass

    return notification


def notify_mentions(db: Session, text: str, actor: User, *, entity_type: str,
                    entity_id: int, project_id: int | None = None) -> None:
    """Notify active users referenced as @email in content."""
    emails = {match.lower() for match in re.findall(r"(?<![\w.])@([\w.+-]+@[\w.-]+\.[A-Za-z]{2,})", text)}
    if not emails:
        return
    users = db.scalars(select(User).where(User.email.in_(emails), User.is_active == True)).all()  # noqa: E712
    for user in users:
        if user.id == actor.id:
            continue
        create_notification(
            db, user.id, "You were mentioned", f"{actor.full_name} mentioned you.",
            "mention", related_entity_type=entity_type, related_entity_id=entity_id, actor=actor,
        )


def notify_upcoming_deadlines(db: Session, days: int = 2) -> int:
    """Create one daily notification for each active task due soon."""
    today = date.today()
    horizon = today + timedelta(days=days)
    start = datetime.combine(today, time.min, tzinfo=timezone.utc)
    tasks = db.query(Task).filter(
        Task.assignee_id.is_not(None), Task.due_date >= today, Task.due_date <= horizon,
        Task.status != TaskStatus.DONE.value,
    ).all()
    created = 0
    for task in tasks:
        already_sent = db.query(Notification.id).filter(
            Notification.user_id == task.assignee_id,
            Notification.type == "deadline_approaching",
            Notification.related_entity_type == "task",
            Notification.related_entity_id == task.id,
            Notification.created_at >= start,
        ).first()
        if already_sent:
            continue
        owner = db.get(User, task.assignee_id)
        if owner:
            create_notification(db, owner.id, "Upcoming deadline", f"Task '{task.title}' is due on {task.due_date}.",
                                "deadline_approaching", related_entity_type="task", related_entity_id=task.id)
            created += 1
    db.commit()
    return created


def mark_as_read(db: Session, notification_id: int, user: User) -> Notification:
    """Mark a single notification as read if it belongs to the user."""
    notification = db.get(Notification, notification_id)
    if not notification:
        raise NotFoundError("Notification not found")
    if notification.user_id != user.id and not user.role.name == "Admin":
        from app.core.exceptions import ForbiddenError
        raise ForbiddenError("You cannot mark this notification as read")
    notification.is_read = True
    from datetime import datetime, timezone
    notification.read_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(notification)
    return notification


def mark_all_as_read(db: Session, user: User) -> int:
    """Mark all unread notifications of a user as read. Returns number updated."""
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    rows = db.query(Notification).filter(Notification.user_id == user.id, Notification.is_read == False)  # noqa: E712
    count = rows.update({"is_read": True, "read_at": now}, synchronize_session=False)
    db.commit()
    return count
