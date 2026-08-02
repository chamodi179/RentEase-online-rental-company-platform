import redis.asyncio as aioredis
from fastapi import APIRouter, WebSocket, status
from jwt import PyJWTError

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.security import decode_token
from app.models.models import User
from app.services.realtime import BOOKING_EVENTS_CHANNEL

router = APIRouter(tags=["admin-realtime"])


def _authenticate(websocket: WebSocket) -> User | None:
    """Same checks as get_current_user + require_role(["staff","super_admin"]),
    done by hand: FastAPI's Depends()-based Cookie/role dependencies are built
    for HTTP request/response, not the websocket handshake, so this mirrors
    that logic directly against the same namespaced cookie (see
    settings.ACCESS_TOKEN_COOKIE — this only ever runs on api-admin, so it's
    always the admin cookie, never the customer one)."""
    token = websocket.cookies.get(settings.ACCESS_TOKEN_COOKIE)
    if not token:
        return None
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            return None
        user_id = int(payload["sub"])
    except (PyJWTError, KeyError, ValueError):
        return None

    db = SessionLocal()
    try:
        user = db.get(User, user_id)
    finally:
        db.close()

    if not user or not user.is_active or user.role not in ("staff", "super_admin"):
        return None
    return user


@router.websocket("/ws/bookings")
async def bookings_live_feed(websocket: WebSocket):
    """Pushes a small JSON message any time a booking is created or changes
    status (cancel, confirm, activate, complete — see booking_service.py's
    publish_booking_event calls). The dashboard doesn't need this to be
    correct — every page still loads fresh from the DB on its own — it just
    means an admin doesn't have to manually reload to see another admin's
    (or a customer's, or a webhook's) change land."""
    user = _authenticate(websocket)
    if not user:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()
    redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(BOOKING_EVENTS_CHANNEL)
    try:
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue
            await websocket.send_text(message["data"])
    except Exception:
        # Covers WebSocketDisconnect and any transient Redis/connection
        # error alike — either way there's nothing left to do but clean up
        # below; the client's own reconnect logic handles resuming the feed.
        pass
    finally:
        await pubsub.unsubscribe(BOOKING_EVENTS_CHANNEL)
        await pubsub.close()
        await redis_client.close()
