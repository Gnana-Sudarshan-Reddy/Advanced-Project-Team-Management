"""Endpoints for project-level discussion boards and replies."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_permission
from app.core.exceptions import AppError, NotFoundError
from app.core.permissions import Perm
from app.db.session import get_db
from app.models import Project, ProjectDiscussion, DiscussionReply, User
from app.schemas.discussion import (
    DiscussionCreate, DiscussionOut, DiscussionReplyCreate, DiscussionReplyOut, DiscussionUpdate,
)
from app.services.access import ensure_project_access
from app.services.activity import log_activity
from app.services.notification import create_notification, notify_mentions
from app.services.utils import apply_changes

router = APIRouter(prefix="/discussions", tags=["Discussions"])


@router.post("", response_model=DiscussionOut, status_code=201)
def create_discussion(payload: DiscussionCreate, db: Session = Depends(get_db),
                      user: User = Depends(require_permission(Perm.DISCUSSIONS_CREATE))):
    """Create a discussion thread in an accessible project."""
    project = ensure_project_access(db, user, payload.project_id)
    discussion = ProjectDiscussion(**payload.model_dump(), created_by_id=user.id)
    db.add(discussion)
    db.flush()
    log_activity(db, user, "discussion.created", project_id=project.id,
                 details={"discussion_id": discussion.id, "title": discussion.title})
    db.commit()
    db.refresh(discussion)
    return discussion


@router.get("", response_model=list[DiscussionOut])
def list_discussions(project_id: int, db: Session = Depends(get_db),
                     user: User = Depends(get_current_user)):
    """List discussions of an accessible project."""
    project = ensure_project_access(db, user, project_id)
    return project.discussions


@router.get("/{discussion_id}", response_model=DiscussionOut)
def get_discussion(discussion_id: int, db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    """Return one discussion after checking project access."""
    discussion = db.get(ProjectDiscussion, discussion_id)
    if not discussion:
        raise NotFoundError("Discussion not found")
    ensure_project_access(db, user, discussion.project_id)
    return discussion


@router.patch("/{discussion_id}", response_model=DiscussionOut)
def update_discussion(discussion_id: int, payload: DiscussionUpdate, db: Session = Depends(get_db),
                      user: User = Depends(require_permission(Perm.DISCUSSIONS_MANAGE))):
    """Update a discussion (creator or manager)."""
    discussion = db.get(ProjectDiscussion, discussion_id)
    if not discussion:
        raise NotFoundError("Discussion not found")
    ensure_project_access(db, user, discussion.project_id)
    data = payload.model_dump(exclude_unset=True, exclude_none=True)
    if not data:
        raise AppError("No fields to update", 422, "validation_error")
    changes = apply_changes(discussion, data)
    if changes:
        log_activity(db, user, "discussion.updated", project_id=discussion.project_id,
                     details={"discussion_id": discussion_id, **changes})
    db.commit()
    db.refresh(discussion)
    return discussion


@router.delete("/{discussion_id}", status_code=204)
def delete_discussion(discussion_id: int, db: Session = Depends(get_db),
                      user: User = Depends(require_permission(Perm.DISCUSSIONS_MANAGE))):
    """Delete a discussion."""
    discussion = db.get(ProjectDiscussion, discussion_id)
    if not discussion:
        raise NotFoundError("Discussion not found")
    ensure_project_access(db, user, discussion.project_id)
    db.delete(discussion)
    db.commit()
    return None


@router.post("/{discussion_id}/replies", response_model=DiscussionReplyOut, status_code=201)
def add_reply(discussion_id: int, payload: DiscussionReplyCreate, db: Session = Depends(get_db),
              user: User = Depends(require_permission(Perm.DISCUSSIONS_CREATE))):
    """Add a reply to a discussion."""
    discussion = db.get(ProjectDiscussion, discussion_id)
    if not discussion:
        raise NotFoundError("Discussion not found")
    ensure_project_access(db, user, discussion.project_id)
    reply = DiscussionReply(
        discussion_id=discussion.id, user_id=user.id, content=payload.content,
        parent_reply_id=payload.parent_reply_id,
    )
    db.add(reply)
    db.flush()
    log_activity(db, user, "discussion.replied", project_id=discussion.project_id,
                 details={"discussion_id": discussion_id, "reply_id": reply.id})
    notify_mentions(db, payload.content, user, entity_type="discussion_reply", entity_id=reply.id,
                    project_id=discussion.project_id)
    for member in discussion.project.members:
        if member.user_id != user.id:
            create_notification(db, member.user_id, "New discussion reply",
                                f"{user.full_name} replied in '{discussion.title}'.", "comment_added",
                                related_entity_type="discussion", related_entity_id=discussion.id, actor=user)
    db.commit()
    db.refresh(reply)
    return reply


@router.get("/{discussion_id}/replies", response_model=list[DiscussionReplyOut])
def list_replies(discussion_id: int, db: Session = Depends(get_db),
                 user: User = Depends(get_current_user)):
    """List top-level replies of a discussion."""
    discussion = db.get(ProjectDiscussion, discussion_id)
    if not discussion:
        raise NotFoundError("Discussion not found")
    ensure_project_access(db, user, discussion.project_id)
    return [r for r in discussion.replies if r.parent_reply_id is None]
