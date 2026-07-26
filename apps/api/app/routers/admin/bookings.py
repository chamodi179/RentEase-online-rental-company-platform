from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.core.deps import get_db, require_role
from app.models.models import Booking, User
from app.schemas.admin import AdminBookingDetailOut, AdminBookingOut, BookingStatusUpdateIn, ManualBookingCreateIn
from app.services.booking_service import change_status, create_booking

router = APIRouter(prefix="/bookings", tags=["admin-bookings"])
staff_only = require_role(["staff", "super_admin"])


@router.get("", response_model=list[AdminBookingOut])
def list_bookings(
    status_filter: str | None = None,
    start_from: datetime | None = None,
    start_to: datetime | None = None,
    db: Session = Depends(get_db),
    _=Depends(staff_only),
):
    query = db.query(Booking)
    if status_filter:
        query = query.filter(Booking.status == status_filter)
    if start_from:
        query = query.filter(Booking.start_datetime >= start_from)
    if start_to:
        query = query.filter(Booking.start_datetime <= start_to)
    return query.order_by(Booking.created_at.desc()).all()


@router.post("", response_model=AdminBookingOut, status_code=status.HTTP_201_CREATED)
def create_manual_booking(payload: ManualBookingCreateIn, db: Session = Depends(get_db), _=Depends(staff_only)):
    """For phone/walk-in customers (spec §5.3)."""
    return create_booking(
        db,
        customer_id=payload.customer_id,
        item_id=payload.item_id,
        branch_pickup_id=payload.branch_pickup_id,
        branch_dropoff_id=payload.branch_dropoff_id,
        start=payload.start_datetime,
        end=payload.end_datetime,
    )


@router.get("/{booking_id}", response_model=AdminBookingDetailOut)
def booking_detail(booking_id: int, db: Session = Depends(get_db), _=Depends(staff_only)):
    booking = (
        db.query(Booking)
        .options(joinedload(Booking.item), joinedload(Booking.branch_pickup), joinedload(Booking.branch_dropoff))
        .filter(Booking.id == booking_id)
        .first()
    )
    if not booking:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Booking not found")
    return booking


@router.post("/{booking_id}/status", response_model=AdminBookingOut)
def update_status(
    booking_id: int, payload: BookingStatusUpdateIn, db: Session = Depends(get_db),
    user: User = Depends(staff_only),
):
    booking = db.get(Booking, booking_id)
    if not booking:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Booking not found")
    return change_status(db, booking, payload.new_status, changed_by=user.id)
