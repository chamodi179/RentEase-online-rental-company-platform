from sqlalchemy import (
    BigInteger, Boolean, CheckConstraint, Column, DateTime, Enum, ForeignKey,
    Numeric, SmallInteger, String, Text, func,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class Category(Base):
    __tablename__ = "categories"
    id = Column(BigInteger, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    items = relationship("ItemCatalog", back_populates="category")


class Branch(Base):
    __tablename__ = "branches"
    id = Column(BigInteger, primary_key=True)
    name = Column(String(150), nullable=False)
    address = Column(String(255), nullable=False)
    city = Column(String(100), nullable=False)
    phone = Column(String(30))
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class User(Base):
    __tablename__ = "users"
    id = Column(BigInteger, primary_key=True)
    full_name = Column(String(150), nullable=False)
    email = Column(String(255), nullable=False, unique=True)
    phone = Column(String(30))
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum("customer", "staff", "super_admin", name="user_role"),
                  nullable=False, default="customer")
    is_verified = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class ItemCatalog(Base):
    __tablename__ = "item_catalog"
    id = Column(BigInteger, primary_key=True)
    category_id = Column(BigInteger, ForeignKey("categories.id"), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    category = relationship("Category", back_populates="items")
    photos = relationship("ItemPhoto", back_populates="catalog", cascade="all, delete-orphan")
    units = relationship("Item", back_populates="catalog")


class ItemPhoto(Base):
    __tablename__ = "item_photos"
    id = Column(BigInteger, primary_key=True)
    catalog_id = Column(BigInteger, ForeignKey("item_catalog.id"), nullable=False)
    url = Column(String(500), nullable=False)
    sort_order = Column(SmallInteger, nullable=False, default=0)
    created_at = Column(DateTime, server_default=func.now())

    catalog = relationship("ItemCatalog", back_populates="photos")


class Item(Base):
    __tablename__ = "items"
    id = Column(BigInteger, primary_key=True)
    catalog_id = Column(BigInteger, ForeignKey("item_catalog.id"), nullable=False)
    branch_id = Column(BigInteger, ForeignKey("branches.id"), nullable=False)
    name = Column(String(150), nullable=False)
    description = Column(Text)
    base_price_daily = Column(Numeric(10, 2), nullable=False)
    deposit_amount = Column(Numeric(10, 2), nullable=False, default=0)
    status = Column(Enum("available", "rented", "maintenance", "retired", name="item_status"),
                     nullable=False, default="available")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    catalog = relationship("ItemCatalog", back_populates="units")
    branch = relationship("Branch")

    __table_args__ = (
        CheckConstraint("base_price_daily >= 0", name="chk_items_base_price"),
        CheckConstraint("deposit_amount >= 0", name="chk_items_deposit"),
    )


class Booking(Base):
    __tablename__ = "bookings"
    id = Column(BigInteger, primary_key=True)
    booking_reference = Column(String(30), nullable=False, unique=True)
    customer_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    item_id = Column(BigInteger, ForeignKey("items.id"), nullable=False)
    branch_pickup_id = Column(BigInteger, ForeignKey("branches.id"), nullable=False)
    branch_dropoff_id = Column(BigInteger, ForeignKey("branches.id"), nullable=False)
    start_datetime = Column(DateTime, nullable=False)
    end_datetime = Column(DateTime, nullable=False)
    status = Column(
        Enum("pending", "confirmed", "active", "completed", "cancelled", name="booking_status"),
        nullable=False, default="pending",
    )
    base_amount = Column(Numeric(10, 2), nullable=False)
    tax_amount = Column(Numeric(10, 2), nullable=False, default=0)
    deposit_amount = Column(Numeric(10, 2), nullable=False, default=0)
    total_amount = Column(Numeric(10, 2), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    item = relationship("Item")
    customer = relationship("User", foreign_keys=[customer_id])
    branch_pickup = relationship("Branch", foreign_keys=[branch_pickup_id])
    branch_dropoff = relationship("Branch", foreign_keys=[branch_dropoff_id])


class BookingStatusHistory(Base):
    __tablename__ = "booking_status_history"
    id = Column(BigInteger, primary_key=True)
    booking_id = Column(BigInteger, ForeignKey("bookings.id"), nullable=False)
    old_status = Column(Enum("pending", "confirmed", "active", "completed", "cancelled", name="bsh_old_status"))
    new_status = Column(Enum("pending", "confirmed", "active", "completed", "cancelled", name="bsh_new_status"), nullable=False)
    changed_by = Column(BigInteger, ForeignKey("users.id"))
    changed_at = Column(DateTime, server_default=func.now())


class Payment(Base):
    __tablename__ = "payments"
    id = Column(BigInteger, primary_key=True)
    booking_id = Column(BigInteger, ForeignKey("bookings.id"), nullable=False)
    type = Column(Enum("payment", "refund", name="payment_type"), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    method = Column(Enum("card", "cash", "bank_transfer", name="payment_method"), nullable=False)
    gateway_reference = Column(String(255))
    status = Column(Enum("pending", "success", "failed", name="payment_status"),
                     nullable=False, default="pending")
    created_at = Column(DateTime, server_default=func.now())

    booking = relationship("Booking")


class DocumentRecord(Base):
    __tablename__ = "documents"
    id = Column(BigInteger, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    document_type = Column(Enum("id_card", "license", "other", name="document_type"), nullable=False)
    file_url = Column(String(500), nullable=False)
    verification_status = Column(Enum("pending", "approved", "rejected", name="verification_status"),
                                  nullable=False, default="pending")
    reviewed_by = Column(BigInteger, ForeignKey("users.id"))
    created_at = Column(DateTime, server_default=func.now())


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(BigInteger, primary_key=True)
    actor_id = Column(BigInteger, ForeignKey("users.id"))
    action = Column(String(150), nullable=False)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(BigInteger, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
