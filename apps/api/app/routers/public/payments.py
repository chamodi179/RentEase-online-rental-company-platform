import stripe
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import get_db, require_role
from app.models.models import Booking, Payment, User
from app.schemas.common import BookingOut, CheckoutSessionOut
from app.services.booking_service import change_status
from app.worker import send_booking_confirmation_email

router = APIRouter(prefix="/payments", tags=["payments"])
customer_only = require_role(["customer"])

stripe.api_key = settings.STRIPE_SECRET_KEY


def _confirm_booking_paid(db: Session, booking: Booking, gateway_reference: str) -> Booking:
    """Idempotent: safe to call from both the webhook and the success-page
    sync check, whichever gets there first."""
    if booking.status != "pending":
        return booking
    db.add(Payment(
        booking_id=booking.id, type="payment", amount=booking.total_amount,
        method="card", gateway_reference=gateway_reference, status="success",
    ))
    booking = change_status(db, booking, "confirmed", changed_by=None)
    send_booking_confirmation_email.delay(
        booking.booking_reference,
        booking.customer.email,
        item_name=booking.item.name,
        start_date=booking.start_datetime.strftime("%Y-%m-%d"),
        end_date=booking.end_datetime.strftime("%Y-%m-%d"),
        total_amount=str(booking.total_amount),
    )
    return booking


@router.post("/checkout/{booking_id}", response_model=CheckoutSessionOut)
def create_checkout_session(booking_id: int, db: Session = Depends(get_db), user: User = Depends(customer_only)):
    booking = db.get(Booking, booking_id)
    if not booking or booking.customer_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Booking not found")
    if booking.status != "pending":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Booking is not awaiting payment")

    try:
        session = stripe.checkout.Session.create(
            mode="payment",
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": "usd",
                    "product_data": {"name": f"{booking.item.name} — {booking.booking_reference}"},
                    # Stripe wants the smallest currency unit (cents).
                    "unit_amount": int(booking.total_amount * 100),
                },
                "quantity": 1,
            }],
            client_reference_id=str(booking.id),
            metadata={"booking_id": str(booking.id), "booking_reference": booking.booking_reference},
            success_url=(
                f"{settings.FRONTEND_ORIGIN}/checkout/success"
                f"?booking_id={booking.id}&session_id={{CHECKOUT_SESSION_ID}}"
            ),
            cancel_url=f"{settings.FRONTEND_ORIGIN}/account/bookings/{booking.id}",
        )
    except stripe.error.StripeError as exc:
        # Without this, an unreachable/misconfigured Stripe account (e.g. a
        # placeholder STRIPE_SECRET_KEY) raises unhandled here, which the
        # browser reports as an opaque "Failed to fetch" — and because the
        # booking created just before this call stays "pending", it keeps
        # holding the calendar slot even though the customer never got a
        # usable error message. Surface a real 502 instead so the frontend
        # can show something actionable and the booking can be retried
        # against the same reservation rather than creating a new one.
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY, f"Could not start payment: {exc.user_message or str(exc)}"
        )
    return CheckoutSessionOut(checkout_url=session.url, session_id=session.id)


@router.get("/checkout/{booking_id}/sync", response_model=BookingOut)
def sync_checkout_session(
    booking_id: int, session_id: str, db: Session = Depends(get_db), user: User = Depends(customer_only)
):
    """Called from the success-page redirect so the customer sees 'confirmed'
    immediately, without waiting on the webhook to land. The webhook (below)
    remains the durable source of truth — this is a best-effort UX shortcut,
    server-verified against Stripe directly rather than trusting query params."""
    booking = db.get(Booking, booking_id)
    if not booking or booking.customer_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Booking not found")

    session = stripe.checkout.Session.retrieve(session_id)
    if session.metadata.get("booking_id") != str(booking.id):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Session does not match booking")
    if session.payment_status == "paid":
        booking = _confirm_booking_paid(db, booking, gateway_reference=session.id)
    return booking


@router.post("/webhook", include_in_schema=False)
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """Stripe hits this directly — never trust the frontend to confirm
    payment success (architecture doc §7). Signature is verified against
    STRIPE_WEBHOOK_SECRET so this can't be spoofed by a POST from anywhere else."""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, settings.STRIPE_WEBHOOK_SECRET)
    except (ValueError, stripe.error.SignatureVerificationError):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid webhook signature")

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        booking_id = session.get("metadata", {}).get("booking_id")
        booking = db.get(Booking, int(booking_id)) if booking_id else None
        if booking and session.get("payment_status") == "paid":
            _confirm_booking_paid(db, booking, gateway_reference=session.get("id"))

    return {"received": True}
