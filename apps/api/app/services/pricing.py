import math
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from app.core.config import settings
from app.models.models import Item


def quote_price(item: Item, start: datetime, end: datetime) -> dict:
    duration_hours = (end - start).total_seconds() / 3600
    days = max(1, math.ceil(duration_hours / 24))  # partial day rounds up to a full day

    base_amount = (item.base_price_daily * days).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    tax_amount = (base_amount * Decimal(str(settings.TAX_RATE))).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    deposit_amount = item.deposit_amount
    total_amount = base_amount + tax_amount + deposit_amount

    return {
        "days": days,
        "base_amount": base_amount,
        "tax_amount": tax_amount,
        "deposit_amount": deposit_amount,
        "total_amount": total_amount,
    }
