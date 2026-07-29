from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator

from app.core.security import validate_password_strength


class OrmBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---- auth ----
class RegisterIn(BaseModel):
    full_name: str
    email: EmailStr
    phone: str | None = None
    password: str

    @field_validator("password")
    @classmethod
    def _password_strength(cls, v: str) -> str:
        return validate_password_strength(v)


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
    is_active: bool
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


# ---- availability ----
class BookedRangeOut(BaseModel):
    start_datetime: datetime
    end_datetime: datetime


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


# ---- file uploads (used for item-catalog photos — see admin/items.py) ----
class PresignRequest(BaseModel):
    filename: str
    content_type: str = "application/octet-stream"


class PresignOut(BaseModel):
    upload_url: str
    file_url: str


# ---- payments ----
class CheckoutSessionOut(BaseModel):
    checkout_url: str
    session_id: str
