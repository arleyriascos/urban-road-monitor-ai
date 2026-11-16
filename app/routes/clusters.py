"""POST /clusters: group the detections into potholes, for the backend only."""

from typing import Any

from fastapi import APIRouter, Depends, Request, Response

from app.clustering.contract import ClusterRequest, ClusterResponse
from app.clustering.service import ClusterService
from app.routing.contract import ErrorResponse
from app.security import require_internal_token

# The token is checked before the body, so a request without it learns nothing else.
router = APIRouter(tags=["clusters"], dependencies=[Depends(require_internal_token)])

_ERRORS: dict[int | str, dict[str, Any]] = {
    401: {"model": ErrorResponse, "description": "UNAUTHORIZED: the token is missing or wrong"},
    404: {"model": ErrorResponse, "description": "NOT_FOUND when INTERNAL_TOKEN is not configured"},
    422: {
        "model": ErrorResponse,
        "description": "INVALID_REQUEST, TOO_MANY_DETECTIONS or DUPLICATE_DETECTION_ID",
    },
}


@router.post(
    "/clusters",
    response_model=ClusterResponse,
    responses=_ERRORS,
    summary="Group the detections into potholes",
)
def post_clusters(body: ClusterRequest, request: Request, response: Response) -> ClusterResponse:
    """Group the detections with DBSCAN and put each pothole on its road segment.

    The service keeps nothing: the backend sends every detection it wants grouped and
    stores what comes back. A plain function on purpose, so FastAPI runs it in a worker
    thread and the clustering does not block other requests.
    """
    response.headers["Cache-Control"] = "no-store"
    service: ClusterService = request.app.state.cluster_service
    return service.cluster(body)
