import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import get_db, require_role
from app.core.s3 import generate_presigned_put
from app.models.models import DocumentRecord, User
from app.schemas.common import DocumentOut, DocumentRegisterIn, PresignOut, PresignRequest
from app.services.audit_service import record_audit_log

router = APIRouter(prefix="/documents", tags=["documents"])
customer_only = require_role(["customer"])


@router.post("/presign", response_model=PresignOut)
def presign_upload(payload: PresignRequest, user: User = Depends(customer_only)):
    """Returns a presigned MinIO/S3 URL the browser uploads directly to —
    the API never proxies file bytes (architecture doc §7)."""
    # uuid4 prefix avoids filename collisions/overwrites between uploads.
    safe_name = payload.filename.replace("/", "_")
    key = f"documents/{user.id}/{uuid.uuid4().hex}_{safe_name}"
    upload_url = generate_presigned_put(key, content_type=payload.content_type)
    file_url = f"{settings.S3_PUBLIC_ENDPOINT}/{settings.S3_BUCKET}/{key}"
    return PresignOut(upload_url=upload_url, file_url=file_url)


@router.post("", response_model=DocumentOut)
def register_document(
    payload: DocumentRegisterIn, db: Session = Depends(get_db), user: User = Depends(customer_only)
):
    # Without this check, register_document trusted whatever file_url the
    # client sent — a user could register any URL (someone else's document,
    # an unrelated site) as their verification doc without ever uploading
    # anything. Require it to match the presigned-upload path we handed out
    # for this specific user.
    expected_prefix = f"{settings.S3_PUBLIC_ENDPOINT}/{settings.S3_BUCKET}/documents/{user.id}/"
    if not payload.file_url.startswith(expected_prefix):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "file_url does not match a document uploaded by this account"
        )
    doc = DocumentRecord(user_id=user.id, document_type=payload.document_type, file_url=payload.file_url)
    db.add(doc)
    db.flush()
    record_audit_log(
        db, actor_id=user.id, action="document.uploaded",
        entity_type="document", entity_id=doc.id,
    )
    db.commit()
    db.refresh(doc)
    return doc


@router.get("", response_model=list[DocumentOut])
def my_documents(db: Session = Depends(get_db), user: User = Depends(customer_only)):
    return db.query(DocumentRecord).filter(DocumentRecord.user_id == user.id).all()
