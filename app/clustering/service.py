"""Answers a clustering request: group the detections and put each pothole on its street.

Coordinates are rounded to 7 decimals (about a centimeter), confidences and fractions to
four decimals and distances to centimeters.
"""

import logging
import time
from datetime import UTC, datetime

from app.clustering.clusters import build_clusters
from app.clustering.contract import ClusterOut, ClusterRequest, ClusterResponse
from app.clustering.models import ClusteringError, Detection
from app.clustering.placement import PlacedCluster, place_clusters
from app.config import Settings
from app.errors import ApiError
from app.graph.store import GraphStore, GraphUnavailableError, LoadedGraph

logger = logging.getLogger(__name__)


class ClusterService:
    def __init__(self, store: GraphStore, settings: Settings) -> None:
        self._store = store
        self._settings = settings

    def cluster(self, request: ClusterRequest) -> ClusterResponse:
        settings = self._settings
        if len(request.detections) > settings.cluster_max_detections:
            raise ApiError(
                422,
                "TOO_MANY_DETECTIONS",
                f"A request may carry at most {settings.cluster_max_detections} detections",
                details={
                    "received": len(request.detections),
                    "limit": settings.cluster_max_detections,
                },
            )
        ids = [d.id for d in request.detections]
        if len(set(ids)) != len(ids):
            raise ApiError(422, "DUPLICATE_DETECTION_ID", "Detection ids must be unique")

        as_of = request.as_of if request.as_of is not None else datetime.now(UTC)
        eps_m = request.eps_m if request.eps_m is not None else settings.cluster_eps_m
        min_points = (
            request.min_points if request.min_points is not None else settings.cluster_min_points
        )
        loaded = self._graph_for(request.graph_version)

        started = time.perf_counter()
        try:
            detections = [
                Detection(d.id, d.latitude, d.longitude, d.severity, d.confidence, d.detected_at)
                for d in request.detections
            ]
            clusters = build_clusters(
                detections, as_of, eps_m, min_points, settings.cluster_half_life_days
            )
        except ClusteringError as error:
            raise ApiError(422, "INVALID_REQUEST", str(error)) from error
        placed = place_clusters(
            clusters,
            loaded.segment_locator if loaded is not None else None,
            settings.cluster_max_segment_distance_m,
        )
        computation_ms = round((time.perf_counter() - started) * 1000)

        return ClusterResponse(
            graph_version=loaded.version if loaded is not None else None,
            as_of=as_of,
            eps_m=eps_m,
            min_points=min_points,
            detection_count=len(detections),
            cluster_count=len(placed),
            confirmed_count=sum(1 for p in placed if p.cluster.count >= min_points),
            placed_count=sum(1 for p in placed if p.segment_id is not None),
            computation_ms=computation_ms,
            clusters=[_to_out(p) for p in placed],
        )

    def _graph_for(self, graph_version: str | None) -> LoadedGraph | None:
        """The graph that places the potholes, or None: without it they are still clustered."""
        if graph_version is None:
            return None
        try:
            return self._store.get(graph_version)
        except GraphUnavailableError:
            logger.warning("clustering without segments: the road graph is not available")
            return None


def _to_out(placed: PlacedCluster) -> ClusterOut:
    cluster = placed.cluster
    return ClusterOut(
        detection_ids=list(cluster.detection_ids),
        count=cluster.count,
        latitude=round(cluster.latitude, 7),
        longitude=round(cluster.longitude, 7),
        severity=cluster.severity,
        confidence=round(cluster.confidence, 4),
        status=cluster.status,
        segment_id=placed.segment_id,
        segment_distance_m=None if placed.distance_m is None else round(placed.distance_m, 2),
        segment_fraction=None if placed.fraction is None else round(placed.fraction, 4),
        first_detected_at=cluster.first_detected_at,
        last_detected_at=cluster.last_detected_at,
    )
