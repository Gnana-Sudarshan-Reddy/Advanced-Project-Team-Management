"""Endpoints for task dependencies (predecessor/successor links)."""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_permission
from app.core.exceptions import AppError, ConflictError, NotFoundError
from app.core.permissions import Perm
from app.db.session import get_db
from app.models import Task, TaskDependency
from app.schemas.task_dependency import TaskDependencyCreate, TaskDependencyOut
from app.services.access import _load_accessible_task, ensure_project_access

router = APIRouter(prefix="/task-dependencies", tags=["Task Dependencies"])


def _has_dependency(db: Session, task_id: int, depends_on_task_id: int) -> bool:
    return db.scalar(
        select(TaskDependency).where(
            TaskDependency.task_id == task_id,
            TaskDependency.depends_on_task_id == depends_on_task_id,
        )
    ) is not None


def _would_create_cycle(db: Session, task_id: int, prerequisite_id: int) -> bool:
    """Return true when adding task -> prerequisite would create a cycle."""
    graph: dict[int, set[int]] = {}
    for source, target in db.query(TaskDependency.task_id, TaskDependency.depends_on_task_id).all():
        graph.setdefault(source, set()).add(target)
    graph.setdefault(task_id, set()).add(prerequisite_id)
    stack = [prerequisite_id]
    visited: set[int] = set()
    while stack:
        current = stack.pop()
        if current == task_id:
            return True
        if current in visited:
            continue
        visited.add(current)
        stack.extend(graph.get(current, ()))
    return False


@router.post("", response_model=TaskDependencyOut, status_code=201)
def add_dependency(payload: TaskDependencyCreate, db: Session = Depends(get_db),
                   user: User = Depends(require_permission(Perm.TASKS_MANAGE_DEPENDENCIES))):
    """Declare that task depends on depends_on_task being completed first."""
    if payload.task_id == payload.depends_on_task_id:
        raise AppError("A task cannot depend on itself", 422, "self_dependency")
    # Both tasks must be in the same accessible project.
    task, project = _load_accessible_task(db, user, payload.task_id)
    dep_task, _ = _load_accessible_task(db, user, payload.depends_on_task_id)
    if dep_task.project_id != project.id:
        raise AppError("Dependent tasks must belong to the same project", 422, "cross_project")
    if _has_dependency(db, payload.task_id, payload.depends_on_task_id):
        raise ConflictError("Dependency already exists", 409, "duplicate_dependency")
    if _would_create_cycle(db, payload.task_id, payload.depends_on_task_id):
        raise ConflictError("Dependency would create a circular dependency", 409, "circular_dependency")
    dependency = TaskDependency(task_id=payload.task_id, depends_on_task_id=payload.depends_on_task_id)
    db.add(dependency)
    db.flush()
    from app.services.activity import log_activity
    log_activity(db, user, "task.dependency_added", project_id=project.id, task_id=payload.task_id,
                 details={"depends_on_task_id": payload.depends_on_task_id})
    db.commit()
    db.refresh(dependency)
    return dependency


@router.get("", response_model=list[TaskDependencyOut])
def list_dependencies(task_id: int, db: Session = Depends(get_db),
                      user: User = Depends(get_current_user)):
    """List dependencies of a task (tasks it depends on)."""
    task, _ = _load_accessible_task(db, user, task_id)
    return task.dependencies_as_dependent


@router.delete("/{dependency_id}", status_code=204)
def remove_dependency(dependency_id: int, db: Session = Depends(get_db),
                      user: User = Depends(require_permission(Perm.TASKS_MANAGE_DEPENDENCIES))):
    """Remove a task dependency."""
    dependency = db.get(TaskDependency, dependency_id)
    if not dependency:
        raise NotFoundError("Dependency not found")
    task, project = _load_accessible_task(db, user, dependency.task_id)
    db.delete(dependency)
    db.commit()
    return None
