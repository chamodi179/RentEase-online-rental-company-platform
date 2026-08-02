from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_db, require_role
from app.models.models import Booking, Payment
from app.schemas.admin import ManualPaymentIn
from app.schemas.common import PaymentOut
from app.services.audit_service import record_audit_log
from app.services.refund_service import refund_booking_payment
from app.services.realtime import publish_booking_event

router = APIRouter(prefix="/payments", tags=["admin-payments"])
staff_only = require_role(["staff", "super_admin"])
super_admin_only = require_role(["super_admin"])


@router.get("", response_model=list[PaymentOut])
def list_payments(status_filter: str | None = None, db: Session = Depends(get_db), _=Depends(staff_only)):
    query = db.query(Payment)
    if status_filter:
        query = query.filter(Payment.status == status_filter)
    return query.order_by(Payment.created_at.desc()).all()


@router.post("", response_model=PaymentOut, status_code=201)
def record_manual_payment(payload: ManualPaymentIn, db: Session = Depends(get_db), user=Depends(super_admin_only)):
    """Cash / bank transfer for offline payments (spec §5.5). Restricted to
    super_admin only — regular staff can view the payments ledger
    (list_payments above) but cannot record manual transactions, since a
    manual payment/refund entry bypasses Stripe entirely and is trusted
    at face value."""
    booking = db.get(Booking, payload.booking_id)
    if not booking:
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
    # Reuses the booking-events channel/hook: the payments ledger page just
    # needs "something changed, go re-fetch", same as the bookings pages —
    # no separate channel or frontend plumbing needed for that.
    publish_booking_event(
        booking_id=booking.id, booking_reference=booking.booking_reference,
        status=booking.status, event=f"payment_{payload.type}",
    )
    return payment


@router.post("/{booking_id}/refund", response_model=PaymentOut)
def refund_payment(booking_id: int, db: Session = Depends(get_db), user=Depends(staff_only)):
    """Explicit, deliberate refund action — the only way a staff-cancelled
    booking gets refunded. cancel_booking() no longer auto-refunds for a
    staff-initiated cancellation (see admin_initiated there): cancelling
    and refunding are different decisions, and moving real money
    shouldn't be a silent side effect of clicking "Mark cancelled". A
    customer's own self-cancellation is the one case that still
    auto-refunds, since eligibility already gates whether they could
    cancel at all (see customer_can_cancel).

    Requires the booking to already be "cancelled" — refunding an
    in-progress rental without cancelling it first would leave the
    customer holding a (possibly still-active) booking with no payment
    behind it. Cancel it first (POST /admin/bookings/{id}/status), then
    come back here.

    Calls the same Stripe-backed, idempotent refund_service used
    everywhere else — calling it twice for the same booking just returns
    the existing refund record rather than double-refunding."""
    booking = db.get(Booking, booking_id)
    if not booking:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Booking not found")
    if booking.status != "cancelled":
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "This booking isn't cancelled yet — cancel it first (which may already refund it automatically).",
        )

    refund = refund_booking_payment(db, booking, actor_id=user.id)
    if not refund:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No successful payment found to refund")
    publish_booking_event(
        booking_id=booking.id, booking_reference=booking.booking_reference,
        status=booking.status, event="refunded",
    )
    return refund
