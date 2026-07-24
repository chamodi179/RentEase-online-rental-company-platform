from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.deps import get_db, require_role
from app.models.models import Booking, DocumentRecord, User
from app.schemas.admin import CustomerOut, DocumentReviewIn
from app.schemas.common import BookingOut, DocumentOut

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
    db.commit()
    db.refresh(doc)
    return doc
