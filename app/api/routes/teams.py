"""Team collaboration and workload endpoints (project members, workload)."""

from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.permissions import Perm
from app.db.session import get_db
from app.models import Project, ProjectMember, ResourceAllocation, Task, User
from app.models.enums import TaskStatus
from app.schemas.user import UserBrief
from app.services.access import accessible_project_ids, ensure_project_access, is_admin

router = APIRouter(prefix="/teams", tags=["Team Collaboration"])


@router.get("/{project_id}/members", response_model=list[UserBrief])
def list_project_members(project_id: int, db: Session = Depends(get_db),
                         user: User = Depends(get_current_user)):
    """List members of an accessible project."""
    project = ensure_project_access(db, user, project_id)
    return [m.user for m in project.members]


@router.get("/workload", response_model=list[dict])
def team_workload(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Open task count per user (workload) across accessible projects."""
    if is_admin(user):
        project_ids = [p[0] for p in db.execute(select(Project.id)).all()]
    else:
        project_ids = [p[0] for p in db.execute(accessible_project_ids(user)).all()]
    rows = db.query(
        User.id, User.full_name,
        func.count(Task.id).label("open_tasks"),
    ).outerjoin(Task, (Task.assignee_id == User.id) & (Task.project_id.in_(project_ids)) &
                (Task.status != TaskStatus.DONE.value)).group_by(User.id, User.full_name).all()
    return [
        {"user_id": r.id, "full_name": r.full_name, "open_tasks": int(r.open_tasks or 0)}
        for r in rows
    ]


@router.get("/availability", response_model=list[dict])
def team_availability(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Show allocated capacity, open work, and overload state for each visible member."""
    if is_admin(user):
        project_ids = [p[0] for p in db.execute(select(Project.id)).all()]
    else:
        project_ids = [p[0] for p in db.execute(accessible_project_ids(user)).all()]
    rows = db.query(User).filter(User.is_active == True).all()  # noqa: E712
    result = []
    for member in rows:
        allocations = db.query(ResourceAllocation).filter(
            ResourceAllocation.user_id == member.id,
            ResourceAllocation.project_id.in_(project_ids) if project_ids else False,
            ResourceAllocation.start_date <= date.today(), ResourceAllocation.end_date >= date.today(),
        ).all()
        allocated = sum(a.allocation_percent for a in allocations)
        open_tasks = db.query(Task).filter(
            Task.assignee_id == member.id, Task.project_id.in_(project_ids) if project_ids else False,
            Task.status != TaskStatus.DONE.value,
        ).count()
        result.append({"user_id": member.id, "full_name": member.full_name,
                       "allocated_percent": allocated, "available_percent": max(0, 100 - allocated),
                       "open_tasks": open_tasks, "overloaded": allocated > 100})
    return result
