from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # "public" -> mounts customer-facing routes only
    # "admin"  -> mounts staff/super_admin routes only
    APP_MODE: str = "public"

    # MySQL 8 / MariaDB — matches 01_schema.sql, already running locally
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_USER: str = "root"
    DB_PASSWORD: str = "root"
    DB_NAME: str = "rentease"
    DB_POOL_SIZE: int = 10

    JWT_SECRET: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7  # shortened to 1 for APP_MODE=admin, see security.py

    COOKIE_DOMAIN: str = "localhost"
    # False for local http:// dev (this stack has no HTTPS anywhere yet) —
    # a Secure cookie is silently dropped by many browsers over plain HTTP,
    # which is what causes "login succeeds but immediately bounces back".
    # Set to True once this runs behind real HTTPS in production.
    COOKIE_SECURE: bool = False
    FRONTEND_ORIGIN: str = "http://localhost:3000"

    STRIPE_SECRET_KEY: str = "sk_test_placeholder"
    STRIPE_WEBHOOK_SECRET: str = "whsec_placeholder"

    # Used server-side (container-to-container) for anything the API itself
    # needs to reach MinIO over, e.g. bucket setup.
    S3_ENDPOINT: str = "http://minio:9000"
    # Used only to SIGN presigned URLs. Must be the host the *browser* will
    # actually call, since the Host header is part of the SigV4 signature —
    # signing against "minio:9000" (container-only DNS) produces a URL the
    # browser can never resolve. No network call happens at signing time, so
    # this doesn't need to be reachable from inside the API container itself.
    S3_PUBLIC_ENDPOINT: str = "http://localhost:9000"
    S3_BUCKET: str = "rentease"
    S3_ACCESS_KEY: str = "minioadmin"
    S3_SECRET_KEY: str = "minioadmin"

    TAX_RATE: float = 0.0  # MVP hardcodes a single tax rate per spec §5.7

    # Booking confirmation email (spec §4.2). Defaults point at the local
    # MailDev container added to docker-compose (see mailer service) so the
    # full send actually happens in dev/demo without needing real SMTP
    # credentials — swap these for a real provider's SMTP settings in
    # production (SES/SendGrid SMTP relay both work fine here too, no code
    # change needed, just env vars).
    SMTP_HOST: str = "mailer"
    SMTP_PORT: int = 1025
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_USE_TLS: bool = False
    SMTP_FROM: str = "RentEase <bookings@rentease.local>"

    @property
    def SQLALCHEMY_DATABASE_URL(self) -> str:
        return (
            f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4"
        )

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
