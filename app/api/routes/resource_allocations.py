"""Endpoints for resource allocation across projects."""

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_permission
from app.core.exceptions import AppError, NotFoundError
from app.core.permissions import Perm, RoleName
from app.db.session import get_db
from app.models import Project, ResourceAllocation, User
from app.schemas.resource_allocation import (
    ResourceAllocationCreate, ResourceAllocationOut, ResourceAllocationUpdate,
)
from app.services.access import ensure_project_access, get_user_or_404
from app.services.activity import log_activity
from app.services.utils import apply_changes

router = APIRouter(prefix="/resource-allocations", tags=["Resource Allocations"])


@router.post("", response_model=ResourceAllocationOut, status_code=201)
def create_allocation(payload: ResourceAllocationCreate, db: Session = Depends(get_db),
                      user: User = Depends(require_permission(Perm.RESOURCE_MANAGE))):
    """Allocate a user's capacity to a project over a date range."""
    project = ensure_project_access(db, user, payload.project_id)
    get_user_or_404(db, payload.user_id)
    if payload.end_date < payload.start_date:
        raise AppError("end_date must be after start_date", 422, "invalid_range")
    allocation = ResourceAllocation(**payload.model_dump())
    db.add(allocation)
    db.flush()
    log_activity(db, user, "resource.allocation_created", project_id=project.id,
                 details={"allocation_id": allocation.id, "user_id": payload.user_id})
    db.commit()
    db.refresh(allocation)
    return allocation


@router.get("", response_model=list[ResourceAllocationOut])
def list_allocations(
    project_id: int | None = Query(None),
    user_id: int | None = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List resource allocations (filterable by project/user)."""
    query = db.query(ResourceAllocation)
    if project_id is not None:
        ensure_project_access(db, user, project_id)
        query = query.filter(ResourceAllocation.project_id == project_id)
    else:
        from app.core.permissions import RoleName
        if user.role.name != RoleName.ADMIN.value:
            from app.services.access import accessible_project_ids
            query = query.filter(ResourceAllocation.project_id.in_(accessible_project_ids(user)))
    if user_id is not None:
        query = query.filter(ResourceAllocation.user_id == user_id)
    return query.order_by(ResourceAllocation.start_date.asc()).all()


@router.get("/{allocation_id}", response_model=ResourceAllocationOut)
def get_allocation(allocation_id: int, db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    """Return one allocation after checking project access."""
    allocation = db.get(ResourceAllocation, allocation_id)
    if not allocation:
        raise NotFoundError("Allocation not found")
    ensure_project_access(db, user, allocation.project_id)
    return allocation


@router.patch("/{allocation_id}", response_model=ResourceAllocationOut)
def update_allocation(allocation_id: int, payload: ResourceAllocationUpdate, db: Session = Depends(get_db),
                      user: User = Depends(require_permission(Perm.RESOURCE_MANAGE))):
    """Update a resource allocation."""
    allocation = db.get(ResourceAllocation, allocation_id)
    if not allocation:
        raise NotFoundError("Allocation not found")
    project = ensure_project_access(db, user, allocation.project_id)
    data = payload.model_dump(exclude_unset=True, exclude_none=True)
    start_date = data.get("start_date", allocation.start_date)
    end_date = data.get("end_date", allocation.end_date)
    if end_date < start_date:
        raise AppError("end_date must be after start_date", 422, "invalid_range")
    changes = apply_changes(allocation, data)
    if changes:
        log_activity(db, user, "resource.allocation_updated", project_id=project.id,
                     details={"allocation_id": allocation_id, **changes})
    db.commit()
    db.refresh(allocation)
    return allocation


@router.delete("/{allocation_id}", status_code=204)
def delete_allocation(allocation_id: int, db: Session = Depends(get_db),
                      user: User = Depends(require_permission(Perm.RESOURCE_MANAGE))):
    """Delete a resource allocation."""
    allocation = db.get(ResourceAllocation, allocation_id)
    if not allocation:
        raise NotFoundError("Allocation not found")
    project = ensure_project_access(db, user, allocation.project_id)
    db.delete(allocation)
    db.commit()
    return None