"""POST /routes: the cheapest route between two clicked points, for the backend only."""

from typing import Any

from fastapi import APIRouter, Depends, Request, Response

from app.routing.contract import ErrorResponse, RouteRequest, RouteResponse
from app.routing.service import RouteService
from app.security import require_internal_token

# The token is checked before the body, so a request without it learns nothing else.
router = APIRouter(tags=["routes"], dependencies=[Depends(require_internal_token)])

_ERRORS: dict[int | str, dict[str, Any]] = {
    401: {"model": ErrorResponse, "description": "UNAUTHORIZED: the token is missing or wrong"},
    404: {
        "model": ErrorResponse,
        "description": "NO_ROUTE, or NOT_FOUND when INTERNAL_TOKEN is not configured",
    },
    422: {"model": ErrorResponse, "description": "OUTSIDE_NETWORK or INVALID_REQUEST"},
    503: {"model": ErrorResponse, "description": "GRAPH_UNAVAILABLE: no road graph is loaded"},
}


@router.post(
    "/routes",
    response_model=RouteResponse,
    responses=_ERRORS,
    summary="Cheapest route between two clicked points",
)
def post_route(body: RouteRequest, request: Request, response: Response) -> RouteResponse:
    """Snap both points to the road network and search with A* (or Dijkstra).

    A plain function on purpose: FastAPI runs it in a worker thread, and the graph store
    uses a lock so simultaneous requests share one download of the graph.
    """
    response.headers["Cache-Control"] = "no-store"
    service: RouteService = request.app.state.route_service
    return service.find_route(body)
