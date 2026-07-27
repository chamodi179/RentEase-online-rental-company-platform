import stripe
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import Booking, Payment
from app.services.audit_service import record_audit_log

stripe.api_key = settings.STRIPE_SECRET_KEY


def refund_booking_payment(db: Session, booking: Booking, *, actor_id: int | None = None) -> Payment | None:
    """Issue a refund for a booking's successful payment and record it.

    Previously nothing in the backend ever created a `type="refund"` Payment
    row or called Stripe on cancellation — cancelling a paid booking just
    flipped its status with no financial follow-through. This is idempotent:
    if a refund has already been recorded for this booking, it's returned
    as-is instead of refunding twice.
    """
    payment = (
        db.query(Payment)
        .filter(Payment.booking_id == booking.id, Payment.type == "payment", Payment.status == "success")
        .order_by(Payment.created_at.desc())
        .first()
    )
    if not payment:
        return None

    existing_refund = (
        db.query(Payment)
        .filter(Payment.booking_id == booking.id, Payment.type == "refund")
        .first()
    )
    if existing_refund:
        return existing_refund

    gateway_reference = None
    refund_status = "success"

    if payment.method == "card" and payment.gateway_reference:
        try:
            # gateway_reference on the original payment is the Checkout
            # Session id; refunds are issued against the PaymentIntent it
            # settled into, so look that up first.
            session = stripe.checkout.Session.retrieve(payment.gateway_reference)
            payment_intent_id = session.payment_intent
            if payment_intent_id:
                refund = stripe.Refund.create(payment_intent=payment_intent_id)
                gateway_reference = refund.id
            else:
                refund_status = "failed"
        except stripe.error.StripeError:
            # Still record that a refund is owed, but flag it "failed" so
            # it shows up for manual follow-up instead of silently looking
            # like money actually moved.
            refund_status = "failed"
    else:
        # Cash / bank-transfer payments have no gateway to call — staff
        # handle those refunds offline; record it as pending their action.
        refund_status = "pending"

    refund_payment = Payment(
        booking_id=booking.id,
        type="refund",
        amount=payment.amount,
        method=payment.method,
        gateway_reference=gateway_reference,
        status=refund_status,
    )
    db.add(refund_payment)
    db.flush()
    record_audit_log(
        db, actor_id=actor_id, action=f"payment.refund_{refund_status}",
        entity_type="payment", entity_id=refund_payment.id,
    )
    db.commit()
    db.refresh(refund_payment)
    return refund_payment
