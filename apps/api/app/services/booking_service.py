import secrets
from datetime import datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.models import Booking, Item
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

# Free cancellation window before pickup (spec §4.3). Enforced here, not just
# in the frontend button state, so a direct API call can't bypass it.
CANCELLATION_WINDOW_HOURS = 48


def generate_booking_reference() -> str:
    return "RE-" + secrets.token_hex(4).upper()


def _set_history_actor(db: Session, actor_id: int | None) -> None:
    """booking_status_history rows are written by the DB triggers
    (trg_bookings_status_history / trg_bookings_status_history_insert, see
    docs/02_triggers.sql), not by this service — writing them from both
    places produced two rows per status change. This just tells the trigger
    who's making the change. Always set explicitly (even to NULL) because
    the underlying connection is pooled and could carry a stale value left
    over from a previous request otherwise."""
    db.execute(text("SET @rentease_actor_id = :actor_id"), {"actor_id": actor_id})


def create_booking(
    db: Session, *, customer_id: int, item_id: int,
    branch_pickup_id: int, branch_dropoff_id: int,
    start: datetime, end: datetime, actor_id: int | None = None,
) -> Booking:
    if end <= start:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "end_datetime must be after start_datetime")

    # Row-lock the item for the rest of this transaction. This is what
    # actually prevents two concurrent requests for the same item/window
    # from both passing the availability check below and creating
    # overlapping bookings (mirrors the locking strategy in
    # docs/03_procedures.sql's sp_create_booking, which the API wasn't
    # actually calling before).
    item = db.query(Item).filter(Item.id == item_id).with_for_update().first()
    if not item or item.status != "available":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Item not available")

    if not is_item_available(db, item_id, start, end):
        raise HTTPException(status.HTTP_409_CONFLICT, "Item is already booked for this window")

    price = quote_price(item, start, end)

    _set_history_actor(db, actor_id if actor_id is not None else customer_id)

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
    _set_history_actor(db, changed_by)
    booking.status = new_status
    db.commit()
    db.refresh(booking)
    return booking


def can_cancel_free(start: datetime) -> bool:
    return start - datetime.now() >= timedelta(hours=CANCELLATION_WINDOW_HOURS)


def cancel_booking(db: Session, booking: Booking, *, actor_id: int | None) -> Booking:
    """Shared cancel path for both the customer and admin flows (spec §4.3).

    Cancellation and refund eligibility are deliberately separate: a
    pending/confirmed booking can ALWAYS be cancelled — change_status()'s
    ALLOWED_TRANSITIONS already enforces that those are the only states it's
    legal from. Only the *refund* outcome is time-gated: ≥48h before pickup
    gets a full refund, <48h still cancels but forfeits the payment. (An
    earlier version of this function incorrectly blocked cancellation itself
    inside the 48h window for customers — that's the exact conflation the
    spec calls out as wrong.)
    """
    was_paid = booking.status == "confirmed"
    refund_eligible = can_cancel_free(booking.start_datetime)

    booking = change_status(db, booking, "cancelled", changed_by=actor_id)

    if was_paid and refund_eligible:
        from app.services.refund_service import refund_booking_payment  # local import avoids a cycle
        refund_booking_payment(db, booking)

    return booking
