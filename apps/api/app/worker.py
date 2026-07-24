from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "rentease",
    broker="redis://redis:6379/0",
    backend="redis://redis:6379/1",
)


@celery_app.task(name="send_booking_confirmation_email")
def send_booking_confirmation_email(booking_reference: str, customer_email: str) -> None:
    # Production: render a template and send via SES/SendGrid. Stubbed for MVP.
    print(f"[worker] Would email {customer_email}: booking {booking_reference} confirmed.")
