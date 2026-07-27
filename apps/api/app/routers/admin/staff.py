from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_db, require_role
from app.core.security import hash_password
from app.models.models import User
from app.schemas.admin import StaffCreateIn
from app.schemas.common import UserOut
from app.services.audit_service import record_audit_log

router = APIRouter(prefix="/staff", tags=["admin-staff"])
super_admin_only = require_role(["super_admin"])


@router.get("", response_model=list[UserOut])
def list_staff(db: Session = Depends(get_db), _=Depends(super_admin_only)):
    return db.query(User).filter(User.role.in_(["staff", "super_admin"])).all()


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_staff(payload: StaffCreateIn, db: Session = Depends(get_db), user: User = Depends(super_admin_only)):
    if payload.role not in ("staff", "super_admin"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "role must be staff or super_admin")
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")

    new_staff = User(
        full_name=payload.full_name, email=payload.email, phone=payload.phone,
        password_hash=hash_password(payload.password), role=payload.role, is_verified=True,
    )
    db.add(new_staff)
    db.flush()
    record_audit_log(
        db, actor_id=user.id, action=f"staff.created:{payload.role}",
        entity_type="staff", entity_id=new_staff.id,
    )
    db.commit()
    db.refresh(new_staff)
    return new_staff


@router.post("/{staff_id}/deactivate", response_model=UserOut)
def deactivate_staff(staff_id: int, db: Session = Depends(get_db), user: User = Depends(super_admin_only)):
    staff = db.get(User, staff_id)
    if not staff or staff.role not in ("staff", "super_admin"):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Staff member not found")

    if staff.id == user.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "You cannot deactivate your own account")

    if staff.role == "super_admin":
        # If this is the last active super_admin, deactivating them locks
        # every super_admin_only route (including this one and /reactivate)
        # with no account left able to call it — an unrecoverable lockout
        # short of direct DB access. Require at least one other active
        # super_admin to remain.
        other_active_super_admins = (
            db.query(User)
            .filter(User.role == "super_admin", User.is_active.is_(True), User.id != staff.id)
            .count()
        )
        if other_active_super_admins == 0:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Cannot deactivate the last active super_admin account",
            )

    staff.is_active = False
    record_audit_log(
        db, actor_id=user.id, action="staff.deactivated",
        entity_type="staff", entity_id=staff.id,
    )
    db.commit()
    db.refresh(staff)
    return staff


@router.post("/{staff_id}/reactivate", response_model=UserOut)
def reactivate_staff(staff_id: int, db: Session = Depends(get_db), user: User = Depends(super_admin_only)):
    staff = db.get(User, staff_id)
    if not staff or staff.role not in ("staff", "super_admin"):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Staff member not found")
    staff.is_active = True
    record_audit_log(
        db, actor_id=user.id, action="staff.reactivated",
        entity_type="staff", entity_id=staff.id,
    )
    db.commit()
    db.refresh(staff)
    return staff
