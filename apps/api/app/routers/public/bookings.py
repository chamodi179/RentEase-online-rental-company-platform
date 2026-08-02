from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.core.deps import get_db, require_role
from app.models.models import Booking, Payment, User
from app.schemas.common import BookingCreateIn, BookingDetailOut, BookingOut
from app.services.booking_service import cancel_booking, create_booking, customer_can_cancel

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
    bookings = (
        db.query(Booking)
        .filter(Booking.customer_id == user.id)
        .order_by(Booking.created_at.desc())
        .all()
    )
    refunded_ids = set()
    if bookings:
        refunded_ids = {
            row[0]
            for row in db.query(Payment.booking_id)
            .filter(
                Payment.type == "refund", Payment.status == "success",
                Payment.booking_id.in_([b.id for b in bookings]),
            )
            .distinct()
        }
    out = []
    for b in bookings:
        row = BookingOut.model_validate(b)
        row.is_refunded = b.id in refunded_ids
        out.append(row)
    return out


def _get_own_booking(db: Session, booking_id: int, user: User) -> Booking:
    booking = (
        db.query(Booking)
        .options(
            joinedload(Booking.item), joinedload(Booking.branch_pickup),
            joinedload(Booking.branch_dropoff), joinedload(Booking.payments),
        )
        .filter(Booking.id == booking_id)
        .first()
    )
    if not booking or booking.customer_id != user.id:
        # Row-level check (Section 4, layer 3): role alone doesn't prove ownership.
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Booking not found")
    return booking


@router.get("/{booking_id}", response_model=BookingDetailOut)
def my_booking_detail(booking_id: int, db: Session = Depends(get_db), user: User = Depends(customer_only)):
    booking = _get_own_booking(db, booking_id, user)
    result = BookingDetailOut.model_validate(booking)
    result.is_refunded = any(p.type == "refund" and p.status == "success" for p in booking.payments)
    return result


@router.post("/{booking_id}/cancel", response_model=BookingOut)
def cancel_my_booking(booking_id: int, db: Session = Depends(get_db), user: User = Depends(customer_only)):
    """Self-service cancel: unpaid bookings any time, paid bookings within
    the 48h-before-pickup OR 24h-post-payment window (customer_can_cancel).
    Past both windows, only staff can cancel it — see
    POST /admin/bookings/{id}/status. Unlike this self-service path, a
    staff-initiated cancellation does NOT auto-refund; staff issue the
    refund separately via POST /admin/payments/{id}/refund once the
    cancellation has landed."""
    booking = _get_own_booking(db, booking_id, user)
    if not customer_can_cancel(db, booking):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "This booking is outside the free-cancellation window (more than 24h since payment, "
            "and less than 48h before pickup), so it can't be cancelled here. "
            "Contact us and our team can cancel it (and refund you) if needed.",
        )
    return cancel_booking(db, booking, actor_id=user.id)
