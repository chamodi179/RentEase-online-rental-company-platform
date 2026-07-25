from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.core.deps import get_db, require_role
from app.models.models import Booking, Payment, User
from app.schemas.common import BookingCreateIn, BookingDetailOut, BookingOut, CancelBookingOut
from app.services.booking_service import change_status, create_booking
from app.services.payments_service import issue_refund

router = APIRouter(prefix="/bookings", tags=["bookings"])
customer_only = require_role(["customer"])


@router.post("", response_model=BookingOut, status_code=status.HTTP_201_CREATED)
def create_my_booking(
    payload: BookingCreateIn, db: Session = Depends(get_db), user: User = Depends(customer_only)
):
    return create_booking(
        db,
        customer_id=user.id,
        item_id=payload.item_id,
        branch_pickup_id=payload.branch_pickup_id,
        branch_dropoff_id=payload.branch_dropoff_id,
        start=payload.start_datetime,
        end=payload.end_datetime,
    )


@router.get("", response_model=list[BookingOut])
def my_bookings(db: Session = Depends(get_db), user: User = Depends(customer_only)):
    return (
        db.query(Booking)
        .filter(Booking.customer_id == user.id)
        .order_by(Booking.created_at.desc())
        .all()
    )


def _get_own_booking(db: Session, booking_id: int, user: User) -> Booking:
    booking = (
        db.query(Booking)
        .options(joinedload(Booking.item), joinedload(Booking.branch_pickup), joinedload(Booking.branch_dropoff))
        .filter(Booking.id == booking_id)
        .first()
    )
    if not booking or booking.customer_id != user.id:
        # Row-level check (Section 4, layer 3): role alone doesn't prove ownership.
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Booking not found")
    return booking


@router.get("/{booking_id}", response_model=BookingDetailOut)
def my_booking_detail(booking_id: int, db: Session = Depends(get_db), user: User = Depends(customer_only)):
    return _get_own_booking(db, booking_id, user)


@router.post("/{booking_id}/cancel", response_model=CancelBookingOut)
def cancel_my_booking(booking_id: int, db: Session = Depends(get_db), user: User = Depends(customer_only)):
    booking = _get_own_booking(db, booking_id, user)

    # Cancellation itself is always available for pending/confirmed bookings
    # (enforced by the state machine below). Only the *refund* is time-gated.
    hours_until_pickup = (booking.start_datetime - datetime.now(timezone.utc).replace(tzinfo=None)).total_seconds() / 3600
    eligible_for_refund = hours_until_pickup >= settings.CANCELLATION_FREE_HOURS

    successful_payment = (
        db.query(Payment)
        .filter(Payment.booking_id == booking.id, Payment.type == "payment", Payment.status == "success")
        .order_by(Payment.created_at.desc())
        .first()
    )

    booking = change_status(db, booking, "cancelled", changed_by=user.id)

    refund_status = None
    if successful_payment and eligible_for_refund:
        refund = issue_refund(db, booking, successful_payment)
        refund_status = refund.status

    return CancelBookingOut(refund_status=refund_status, **BookingOut.model_validate(booking).model_dump())
