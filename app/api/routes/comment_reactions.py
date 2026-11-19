"""Endpoints for emoji reactions on comments and discussion replies."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_permission
from app.core.exceptions import AppError, ConflictError, ForbiddenError, NotFoundError
from app.core.permissions import Perm
from app.db.session import get_db
from app.models import CommentReaction, DiscussionReply, ProjectDiscussion, TaskComment, User
from app.schemas.comment_reaction import CommentReactionCreate, CommentReactionOut
from app.services.access import _load_accessible_task, ensure_project_access, get_user_or_404
from app.services.activity import log_activity

router = APIRouter(prefix="/comment-reactions", tags=["Comment Reactions"])


def _target_accessible(db: Session, user: User, task_comment_id: int | None,
                       discussion_reply_id: int | None):
    """Verify the reaction target exists and its parent task/discussion is accessible."""
    if task_comment_id is not None:
        comment = db.get(TaskComment, task_comment_id)
        if not comment:
            raise NotFoundError("Comment not found")
        task, project = _load_accessible_task(db, user, comment.task_id)
        return comment, project
    if discussion_reply_id is not None:
        reply = db.get(DiscussionReply, discussion_reply_id)
        if not reply:
            raise NotFoundError("Reply not found")
        from app.services.access import ensure_project_access
        discussion = db.get(ProjectDiscussion, reply.discussion_id)
        ensure_project_access(db, user, discussion.project_id)
        return reply, discussion.project
    raise AppError("Must specify task_comment_id or discussion_reply_id", 422, "invalid_target")


@router.post("", response_model=CommentReactionOut, status_code=201)
def add_reaction(payload: CommentReactionCreate, db: Session = Depends(get_db),
                 user: User = Depends(require_permission(Perm.COMMENTS_CREATE))):
    """Add or toggle a reaction on a comment or reply."""
    _target_accessible(db, user, payload.task_comment_id, payload.discussion_reply_id)
    existing = db.query(CommentReaction).filter(
        CommentReaction.user_id == user.id,
        CommentReaction.task_comment_id == payload.task_comment_id,
        CommentReaction.discussion_reply_id == payload.discussion_reply_id,
    ).first()
    if existing:
        existing.reaction = payload.reaction
        db.flush()
        db.refresh(existing)
        return existing
    reaction = CommentReaction(
        task_comment_id=payload.task_comment_id,
        discussion_reply_id=payload.discussion_reply_id,
        user_id=user.id, reaction=payload.reaction,
    )
    db.add(reaction)
    db.flush()
    log_activity(db, user, "reaction.added", details={"reaction": payload.reaction})
    db.commit()
    db.refresh(reaction)
    return reaction


@router.get("/comment/{comment_id}", response_model=list[CommentReactionOut])
def reactions_on_comment(comment_id: int, db: Session = Depends(get_db),
                         user: User = Depends(get_current_user)):
    """List reactions on a task comment."""
    comment = db.get(TaskComment, comment_id)
    if not comment:
        raise NotFoundError("Comment not found")
    _load_accessible_task(db, user, comment.task_id)
    return comment.reactions


@router.get("/reply/{reply_id}", response_model=list[CommentReactionOut])
def reactions_on_reply(reply_id: int, db: Session = Depends(get_db),
                       user: User = Depends(get_current_user)):
    """List reactions on a discussion reply."""
    reply = db.get(DiscussionReply, reply_id)
    if not reply:
        raise NotFoundError("Reply not found")
    from app.services.access import ensure_project_access
    discussion = db.get(ProjectDiscussion, reply.discussion_id)
    ensure_project_access(db, user, discussion.project_id)
    return reply.reactions


@router.delete("/{reaction_id}", status_code=204)
def delete_reaction(reaction_id: int, db: Session = Depends(get_db),
                    user: User = Depends(require_permission(Perm.COMMENTS_CREATE))):
    """Delete a reaction (owner or admin)."""
    reaction = db.get(CommentReaction, reaction_id)
    if not reaction:
        raise NotFoundError("Reaction not found")
    if reaction.user_id != user.id:
        from app.core.exceptions import ForbiddenError
        raise ForbiddenError("You can only remove your own reactions")
    db.delete(reaction)
    db.commit()
    return None