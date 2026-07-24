from datetime import datetime

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.models.models import Booking

# Statuses that hold an item's calendar — mirrors spec §7.1: exclude any item
# with a booking in (pending, confirmed, active) whose window overlaps.
BLOCKING_STATUSES = ("pending", "confirmed", "active")


def is_item_available(db: Session, item_id: int, start: datetime, end: datetime,
                       exclude_booking_id: int | None = None) -> bool:
    query = db.query(Booking).filter(
        Booking.item_id == item_id,
        Booking.status.in_(BLOCKING_STATUSES),
        and_(Booking.start_datetime < end, Booking.end_datetime > start),
    )
    if exclude_booking_id:
        query = query.filter(Booking.id != exclude_booking_id)
    return db.query(~query.exists()).scalar()


def available_item_ids(db: Session, item_ids: list[int], start: datetime, end: datetime) -> set[int]:
    """Bulk version for browse/search pages — returns the subset of item_ids
    that are free for the requested window."""
    if not item_ids:
        return set()
    blocked = (
        db.query(Booking.item_id)
        .filter(
            Booking.item_id.in_(item_ids),
            Booking.status.in_(BLOCKING_STATUSES),
            and_(Booking.start_datetime < end, Booking.end_datetime > start),
        )
        .distinct()
        .all()
    )
    blocked_ids = {row[0] for row in blocked}
    return set(item_ids) - blocked_ids
