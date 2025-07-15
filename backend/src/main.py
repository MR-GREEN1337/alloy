from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.settings import get_settings
from src.api.v1 import router as api_router
from src.utils import lifespan

settings = get_settings()

# --- FastAPI App Initialization ---
app = FastAPI(
    title="Alloy API",
    version="1.0.0",
    description="Backend services for the Alloy Cultural Due Diligence Platform.",
    lifespan=lifespan,
)

# --- CORS Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- API Routers ---
app.include_router(api_router, prefix="/api/v1", tags=["System"])