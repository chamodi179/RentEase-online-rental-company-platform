from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.deps import get_db, require_role
from app.models.models import Booking, BookingStatusHistory, Payment, User
from app.schemas.common import BookingOut, CheckoutSessionOut
from app.services.payments_service import create_checkout_session as build_checkout_session
from app.services.payments_service import is_stripe_configured
from app.worker import send_booking_confirmation_email

router = APIRouter(prefix="/payments", tags=["payments"])
customer_only = require_role(["customer"])


def _get_own_pending_booking(db: Session, booking_id: int, user: User) -> Booking:
    booking = db.get(Booking, booking_id)
    if not booking or booking.customer_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Booking not found")
    if booking.status != "pending":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Booking is not awaiting payment")
    return booking


@router.post("/checkout/{booking_id}", response_model=CheckoutSessionOut)
def create_checkout_session(booking_id: int, db: Session = Depends(get_db), user: User = Depends(customer_only)):
    booking = _get_own_pending_booking(db, booking_id, user)
    checkout_url, session_id, is_mock = build_checkout_session(booking)
    return CheckoutSessionOut(checkout_url=checkout_url, session_id=session_id, is_mock=is_mock)


@router.post("/mock-complete/{booking_id}", response_model=BookingOut)
def mock_complete_checkout(booking_id: int, db: Session = Depends(get_db), user: User = Depends(customer_only)):
    """Local-dev only: simulates the Stripe webhook confirming a successful
    card payment (the 'Simulate successful payment' button on
    /mock-checkout). Disabled once a real STRIPE_SECRET_KEY is configured,
    since real payments must be confirmed by the real webhook instead."""
    if is_stripe_configured():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Mock checkout is disabled — Stripe is configured")

    booking = _get_own_pending_booking(db, booking_id, user)

    db.add(Payment(
        booking_id=booking.id, type="payment", amount=booking.total_amount,
        method="card", gateway_reference=f"cs_mock_{booking.booking_reference}", status="success",
    ))
    old_status = booking.status
    booking.status = "confirmed"
    db.add(BookingStatusHistory(booking_id=booking.id, old_status=old_status, new_status="confirmed", changed_by=user.id))
    db.commit()
    db.refresh(booking)

    # Same state-machine path the real Stripe webhook uses, so it shows up
    # in booking_status_history either way.
    send_booking_confirmation_email.delay(booking.booking_reference, booking.customer.email)
    return booking


@router.post("/webhook", include_in_schema=False)
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """Stripe hits this directly — never trust the frontend to confirm
    payment success (architecture doc §7)."""
    payload = await request.json()
    event_type = payload.get("type")

    if event_type == "checkout.session.completed":
        session = payload["data"]["object"]
        booking_ref = session.get("metadata", {}).get("booking_reference")
        booking = db.query(Booking).filter(Booking.booking_reference == booking_ref).first()
        if booking:
            db.add(Payment(
                booking_id=booking.id, type="payment", amount=booking.total_amount,
                # payment_intent (not the checkout session id) is what
                # stripe.Refund.create(payment_intent=...) needs later.
                method="card", gateway_reference=session.get("payment_intent"), status="success",
            ))
            booking.status = "confirmed"
            db.commit()
            # Enqueued to Celery — neither frontend nor this request waits on email delivery.
            send_booking_confirmation_email.delay(booking.booking_reference, booking.customer.email)

    return {"received": True}
