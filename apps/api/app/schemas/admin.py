from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, EmailStr, field_validator

from app.core.security import validate_password_strength
from app.schemas.common import (
    BookingDetailOut, CategoryOut, ItemPhotoOut, OrmBase, PresignRequest, UserOut,
)


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


class AdminCatalogOut(OrmBase):
    id: int
    category_id: int
    category: CategoryOut | None = None
    photos: list[ItemPhotoOut] = []


class ItemPhotoPresignIn(PresignRequest):
    """Same shape as the shared PresignRequest (filename + content_type) —
    kept as a distinct name so it's clear this presign is scoped to a
    catalog entry's photos, not documents."""


class ItemPhotoRegisterIn(BaseModel):
    file_url: str
    sort_order: int = 0


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
    # Computed in the list endpoint (a correlated lookup, not an ORM
    # attribute — Booking has no such column) so the list view can show
    # "refunded" instead of a bare "cancelled" without a second request
    # per row. See AdminBookingDetailOut.payments for the full picture.
    is_refunded: bool = False


class AuditLogOut(BaseModel):
    id: int
    action: str
    entity_type: str
    entity_id: int
    actor_id: int | None
    actor_name: str | None  # None + actor_id=None means a system action (e.g. the pending-expiry job)
    created_at: datetime


class AdminBookingDetailOut(BookingDetailOut):
    customer_id: int
    # BookingDetailOut already carries `payments` (see common.py) — every
    # customer-visible field the admin view needs is inherited, this adds
    # what's admin-only: who's booking it, and the audit trail (status
    # changes + payment/refund actions) for this booking and its payments,
    # merged and time-ordered — previously nothing surfaced this at all,
    # so there was no way to confirm from the UI that a cancel/refund
    # action had actually been recorded.
    audit_log: list[AuditLogOut] = []


class BookingStatusUpdateIn(BaseModel):
    new_status: str


class ManualBookingCreateIn(BaseModel):
    customer_id: int
    item_id: int
    branch_pickup_id: int
    branch_dropoff_id: int
    start_datetime: datetime
    end_datetime: datetime


class ManualPaymentIn(BaseModel):
    booking_id: int
    type: str  # payment | refund
    amount: Decimal
    method: str  # card | cash | bank_transfer
    gateway_reference: str | None = None


class StaffCreateIn(BaseModel):
    full_name: str
    email: EmailStr
    phone: str | None = None
    password: str
    role: str = "staff"  # staff | super_admin

    @field_validator("password")
    @classmethod
    def _password_strength(cls, v: str) -> str:
        return validate_password_strength(v)


class CustomerOut(UserOut):
    booking_count: int = 0
