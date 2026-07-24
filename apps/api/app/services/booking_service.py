import secrets
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.models import Booking, BookingStatusHistory, Item
from app.services.availability import is_item_available
from app.services.pricing import quote_price

# Booking state machine — enforced here so both the customer flow (cancel)
# and the admin flow (confirm/activate/complete/cancel) go through one gate.
ALLOWED_TRANSITIONS = {
    "pending": {"confirmed", "cancelled"},
    "confirmed": {"active", "cancelled"},
    "active": {"completed", "cancelled"},
    "completed": set(),
    "cancelled": set(),
}


def generate_booking_reference() -> str:
    return "RE-" + secrets.token_hex(4).upper()


def create_booking(
    db: Session, *, customer_id: int, item_id: int,
    branch_pickup_id: int, branch_dropoff_id: int,
    start: datetime, end: datetime,
) -> Booking:
    if end <= start:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "end_datetime must be after start_datetime")

    item = db.get(Item, item_id)
    if not item or item.status != "available":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Item not available")

    if not is_item_available(db, item_id, start, end):
        raise HTTPException(status.HTTP_409_CONFLICT, "Item is already booked for this window")

    price = quote_price(item, start, end)

    booking = Booking(
        booking_reference=generate_booking_reference(),
        customer_id=customer_id,
        item_id=item_id,
        branch_pickup_id=branch_pickup_id,
        branch_dropoff_id=branch_dropoff_id,
        start_datetime=start,
        end_datetime=end,
        status="pending",
        base_amount=price["base_amount"],
        tax_amount=price["tax_amount"],
        deposit_amount=price["deposit_amount"],
        total_amount=price["total_amount"],
    )
    db.add(booking)
    db.flush()
    db.add(BookingStatusHistory(booking_id=booking.id, old_status=None, new_status="pending"))
    db.commit()
    db.refresh(booking)
    return booking


def change_status(db: Session, booking: Booking, new_status: str, changed_by: int | None) -> Booking:
    allowed = ALLOWED_TRANSITIONS.get(booking.status, set())
    if new_status not in allowed:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Cannot transition booking from '{booking.status}' to '{new_status}'",
        )
    old_status = booking.status
    booking.status = new_status
    db.add(BookingStatusHistory(
        booking_id=booking.id, old_status=old_status, new_status=new_status, changed_by=changed_by,
    ))
    db.commit()
    db.refresh(booking)
    return booking
