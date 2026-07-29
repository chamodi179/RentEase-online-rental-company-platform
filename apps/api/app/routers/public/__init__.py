from fastapi import APIRouter

from app.routers.public import auth, bookings, items, payments

router = APIRouter()
router.include_router(auth.router)
router.include_router(items.router)
router.include_router(bookings.router)
router.include_router(payments.router)
