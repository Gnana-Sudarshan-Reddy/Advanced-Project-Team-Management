"""Reporting and analytics queries used by the analytics endpoints."""

from datetime import date, datetime, timedelta

from sqlalchemy import func, select

from app.core.exceptions import ForbiddenError, NotFoundError
from app.models import Project, Task, TimeEntry, Timesheet, User
from app.models.enums import TaskStatus, TimesheetStatus
from app.services.access import accessible_project_ids, ensure_project_access, is_admin


def project_completion_report(db, project_id: int, user: User) -> dict:
    """Task completion summary for a project."""
    project = ensure_project_access(db, user, project_id)
    total = db.query(Task).filter(Task.project_id == project_id).count()
    done = db.query(Task).filter(Task.project_id == project_id, Task.status == TaskStatus.DONE.value).count()
    return {
        "project_id": project_id,
        "project_name": project.name,
        "total_tasks": total,
        "completed_tasks": done,
        "completion_percent": round(done / total * 100, 1) if total else 0.0,
    }


def team_productivity_report(db, user: User) -> list[dict]:
    """Tasks completed per user across accessible projects."""
    if not is_admin(user):
        # Managers/members see only their own productivity
        rows = db.query(
            User.id, User.full_name,
            func.count(Task.id).label("total"),
            func.sum(select(func.count()).where(Task.status == TaskStatus.DONE.value).correlate(Task).scalar_subquery()).label("done"),
        ).outerjoin(Task, Task.assignee_id == User.id).filter(User.id == user.id).group_by(User.id, User.full_name).all()
    else:
        rows = db.query(
            User.id, User.full_name,
            func.count(Task.id).label("total"),
            func.sum(select(func.count()).where(Task.status == TaskStatus.DONE.value).correlate(Task).scalar_subquery()).label("done"),
        ).outerjoin(Task, Task.assignee_id == User.id).group_by(User.id, User.full_name).all()
    return [
        {"user_id": r.id, "full_name": r.full_name, "total_tasks": int(r.total or 0),
         "completed_tasks": int(r.done or 0)}
        for r in rows
    ]


def delayed_tasks_report(db, user: User) -> list[dict]:
    """Tasks whose due date has passed but are not done."""
    if is_admin(user):
        project_ids = [p[0] for p in db.execute(select(Project.id)).all()]
    else:
        project_ids = [p[0] for p in db.execute(accessible_project_ids(user)).all()]
    from datetime import date as _date
    rows = db.query(Task, Project).join(Project, Project.id == Task.project_id).filter(
        Task.project_id.in_(project_ids),
        Task.due_date < _date.today(),
        Task.status != TaskStatus.DONE.value,
    ).all()
    return [
        {"task_id": t.id, "title": t.title, "project_name": p.name,
         "due_date": t.due_date.isoformat() if t.due_date else None,
         "assignee_id": t.assignee_id}
        for t, p in rows
    ]


def project_time_report(db, project_id: int, user: User) -> dict:
    """Estimated versus actual hours for a project."""
    project = ensure_project_access(db, user, project_id)
    entries = db.query(TimeEntry).join(Task, Task.id == TimeEntry.task_id).filter(
        Task.project_id == project_id, TimeEntry.is_running == False,  # noqa: E712
    ).all()
    actual_hours = round(sum((e.duration_minutes or 0) for e in entries) / 60, 2)
    estimated_hours = round(sum((t.estimated_hours or 0) for t in project.tasks), 2)
    return {
        "project_id": project_id,
        "project_name": project.name,
        "estimated_hours": estimated_hours,
        "actual_hours": actual_hours,
        "variance_hours": round(actual_hours - estimated_hours, 2),
    }


def team_workload_report(db, user: User) -> list[dict]:
    """Open task count per user across accessible projects (workload)."""
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


def milestone_completion_report(db, project_id: int, user: User) -> list[dict]:
    """Completion percentage per milestone in a project."""
    project = ensure_project_access(db, user, project_id)
    result = []
    for milestone in project.milestones:
        total = len(milestone.tasks)
        done = sum(1 for t in milestone.tasks if t.status == TaskStatus.DONE.value)
        result.append({
            "milestone_id": milestone.id,
            "name": milestone.name,
            "due_date": milestone.due_date.isoformat() if milestone.due_date else None,
            "status": milestone.status,
            "total_tasks": total,
            "completed_tasks": done,
            "completion_percent": round(done / total * 100, 1) if total else 0.0,
        })
    return result