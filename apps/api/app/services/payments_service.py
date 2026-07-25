"""Stripe integration with a local-dev mock fallback.

If STRIPE_SECRET_KEY in .env is a real key, checkout goes through actual
Stripe Checkout Sessions and refunds go through actual stripe.Refund.
Locally, .env.example ships with a placeholder key, so both operations
fall back to a mock path that lets the whole booking -> pay -> cancel ->
refund flow be exercised end-to-end without a Stripe account. Swap in a
real key and the mock path is never used; nothing else changes.
"""

import stripe

from app.core.config import settings
from app.models.models import Booking, Payment

stripe.api_key = settings.STRIPE_SECRET_KEY


def is_stripe_configured() -> bool:
    key = settings.STRIPE_SECRET_KEY
    return bool(key) and "placeholder" not in key and "xxx" not in key


def create_checkout_session(booking: Booking) -> tuple[str, str, bool]:
    """Returns (checkout_url, session_id, is_mock)."""
    if is_stripe_configured():
        session = stripe.checkout.Session.create(
            mode="payment",
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": "usd",
                    "unit_amount": int(booking.total_amount * 100),
                    "product_data": {"name": f"RentEase booking {booking.booking_reference}"},
                },
                "quantity": 1,
            }],
            success_url=f"{settings.FRONTEND_ORIGIN}/account/bookings/{booking.id}",
            cancel_url=f"{settings.FRONTEND_ORIGIN}/account/bookings/{booking.id}",
            metadata={"booking_reference": booking.booking_reference},
        )
        return session.url, session.id, False

    # Mock path: no real Stripe call, hand back a link to the in-app
    # mock checkout page so the flow can be completed locally.
    mock_session_id = f"cs_mock_{booking.booking_reference}"
    checkout_url = f"{settings.FRONTEND_ORIGIN}/mock-checkout/{mock_session_id}?booking_id={booking.id}"
    return checkout_url, mock_session_id, True


def issue_refund(db, booking: Booking, original_payment: Payment | None) -> Payment:
    """Records a refund payment row. Attempts a real Stripe refund when
    configured and a gateway reference exists; otherwise leaves the refund
    `pending` for manual reconciliation via the admin Payments screen —
    the same as a cash/bank-transfer refund would be handled."""
    refund_status = "pending"

    if is_stripe_configured() and original_payment and original_payment.gateway_reference:
        try:
            stripe.Refund.create(payment_intent=original_payment.gateway_reference)
            refund_status = "success"
        except stripe.error.StripeError:
            refund_status = "failed"

    refund = Payment(
        booking_id=booking.id,
        type="refund",
        amount=booking.total_amount,
        method=original_payment.method if original_payment else "card",
        gateway_reference=original_payment.gateway_reference if original_payment else None,
        status=refund_status,
    )
    db.add(refund)
    db.commit()
    db.refresh(refund)
    return refund
