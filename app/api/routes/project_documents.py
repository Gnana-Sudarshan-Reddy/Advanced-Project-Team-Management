"""Project document sharing endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_permission
from app.core.exceptions import NotFoundError
from app.core.permissions import Perm
from app.db.session import get_db
from app.models import ProjectDocument, User
from app.schemas.project_document import ProjectDocumentCreate, ProjectDocumentOut
from app.services.access import ensure_project_access
from app.services.activity import log_activity

router = APIRouter(prefix="/project-documents", tags=["Project Documents"])


@router.post("", response_model=ProjectDocumentOut, status_code=201)
def create_document(payload: ProjectDocumentCreate, project_id: int, db: Session = Depends(get_db),
                    user: User = Depends(require_permission(Perm.PROJECTS_MEMBERS))):
    project = ensure_project_access(db, user, project_id)
    document = ProjectDocument(project_id=project.id, uploaded_by_id=user.id, **payload.model_dump())
    db.add(document)
    db.flush()
    log_activity(db, user, "project.document_added", project_id=project.id,
                 details={"document_id": document.id, "filename": document.filename})
    db.commit()
    db.refresh(document)
    return document


@router.get("", response_model=list[ProjectDocumentOut])
def list_documents(project_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    project = ensure_project_access(db, user, project_id)
    return project.documents


@router.delete("/{document_id}", status_code=204)
def delete_document(document_id: int, db: Session = Depends(get_db),
                    user: User = Depends(require_permission(Perm.PROJECTS_MEMBERS))):
    document = db.get(ProjectDocument, document_id)
    if not document:
        raise NotFoundError("Project document not found")
    ensure_project_access(db, user, document.project_id)
    db.delete(document)
    db.commit()
