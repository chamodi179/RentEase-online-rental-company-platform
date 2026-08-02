from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.core.deps import get_db, require_role
from app.models.models import AuditLog, Booking, Payment, User
from app.schemas.admin import (
    AdminBookingDetailOut, AdminBookingOut, AuditLogOut, BookingStatusUpdateIn, ManualBookingCreateIn,
)
from app.services.booking_service import cancel_booking, change_status, create_booking

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
    bookings = query.order_by(Booking.created_at.desc()).all()

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
        row = AdminBookingOut.model_validate(b)
        row.is_refunded = b.id in refunded_ids
        out.append(row)
    return out


@router.post("", response_model=AdminBookingOut, status_code=status.HTTP_201_CREATED)
def create_manual_booking(
    payload: ManualBookingCreateIn, db: Session = Depends(get_db), user: User = Depends(staff_only)
):
    """For phone/walk-in customers (spec §5.3)."""
    return create_booking(
        db,
        customer_id=payload.customer_id,
        item_id=payload.item_id,
        branch_pickup_id=payload.branch_pickup_id,
        branch_dropoff_id=payload.branch_dropoff_id,
        start=payload.start_datetime,
        end=payload.end_datetime,
        actor_id=user.id,  # audit trail should show which staff member created it, not the customer
    )


@router.get("/{booking_id}", response_model=AdminBookingDetailOut)
def booking_detail(booking_id: int, db: Session = Depends(get_db), _=Depends(staff_only)):
    booking = (
        db.query(Booking)
        .options(
            joinedload(Booking.item), joinedload(Booking.branch_pickup),
            joinedload(Booking.branch_dropoff), joinedload(Booking.payments),
        )
        .filter(Booking.id == booking_id)
        .first()
    )
    if not booking:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Booking not found")

    # record_audit_log() writes rows for both booking status changes and
    # payment/refund actions (change_status, refund_service,
    # record_manual_payment) — but nothing ever surfaced them anywhere.
    # Merge both into one time-ordered trail for this booking's page.
    payment_ids = [p.id for p in booking.payments]
    filters = [(AuditLog.entity_type == "booking") & (AuditLog.entity_id == booking.id)]
    if payment_ids:
        filters.append((AuditLog.entity_type == "payment") & (AuditLog.entity_id.in_(payment_ids)))
    audit_rows = (
        db.query(AuditLog, User.full_name)
        .outerjoin(User, User.id == AuditLog.actor_id)
        .filter(or_(*filters))
        .order_by(AuditLog.created_at.asc())
        .all()
    )
    result = AdminBookingDetailOut.model_validate(booking)
    result.is_refunded = any(p.type == "refund" and p.status == "success" for p in booking.payments)
    result.audit_log = [
        AuditLogOut(
            id=log.id, action=log.action, entity_type=log.entity_type, entity_id=log.entity_id,
            actor_id=log.actor_id, actor_name=actor_name or ("System" if log.actor_id is None else None),
            created_at=log.created_at,
        )
        for log, actor_name in audit_rows
    ]
    return result


@router.post("/{booking_id}/status", response_model=AdminBookingOut)
def update_status(
    booking_id: int, payload: BookingStatusUpdateIn, db: Session = Depends(get_db),
    user: User = Depends(staff_only),
):
    booking = db.get(Booking, booking_id)
    if not booking:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Booking not found")
    if payload.new_status == "cancelled":
        # Staff can cancel any booking, any time — but cancelling never
        # auto-refunds for a staff-initiated cancellation (admin_initiated
        # skips the customer time-window refund logic entirely). Refunding
        # is a deliberate, separate action via
        # POST /admin/payments/{id}/refund once the cancellation has
        # landed — not a side effect of clicking "Mark cancelled".
        return cancel_booking(db, booking, actor_id=user.id, admin_initiated=True)
    return change_status(db, booking, payload.new_status, changed_by=user.id)
