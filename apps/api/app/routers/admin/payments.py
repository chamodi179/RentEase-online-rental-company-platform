from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_db, require_role
from app.models.models import Booking, Payment
from app.schemas.admin import ManualPaymentIn, PaymentOut

router = APIRouter(prefix="/payments", tags=["admin-payments"])
staff_only = require_role(["staff", "super_admin"])


@router.get("", response_model=list[PaymentOut])
def list_payments(status_filter: str | None = None, db: Session = Depends(get_db), _=Depends(staff_only)):
    query = db.query(Payment)
    if status_filter:
        query = query.filter(Payment.status == status_filter)
    return query.order_by(Payment.created_at.desc()).all()


@router.post("", response_model=PaymentOut, status_code=201)
def record_manual_payment(payload: ManualPaymentIn, db: Session = Depends(get_db), _=Depends(staff_only)):
    """Cash / bank transfer for offline payments (spec §5.5)."""
    if not db.get(Booking, payload.booking_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Booking not found")
    payment = Payment(**payload.model_dump(), status="success")
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return payment
