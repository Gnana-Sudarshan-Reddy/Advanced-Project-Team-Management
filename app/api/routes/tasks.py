"""Endpoints for task workflows, comments, filtering, and task history."""

from datetime import date

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_permission
from app.core.exceptions import AppError, ForbiddenError
from app.core.permissions import Perm
from app.db.session import get_db
from app.models import ActivityLog, Project, Task, TaskComment, User
from app.models.enums import TaskPriority, TaskStatus
from app.models.mixins import utcnow
from app.schemas.common import Page, PaginationParams, make_page
from app.schemas.task import ActivityOut, CommentCreate, CommentOut, TaskCreate, TaskOut, TaskUpdate
from app.services.access import (
    accessible_project_ids, ensure_project_access, get_task_or_404, get_user_or_404, has_permission, is_admin,
)
from app.services.activity import log_activity
from app.services.notification import create_notification, notify_mentions
from app.services.utils import apply_changes, plain

router = APIRouter(prefix="/tasks", tags=["Tasks"])

SORTABLE_TASK_COLUMNS = {
    "created_at": Task.created_at,
    "updated_at": Task.updated_at,
    "due_date": Task.due_date,
    "title": Task.title,
}


# ---------- validation helpers ----------

def validate_deadline(project: Project, due: date | None) -> None:
    """Ensure a task deadline is not in the past or beyond the project end date."""
    if due is None:
        return
    if due < date.today():
        raise AppError("due_date cannot be in the past", 422, "invalid_deadline")
    if project.end_date and due > project.end_date:
        raise AppError(f"due_date cannot be after the project end date ({project.end_date})", 422, "invalid_deadline")


def validate_assignee(db: Session, project: Project, assignee_id: int | None) -> None:
    """Ensure an assignee exists, is active, and belongs to the project."""
    if assignee_id is None:
        return
    user = get_user_or_404(db, assignee_id)
    if not user.is_active:
        raise AppError("Cannot assign tasks to a deactivated user", 422, "inactive_user")
    if user.id != project.owner_id and not any(m.user_id == user.id for m in project.members):
        raise AppError("Assignee must be a member of the project", 422, "assignee_not_member")


class TaskFilters:
    """Validated query parameters shared by task list endpoints."""

    project_id: int | None
    status_: TaskStatus | None
    priority: TaskPriority | None
    assignee_id: int | None
    created_by_id: int | None
    q: str | None
    due_before: date | None
    due_after: date | None
    overdue: bool | None
    sort_by: str
    order: str

    def __init__(
        self,
        project_id: int | None = None,
        status_: TaskStatus | None = Query(None, alias="status"),
        priority: TaskPriority | None = None,
        assignee_id: int | None = None,
        created_by_id: int | None = None,
        q: str | None = Query(None, description="Search title/description"),
        due_before: date | None = None,
        due_after: date | None = None,
        overdue: bool | None = Query(None, description="true = only overdue, false = only not overdue"),
        sort_by: str = Query("created_at", pattern="^(created_at|updated_at|due_date|title)$"),
        order: str = Query("desc", pattern="^(asc|desc)$"),
    ):
        """Store validated query values for the shared task-list query."""
        self.project_id = project_id
        self.status_ = status_
        self.priority = priority
        self.assignee_id = assignee_id
        self.created_by_id = created_by_id
        self.q = q
        self.due_before = due_before
        self.due_after = due_after
        self.overdue = overdue
        self.sort_by = sort_by
        self.order = order


def _load_accessible_task(db: Session, user: User, task_id: int):
    """Load a task and its project when the user has project access."""
    task = get_task_or_404(db, task_id)
    project = ensure_project_access(db, user, task.project_id)
    return task, project


@router.post("", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
def create_task(payload: TaskCreate, db: Session = Depends(get_db),
                user: User = Depends(require_permission(Perm.TASKS_CREATE))):
    """Create a task in an accessible project."""
    project = ensure_project_access(db, user, payload.project_id)
    validate_deadline(project, payload.due_date)
    validate_assignee(db, project, payload.assignee_id)
    data = payload.model_dump()
    data["status"] = plain(data["status"])
    data["priority"] = plain(data["priority"])
    task = Task(**data, created_by_id=user.id, updated_by_id=user.id)
    db.add(task)
    db.flush()
    log_activity(db, user, "task.created", project_id=project.id, task_id=task.id,
                 details={"title": task.title})
    if task.assignee_id and task.assignee_id != user.id:
        create_notification(db, task.assignee_id, "Task assigned", f"You were assigned task '{task.title}'.",
                            "task_assigned", related_entity_type="task", related_entity_id=task.id, actor=user)
    db.commit()
    db.refresh(task)
    return task


@router.get("", response_model=Page[TaskOut])
def list_tasks(filters: TaskFilters = Depends(), db: Session = Depends(get_db),
               user: User = Depends(get_current_user)):
    """Return tasks visible to the user, with filters, search, sort and pagination."""
    stmt = select(Task)
    if filters.project_id is not None:
        ensure_project_access(db, user, filters.project_id)
        stmt = stmt.where(Task.project_id == filters.project_id)
    else:
        if not is_admin(user):
            stmt = stmt.where(Task.project_id.in_(accessible_project_ids(user)))
    if filters.status_:
        stmt = stmt.where(Task.status == filters.status_.value)
    if filters.priority:
        stmt = stmt.where(Task.priority == filters.priority.value)
    if filters.assignee_id is not None:
        stmt = stmt.where(Task.assignee_id == filters.assignee_id)
    if filters.created_by_id is not None:
        stmt = stmt.where(Task.created_by_id == filters.created_by_id)
    if filters.q:
        stmt = stmt.where(or_(Task.title.ilike(f"%{filters.q}%"), Task.description.ilike(f"%{filters.q}%")))
    if filters.due_before:
        stmt = stmt.where(Task.due_date <= filters.due_before)
    if filters.due_after:
        stmt = stmt.where(Task.due_date >= filters.due_after)
    if filters.overdue is True:
        stmt = stmt.where(Task.due_date < date.today(), Task.status != TaskStatus.DONE.value)
    elif filters.overdue is False:
        stmt = stmt.where(or_(Task.due_date >= date.today(), Task.status == TaskStatus.DONE.value))
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    order_col = SORTABLE_TASK_COLUMNS[filters.sort_by]
    if filters.order == "asc":
        stmt = stmt.order_by(order_col.asc(), Task.id.asc())
    else:
        stmt = stmt.order_by(order_col.desc(), Task.id.desc())
    rows = db.scalars(stmt.offset(filters.offset).limit(filters.size)).unique().all()
    return make_page(TaskOut, rows, total, filters)


@router.patch("/{task_id}", response_model=TaskOut)
def update_task(task_id: int, payload: TaskUpdate, db: Session = Depends(get_db),
                user: User = Depends(get_current_user)):
    """Update a task, including reassignment and recurring-task settings."""
    task, project = _load_accessible_task(db, user, task_id)
    if not has_permission(user, Perm.TASKS_UPDATE) and not (
        has_permission(user, Perm.TASKS_UPDATE_STATUS) and task.assignee_id == user.id
    ):
        raise ForbiddenError("You do not have permission to update this task")
    data = payload.model_dump(exclude_unset=True, exclude_none=True)
    if "due_date" in data:
        validate_deadline(project, data["due_date"])
    if "assignee_id" in data:
        validate_assignee(db, project, data["assignee_id"])
    if "status" in data:
        data["status"] = plain(data["status"])
    if "priority" in data:
        data["priority"] = plain(data["priority"])
    old_assignee = task.assignee_id
    changes = apply_changes(task, data)
    task.updated_by_id = user.id
    if changes:
        log_activity(db, user, "task.updated", project_id=project.id, task_id=task.id, details=changes)
        if "assignee_id" in changes and task.assignee_id and task.assignee_id != user.id:
            create_notification(db, task.assignee_id, "Task reassigned", f"Task '{task.title}' was assigned to you.",
                                "task_reassigned", related_entity_type="task", related_entity_id=task.id, actor=user)
    db.commit()
    db.refresh(task)
    return task


@router.delete("/{task_id}", status_code=204)
def delete_task(task_id: int, db: Session = Depends(get_db),
                user: User = Depends(require_permission(Perm.TASKS_DELETE))):
    task, project = _load_accessible_task(db, user, task_id)
    db.delete(task)
    log_activity(db, user, "task.deleted", project_id=project.id, task_id=task.id)
    db.commit()


@router.post("/{task_id}/comments", response_model=CommentOut, status_code=201)
def create_comment(task_id: int, payload: CommentCreate, db: Session = Depends(get_db),
                   user: User = Depends(require_permission(Perm.COMMENTS_CREATE))):
    """Add a task comment or reply and notify the assignee/mentioned users."""
    task, project = _load_accessible_task(db, user, task_id)
    parent = None
    if payload.parent_comment_id:
        parent = db.get(TaskComment, payload.parent_comment_id)
        if not parent or parent.task_id != task.id:
            raise AppError("Parent comment not found on this task", 404, "not_found")
    comment = TaskComment(task_id=task.id, user_id=user.id, content=payload.content,
                          parent_comment_id=payload.parent_comment_id)
    db.add(comment)
    db.flush()
    log_activity(db, user, "task.comment_added", project_id=project.id, task_id=task.id,
                 details={"comment_id": comment.id})
    if task.assignee_id and task.assignee_id != user.id:
        create_notification(db, task.assignee_id, "New task comment", f"{user.full_name} commented on '{task.title}'.",
                            "comment_added", related_entity_type="task", related_entity_id=task.id, actor=user)
    notify_mentions(db, payload.content, user, entity_type="task_comment", entity_id=comment.id,
                    project_id=project.id)
    db.commit()
    db.refresh(comment)
    return comment


@router.get("/{task_id}/comments", response_model=list[CommentOut])
def list_comments(task_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    task, _ = _load_accessible_task(db, user, task_id)
    return db.query(TaskComment).filter(TaskComment.task_id == task.id).order_by(TaskComment.created_at.asc()).all()


@router.get("/me", response_model=Page[TaskOut])
def my_tasks(filters: TaskFilters = Depends(), db: Session = Depends(get_db),
             user: User = Depends(get_current_user)):
    """Return tasks assigned to the current user."""
    filters.assignee_id = user.id
    return list_tasks(filters, db, user)
