import secrets
from datetime import datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.models import Booking, BookingStatusHistory, Item
from app.services.audit_service import record_audit_log
from app.services.availability import is_item_available
from app.services.pricing import quote_price
from app.services.realtime import publish_booking_event

# Booking state machine — enforced here so both the customer flow (cancel)
# and the admin flow (confirm/activate/complete/cancel) go through one gate.
ALLOWED_TRANSITIONS = {
    "pending": {"confirmed", "cancelled"},
    "confirmed": {"active", "cancelled"},
    "active": {"completed", "cancelled"},
    "completed": set(),
    "cancelled": set(),
}

# A "pending" booking holds the item's calendar exactly like a paid one
# (see availability.BLOCKING_STATUSES) — an abandoned checkout that never
# paid would otherwise lock that slot forever. expire_stale_pending_bookings
# (app/worker.py, run on a schedule) cancels anything still "pending" past
# this age. No refund logic applies: nothing was ever paid.
PENDING_EXPIRY_HOURS = 24

# A "cooling-off" window right after payment: the customer can cancel a
# confirmed booking for a full refund within this many hours of payment,
# independent of how close pickup is — separate from, and in addition to,
# CANCELLATION_WINDOW_HOURS below.
CONFIRMED_COOLING_OFF_HOURS = 24

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
    db.flush()  # assigns booking.id so the audit row below can reference it
    record_audit_log(
        db, actor_id=actor_id if actor_id is not None else customer_id,
        action="booking.created", entity_type="booking", entity_id=booking.id,
    )
    db.commit()
    db.refresh(booking)
    publish_booking_event(
        booking_id=booking.id, booking_reference=booking.booking_reference,
        status=booking.status, event="created",
    )
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
    record_audit_log(
        db, actor_id=changed_by, action=f"booking.status_changed:{new_status}",
        entity_type="booking", entity_id=booking.id,
    )
    db.commit()
    db.refresh(booking)
    publish_booking_event(
        booking_id=booking.id, booking_reference=booking.booking_reference,
        status=booking.status, event="status_changed",
    )
    return booking


def can_cancel_free(start: datetime) -> bool:
    return start - datetime.now() >= timedelta(hours=CANCELLATION_WINDOW_HOURS)


def _confirmed_at(db: Session, booking: Booking) -> datetime | None:
    """When this booking most recently became "confirmed", from the audit
    trail the DB triggers already write (booking_status_history) — more
    reliable than reading booking.updated_at, which bumps on any field
    change, not just this one status transition."""
    row = (
        db.query(BookingStatusHistory.changed_at)
        .filter(BookingStatusHistory.booking_id == booking.id, BookingStatusHistory.new_status == "confirmed")
        .order_by(BookingStatusHistory.changed_at.desc())
        .first()
    )
    return row[0] if row else None


def _customer_refund_window_ok(db: Session, booking: Booking) -> bool:
    """A confirmed booking is free to cancel if EITHER window applies:
    ≥48h before pickup (CANCELLATION_WINDOW_HOURS), or within 24h of
    payment (CONFIRMED_COOLING_OFF_HOURS) — a no-questions-asked
    cooling-off period regardless of how close pickup is. Shared by both
    customer_can_cancel (the pre-flight gate) and cancel_booking (the
    actual refund decision) so the two can never disagree."""
    if can_cancel_free(booking.start_datetime):
        return True
    confirmed_at = _confirmed_at(db, booking)
    return confirmed_at is not None and datetime.now() - confirmed_at <= timedelta(hours=CONFIRMED_COOLING_OFF_HOURS)


def customer_can_cancel(db: Session, booking: Booking) -> bool:
    """Self-service cancellation policy: an unpaid ("pending") booking can
    always be cancelled — nothing's at stake yet. A paid ("confirmed")
    booking can be self-cancelled if either free-cancellation window is
    still open (see _customer_refund_window_ok); once both have closed,
    only staff can cancel it (see admin_initiated below)."""
    if booking.status == "pending":
        return True
    if booking.status == "confirmed":
        return _customer_refund_window_ok(db, booking)
    return False


def cancel_booking(db: Session, booking: Booking, *, actor_id: int | None, admin_initiated: bool = False) -> Booking:
    """Shared cancel path for the customer flow, the staff flow, and the
    automatic pending-expiry job (app/worker.py).

    Cancellation and refund are two different decisions, made by two
    different people:
    - Customer self-service: gated by customer_can_cancel() at the router
      level before this is even called — unpaid bookings any time, paid
      bookings within the 48h-before-pickup or 24h-post-payment window.
      Because that gate already ensures _customer_refund_window_ok() is
      true whenever a customer's call reaches here, a successful customer
      cancellation always refunds — the customer already knows, by virtue
      of being allowed to cancel at all, that this is the "free" case.
    - Staff (admin_initiated=True): can cancel ANY booking, at any point
      from creation up to pickup ("pending" or "confirmed" —
      ALLOWED_TRANSITIONS blocks "active"/"completed" the same way for
      everyone) — but cancelling never refunds on its own, regardless of
      timing. Refunding a paid booking is a separate, deliberate action
      staff take via POST /admin/payments/{id}/refund after seeing the
      cancellation land — not an automatic side effect they might not
      even have intended (e.g. clicking "Mark cancelled" shouldn't
      silently move real money).
    - Automatic pending-expiry: was_paid is False for a "pending" booking,
      so refund_eligible is never even consulted — nothing to refund.
    """
    was_paid = booking.status == "confirmed"
    refund_eligible = not admin_initiated and _customer_refund_window_ok(db, booking)

    booking = change_status(db, booking, "cancelled", changed_by=actor_id)

    if was_paid and refund_eligible:
        from app.services.refund_service import refund_booking_payment  # local import avoids a cycle
        refund_booking_payment(db, booking, actor_id=actor_id)

    return booking
