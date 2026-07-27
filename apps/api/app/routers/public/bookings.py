from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.core.deps import get_db, require_role
from app.models.models import Booking, User
from app.schemas.common import BookingCreateIn, BookingDetailOut, BookingOut
from app.services.booking_service import cancel_booking, create_booking

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


@router.post("/{booking_id}/cancel", response_model=BookingOut)
def cancel_my_booking(booking_id: int, db: Session = Depends(get_db), user: User = Depends(customer_only)):
    booking = _get_own_booking(db, booking_id, user)
    return cancel_booking(db, booking, actor_id=user.id)
