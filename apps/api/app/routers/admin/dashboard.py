from datetime import datetime, time

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_db, require_role
from app.models.models import Booking
from app.schemas.admin import DashboardSummaryOut

router = APIRouter(prefix="/dashboard", tags=["admin-dashboard"])
staff_only = require_role(["staff", "super_admin"])


@router.get("/summary", response_model=DashboardSummaryOut)
def dashboard_summary(db: Session = Depends(get_db), _=Depends(staff_only)):
    today = datetime.now().date()
    day_start = datetime.combine(today, time.min)
    day_end = datetime.combine(today, time.max)

    pickups = db.query(Booking).filter(
        Booking.start_datetime.between(day_start, day_end),
        Booking.status.in_(["confirmed", "active"]),
    ).count()

    returns = db.query(Booking).filter(
        Booking.end_datetime.between(day_start, day_end),
        Booking.status == "active",
    ).count()

    active = db.query(Booking).filter(Booking.status == "active").count()

    return DashboardSummaryOut(todays_pickups=pickups, todays_returns=returns, active_rentals=active)
