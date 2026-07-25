from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr


class OrmBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---- auth ----
class RegisterIn(BaseModel):
    full_name: str
    email: EmailStr
    phone: str | None = None
    password: str


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class UserOut(OrmBase):
    id: int
    full_name: str
    email: str
    phone: str | None
    role: str
    is_verified: bool
    created_at: datetime


# ---- catalog / items ----
class ItemPhotoOut(OrmBase):
    id: int
    url: str
    sort_order: int


class BranchOut(OrmBase):
    id: int
    name: str
    address: str
    city: str
    phone: str | None


class CategoryOut(OrmBase):
    id: int
    name: str
    description: str | None


class ItemListOut(OrmBase):
    id: int
    name: str
    description: str | None
    base_price_daily: Decimal
    deposit_amount: Decimal
    status: str
    branch: BranchOut
    photos: list[ItemPhotoOut] = []


class ItemDetailOut(ItemListOut):
    category: CategoryOut | None = None


# ---- bookings ----
class PriceQuoteOut(BaseModel):
    days: int
    base_amount: Decimal
    tax_amount: Decimal
    deposit_amount: Decimal
    total_amount: Decimal


class BookingCreateIn(BaseModel):
    item_id: int
    branch_pickup_id: int
    branch_dropoff_id: int
    start_datetime: datetime
    end_datetime: datetime


class BookingOut(OrmBase):
    id: int
    booking_reference: str
    item_id: int
    status: str
    start_datetime: datetime
    end_datetime: datetime
    base_amount: Decimal
    tax_amount: Decimal
    deposit_amount: Decimal
    total_amount: Decimal
    created_at: datetime


class BookingDetailOut(BookingOut):
    item: ItemListOut
    branch_pickup: BranchOut
    branch_dropoff: BranchOut


# ---- documents ----
class DocumentOut(OrmBase):
    id: int
    document_type: str
    file_url: str
    verification_status: str
    created_at: datetime


class CancelBookingOut(BookingOut):
    # None when there was nothing to refund (e.g. booking never paid);
    # otherwise "success" (refunded), "pending" (manual reconciliation),
    # or "failed" (gateway declined the refund).
    refund_status: str | None = None


# ---- payments ----
class CheckoutSessionOut(BaseModel):
    checkout_url: str
    session_id: str
    is_mock: bool = False
