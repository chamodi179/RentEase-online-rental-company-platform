from sqlalchemy.orm import Session

from app.models.models import AuditLog

# Naming convention for the `action` string:
#   "<entity_type>.<verb>"        e.g. "item.created", "staff.deactivated"
#   "<entity_type>.<verb>:<detail>"  only when a short qualifier adds real
#                                     value, e.g. "booking.status_changed:active"
# `entity_type` should match the value used elsewhere for that entity
# (booking, document, item, item_catalog, item_photo, payment, staff).
# Verbs are past tense. Keep the whole string terse — this column is
# String(150) and meant to be skimmed in a log viewer, not parsed.


def record_audit_log(
    db: Session, *, actor_id: int | None, action: str, entity_type: str, entity_id: int,
) -> None:
    """Write one row to audit_logs.

    Deliberately does NOT call db.commit() — callers already commit the
    entity change in the same transaction (e.g. booking status update,
    document review), and an audit row should never be persisted on its own
    if that surrounding change fails to commit. Just db.add(); the caller's
    existing commit() picks it up.
    """
    db.add(
        AuditLog(
            actor_id=actor_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
        )
    )
