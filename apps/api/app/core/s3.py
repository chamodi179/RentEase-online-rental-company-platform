import boto3
from botocore.client import Config as BotoConfig

from app.core.config import settings


def get_presigning_client():
    """Client used only to SIGN URLs. region_name must match the bucket's
    actual AWS region or SigV4 signing fails. addressing_style="path" keeps
    generated URLs as f"{endpoint}/{bucket}/{key}" (same shape MinIO used),
    so key_from_file_url() below doesn't need to change."""
    return boto3.client(
        "s3",
        endpoint_url=settings.S3_PUBLIC_ENDPOINT,
        aws_access_key_id=settings.S3_ACCESS_KEY,
        aws_secret_access_key=settings.S3_SECRET_KEY,
        config=BotoConfig(signature_version="s3v4", s3={"addressing_style": "path"}),
        region_name=settings.AWS_REGION,
    )


def generate_presigned_put(key: str, content_type: str = "application/octet-stream", expires_in: int = 300) -> str:
    client = get_presigning_client()
    return client.generate_presigned_url(
        "put_object",
        Params={"Bucket": settings.S3_BUCKET, "Key": key, "ContentType": content_type},
        ExpiresIn=expires_in,
    )


def generate_presigned_get(key: str, expires_in: int = 300) -> str:
    """A presigned PUT only ever authorizes the upload itself — the bucket
    stays private, so a stored file_url can't be opened directly afterward
    (browsers hit AccessDenied). Viewing a private object needs its own,
    separately-signed GET url, generated on demand. Not currently called
    anywhere (item-catalog photos are served from a public bucket path),
    kept here as the general-purpose helper for any future private-object
    read case."""
    client = get_presigning_client()
    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.S3_BUCKET, "Key": key},
        ExpiresIn=expires_in,
    )


def key_from_file_url(file_url: str) -> str:
    """Recovers the S3 object key from a stored file_url of the form
    f"{S3_PUBLIC_ENDPOINT}/{S3_BUCKET}/{key}" (see presign_catalog_photo in
    routers/admin/items.py)."""
    prefix = f"{settings.S3_PUBLIC_ENDPOINT}/{settings.S3_BUCKET}/"
    if not file_url.startswith(prefix):
        raise ValueError("file_url is not a recognized S3 object URL")
    return file_url[len(prefix):]
