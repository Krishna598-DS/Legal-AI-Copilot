"""Document management routes."""

from fastapi import APIRouter, BackgroundTasks, Depends, File, UploadFile
from sqlalchemy.orm import Session

from src.api.deps import enforce_upload_rate_limit, get_current_user
from src.auth.schemas import DocumentResponse, UploadResponse
from src.db.database import get_db
from src.db.models import User
from src.services import document_service, rag_service

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("", response_model=list[DocumentResponse])
def list_my_documents(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return document_service.list_documents(db, user)


@router.post("/upload", response_model=UploadResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user: User = Depends(enforce_upload_rate_limit),
    db: Session = Depends(get_db),
):
    """
    Accept upload immediately, then parse/chunk/embed in a background task.
    Poll GET /documents/{id} until status is READY or FAILED.
    """
    doc = await document_service.accept_upload(db, user, file)
    background_tasks.add_task(document_service.run_ingestion_job, doc.id)
    return UploadResponse(
        message="Document uploaded. Processing started.",
        document=DocumentResponse.model_validate(doc),
    )


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    doc = document_service.get_user_document(db, user, document_id)
    return DocumentResponse.model_validate(doc)


@router.delete("/{document_id}")
def delete_document(
    document_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    document_service.delete_document(db, user, document_id)
    rag_service.invalidate_rag(document_id)
    return {"message": "Document deleted"}
