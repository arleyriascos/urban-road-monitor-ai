"""Health check, used by Render and by the backend to know the service is awake."""

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

from app import __version__

router = APIRouter(tags=["health"])

SERVICE_NAME = "urban-road-monitor-ai"


class HealthResponse(BaseModel):
    """Answer of the health check. It never includes settings or secrets."""

    status: Literal["ok"]
    service: str
    version: str


@router.get("/health", response_model=HealthResponse)
def get_health() -> HealthResponse:
    """Report that the service is running."""
    return HealthResponse(status="ok", service=SERVICE_NAME, version=__version__)
