"""Endpoints for task checklists."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_permission
from app.core.exceptions import AppError, NotFoundError
from app.core.permissions import Perm
from app.db.session import get_db
from app.models import Task, TaskChecklist
from app.schemas.task_checklist import TaskChecklistCreate, TaskChecklistOut, TaskChecklistUpdate
from app.services.access import _load_accessible_task
from app.services.activity import log_activity
from app.services.utils import apply_changes

router = APIRouter(prefix="/task-checklists", tags=["Task Checklists"])


@router.post("/{task_id}", response_model=TaskChecklistOut, status_code=201)
def add_checklist_item(task_id: int, payload: TaskChecklistCreate, db: Session = Depends(get_db),
                       user: User = Depends(require_permission(Perm.TASKS_MANAGE_CHECKLISTS))):
    """Add a checklist item to a task."""
    task, project = _load_accessible_task(db, user, task_id)
    item = TaskChecklist(task_id=task.id, **payload.model_dump())
    db.add(item)
    db.flush()
    log_activity(db, user, "task.checklist_added", project_id=project.id, task_id=task.id,
                 details={"checklist_id": item.id, "title": item.title})
    db.commit()
    db.refresh(item)
    return item


@router.get("/{task_id}", response_model=list[TaskChecklistOut])
def list_checklist_items(task_id: int, db: Session = Depends(get_db),
                         user: User = Depends(get_current_user)):
    """List checklist items of a task."""
    task, _ = _load_accessible_task(db, user, task_id)
    return task.checklists


@router.patch("/{task_id}/items/{item_id}", response_model=TaskChecklistOut)
def update_checklist_item(task_id: int, item_id: int, payload: TaskChecklistUpdate, db: Session = Depends(get_db),
                          user: User = Depends(require_permission(Perm.TASKS_MANAGE_CHECKLISTS))):
    """Update a checklist item (e.g. mark completed)."""
    task, project = _load_accessible_task(db, user, task_id)
    item = db.get(TaskChecklist, item_id)
    if not item or item.task_id != task_id:
        raise NotFoundError("Checklist item not found")
    data = payload.model_dump(exclude_unset=True, exclude_none=True)
    if not data:
        raise AppError("No fields to update", 422, "validation_error")
    changes = apply_changes(item, data)
    if changes:
        log_activity(db, user, "task.checklist_updated", project_id=project.id, task_id=task.id,
                     details={"checklist_id": item_id, **changes})
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{task_id}/items/{item_id}", status_code=204)
def delete_checklist_item(task_id: int, item_id: int, db: Session = Depends(get_db),
                          user: User = Depends(require_permission(Perm.TASKS_MANAGE_CHECKLISTS))):
    """Delete a checklist item."""
    task, project = _load_accessible_task(db, user, task_id)
    item = db.get(TaskChecklist, item_id)
    if not item or item.task_id != task_id:
        raise NotFoundError("Checklist item not found")
    db.delete(item)
    db.commit()
    return None