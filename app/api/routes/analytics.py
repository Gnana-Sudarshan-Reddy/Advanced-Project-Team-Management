"""Endpoints for advanced reports and analytics."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_permission
from app.core.permissions import Perm
from app.db.session import get_db
from app.models import Project, Task, User
from app.models.enums import ProjectHealth, TaskStatus
from app.services.access import ensure_project_access, is_admin
from app.services.analytics import (
    delayed_tasks_report, milestone_completion_report, project_completion_report,
    project_time_report, team_productivity_report, team_workload_report,
)

router = APIRouter(prefix="/analytics", tags=["Reports & Analytics"])


@router.get("/projects/{project_id}/completion", response_model=dict)
def completion_report(project_id: int, db: Session = Depends(get_db),
                      user: User = Depends(get_current_user)):
    """Task completion summary for a project."""
    return project_completion_report(db, project_id, user)


@router.get("/team/productivity", response_model=list[dict])
def productivity_report(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Tasks completed per user across accessible projects."""
    return team_productivity_report(db, user)


@router.get("/tasks/delayed", response_model=list[dict])
def delayed_report(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Tasks whose due date passed but are not done."""
    return delayed_tasks_report(db, user)


@router.get("/projects/{project_id}/time", response_model=dict)
def time_report(project_id: int, db: Session = Depends(get_db),
                user: User = Depends(get_current_user)):
    """Estimated versus actual hours for a project."""
    return project_time_report(db, project_id, user)


@router.get("/projects/{project_id}/health", response_model=dict)
def project_health(project_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Return project health based on overdue work and the project deadline."""
    project = ensure_project_access(db, user, project_id)
    from datetime import date, timedelta
    overdue = db.query(Task).filter(Task.project_id == project_id,
                                    Task.due_date < date.today(), Task.status != TaskStatus.DONE.value).count()
    upcoming = db.query(Task).filter(Task.project_id == project_id,
                                     Task.due_date <= date.today() + timedelta(days=7),
                                     Task.status != TaskStatus.DONE.value).count()
    if overdue or (project.end_date and project.end_date < date.today()):
        health = ProjectHealth.DELAYED.value
    elif upcoming:
        health = ProjectHealth.AT_RISK.value
    else:
        health = ProjectHealth.ON_TRACK.value
    if project.health_status != health:
        project.health_status = health
        db.commit()
    return {"project_id": project.id, "health_status": health, "overdue_tasks": overdue,
            "upcoming_deadline_tasks": upcoming}


@router.get("/team/workload", response_model=list[dict])
def workload_report(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Open task count per user (workload) across accessible projects."""
    return team_workload_report(db, user)


@router.get("/projects/{project_id}/milestones/completion", response_model=list[dict])
def milestones_completion(project_id: int, db: Session = Depends(get_db),
                          user: User = Depends(get_current_user)):
    """Completion percentage per milestone in a project."""
    return milestone_completion_report(db, project_id, user)


@router.get("/dashboard", response_model=dict)
def performance_dashboard(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Project performance dashboard: high-level KPIs."""
    from app.models import Project, Task
    from app.models.enums import TaskStatus
    from app.services.access import accessible_project_ids
    if is_admin(user):
        project_ids = [p[0] for p in db.execute(select(Project.id)).all()]
    else:
        project_ids = [p[0] for p in db.execute(accessible_project_ids(user)).all()]
    from sqlalchemy import select
    total_projects = len(project_ids)
    total_tasks = db.query(Task).filter(Task.project_id.in_(project_ids)).count() if project_ids else 0
    done_tasks = db.query(Task).filter(
        Task.project_id.in_(project_ids), Task.status == TaskStatus.DONE.value
    ).count() if project_ids else 0
    return {
        "total_projects": total_projects,
        "total_tasks": total_tasks,
        "completed_tasks": done_tasks,
        "completion_percent": round(done_tasks / total_tasks * 100, 1) if total_tasks else 0.0,
    }
