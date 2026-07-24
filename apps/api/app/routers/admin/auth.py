from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db
from app.core.security import create_access_token, create_refresh_token, verify_password
from app.models.models import User
from app.schemas.common import LoginIn, UserOut

router = APIRouter(prefix="/auth", tags=["admin-auth"])

# Shorter-lived cookies for admin sessions (Section 5 of the architecture doc).
COOKIE_KWARGS = dict(httponly=True, secure=True, samesite="lax")


@router.post("/login", response_model=UserOut)
def admin_login(payload: LoginIn, response: Response, db: Session = Depends(get_db)):
    user = (
        db.query(User)
        .filter(User.email == payload.email, User.role.in_(["staff", "super_admin"]))
        .first()
    )
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Account is deactivated")

    response.set_cookie("access_token", create_access_token(user.id, user.role), **COOKIE_KWARGS)
    response.set_cookie("refresh_token", create_refresh_token(user.id, user.role), **COOKIE_KWARGS)
    return user


@router.post("/logout")
def admin_logout(response: Response):
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    return {"detail": "Logged out"}


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user
