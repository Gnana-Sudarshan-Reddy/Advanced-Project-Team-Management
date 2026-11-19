"""Application settings, loaded from environment variables / .env file."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application options populated from environment variables and the .env file."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str = "Project & Team Management API"
    APP_VERSION: str = "2.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # SQLite (default, zero setup). For MySQL:
    # DATABASE_URL=mysql+pymysql://pm_user:pm_pass@localhost:3306/pm_db
    DATABASE_URL: str = "sqlite:///./app.db"
    AUTO_CREATE_TABLES: bool = False

    SECRET_KEY: str = "change-this-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    FIRST_ADMIN_EMAIL: str = "admin@example.com"
    FIRST_ADMIN_PASSWORD: str = "Admin@12345"
    FIRST_ADMIN_NAME: str = "System Admin"

    LOG_LEVEL: str = "INFO"
    LOG_FILE: str | None = "logs/app.log"
    SENTRY_DSN: str | None = None  # optional error monitoring
    CORS_ORIGINS: list[str] = ["*"]
    UPLOAD_DIR: str = "uploads"
    DEADLINE_NOTIFICATION_DAYS: int = 2


@lru_cache
def get_settings() -> Settings:
    """Load settings once so all application modules share the same configuration."""
    return Settings()


settings = get_settings()
