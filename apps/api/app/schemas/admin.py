from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, EmailStr

from app.schemas.common import BookingDetailOut, OrmBase, UserOut


class DashboardSummaryOut(BaseModel):
    todays_pickups: int
    todays_returns: int
    active_rentals: int


class ItemCatalogCreateIn(BaseModel):
    category_id: int


class ItemUnitCreateIn(BaseModel):
    catalog_id: int
    branch_id: int
    name: str
    description: str | None = None
    base_price_daily: Decimal
    deposit_amount: Decimal = Decimal("0.00")
    status: str = "available"


class ItemUnitUpdateIn(BaseModel):
    name: str | None = None
    description: str | None = None
    base_price_daily: Decimal | None = None
    deposit_amount: Decimal | None = None
    status: str | None = None
    branch_id: int | None = None


class AdminItemOut(OrmBase):
    id: int
    name: str
    description: str | None
    base_price_daily: Decimal
    deposit_amount: Decimal
    status: str
    branch_id: int
    catalog_id: int


class AdminBookingOut(OrmBase):
    id: int
    booking_reference: str
    customer_id: int
    item_id: int
    status: str
    start_datetime: datetime
    end_datetime: datetime
    total_amount: Decimal
    created_at: datetime


class AdminBookingDetailOut(BookingDetailOut):
    customer_id: int


class BookingStatusUpdateIn(BaseModel):
    new_status: str


class ManualBookingCreateIn(BaseModel):
    customer_id: int
    item_id: int
    branch_pickup_id: int
    branch_dropoff_id: int
    start_datetime: datetime
    end_datetime: datetime


class DocumentReviewIn(BaseModel):
    verification_status: str  # approved | rejected


class ManualPaymentIn(BaseModel):
    booking_id: int
    type: str  # payment | refund
    amount: Decimal
    method: str  # card | cash | bank_transfer
    gateway_reference: str | None = None


class PaymentOut(OrmBase):
    id: int
    booking_id: int
    type: str
    amount: Decimal
    method: str
    status: str
    created_at: datetime


class StaffCreateIn(BaseModel):
    full_name: str
    email: EmailStr
    phone: str | None = None
    password: str
    role: str = "staff"  # staff | super_admin


class CustomerOut(UserOut):
    booking_count: int = 0
