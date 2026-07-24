from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_db, require_role
from app.models.models import Item, ItemCatalog
from app.schemas.admin import AdminItemOut, ItemCatalogCreateIn, ItemUnitCreateIn, ItemUnitUpdateIn

router = APIRouter(prefix="/items", tags=["admin-items"])
staff_only = require_role(["staff", "super_admin"])


@router.get("", response_model=list[AdminItemOut])
def list_items(db: Session = Depends(get_db), _=Depends(staff_only)):
    return db.query(Item).all()


@router.post("/catalog", status_code=status.HTTP_201_CREATED)
def create_catalog_entry(payload: ItemCatalogCreateIn, db: Session = Depends(get_db), _=Depends(staff_only)):
    entry = ItemCatalog(category_id=payload.category_id)
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return {"id": entry.id, "category_id": entry.category_id}


@router.post("", response_model=AdminItemOut, status_code=status.HTTP_201_CREATED)
def create_item(payload: ItemUnitCreateIn, db: Session = Depends(get_db), _=Depends(staff_only)):
    item = Item(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.patch("/{item_id}", response_model=AdminItemOut)
def update_item(item_id: int, payload: ItemUnitUpdateIn, db: Session = Depends(get_db), _=Depends(staff_only)):
    item = db.get(Item, item_id)
    if not item:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Item not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(item_id: int, db: Session = Depends(get_db), _=Depends(staff_only)):
    item = db.get(Item, item_id)
    if not item:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Item not found")
    # Soft-delete via status, matching the item lifecycle enum instead of a hard DELETE.
    item.status = "retired"
    db.commit()
