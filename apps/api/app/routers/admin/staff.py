from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_db, require_role
from app.core.security import hash_password
from app.models.models import User
from app.schemas.admin import StaffCreateIn
from app.schemas.common import UserOut

router = APIRouter(prefix="/staff", tags=["admin-staff"])
super_admin_only = require_role(["super_admin"])


@router.get("", response_model=list[UserOut])
def list_staff(db: Session = Depends(get_db), _=Depends(super_admin_only)):
    return db.query(User).filter(User.role.in_(["staff", "super_admin"])).all()


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_staff(payload: StaffCreateIn, db: Session = Depends(get_db), _=Depends(super_admin_only)):
    if payload.role not in ("staff", "super_admin"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "role must be staff or super_admin")
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")

    user = User(
        full_name=payload.full_name, email=payload.email, phone=payload.phone,
        password_hash=hash_password(payload.password), role=payload.role, is_verified=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/{staff_id}/deactivate", response_model=UserOut)
def deactivate_staff(staff_id: int, db: Session = Depends(get_db), _=Depends(super_admin_only)):
    staff = db.get(User, staff_id)
    if not staff or staff.role not in ("staff", "super_admin"):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Staff member not found")
    staff.is_active = False
    db.commit()
    db.refresh(staff)
    return staff
