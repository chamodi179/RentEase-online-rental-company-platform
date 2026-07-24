from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_db, require_role
from app.models.models import DocumentRecord, User
from app.schemas.common import DocumentOut

router = APIRouter(prefix="/documents", tags=["documents"])
customer_only = require_role(["customer"])


@router.post("/presign")
def presign_upload(filename: str, user: User = Depends(customer_only)):
    """Returns a presigned MinIO/S3 URL the browser uploads directly to —
    the API never proxies file bytes (architecture doc §7)."""
    key = f"documents/{user.id}/{filename}"
    # In production this calls boto3's generate_presigned_url against MinIO.
    return {"upload_url": f"https://minio.rentease.internal/{key}?X-Amz-Signature=stub", "file_key": key}


@router.post("", response_model=DocumentOut)
def register_document(
    document_type: str, file_url: str, db: Session = Depends(get_db), user: User = Depends(customer_only)
):
    doc = DocumentRecord(user_id=user.id, document_type=document_type, file_url=file_url)
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


@router.get("", response_model=list[DocumentOut])
def my_documents(db: Session = Depends(get_db), user: User = Depends(customer_only)):
    return db.query(DocumentRecord).filter(DocumentRecord.user_id == user.id).all()
