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

    # Account-lockout (brute-force protection) — applies to both customer
    # (public/auth.py) and staff (admin/auth.py) login. After
    # MAX_LOGIN_ATTEMPTS consecutive wrong passwords, the account is locked
    # for LOCKOUT_MINUTES, even if the correct password is supplied next.
    MAX_LOGIN_ATTEMPTS: int = 5
    LOCKOUT_MINUTES: int = 15

    # Password policy, enforced in schemas/common.py (RegisterIn) and
    # schemas/admin.py (StaffCreateIn).
    PASSWORD_MIN_LENGTH: int = 8

    COOKIE_DOMAIN: str = "localhost"

    @property
    def ACCESS_TOKEN_COOKIE(self) -> str:
        # api-public and api-admin both set/read a plain "access_token"
        # cookie with no explicit Domain attribute. Browsers scope cookies
        # by domain only, not port, so on local dev (everything on
        # "localhost", just different ports) the two instances silently
        # share one cookie jar — logging into the admin panel in one tab
        # overwrites the customer session's token in another tab, and vice
        # versa. Namespacing the cookie name per instance keeps the two
        # sessions isolated even when the host is identical.
        return "admin_access_token" if self.APP_MODE == "admin" else "public_access_token"

    @property
    def REFRESH_TOKEN_COOKIE(self) -> str:
        return "admin_refresh_token" if self.APP_MODE == "admin" else "public_refresh_token"
    # False for local http:// dev (this stack has no HTTPS anywhere yet) —
    # a Secure cookie is silently dropped by many browsers over plain HTTP,
    # which is what causes "login succeeds but immediately bounces back".
    # Set to True once this runs behind real HTTPS in production.
    COOKIE_SECURE: bool = False
    FRONTEND_ORIGIN: str = "http://localhost:3000"

    STRIPE_SECRET_KEY: str = "sk_test_placeholder"
    STRIPE_WEBHOOK_SECRET: str = "whsec_placeholder"

    # Pub/sub channel for live-refreshing the admin dashboard (booking
    # status changes, etc.) — same Redis container Celery already uses as
    # its broker/result backend (db 0/1), just a different logical db so
    # pub/sub traffic doesn't share keyspace with task queues.
    REDIS_URL: str = "redis://redis:6379/2"

    # Used server-side (container-to-container) for anything the API itself
    # needs to reach MinIO over, e.g. bucket setup.
    # Region the bucket actually lives in — SigV4 signing fails with
    # SignatureDoesNotMatch if this doesn't match the bucket's real region.
    AWS_REGION: str = "eu-north-1"
    # Real S3 regional endpoint (not MinIO). Same value used server-side and
    # for signing since S3 endpoints are publicly resolvable either way —
    # unlike MinIO there's no container-only-DNS vs browser-facing split.
    S3_ENDPOINT: str = "https://s3.eu-north-1.amazonaws.com"
    S3_PUBLIC_ENDPOINT: str = "https://s3.eu-north-1.amazonaws.com"
    S3_BUCKET: str = "rentease"
    S3_ACCESS_KEY: str = ""
    S3_SECRET_KEY: str = ""

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