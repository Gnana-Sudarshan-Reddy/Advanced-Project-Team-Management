"""Endpoints for task watchers/followers."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_permission
from app.core.exceptions import AppError, ConflictError, NotFoundError
from app.core.permissions import Perm
from app.db.session import get_db
from app.models import Task, TaskWatcher, User
from app.schemas.task_watcher import TaskWatcherCreate, TaskWatcherOut
from app.services.access import _load_accessible_task, get_user_or_404
from app.services.activity import log_activity

router = APIRouter(prefix="/task-watchers", tags=["Task Watchers"])


@router.post("/{task_id}", response_model=TaskWatcherOut, status_code=201)
def add_watcher(task_id: int, payload: TaskWatcherCreate, db: Session = Depends(get_db),
                user: User = Depends(require_permission(Perm.TASKS_MANAGE_WATCHERS))):
    """Add a watcher to a task."""
    task, project = _load_accessible_task(db, user, task_id)
    get_user_or_404(db, payload.user_id)
    if db.query(TaskWatcher).filter(TaskWatcher.task_id == task_id, TaskWatcher.user_id == payload.user_id).first():
        raise ConflictError("User is already watching this task", 409, "already_watching")
    watcher = TaskWatcher(task_id=task.id, user_id=payload.user_id)
    db.add(watcher)
    db.flush()
    log_activity(db, user, "task.watcher_added", project_id=project.id, task_id=task.id,
                 details={"watcher_user_id": payload.user_id})
    db.commit()
    db.refresh(watcher)
    return watcher


@router.get("/{task_id}", response_model=list[TaskWatcherOut])
def list_watchers(task_id: int, db: Session = Depends(get_db),
                  user: User = Depends(get_current_user)):
    """List watchers of a task."""
    task, _ = _load_accessible_task(db, user, task_id)
    return task.watchers


@router.delete("/{task_id}/watchers/{user_id}", status_code=204)
def remove_watcher(task_id: int, user_id: int, db: Session = Depends(get_db),
                   user: User = Depends(require_permission(Perm.TASKS_MANAGE_WATCHERS))):
    """Remove a watcher from a task."""
    task, project = _load_accessible_task(db, user, task_id)
    watcher = db.query(TaskWatcher).filter(TaskWatcher.task_id == task_id, TaskWatcher.user_id == user_id).first()
    if not watcher:
        raise NotFoundError("Watcher not found")
    db.delete(watcher)
    db.commit()
    return None