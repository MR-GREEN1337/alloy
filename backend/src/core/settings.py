from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    class Config:
        env_file = ".env"

    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    FAIL_FAST: bool = False

    # Security & JWT
    SECRET_KEY: str  # No default! Must be set in .env
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # Database
    POSTGRES_DATABASE_URL: str  # No default!
    POSTGRES_SCHEMA: str = "public"
    POSTGRES_POOL_SIZE: int = 10
    POSTGRES_MAX_OVERFLOW: int = 5
    POSTGRES_POOL_TIMEOUT: int = 30
    POSTGRES_POOL_RECYCLE: int = 1800
    POSTGRES_USE_SSL: bool = False

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

@lru_cache
def get_settings():
    return Settings()