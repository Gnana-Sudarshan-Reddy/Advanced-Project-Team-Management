"""Endpoints for project milestones."""

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_permission
from app.core.exceptions import AppError, NotFoundError
from app.core.permissions import Perm
from app.db.session import get_db
from app.models import Project, ProjectMilestone, Task, User
from app.models.enums import MilestoneStatus, TaskStatus
from app.schemas.milestone import MilestoneCreate, MilestoneOut, MilestoneUpdate
from app.schemas.task import TaskOut
from app.services.access import ensure_project_access, get_project_or_404

router = APIRouter(prefix="/milestones", tags=["Milestones"])


@router.post("", response_model=MilestoneOut, status_code=201)
def create_milestone(payload: MilestoneCreate, db: Session = Depends(get_db),
                     user: User = Depends(require_permission(Perm.MILESTONES_MANAGE))):
    """Create a milestone in an accessible project."""
    project = ensure_project_access(db, user, payload.project_id)
    if payload.due_date and project.end_date and payload.due_date > project.end_date:
        raise AppError("milestone due_date cannot be after the project end date", 422, "invalid_deadline")
    milestone = ProjectMilestone(**payload.model_dump(), created_by_id=user.id)
    db.add(milestone)
    db.flush()
    from app.services.activity import log_activity
    log_activity(db, user, "milestone.created", project_id=project.id,
                 details={"milestone_id": milestone.id, "name": milestone.name})
    db.commit()
    db.refresh(milestone)
    return milestone


@router.get("", response_model=list[MilestoneOut])
def list_milestones(project_id: int = Query(...), db: Session = Depends(get_db),
                    user: User = Depends(get_current_user)):
    """List milestones of an accessible project."""
    project = ensure_project_access(db, user, project_id)
    return project.milestones


@router.get("/{milestone_id}", response_model=MilestoneOut)
def get_milestone(milestone_id: int, db: Session = Depends(get_db),
                  user: User = Depends(get_current_user)):
    """Return one milestone after checking project access."""
    milestone = db.get(ProjectMilestone, milestone_id)
    if not milestone:
        raise NotFoundError("Milestone not found")
    ensure_project_access(db, user, milestone.project_id)
    return milestone


@router.patch("/{milestone_id}", response_model=MilestoneOut)
def update_milestone(milestone_id: int, payload: MilestoneUpdate, db: Session = Depends(get_db),
                     user: User = Depends(require_permission(Perm.MILESTONES_MANAGE))):
    """Update a milestone (project owner/manager/admin)."""
    milestone = db.get(ProjectMilestone, milestone_id)
    if not milestone:
        raise NotFoundError("Milestone not found")
    project = ensure_project_access(db, user, milestone.project_id)
    from app.core.permissions import RoleName
    is_owner_or_admin = user.role.name == RoleName.ADMIN or project.owner_id == user.id
    if not is_owner_or_admin:
        from app.core.exceptions import ForbiddenError
        raise ForbiddenError("Only the project owner or an admin can update milestones")
    data = payload.model_dump(exclude_unset=True, exclude_none=True)
    if "due_date" in data and data["due_date"] and project.end_date and data["due_date"] > project.end_date:
        raise AppError("milestone due_date cannot be after the project end date", 422, "invalid_deadline")
    from app.services.utils import apply_changes, plain
    if "status" in data:
        data["status"] = plain(data["status"])
    changes = apply_changes(milestone, data)
    if changes:
        from app.services.activity import log_activity
        log_activity(db, user, "milestone.updated", project_id=project.id,
                     details={"milestone_id": milestone.id, **changes})
    db.commit()
    db.refresh(milestone)
    return milestone


@router.delete("/{milestone_id}", status_code=204)
def delete_milestone(milestone_id: int, db: Session = Depends(get_db),
                     user: User = Depends(require_permission(Perm.MILESTONES_MANAGE))):
    """Delete a milestone (owner/admin only)."""
    milestone = db.get(ProjectMilestone, milestone_id)
    if not milestone:
        raise NotFoundError("Milestone not found")
    project = ensure_project_access(db, user, milestone.project_id)
    from app.core.permissions import RoleName
    if not (user.role.name == RoleName.ADMIN or project.owner_id == user.id):
        from app.core.exceptions import ForbiddenError
        raise ForbiddenError("Only the project owner or an admin can delete milestones")
    db.delete(milestone)
    db.commit()
    return None


@router.get("/{milestone_id}/tasks", response_model=list[TaskOut])
def milestone_tasks(milestone_id: int, db: Session = Depends(get_db),
                    user: User = Depends(get_current_user)):
    """List tasks grouped under a milestone."""
    milestone = db.get(ProjectMilestone, milestone_id)
    if not milestone:
        raise NotFoundError("Milestone not found")
    ensure_project_access(db, user, milestone.project_id)
    return milestone.tasks


@router.get("/{project_id}/completion", response_model=list[dict])
def milestone_completion(project_id: int, db: Session = Depends(get_db),
                         user: User = Depends(get_current_user)):
    """Completion percentage per milestone in a project."""
    from app.services.analytics import milestone_completion_report
    return milestone_completion_report(db, project_id, user)