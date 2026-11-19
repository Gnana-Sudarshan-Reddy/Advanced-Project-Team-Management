"""Endpoints for subtasks (self-referential child tasks)."""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_permission
from app.core.exceptions import AppError, ForbiddenError, NotFoundError
from app.core.permissions import Perm, RoleName
from app.db.session import get_db
from app.models import Task
from app.models.enums import TaskPriority, TaskStatus
from app.schemas.subtask import SubtaskCreate, SubtaskOut, SubtaskUpdate
from app.models.mixins import utcnow
from app.services.access import _load_accessible_task, ensure_project_access
from app.services.activity import log_activity
from app.services.utils import apply_changes, plain

router = APIRouter(prefix="/subtasks", tags=["Subtasks"])


@router.post("/{task_id}", response_model=SubtaskOut, status_code=201)
def create_subtask(task_id: int, payload: SubtaskCreate, db: Session = Depends(get_db),
                   user: User = Depends(require_permission(Perm.TASKS_MANAGE_SUBTASKS))):
    """Create a subtask under a parent task."""
    parent, project = _load_accessible_task(db, user, task_id)
    data = payload.model_dump()
    data["status"] = plain(data["status"])
    data["priority"] = plain(data["priority"])
    subtask = Task(**data, project_id=project.id, parent_task_id=task_id, created_by_id=user.id,
                   updated_by_id=user.id)
    db.add(subtask)
    db.flush()
    log_activity(db, user, "subtask.created", project_id=project.id, task_id=task_id,
                 details={"subtask_id": subtask.id, "title": subtask.title})
    db.commit()
    db.refresh(subtask)
    return subtask


@router.get("/{task_id}", response_model=list[SubtaskOut])
def list_subtasks(task_id: int, db: Session = Depends(get_db),
                  user: User = Depends(get_current_user)):
    """List subtasks of a parent task."""
    parent, _ = _load_accessible_task(db, user, task_id)
    return parent.subtasks_orm


@router.get("/{task_id}/subtasks/{subtask_id}", response_model=SubtaskOut)
def get_subtask(task_id: int, subtask_id: int, db: Session = Depends(get_db),
                user: User = Depends(get_current_user)):
    """Return one subtask."""
    parent, _ = _load_accessible_task(db, user, task_id)
    subtask = db.get(Task, subtask_id)
    if not subtask or subtask.parent_task_id != task_id:
        raise NotFoundError("Subtask not found")
    return subtask


@router.patch("/{task_id}/subtasks/{subtask_id}", response_model=SubtaskOut)
def update_subtask(task_id: int, subtask_id: int, payload: SubtaskUpdate, db: Session = Depends(get_db),
                   user: User = Depends(require_permission(Perm.TASKS_MANAGE_SUBTASKS))):
    """Update a subtask."""
    parent, project = _load_accessible_task(db, user, task_id)
    subtask = db.get(Task, subtask_id)
    if not subtask or subtask.parent_task_id != task_id:
        raise NotFoundError("Subtask not found")
    data = payload.model_dump(exclude_unset=True, exclude_none=True)
    if not data:
        raise AppError("No fields to update", 422, "validation_error")
    if "status" in data:
        data["status"] = plain(data["status"])
    if "priority" in data:
        data["priority"] = plain(data["priority"])
    changes = apply_changes(subtask, data)
    if changes:
        if "status" in changes:
            subtask.completed_at = utcnow() if subtask.status == TaskStatus.DONE.value else None
        subtask.updated_by_id = user.id
        log_activity(db, user, "subtask.updated", project_id=project.id, task_id=subtask.id,
                     details={"parent_task_id": task_id, **changes})
    db.commit()
    db.refresh(subtask)
    return subtask


@router.delete("/{task_id}/subtasks/{subtask_id}", status_code=204)
def delete_subtask(task_id: int, subtask_id: int, db: Session = Depends(get_db),
                   user: User = Depends(require_permission(Perm.TASKS_MANAGE_SUBTASKS))):
    """Delete a subtask."""
    parent, project = _load_accessible_task(db, user, task_id)
    subtask = db.get(Task, subtask_id)
    if not subtask or subtask.parent_task_id != task_id:
        raise NotFoundError("Subtask not found")
    db.delete(subtask)
    db.commit()
    return None