import json

import redis

from app.core.config import settings

# One channel is enough for now — the admin dashboard just needs to know
# "something about this booking changed, go re-fetch it", not a full event
# payload. Keeping it structured (not just a bare booking id) leaves room
# to filter client-side later (e.g. only refresh if the visible list's
# status filter matches) without a backend change.
BOOKING_EVENTS_CHANNEL = "admin:bookings"

_client: redis.Redis | None = None


def _get_client() -> redis.Redis:
    global _client
    if _client is None:
        _client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _client


def publish_booking_event(*, booking_id: int, booking_reference: str, status: str, event: str) -> None:
    """Best-effort notification for the admin dashboard's live-refresh.

    Deliberately swallows Redis errors: the booking's DB row is already
    committed by the time this is called (see booking_service.py), so a
    Redis hiccup should never fail the request or roll back a real state
    change over what's purely a UX nicety. Worst case, the admin dashboard
    just doesn't live-refresh until the next manual reload — the data
    itself is still correct.
    """
    try:
        _get_client().publish(
            BOOKING_EVENTS_CHANNEL,
            json.dumps(
                {
                    "event": event,  # "created" | "status_changed"
                    "booking_id": booking_id,
                    "booking_reference": booking_reference,
                    "status": status,
                }
            ),
        )
    except redis.RedisError:
        pass
