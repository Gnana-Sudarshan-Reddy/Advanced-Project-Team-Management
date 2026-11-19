"""Endpoints for project approval workflows."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_permission
from app.core.exceptions import AppError, ConflictError, ForbiddenError, NotFoundError
from app.core.permissions import Perm, RoleName
from app.db.session import get_db
from app.models import Project, ProjectApproval, Task, User
from app.models.enums import ApprovalStatus
from app.schemas.project_approval import (
    ProjectApprovalCreate, ProjectApprovalOut, ProjectApprovalUpdate,
)
from app.services.access import ensure_project_access, get_task_or_404, get_user_or_404
from app.services.activity import log_activity
from app.services.notification import create_notification

router = APIRouter(prefix="/project-approvals", tags=["Project Approvals"])


@router.post("", response_model=ProjectApprovalOut, status_code=201)
def request_approval(payload: ProjectApprovalCreate, db: Session = Depends(get_db),
                     user: User = Depends(require_permission(Perm.PROJECT_APPROVAL))):
    """Request approval for completed project work."""
    project = ensure_project_access(db, user, payload.project_id)
    if payload.task_id:
        get_task_or_404(db, payload.task_id)
    approval = ProjectApproval(
        project_id=payload.project_id, task_id=payload.task_id,
        submitted_by_id=user.id, comments=payload.comments,
    )
    db.add(approval)
    db.flush()
    log_activity(db, user, "approval.requested", project_id=project.id,
                 task_id=payload.task_id,
                 details={"approval_id": approval.id})
    # Notify project managers/admins
    _notify_approvers(db, project, user)
    db.commit()
    db.refresh(approval)
    return approval


def _notify_approvers(db: Session, project: Project, requester: User) -> None:
    """Create notifications for users who can approve (PMs and admins)."""
    from app.models import User
    approvers = db.query(User).filter(
        User.role.name.in_([RoleName.ADMIN.value, RoleName.PROJECT_MANAGER.value]),
        User.is_active == True,  # noqa: E712
    ).all()
    for approver in approvers:
        if approver.id == requester.id:
            continue
        create_notification(
            db, approver.id,
            title="Approval requested",
            message=f"{requester.full_name} requested approval for project '{project.name}'.",
            type="approval_requested",
            related_entity_type="project",
            related_entity_id=project.id,
            actor=requester,
        )


@router.get("", response_model=list[ProjectApprovalOut])
def list_approvals(project_id: int | None = None, db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    """List approvals (filterable by project)."""
    query = db.query(ProjectApproval)
    if project_id is not None:
        ensure_project_access(db, user, project_id)
        query = query.filter(ProjectApproval.project_id == project_id)
    elif not (user.role.name == RoleName.ADMIN.value):
        # non-admin: only approvals on accessible projects
        from app.services.access import accessible_project_ids
        query = query.filter(ProjectApproval.project_id.in_(accessible_project_ids(user)))
    return query.order_by(ProjectApproval.created_at.desc()).all()


@router.get("/{approval_id}", response_model=ProjectApprovalOut)
def get_approval(approval_id: int, db: Session = Depends(get_db),
                 user: User = Depends(get_current_user)):
    """Return one approval after checking project access."""
    approval = db.get(ProjectApproval, approval_id)
    if not approval:
        raise NotFoundError("Approval not found")
    ensure_project_access(db, user, approval.project_id)
    return approval


@router.patch("/{approval_id}", response_model=ProjectApprovalOut)
def review_approval(approval_id: int, payload: ProjectApprovalUpdate, db: Session = Depends(get_db),
                    reviewer: User = Depends(require_permission(Perm.PROJECT_APPROVAL))):
    """Approve or reject a pending approval (manager/admin)."""
    approval = db.get(ProjectApproval, approval_id)
    if not approval:
        raise NotFoundError("Approval not found")
    ensure_project_access(db, reviewer, approval.project_id)
    if approval.status != ApprovalStatus.PENDING.value:
        raise ConflictError("Only pending approvals can be reviewed", 409, "not_pending")
    from datetime import datetime, timezone
    approval.status = payload.status
    approval.reviewer_id = reviewer.id
    approval.reviewed_at = datetime.now(timezone.utc)
    approval.comments = payload.comments or approval.comments
    log_activity(db, reviewer, f"approval.{payload.status}", project_id=approval.project_id,
                 task_id=approval.task_id,
                 details={"approval_id": approval_id, "reviewer_id": reviewer.id})
    db.commit()
    db.refresh(approval)
    return approval


@router.delete("/{approval_id}", status_code=204)
def delete_approval(approval_id: int, db: Session = Depends(get_db),
                    user: User = Depends(require_permission(Perm.PROJECT_APPROVAL))):
    """Delete a pending approval (submitter or admin)."""
    approval = db.get(ProjectApproval, approval_id)
    if not approval:
        raise NotFoundError("Approval not found")
    project = ensure_project_access(db, user, approval.project_id)
    if approval.submitted_by_id != user.id and user.role.name != RoleName.ADMIN.value:
        raise ForbiddenError("Only the submitter or an admin can delete this approval")
    if approval.status != ApprovalStatus.PENDING.value:
        raise ConflictError("Only pending approvals can be deleted", 409, "not_pending")
    db.delete(approval)
    db.commit()
    return None