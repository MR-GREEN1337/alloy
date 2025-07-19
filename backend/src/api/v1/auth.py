from fastapi import APIRouter, Depends, HTTPException, status, Request, Header
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from typing import Annotated, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from urllib.parse import urlencode, urlparse
import httpx
from loguru import logger
import uuid
import random

from fastapi_simple_rate_limiter import rate_limiter
from src.core.security import (
    create_access_token,
    create_refresh_token,
    verify_password,
    get_password_hash,
    decode_token,
    get_user_by_email
)
from src.core.settings import get_settings
from src.db.postgresql import get_session
from src.db import models
from pydantic import BaseModel

settings = get_settings()
router = APIRouter()

# --- Pydantic Models ---
class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str

class TokenRefreshRequest(BaseModel):
    refresh_token: str
    
class TokenRefreshResponse(BaseModel):
    access_token: str
    token_type: str

class UserCreate(BaseModel):
    email: str
    password: str

# --- OAuth2 Provider Constants ---
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"
GOOGLE_SCOPES = "openid email profile"

# --- Guest Mode Constants ---
GUEST_NAMES = [
    "Curious Capybara", "Analytical Aardvark", "Synergy Shark", 
    "Due Diligence Duck", "Strategic Squirrel", "Data-driven Dingo"
]

# --- Helper Function ---
def get_backend_base_url() -> str:
    """
    Determines the backend's base URL. In production, it uses the first
    CORS origin (which should be the frontend URL) to derive the backend URL,
    ensuring the correct scheme (https://) and domain.
    """
    # In a production/staging environment, trust the CORS origin setting.
    # This assumes the frontend and backend are on the same domain.
    # e.g., web is on https://alloy.app, backend is on https://alloy.app
    if settings.ENVIRONMENT != "development":
        # We assume the first CORS origin is the primary frontend URL.
        # e.g., https://alloy-web-*.run.app
        frontend_url = settings.CORS_ORIGINS[0]
        parsed_uri = urlparse(frontend_url)
        # We derive the backend URL from the web URL. This is a common pattern
        # when they are hosted on subdomains of the same parent service.
        # This part might need adjustment based on your specific CNAME/DNS setup.
        # For Cloud Run, this simple replacement is often sufficient if you use a similar naming convention.
        backend_host = parsed_uri.hostname.replace("web", "backend") if parsed_uri.hostname else "localhost"
        return f"https://{backend_host}"
    
    # In development, you might be running on http://localhost:8000
    # A more robust solution for dev would be to use an env var.
    # For now, we will construct it simply.
    return "http://localhost:8000"


async def create_user_if_not_exists(session: AsyncSession, user_data: Dict[str, Any]) -> models.User:
    db_user = await get_user_by_email(session, user_data["email"])
    if db_user:
        return db_user
    
    # CORE FIX: Instantiate the model directly instead of using model_validate.
    # This allows the database to apply the server_default for created_at and updated_at.
    new_user = models.User(**user_data)
    
    try:
        session.add(new_user)
        await session.commit()
        await session.refresh(new_user)
        logger.info(f"New user created via SSO: {new_user.email}")
        return new_user
    except Exception as e:
        await session.rollback()
        logger.error(f"Error during SSO user creation for {user_data['email']}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not create user account."
        )


# --- API Endpoints ---
DBSession = Annotated[AsyncSession, Depends(get_session)]

@router.post("/register", status_code=status.HTTP_201_CREATED)
@rate_limiter(limit=30, seconds=60)
async def register_user(user_create: UserCreate, session: DBSession):
    if await get_user_by_email(session, user_create.email):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Email already registered")
    
    new_user = models.User(
        email=user_create.email, 
        hashed_password=get_password_hash(user_create.password)
    )
    session.add(new_user)
    await session.commit()
    return {"message": "User created successfully"}

@router.post("/login", response_model=Token)
@rate_limiter(limit=30, seconds=60)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()], 
    session: DBSession
):
    user = await get_user_by_email(session, form_data.username)
    if not user or not user.hashed_password or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Incorrect email or password",
            {"WWW-Authenticate": "Bearer"},
        )
    
    token_data = {"sub": user.email, "full_name": user.full_name}
    return Token(
        access_token=create_access_token(data=token_data),
        refresh_token=create_refresh_token(data=token_data),
        token_type="bearer"
    )

@router.post("/refresh", response_model=TokenRefreshResponse)
@rate_limiter(limit=30, seconds=60)
async def refresh_access_token(
    refresh_request: TokenRefreshRequest,
    session: DBSession
):
    token_data = decode_token(refresh_request.refresh_token)
    if not token_data or "sub" not in token_data:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token")
    
    user = await get_user_by_email(session, token_data["sub"])
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")

    new_token_data = {"sub": user.email, "full_name": user.full_name}
    return TokenRefreshResponse(
        access_token=create_access_token(data=new_token_data),
        token_type="bearer"
    )

@router.get("/google/authorize", tags=["auth"], response_class=RedirectResponse)
async def google_authorize(request: Request):
    # THE FIX: Use the request's own headers to determine the base URL
    # This correctly handles https and the domain from behind a proxy.
    # Cloud Run provides X-Forwarded-Proto and X-Forwarded-Host headers.
    scheme = request.headers.get("x-forwarded-proto", "http")
    host = request.headers.get("x-forwarded-host", request.url.netloc)
    
    # Construct the base URL and the final redirect URI
    base_url = f"{scheme}://{host}"
    redirect_uri = f"{base_url}/api/v1/auth/google/callback"
    
    logger.info(f"Generated Google redirect URI: {redirect_uri}")

    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": GOOGLE_SCOPES,
        "access_type": "offline",
        "prompt": "consent",
    }
    auth_url = f"{GOOGLE_AUTH_URL}?{urlencode(params)}"
    return RedirectResponse(auth_url)


@router.get("/google/callback", tags=["auth"], response_class=RedirectResponse)
@rate_limiter(limit=30, seconds=60)
async def google_callback(
    request: Request, code: str, session: DBSession
):
    """Handles the callback from Google, exchanges code for token, and gets user info."""
    # THE FIX: Reconstruct the redirect_uri exactly as it was in the authorize step.
    scheme = request.headers.get("x-forwarded-proto", "http")
    host = request.headers.get("x-forwarded-host", request.url.netloc)
    base_url = f"{scheme}://{host}"
    redirect_uri = f"{base_url}/api/v1/auth/google/callback"

    logger.info(f"Handling Google callback for redirect URI: {redirect_uri}")

    token_data = {
        "code": code,
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }
    
    async with httpx.AsyncClient() as client:
        token_response = await client.post(GOOGLE_TOKEN_URL, data=token_data)
        if token_response.status_code != 200:
            logger.error(f"Google token exchange FAILED. Status: {token_response.status_code}, Response: {token_response.json()}")
            raise HTTPException(status_code=400, detail="Could not exchange token with Google.")
        
        access_token_ext = token_response.json().get("access_token")

        user_info_response = await client.get(
            GOOGLE_USERINFO_URL, headers={"Authorization": f"Bearer {access_token_ext}"}
        )
        if user_info_response.status_code != 200:
            logger.error(f"Google user info fetch FAILED: {user_info_response.json()}")
            raise HTTPException(status_code=400, detail="Could not retrieve user info from Google.")
        
        user_info = user_info_response.json()

    email = user_info.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="No email returned from Google.")

    user = await create_user_if_not_exists(session, {"email": email, "full_name": user_info.get("name")})
    
    access_token = create_access_token(data={"sub": user.email, "full_name": user.full_name})
    refresh_token = create_refresh_token(data={"sub": user.email})

    params = urlencode({"access_token": access_token, "refresh_token": refresh_token})
    # Use the first CORS origin as the definitive frontend URL to redirect back to.
    frontend_redirect_url = f"{settings.CORS_ORIGINS[0]}/token?{params}"
    
    return RedirectResponse(url=frontend_redirect_url)

@router.post("/guest", response_model=Token, tags=["auth"])
async def guest_login(session: DBSession):
    """Creates a temporary guest user and returns auth tokens. For the sake of demo, guest users are created with random names and emails."""
    guest_email = f"guest_{uuid.uuid4()}@alloy.dev"
    guest_name = random.choice(GUEST_NAMES)
    
    logger.info(f"Creating new guest user: {guest_name} ({guest_email})")
    
    # Guest users don't have passwords
    guest_user = models.User(
        email=guest_email,
        full_name=guest_name,
        is_active=True, 
        hashed_password=None
    )
    
    try:
        session.add(guest_user)
        await session.commit()
        await session.refresh(guest_user)
    except Exception as e:
        await session.rollback()
        logger.error(f"Error creating guest user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not create guest account."
        )

    token_data = {"sub": guest_user.email, "full_name": guest_user.full_name}
    return Token(
        access_token=create_access_token(data=token_data),
        refresh_token=create_refresh_token(data=token_data),
        token_type="bearer"
    )

async def get_current_user(
    token: Annotated[str, Header(alias="Authorization")],
    session: DBSession,
) -> models.User:
    if not token.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
    
    token = token.split(" ")[1]
    token_data = decode_token(token)
    if not token_data or "sub" not in token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = await get_user_by_email(session, email=token_data["sub"])
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    return user