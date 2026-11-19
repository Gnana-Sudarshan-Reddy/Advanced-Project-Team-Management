"""Endpoints for user notifications (read/unread, preferences, WebSocket info)."""

from typing import List

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from fastapi import Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.models import Notification, NotificationPreference, User
from app.schemas.notification import NotificationOut, NotificationPreference
from app.services.access import get_user_or_404
from app.services.notification import manager, mark_all_as_read, mark_as_read

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.websocket("/ws")
async def websocket_notifications(websocket: WebSocket, user_id: int):
    """WebSocket endpoint for real-time notifications (token passed as query param)."""
    # Authenticate via token query param
    from app.api.deps import oauth2_scheme
    from app.core.security import decode_access_token
    import jwt
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4001)
        return
    try:
        user_id_from_token = int(decode_access_token(token)["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        await websocket.close(code=4002)
        return
    if user_id_from_token != user_id:
        await websocket.close(code=4003)
        return
    await manager.connect(websocket, user_id)
    try:
        while True:
            await websocket.receive_text()  # keep connection alive
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)


@router.get("", response_model=List[NotificationOut])
def list_notifications(
    unread_only: bool = Query(False),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List the current user's notifications."""
    query = db.query(Notification).filter(Notification.user_id == user.id)
    if unread_only:
        query = query.filter(Notification.is_read == False)  # noqa: E712
    return query.order_by(Notification.created_at.desc()).all()


@router.patch("/{notification_id}/read", response_model=NotificationOut)
def mark_read(notification_id: int, db: Session = Depends(get_db),
              user: User = Depends(get_current_user)):
    """Mark a notification as read."""
    return mark_as_read(db, notification_id, user)


@router.patch("/read-all", response_model=dict)
def mark_all_read(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Mark all notifications of the current user as read."""
    count = mark_all_as_read(db, user)
    return {"marked_read": count}


@router.get("/unread-count", response_model=dict)
def unread_count(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Return the number of unread notifications."""
    count = db.query(Notification).filter(
        Notification.user_id == user.id, Notification.is_read == False  # noqa: E712
    ).count()
    return {"unread_count": count}


@router.get("/preferences", response_model=NotificationPreference)
def get_preferences(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Return the current user's persisted notification preferences."""
    if user.notification_preference is None:
        user.notification_preference = NotificationPreference(user_id=user.id)
        db.commit()
        db.refresh(user.notification_preference)
    return user.notification_preference


@router.patch("/preferences", response_model=NotificationPreference)
def update_preferences(payload: NotificationPreference, db: Session = Depends(get_db),
                       user: User = Depends(get_current_user)):
    """Persist notification preferences for the current user."""
    preference = user.notification_preference
    if preference is None:
        preference = NotificationPreference(user_id=user.id)
        db.add(preference)
    for field in payload.model_fields:
        setattr(preference, field, getattr(payload, field))
    db.commit()
    db.refresh(preference)
    return preference
