from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
import os

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env.test" if os.getenv("ENVIRONMENT") == "test" else ".env"
    )

    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    FAIL_FAST: bool = False

    # Security & JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # AI APIs
    QLOO_API_KEY: str
    GEMINI_API_KEY: str
    GEMINI_MODEL_NAME: str = "gemini-2.5-pro"
    TAVILY_API_KEY: str
    SCRAPER_API_KEY: str
    
    # Google OAuth
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str

    # Database
    POSTGRES_DATABASE_URL: str
    POSTGRES_SCHEMA: str = "public"
    POSTGRES_POOL_SIZE: int = 10
    POSTGRES_MAX_OVERFLOW: int = 5
    POSTGRES_POOL_TIMEOUT: int = 30
    POSTGRES_POOL_RECYCLE: int = 1800
    POSTGRES_USE_SSL: bool = True

    # CORS & Frontend
    CORS_ORIGINS: list[str]

@lru_cache
def get_settings():
    return Settings()