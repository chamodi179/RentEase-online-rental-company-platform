from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_db, require_role
from app.models.models import Booking, Payment
from app.schemas.admin import ManualPaymentIn, PaymentOut
from app.services.audit_service import record_audit_log

router = APIRouter(prefix="/payments", tags=["admin-payments"])
staff_only = require_role(["staff", "super_admin"])


@router.get("", response_model=list[PaymentOut])
def list_payments(status_filter: str | None = None, db: Session = Depends(get_db), _=Depends(staff_only)):
    query = db.query(Payment)
    if status_filter:
        query = query.filter(Payment.status == status_filter)
    return query.order_by(Payment.created_at.desc()).all()


@router.post("", response_model=PaymentOut, status_code=201)
def record_manual_payment(payload: ManualPaymentIn, db: Session = Depends(get_db), user=Depends(staff_only)):
    """Cash / bank transfer for offline payments (spec §5.5)."""
    if not db.get(Booking, payload.booking_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Booking not found")
    payment = Payment(**payload.model_dump(), status="success")
    db.add(payment)
    db.flush()
    record_audit_log(
        db, actor_id=user.id, action="payment.recorded_manual",
        entity_type="payment", entity_id=payment.id,
    )
    db.commit()
    db.refresh(payment)
    return payment
