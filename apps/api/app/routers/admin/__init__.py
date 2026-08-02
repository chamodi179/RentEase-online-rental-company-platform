from fastapi import APIRouter

from app.routers.admin import auth, bookings, customers, dashboard, items, payments, realtime, staff

router = APIRouter()
router.include_router(auth.router)
router.include_router(dashboard.router)
router.include_router(items.router)
router.include_router(bookings.router)
router.include_router(customers.router)
router.include_router(payments.router)
router.include_router(staff.router)
router.include_router(realtime.router)
