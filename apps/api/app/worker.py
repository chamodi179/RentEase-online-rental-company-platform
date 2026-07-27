import smtplib
from email.message import EmailMessage

from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "rentease",
    broker="redis://redis:6379/0",
    backend="redis://redis:6379/1",
)


@celery_app.task(
    name="send_booking_confirmation_email",
    autoretry_for=(smtplib.SMTPException, ConnectionError, OSError),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def send_booking_confirmation_email(
    booking_reference: str,
    customer_email: str,
    item_name: str = "",
    start_date: str = "",
    end_date: str = "",
    total_amount: str = "",
) -> None:
    """Actually sends the confirmation email over SMTP (spec §4.2) — this
    used to just print to the console. Points at a local MailDev container
    by default (see mailer service in docker-compose.yml / SMTP_* settings in
    config.py), so it's a real send even for local MVP demo purposes, not a
    simulated one; swap SMTP_* env vars for a real provider in production."""
    subject = f"Booking confirmed — {booking_reference}"

    details_lines = [f"Booking reference: {booking_reference}"]
    if item_name:
        details_lines.append(f"Item: {item_name}")
    if start_date and end_date:
        details_lines.append(f"Dates: {start_date} to {end_date}")
    if total_amount:
        details_lines.append(f"Total paid: {total_amount}")
    details_text = "\n".join(details_lines)

    text_body = (
        f"Hi,\n\nYour RentEase booking is confirmed.\n\n{details_text}\n\n"
        f"You can view this booking any time in My Bookings.\n\nThanks,\nRentEase"
    )
    html_rows = "".join(f"<tr><td style='padding:4px 0;color:#555'>{line}</td></tr>" for line in details_lines)
    html_body = f"""
    <div style="font-family:sans-serif;max-width:480px;margin:0 auto">
      <h2 style="color:#111">Booking confirmed</h2>
      <p>Your RentEase booking is confirmed.</p>
      <table style="width:100%;border-top:1px solid #eee;margin-top:12px">{html_rows}</table>
      <p style="margin-top:20px;color:#777;font-size:13px">You can view this booking any time in My Bookings.</p>
    </div>
    """

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings.SMTP_FROM
    message["To"] = customer_email
    message.set_content(text_body)
    message.add_alternative(html_body, subtype="html")

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as smtp:
        if settings.SMTP_USE_TLS:
            smtp.starttls()
        if settings.SMTP_USER:
            smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        smtp.send_message(message)
