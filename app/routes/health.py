"""Health check, used by Render and by the backend to know the service is awake.

It always answers 200, even when the road graph is not loaded yet: the backend may be
asleep, and that must not make Render think this service is down.
"""

from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from app import __version__
from app.graph.store import GraphStore

router = APIRouter(tags=["health"])

SERVICE_NAME = "urban-road-monitor-ai"


class GraphStatus(BaseModel):
    """State of the road graph in memory. Nothing in it is secret."""

    model_config = ConfigDict(
        alias_generator=to_camel, validate_by_name=True, validate_by_alias=True
    )

    loaded: bool
    version: str | None = None
    nodes: int | None = None
    segments: int | None = None
    loaded_at: datetime | None = None


class HealthResponse(BaseModel):
    """Answer of the health check. It never includes settings or secrets."""

    status: Literal["ok"]
    service: str
    version: str
    graph: GraphStatus


@router.get("/health", response_model=HealthResponse)
def get_health(request: Request) -> HealthResponse:
    """Report that the service is running and whether the road graph is loaded."""
    store: GraphStore = request.app.state.graph_store
    current = store.current
    graph = (
        GraphStatus(loaded=False)
        if current is None
        else GraphStatus(
            loaded=True,
            version=current.version,
            nodes=current.node_count,
            segments=current.segment_count,
            loaded_at=current.loaded_at,
        )
    )
    return HealthResponse(status="ok", service=SERVICE_NAME, version=__version__, graph=graph)
