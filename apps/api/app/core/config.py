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

    S3_ENDPOINT: str = "http://minio:9000"
    S3_BUCKET: str = "rentease"
    S3_ACCESS_KEY: str = "minioadmin"
    S3_SECRET_KEY: str = "minioadmin"

    TAX_RATE: float = 0.0  # MVP hardcodes a single tax rate per spec §5.7

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
