from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from jwt import PyJWTError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import get_current_user, get_db
from app.core.security import create_access_token, create_refresh_token, decode_token, verify_password
from app.models.models import User
from app.schemas.common import LoginIn, UserOut
from app.services.audit_service import record_audit_log

router = APIRouter(prefix="/auth", tags=["admin-auth"])

# Shorter-lived cookies for admin sessions (Section 5 of the architecture doc).
COOKIE_KWARGS = dict(httponly=True, secure=settings.COOKIE_SECURE, samesite="lax")


def _as_aware(dt: datetime) -> datetime:
    """MySQL DATETIME columns come back naive; treat them as UTC (everything
    in this app is written/read in UTC) so they can be compared against
    datetime.now(timezone.utc) without raising."""
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


@router.post("/login", response_model=UserOut)
def admin_login(payload: LoginIn, response: Response, db: Session = Depends(get_db)):
    user = (
        db.query(User)
        .filter(User.email == payload.email, User.role.in_(["staff", "super_admin"]))
        .first()
    )

    now = datetime.now(timezone.utc)
    if user and user.locked_until and _as_aware(user.locked_until) > now:
        retry_minutes = max(1, int((_as_aware(user.locked_until) - now).total_seconds() // 60) + 1)
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            f"Account temporarily locked due to repeated failed logins. Try again in about {retry_minutes} minute(s).",
        )

    if not user or not verify_password(payload.password, user.password_hash):
        if user:
            user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
            action = "staff.login_failed"
            if user.failed_login_attempts >= settings.MAX_LOGIN_ATTEMPTS:
                user.locked_until = now + timedelta(minutes=settings.LOCKOUT_MINUTES)
                action = "staff.account_locked"
            record_audit_log(
                db, actor_id=user.id, action=action,
                entity_type="staff", entity_id=user.id,
            )
            db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
    if not user.is_active:
        record_audit_log(
            db, actor_id=user.id, action="staff.login_blocked",
            entity_type="staff", entity_id=user.id,
        )
        db.commit()
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Account is deactivated")

    user.failed_login_attempts = 0
    user.locked_until = None
    record_audit_log(
        db, actor_id=user.id, action="staff.logged_in",
        entity_type="staff", entity_id=user.id,
    )
    db.commit()
    response.set_cookie(settings.ACCESS_TOKEN_COOKIE, create_access_token(user.id, user.role), **COOKIE_KWARGS)
    response.set_cookie(settings.REFRESH_TOKEN_COOKIE, create_refresh_token(user.id, user.role), **COOKIE_KWARGS)
    return user


@router.post("/refresh", response_model=UserOut)
def admin_refresh(
    response: Response,
    refresh_token: str | None = Cookie(default=None, alias=settings.REFRESH_TOKEN_COOKIE),
    db: Session = Depends(get_db),
):
    """See the matching public/auth.py refresh endpoint — same gap existed
    here, so staff got logged out on every access-token expiry too."""
    if not refresh_token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    try:
        payload = decode_token(refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token type")
        user_id = int(payload["sub"])
    except (PyJWTError, KeyError, ValueError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired refresh token")

    user = db.get(User, user_id)
    if not user or not user.is_active or user.role not in ("staff", "super_admin"):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found or inactive")

    response.set_cookie(settings.ACCESS_TOKEN_COOKIE, create_access_token(user.id, user.role), **COOKIE_KWARGS)
    return user


@router.post("/logout")
def admin_logout(response: Response):
    response.delete_cookie(settings.ACCESS_TOKEN_COOKIE)
    response.delete_cookie(settings.REFRESH_TOKEN_COOKIE)
    return {"detail": "Logged out"}


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user
