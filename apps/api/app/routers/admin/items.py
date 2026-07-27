import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.core.deps import get_db, require_role
from app.core.s3 import generate_presigned_put
from app.models.models import Category, Item, ItemCatalog, ItemPhoto, User
from app.schemas.admin import (
    AdminCatalogOut,
    AdminItemOut,
    ItemCatalogCreateIn,
    ItemPhotoPresignIn,
    ItemPhotoRegisterIn,
    ItemUnitCreateIn,
    ItemUnitUpdateIn,
)
from app.schemas.common import CategoryOut, ItemPhotoOut, PresignOut
from app.services.audit_service import record_audit_log

router = APIRouter(prefix="/items", tags=["admin-items"])
staff_only = require_role(["staff", "super_admin"])


@router.get("", response_model=list[AdminItemOut])
def list_items(db: Session = Depends(get_db), _=Depends(staff_only)):
    return db.query(Item).all()


@router.get("/categories", response_model=list[CategoryOut])
def list_categories(db: Session = Depends(get_db), _=Depends(staff_only)):
    """No categories endpoint existed anywhere — without it, creating a
    catalog entry meant guessing category_id numbers blind. Needed for the
    catalog/photo-management screen to actually be usable."""
    return db.query(Category).order_by(Category.name).all()


@router.get("/catalog", response_model=list[AdminCatalogOut])
def list_catalog(db: Session = Depends(get_db), _=Depends(staff_only)):
    """Backs the photo-management screen: staff need to see which catalog
    entries (item models) exist and what photos each already has before they
    can attach more — there was previously no way to list this at all."""
    return (
        db.query(ItemCatalog)
        .options(joinedload(ItemCatalog.category), joinedload(ItemCatalog.photos))
        .all()
    )


@router.post("/catalog", status_code=status.HTTP_201_CREATED)
def create_catalog_entry(
    payload: ItemCatalogCreateIn, db: Session = Depends(get_db), user: User = Depends(staff_only)
):
    entry = ItemCatalog(category_id=payload.category_id)
    db.add(entry)
    db.flush()
    record_audit_log(
        db, actor_id=user.id, action="item_catalog.created",
        entity_type="item_catalog", entity_id=entry.id,
    )
    db.commit()
    db.refresh(entry)
    return {"id": entry.id, "category_id": entry.category_id}


@router.post("/catalog/{catalog_id}/photos/presign", response_model=PresignOut)
def presign_catalog_photo(
    catalog_id: int, payload: ItemPhotoPresignIn, db: Session = Depends(get_db), _=Depends(staff_only)
):
    """Mirrors the customer document-upload presign flow (routers/public/documents.py):
    the API only signs the URL, the browser PUTs the bytes straight to
    MinIO/S3, and the API never proxies file bytes (architecture doc §7)."""
    catalog = db.get(ItemCatalog, catalog_id)
    if not catalog:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Catalog entry not found")
    safe_name = payload.filename.replace("/", "_")
    key = f"item-photos/{catalog_id}/{uuid.uuid4().hex}_{safe_name}"
    upload_url = generate_presigned_put(key, content_type=payload.content_type)
    file_url = f"{settings.S3_PUBLIC_ENDPOINT}/{settings.S3_BUCKET}/{key}"
    return PresignOut(upload_url=upload_url, file_url=file_url)


@router.post("/catalog/{catalog_id}/photos", response_model=ItemPhotoOut, status_code=status.HTTP_201_CREATED)
def register_catalog_photo(
    catalog_id: int, payload: ItemPhotoRegisterIn, db: Session = Depends(get_db), user: User = Depends(staff_only)
):
    catalog = db.get(ItemCatalog, catalog_id)
    if not catalog:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Catalog entry not found")
    # Same guard as documents.py's register_document: without this, a caller
    # could register any arbitrary URL as a photo instead of one actually
    # uploaded via the presign step above.
    expected_prefix = f"{settings.S3_PUBLIC_ENDPOINT}/{settings.S3_BUCKET}/item-photos/{catalog_id}/"
    if not payload.file_url.startswith(expected_prefix):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "file_url does not match a photo uploaded for this catalog entry"
        )
    photo = ItemPhoto(catalog_id=catalog_id, url=payload.file_url, sort_order=payload.sort_order)
    db.add(photo)
    db.flush()
    record_audit_log(
        db, actor_id=user.id, action="item_photo.created",
        entity_type="item_photo", entity_id=photo.id,
    )
    db.commit()
    db.refresh(photo)
    return photo


@router.delete("/catalog/photos/{photo_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_catalog_photo(photo_id: int, db: Session = Depends(get_db), user: User = Depends(staff_only)):
    photo = db.get(ItemPhoto, photo_id)
    if not photo:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Photo not found")
    photo_id_for_log = photo.id
    db.delete(photo)
    record_audit_log(
        db, actor_id=user.id, action="item_photo.deleted",
        entity_type="item_photo", entity_id=photo_id_for_log,
    )
    db.commit()


@router.post("", response_model=AdminItemOut, status_code=status.HTTP_201_CREATED)
def create_item(payload: ItemUnitCreateIn, db: Session = Depends(get_db), user: User = Depends(staff_only)):
    item = Item(**payload.model_dump())
    db.add(item)
    db.flush()
    record_audit_log(
        db, actor_id=user.id, action="item.created",
        entity_type="item", entity_id=item.id,
    )
    db.commit()
    db.refresh(item)
    return item


@router.patch("/{item_id}", response_model=AdminItemOut)
def update_item(
    item_id: int, payload: ItemUnitUpdateIn, db: Session = Depends(get_db), user: User = Depends(staff_only)
):
    item = db.get(Item, item_id)
    if not item:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Item not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    record_audit_log(
        db, actor_id=user.id, action="item.updated",
        entity_type="item", entity_id=item.id,
    )
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(item_id: int, db: Session = Depends(get_db), user: User = Depends(staff_only)):
    item = db.get(Item, item_id)
    if not item:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Item not found")
    # Soft-delete via status, matching the item lifecycle enum instead of a hard DELETE.
    item.status = "retired"
    record_audit_log(
        db, actor_id=user.id, action="item.retired",
        entity_type="item", entity_id=item.id,
    )
    db.commit()
