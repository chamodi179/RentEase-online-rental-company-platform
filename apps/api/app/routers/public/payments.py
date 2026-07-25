from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.deps import get_db, require_role
from app.models.models import Booking, Payment, User
from app.schemas.common import CheckoutSessionOut
from app.worker import send_booking_confirmation_email

router = APIRouter(prefix="/payments", tags=["payments"])
customer_only = require_role(["customer"])


@router.post("/checkout/{booking_id}", response_model=CheckoutSessionOut)
def create_checkout_session(booking_id: int, db: Session = Depends(get_db), user: User = Depends(customer_only)):
    booking = db.get(Booking, booking_id)
    if not booking or booking.customer_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Booking not found")
    if booking.status != "pending":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Booking is not awaiting payment")

    # Production: stripe.checkout.Session.create(...) with booking.total_amount,
    # success_url pointing back to /account/bookings/{id}, metadata={booking_id}.
    fake_session_id = f"cs_test_{booking.booking_reference}"
    return CheckoutSessionOut(
        checkout_url=f"https://checkout.stripe.com/pay/{fake_session_id}",
        session_id=fake_session_id,
    )


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
                method="card", gateway_reference=session.get("id"), status="success",
            ))
            booking.status = "confirmed"
            db.commit()
            # Enqueued to Celery — neither frontend nor this request waits on email delivery.
            send_booking_confirmation_email.delay(booking.booking_reference, booking.customer.email)

    return {"received": True}
