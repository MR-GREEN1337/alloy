import pytest_asyncio
import asyncio
from typing import AsyncGenerator, Generator
from httpx import AsyncClient, ASGITransport
from sqlmodel import SQLModel
from sqlalchemy.ext.asyncio import AsyncSession

# Set the environment variable to 'test' BEFORE importing the app
import os
os.environ['ENVIRONMENT'] = 'test'

from src.main import app
from src.db.postgresql import postgres_db
from src.db import models
from src.core.security import get_password_hash, create_access_token

# --- Core Fixtures ---
@pytest_asyncio.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for each test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[asyncio.AbstractEventLoop, None]:
    """
    Fixture to provide a database session for a test.
    This will create all tables before the test and drop them after,
    ensuring a clean slate for each test function.
    """
    # Establish connection and create tables
    async with postgres_db.engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all) # Drop first to be safe
        await conn.run_sync(SQLModel.metadata.create_all)

    # Yield the session to the test
    async with postgres_db.get_session() as session:
        yield session

    # After the test, drop all tables to ensure isolation
    async with postgres_db.engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
    
    # Dispose the engine to close all connections
    await postgres_db.engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    Fixture to provide an HTTPX client for making requests to the test app.
    It depends on db_session to ensure the database is ready.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

# --- Test User and Authentication Fixtures ---

@pytest_asyncio.fixture(scope="function")
async def test_user(db_session: AsyncSession) -> models.User:
    """Fixture to create a standard test user in the database."""
    user = models.User(
        email="test@example.com",
        full_name="Test User",
        hashed_password=get_password_hash("testpassword"),
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user

@pytest_asyncio.fixture(scope="function")
def test_user_token(test_user: models.User) -> str:
    """Fixture to create a JWT token for the test user."""
    return create_access_token(data={"sub": test_user.email})

@pytest_asyncio.fixture(scope="function")
async def authorized_client(client: AsyncClient, test_user_token: str) -> AsyncClient:
    """Fixture to provide an authenticated client."""
    client.headers["Authorization"] = f"Bearer {test_user_token}"
    return client