import boto3
from botocore.client import Config as BotoConfig

from app.core.config import settings


def get_presigning_client():
    """Client used only to SIGN URLs — endpoint must be the browser-facing
    host (see S3_PUBLIC_ENDPOINT comment in config.py)."""
    return boto3.client(
        "s3",
        endpoint_url=settings.S3_PUBLIC_ENDPOINT,
        aws_access_key_id=settings.S3_ACCESS_KEY,
        aws_secret_access_key=settings.S3_SECRET_KEY,
        config=BotoConfig(signature_version="s3v4"),
        region_name="us-east-1",
    )


def generate_presigned_put(key: str, content_type: str = "application/octet-stream", expires_in: int = 300) -> str:
    client = get_presigning_client()
    return client.generate_presigned_url(
        "put_object",
        Params={"Bucket": settings.S3_BUCKET, "Key": key, "ContentType": content_type},
        ExpiresIn=expires_in,
    )
