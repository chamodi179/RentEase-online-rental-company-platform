from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.deps import get_db, require_role
from app.core.s3 import generate_presigned_get, key_from_file_url
from app.models.models import Booking, DocumentRecord, User
from app.schemas.admin import CustomerOut, DocumentReviewIn, DocumentViewUrlOut
from app.schemas.common import BookingOut, DocumentOut
from app.services.audit_service import record_audit_log

router = APIRouter(prefix="/customers", tags=["admin-customers"])
staff_only = require_role(["staff", "super_admin"])


@router.get("", response_model=list[CustomerOut])
def list_customers(q: str | None = None, db: Session = Depends(get_db), _=Depends(staff_only)):
    query = (
        db.query(User, func.count(Booking.id).label("booking_count"))
        .outerjoin(Booking, Booking.customer_id == User.id)
        .filter(User.role == "customer")
        .group_by(User.id)
    )
    if q:
        query = query.filter(User.full_name.ilike(f"%{q}%") | User.email.ilike(f"%{q}%"))

    results = []
    for user, count in query.all():
        out = CustomerOut.model_validate(user)
        out.booking_count = count
        results.append(out)
    return results


@router.get("/{customer_id}/bookings", response_model=list[BookingOut])
def customer_bookings(customer_id: int, db: Session = Depends(get_db), _=Depends(staff_only)):
    return db.query(Booking).filter(Booking.customer_id == customer_id).all()


@router.get("/documents/pending", response_model=list[DocumentOut])
def pending_documents(db: Session = Depends(get_db), _=Depends(staff_only)):
    return db.query(DocumentRecord).filter(DocumentRecord.verification_status == "pending").all()


@router.get("/documents/{document_id}/view-url", response_model=DocumentViewUrlOut)
def document_view_url(document_id: int, db: Session = Depends(get_db), _=Depends(staff_only)):
    """The bucket is private, so DocumentRecord.file_url can't be opened
    directly — the presigned PUT used at upload time only ever authorized
    that one write, not a later read (see s3.py). Mint a short-lived
    presigned GET for staff to actually view the file."""
    doc = db.get(DocumentRecord, document_id)
    if not doc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    key = key_from_file_url(doc.file_url)
    return DocumentViewUrlOut(view_url=generate_presigned_get(key))


@router.post("/documents/{document_id}/review", response_model=DocumentOut)
def review_document(
    document_id: int, payload: DocumentReviewIn, db: Session = Depends(get_db), user=Depends(staff_only)
):
    doc = db.get(DocumentRecord, document_id)
    if not doc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    if payload.verification_status not in ("approved", "rejected"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid verification_status")
    doc.verification_status = payload.verification_status
    doc.reviewed_by = user.id
    record_audit_log(
        db, actor_id=user.id, action=f"document.{payload.verification_status}",
        entity_type="document", entity_id=doc.id,
    )
    db.commit()
    db.refresh(doc)
    return doc
