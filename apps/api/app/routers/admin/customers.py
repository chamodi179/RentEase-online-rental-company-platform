from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.deps import get_db, require_role
from app.models.models import Booking, User
from app.schemas.admin import CustomerOut
from app.schemas.common import BookingOut

router = APIRouter(prefix="/customers", tags=["admin-customers"])
staff_only = require_role(["staff", "super_admin"])


@router.get("", response_model=list[CustomerOut])
def list_customers(q: str | None = None, db: Session = Depends(get_db), _=Depends(staff_only)):
    query = (
        db.query(User, func.count(Booking.id).label("booking_count"))
        .outerjoin(Booking, Booking.customer_id == User.id)
        .filter(User.role == "customer")
        .group_by(User.id)
    )
    if q:
        query = query.filter(User.full_name.ilike(f"%{q}%") | User.email.ilike(f"%{q}%"))

    results = []
    for user, count in query.all():
        out = CustomerOut.model_validate(user)
        out.booking_count = count
        results.append(out)
    return results


@router.get("/{customer_id}/bookings", response_model=list[BookingOut])
def customer_bookings(customer_id: int, db: Session = Depends(get_db), _=Depends(staff_only)):
    return db.query(Booking).filter(Booking.customer_id == customer_id).all()
