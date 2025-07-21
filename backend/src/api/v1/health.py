from fastapi import APIRouter, status
from pydantic import BaseModel
from fastapi_simple_rate_limiter import rate_limiter
router = APIRouter()

class HealthCheck(BaseModel):
    status: str
    version: str

@router.get(
    "/",
    response_model=HealthCheck,
    status_code=status.HTTP_200_OK,
    tags=["Health"],
    summary="Perform a Health Check",
    description="Checks the operational status of the API service.",
)
@rate_limiter(limit=30, seconds=60)
def health_check(app_version: str = "1.0.0"):
    return HealthCheck(status="ok", version=app_version)