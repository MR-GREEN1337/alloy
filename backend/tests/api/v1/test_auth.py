import pytest
from httpx import AsyncClient
from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.db import models

@pytest.mark.asyncio
async def test_register_user(client: AsyncClient, db_session: AsyncSession):
    # Successful registration
    response = await client.post("/api/v1/auth/register", json={"email": "newuser@example.com", "password": "password123"})
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json() == {"message": "User created successfully"}

    # Verify user is in the database
    user = (await db_session.execute(select(models.User).where(models.User.email == "newuser@example.com"))).scalar_one_or_none()
    assert user is not None
    assert user.email == "newuser@example.com"

    # Test duplicate email registration
    response = await client.post("/api/v1/auth/register", json={"email": "newuser@example.com", "password": "password123"})
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Email already registered" in response.json()["detail"]

@pytest.mark.asyncio
async def test_login_for_access_token(client: AsyncClient, test_user: models.User):
    # Test successful login
    login_data = {"username": test_user.email, "password": "testpassword"}
    response = await client.post("/api/v1/auth/login", data=login_data)
    assert response.status_code == status.HTTP_200_OK
    token_data = response.json()
    assert "access_token" in token_data
    assert "refresh_token" in token_data
    assert token_data["token_type"] == "bearer"

    # Test incorrect password
    login_data["password"] = "wrongpassword"
    response = await client.post("/api/v1/auth/login", data=login_data)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

@pytest.mark.asyncio
async def test_guest_login(client: AsyncClient, db_session: AsyncSession):
    response = await client.post("/api/v1/auth/guest")
    assert response.status_code == status.HTTP_200_OK
    token_data = response.json()
    assert "access_token" in token_data
    assert "refresh_token" in token_data

    # Verify a guest user was created
    users = (await db_session.execute(select(models.User).where(models.User.email.like("guest_%@alloy.dev")))).scalars().all()
    assert len(users) > 0

@pytest.mark.asyncio
async def test_get_current_user_dependency(authorized_client: AsyncClient, test_user: models.User):
    # This endpoint doesn't exist directly, but we can test a protected endpoint that uses it.
    # Let's test the /reports/draft endpoint which is protected.
    response = await authorized_client.post("/api/v1/reports/draft")
    assert response.status_code == status.HTTP_201_CREATED
    report_data = response.json()
    assert report_data["user_id"] == test_user.id