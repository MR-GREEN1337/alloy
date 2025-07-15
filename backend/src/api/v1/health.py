from fastapi import APIRouter, status
from pydantic import BaseModel

router = APIRouter()

class HealthCheck(BaseModel):
    status: str
    version: str

@router.get(
    "/health",
    response_model=HealthCheck,
    status_code=status.HTTP_200_OK,
    tags=["Health"],
    summary="Perform a Health Check",
    description="Checks the operational status of the API service.",
)
def health_check(app_version: str = "0.1.0"):
    return HealthCheck(status="ok", version=app_version)