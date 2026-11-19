"""Validation and response schemas for resource allocations."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class ResourceAllocationBase(BaseModel):
    """Fields shared by resource allocation creation and details."""

    allocation_percent: int = Field(default=100, ge=0, le=100)
    start_date: date
    end_date: date


class ResourceAllocationCreate(ResourceAllocationBase):
    """Input for allocating a user to a project."""


class ResourceAllocationUpdate(BaseModel):
    """Optional fields accepted when changing a resource allocation."""

    allocation_percent: int | None = Field(default=None, ge=0, le=100)
    start_date: date | None = None
    end_date: date | None = None


class ResourceAllocationOut(ResourceAllocationBase):
    """Resource allocation fields returned by the API."""

    model_config = ConfigDict(from_attributes=True)
    id: int
    project_id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
