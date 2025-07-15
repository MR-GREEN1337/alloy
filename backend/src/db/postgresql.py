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
        # Get database URL from environment or settings
        self.DATABASE_URL = settings.POSTGRES_DATABASE_URL
        if not self.DATABASE_URL:
            logger.warning("DATABASE_URL not set, using development defaults")
            self.DATABASE_URL = (
                "postgresql+asyncpg://postgres:postgres@localhost:5432/ustadh"
            )

        # Parse the database URL
        url = urlparse(self.DATABASE_URL)

        # Create base URL without query parameters (removing sslmode if present)
        base_url = f"postgresql+asyncpg://{url.netloc}{url.path}"

        # Store connection details for better error reporting
        self.db_host = url.hostname
        self.db_port = url.port or 5432
        self.db_user = url.username
        self.db_name = url.path.lstrip("/") if url.path else None

        # Extract schema from settings or use default
        self.schema = (
            settings.POSTGRES_SCHEMA
            if hasattr(settings, "POSTGRES_SCHEMA")
            else "public"
        )

        # Create SSL context if needed
        ssl_context = None
        if settings.POSTGRES_USE_SSL:
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE  # For development

        # Connection arguments
        connect_args = {}
        if ssl_context:
            connect_args["ssl"] = ssl_context

        # Configure connection pool
        self.pool_size = settings.POSTGRES_POOL_SIZE
        self.max_overflow = settings.POSTGRES_MAX_OVERFLOW
        self.pool_timeout = settings.POSTGRES_POOL_TIMEOUT
        self.pool_recycle = int(
            os.getenv("POSTGRES_POOL_RECYCLE", "1800")
        )  # 30 minutes

        # Connection retry settings
        self.max_retries = int(os.getenv("POSTGRES_MAX_RETRIES", "5"))
        self.retry_delay = int(os.getenv("POSTGRES_RETRY_DELAY", "2"))

        # Debug mode for logging
        self.debug_mode = settings.DEBUG

        # Create the async engine with configuration
        try:
            self.engine = create_async_engine(
                base_url,  # Use base_url without query parameters
                echo=self.debug_mode,
                pool_size=self.pool_size,
                max_overflow=self.max_overflow,
                pool_timeout=self.pool_timeout,
                pool_recycle=self.pool_recycle,
                pool_pre_ping=True,
                connect_args=connect_args,
            )

            # Create async session factory
            self.async_session_maker = sessionmaker(
                self.engine, class_=AsyncSession, expire_on_commit=False
            )

            logger.info(
                f"PostgreSQL connection initialized: host={self.db_host}, "
                f"user={self.db_user}, database={self.db_name}, "
                f"schema={self.schema}, pool_size={self.pool_size}"
            )
        except Exception as e:
            logger.error(f"Failed to initialize PostgreSQL connection: {str(e)}")
            raise

    async def create_db_and_tables(self):
        """
        Initialize database tables with retry logic.
        Useful during application startup to ensure database is ready.
        """
        retries = 0
        last_error = None

        while retries < self.max_retries:
            try:
                logger.info(
                    f"Attempting to connect to database (attempt {retries + 1})"
                )

                # Test connection first
                async with self.async_session_maker() as session:
                    result = await session.execute(text("SELECT 1"))
                    # Fixed: Don't await the row, just get the scalar result
                    value = result.scalar()
                    logger.info(f"Database connection successful: {value}")

                # Create schema if it doesn't exist
                async with self.engine.begin() as conn:
                    await conn.execute(
                        text(f"CREATE SCHEMA IF NOT EXISTS {self.schema}")
                    )
                    logger.info(f"Ensured schema '{self.schema}' exists")

                    # Set search path to include our schema
                    await conn.execute(
                        text(f"SET search_path TO {self.schema}, public")
                    )

                    # Create tables in the specified schema
                    await conn.run_sync(lambda conn: SQLModel.metadata.create_all(conn))

                logger.info(
                    f"PostgreSQL tables created or verified in schema '{self.schema}'"
                )
                return True

            except Exception as e:
                retries += 1
                last_error = e

                if retries < self.max_retries:
                    wait_time = self.retry_delay * retries  # Exponential backoff
                    logger.warning(
                        f"Database connection failed: {str(e)}. "
                        f"Retrying in {wait_time} seconds ({retries}/{self.max_retries})"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(
                        f"Failed to connect to database after {self.max_retries} attempts. "
                        f"Last error: {str(last_error)}"
                    )

        # If we get here, all retries failed
        raise last_error or RuntimeError("Failed to connect to database")

    async def _set_schema(self, session):
        """Set the search path to include our schema."""
        await session.execute(text(f"SET search_path TO {self.schema}, public"))

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Get async database session with automatic cleanup.
        Uses context manager pattern for proper resource handling.
        """
        async with self.async_session_maker() as session:
            try:
                # Set schema for this session
                await self._set_schema(session)
                yield session
                await session.commit()
            except Exception as e:
                await session.rollback()
                logger.error(f"Database transaction error: {str(e)}")
                raise
            finally:
                await session.close()

    # For FastAPI dependency injection
    async def get_db_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Dependency for FastAPI to get an async database session."""
        async with self.get_session() as session:
            yield session

    async def health_check(self) -> Dict[str, Any]:
        """
        Check database connection health and return detailed status.
        Useful for monitoring endpoints.
        """
        start_time = datetime.utcnow()
        status = {
            "status": "error",
            "message": "",
            "details": {
                "host": self.db_host,
                "database": self.db_name,
                "schema": self.schema,
                "user": self.db_user,
                "response_time_ms": None,
            },
        }

        try:
            async with self.async_session_maker() as session:
                await self._set_schema(session)  # Set schema
                await session.execute(text("SELECT 1"))
                end_time = datetime.utcnow()
                response_time = (end_time - start_time).total_seconds() * 1000

                status.update(
                    {
                        "status": "ok",
                        "message": "Database connection successful",
                        "details": {
                            "host": self.db_host,
                            "database": self.db_name,
                            "schema": self.schema,
                            "user": self.db_user,
                            "response_time_ms": round(response_time, 2),
                        },
                    }
                )
                return status
        except Exception as e:
            end_time = datetime.utcnow()
            response_time = (end_time - start_time).total_seconds() * 1000

            status.update(
                {
                    "status": "error",
                    "message": str(e),
                    "details": {
                        "host": self.db_host,
                        "database": self.db_name,
                        "schema": self.schema,
                        "user": self.db_user,
                        "response_time_ms": round(response_time, 2),
                        "error": str(e),
                    },
                }
            )
            return status


# Create a singleton instance
postgres_db = PostgresDatabase()


# For FastAPI dependency injection
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency to get database session"""
    async for session in postgres_db.get_db_session():
        yield session
