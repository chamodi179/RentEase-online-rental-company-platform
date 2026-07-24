from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.core.deps import get_db
from app.models.models import Item, ItemCatalog
from app.schemas.common import ItemDetailOut, ItemListOut, PriceQuoteOut
from app.services.availability import available_item_ids
from app.services.pricing import quote_price

router = APIRouter(prefix="/items", tags=["items"])


@router.get("", response_model=list[ItemListOut])
def browse_items(
    category_id: int | None = None,
    q: str | None = Query(default=None, description="keyword search on item name"),
    start: datetime | None = None,
    end: datetime | None = None,
    db: Session = Depends(get_db),
):
    # photos live on ItemCatalog (shared across units of the same model), so
    # they're eager-loaded via catalog -> photos, not directly off Item.
    query = db.query(Item).options(
        joinedload(Item.branch), joinedload(Item.catalog).joinedload(ItemCatalog.photos)
    ).filter(Item.status == "available")

    if category_id:
        query = query.join(Item.catalog).filter_by(category_id=category_id)
    if q:
        query = query.filter(Item.name.ilike(f"%{q}%"))

    items = query.all()

    if start and end:
        ids = available_item_ids(db, [i.id for i in items], start, end)
        items = [i for i in items if i.id in ids]

    return items


@router.get("/{item_id}", response_model=ItemDetailOut)
def get_item(item_id: int, db: Session = Depends(get_db)):
    item = (
        db.query(Item)
        .options(
            joinedload(Item.branch),
            joinedload(Item.catalog).joinedload(ItemCatalog.photos),
            joinedload(Item.catalog),
        )
        .filter(Item.id == item_id)
        .first()
    )
    if not item:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Item not found")
    item.category = item.catalog.category if item.catalog else None
    return item


@router.get("/{item_id}/quote", response_model=PriceQuoteOut)
def get_quote(item_id: int, start: datetime, end: datetime, db: Session = Depends(get_db)):
    item = db.get(Item, item_id)
    if not item:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Item not found")
    if end <= start:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "end must be after start")
    return quote_price(item, start, end)
