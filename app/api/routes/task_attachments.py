"""Endpoints for task attachments (file metadata records)."""

from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_permission
from app.core.exceptions import AppError, NotFoundError
from app.core.permissions import Perm
from app.core.config import settings
from app.db.session import get_db
from app.models import Task, TaskAttachment, User
from app.schemas.task_attachment import TaskAttachmentOut, TaskAttachmentUpload
from app.services.access import _load_accessible_task
from app.services.activity import log_activity

router = APIRouter(prefix="/task-attachments", tags=["Task Attachments"])


@router.post("/{task_id}/upload", response_model=TaskAttachmentOut, status_code=201)
def upload_attachment(task_id: int, file: UploadFile = File(...), db: Session = Depends(get_db),
                      user: User = Depends(require_permission(Perm.TASKS_MANAGE_ATTACHMENTS))):
    """Upload a file and attach it to a task."""
    task, project = _load_accessible_task(db, user, task_id)
    if file.content_type not in settings.ALLOWED_UPLOAD_TYPES:
        raise AppError("Unsupported file type", 415, "unsupported_file_type")
    contents = file.file.read(settings.MAX_UPLOAD_BYTES + 1)
    if len(contents) > settings.MAX_UPLOAD_BYTES:
        raise AppError("File exceeds the maximum upload size", 413, "file_too_large")
    upload_dir = Path(settings.UPLOAD_DIR) / "tasks" / str(task.id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    safe_name = Path(file.filename or "upload.bin").name
    target = upload_dir / f"{uuid4().hex}_{safe_name}"
    target.write_bytes(contents)
    attachment = TaskAttachment(task_id=task.id, uploaded_by_id=user.id, filename=safe_name,
                                file_path=str(target), file_size=len(contents),
                                content_type=file.content_type)
    db.add(attachment)
    db.flush()
    log_activity(db, user, "task.attachment_added", project_id=project.id, task_id=task.id,
                 details={"attachment_id": attachment.id, "filename": safe_name})
    db.commit()
    db.refresh(attachment)
    return attachment


@router.post("/{task_id}", response_model=TaskAttachmentOut, status_code=201)
def add_attachment(task_id: int, payload: TaskAttachmentUpload, db: Session = Depends(get_db),
                   user: User = Depends(require_permission(Perm.TASKS_MANAGE_ATTACHMENTS))):
    """Record an attachment on a task (file is stored at file_path by the client)."""
    task, project = _load_accessible_task(db, user, task_id)
    attachment = TaskAttachment(
        task_id=task.id, uploaded_by_id=user.id,
        filename=payload.filename, file_path=payload.file_path,
        file_size=payload.file_size, content_type=payload.content_type,
    )
    db.add(attachment)
    db.flush()
    log_activity(db, user, "task.attachment_added", project_id=project.id, task_id=task.id,
                 details={"attachment_id": attachment.id, "filename": payload.filename})
    db.commit()
    db.refresh(attachment)
    return attachment


@router.get("/{task_id}", response_model=list[TaskAttachmentOut])
def list_attachments(task_id: int, db: Session = Depends(get_db),
                     user: User = Depends(get_current_user)):
    """List attachments of a task."""
    task, _ = _load_accessible_task(db, user, task_id)
    return task.attachments


@router.get("/download/{attachment_id}")
def download_attachment(attachment_id: int, db: Session = Depends(get_db),
                        user: User = Depends(get_current_user)):
    """Download an attachment after checking project access and storage boundaries."""
    attachment = db.get(TaskAttachment, attachment_id)
    if not attachment:
        raise NotFoundError("Attachment not found")
    _load_accessible_task(db, user, attachment.task_id)
    upload_root = Path(settings.UPLOAD_DIR).resolve()
    file_path = Path(attachment.file_path).resolve()
    if upload_root not in file_path.parents or not file_path.is_file():
        raise NotFoundError("Attachment file is unavailable")
    return FileResponse(file_path, media_type=attachment.content_type or "application/octet-stream",
                        filename=attachment.filename)


@router.delete("/{attachment_id}", status_code=204)
def delete_attachment(attachment_id: int, db: Session = Depends(get_db),
                      user: User = Depends(require_permission(Perm.TASKS_MANAGE_ATTACHMENTS))):
    """Delete an attachment record."""
    attachment = db.get(TaskAttachment, attachment_id)
    if not attachment:
        raise NotFoundError("Attachment not found")
    task, project = _load_accessible_task(db, user, attachment.task_id)
    db.delete(attachment)
    db.commit()
    return None
