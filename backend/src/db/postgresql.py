from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import text
from typing import AsyncGenerator, Dict, Any
from contextlib import asynccontextmanager
import asyncio
from datetime import datetime
from sqlmodel import SQLModel
from urllib.parse import urlparse
from loguru import logger
import ssl
import os
from src.core.settings import get_settings

settings = get_settings()


class PostgresDatabase:
    def __init__(self):
        self.DATABASE_URL = settings.POSTGRES_DATABASE_URL
        if not self.DATABASE_URL:
            logger.warning("DATABASE_URL not set, using development defaults")
            self.DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/ustadh"
        
        url = urlparse(self.DATABASE_URL)
        base_url = f"postgresql+asyncpg://{url.netloc}{url.path}"
        self.db_host, self.db_port, self.db_user = url.hostname, url.port or 5432, url.username
        self.db_name = url.path.lstrip("/") if url.path else None
        self.schema = getattr(settings, "POSTGRES_SCHEMA", "public")

        ssl_context = None
        if settings.POSTGRES_USE_SSL:
            ssl_context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

        connect_args: Dict[str, Any] = {}
        if ssl_context:
            connect_args["ssl"] = ssl_context

        # THE FIX: In a development environment, prepared statement caching can cause
        # errors when the schema changes during hot-reloading (e.g., dropping/creating
        # tables on startup). Disabling the cache for asyncpg resolves this.
        if settings.ENVIRONMENT == "development":
            # The value 0 disables the cache.
            connect_args["statement_cache_size"] = 0
            logger.warning(
                "DEV MODE: Disabling statement cache to prevent schema change errors."
            )

        self.pool_size = settings.POSTGRES_POOL_SIZE
        self.max_overflow = settings.POSTGRES_MAX_OVERFLOW
        self.pool_timeout = settings.POSTGRES_POOL_TIMEOUT
        self.pool_recycle = int(os.getenv("POSTGRES_POOL_RECYCLE", "1800"))
        self.max_retries = int(os.getenv("POSTGRES_MAX_RETRIES", "5"))
        self.retry_delay = int(os.getenv("POSTGRES_RETRY_DELAY", "2"))
        self.debug_mode = settings.DEBUG

        try:
            self.engine = create_async_engine(
                base_url, echo=self.debug_mode, pool_size=self.pool_size, max_overflow=self.max_overflow,
                pool_timeout=self.pool_timeout, pool_recycle=self.pool_recycle, pool_pre_ping=True, connect_args=connect_args
            )
            self.async_session_maker = sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)
            logger.info(f"PostgreSQL connection initialized: host={self.db_host}, user={self.db_user}, db={self.db_name}, schema={self.schema}")
        except Exception as e:
            logger.error(f"Failed to initialize PostgreSQL connection: {str(e)}")
            raise

    async def create_db_and_tables(self):
        """
        Initializes database tables. For development, it drops and recreates tables
        to ensure the schema is always in sync with the models. For production,
        it creates tables if they don't exist, but does not perform migrations.
        """
        retries = 0
        last_error = None
        while retries < self.max_retries:
            try:
                logger.info(f"Attempting to connect to database (attempt {retries + 1})")
                async with self.engine.begin() as conn:
                    # Ensure the schema exists
                    await conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {self.schema}"))
                    
                    # THE FIX: In a dev environment, ensure schema is always up-to-date.
                    if settings.ENVIRONMENT == "development":
                        logger.warning("DEV MODE: Dropping and recreating tables for schema sync.")
                        await conn.run_sync(SQLModel.metadata.drop_all)

                    # Create all tables. This is idempotent and will not
                    # alter existing tables unless they were just dropped.
                    await conn.run_sync(SQLModel.metadata.create_all)

                logger.success("Database schema verified and ready.")
                return True

            except Exception as e:
                retries += 1
                last_error = e
                if retries < self.max_retries:
                    wait_time = self.retry_delay * retries
                    logger.warning(f"DB connection failed: {str(e)}. Retrying in {wait_time}s ({retries}/{self.max_retries})")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Failed to connect to database after {self.max_retries} attempts. Last error: {str(last_error)}")
        raise last_error or RuntimeError("Failed to connect to database")

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        async with self.async_session_maker() as session:
            try:
                await session.execute(text(f"SET search_path TO {self.schema}, public"))
                yield session
                await session.commit()
            except Exception as e:
                await session.rollback()
                logger.error(f"Database transaction error: {str(e)}")
                raise
            finally:
                await session.close()

    async def get_db_session(self) -> AsyncGenerator[AsyncSession, None]:
        async with self.get_session() as session:
            yield session

    async def health_check(self) -> Dict[str, Any]:
        start_time = datetime.utcnow()
        status = {"status": "error", "message": "", "details": {}}
        try:
            async with self.async_session_maker() as session:
                await session.execute(text("SELECT 1"))
            end_time = datetime.utcnow()
            response_time = (end_time - start_time).total_seconds() * 1000
            status.update({"status": "ok", "message": "Database connection successful", "details": {"response_time_ms": round(response_time, 2)}})
        except Exception as e:
            status.update({"message": str(e)})
        return status

postgres_db = PostgresDatabase()

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async for session in postgres_db.get_db_session():
        yield session