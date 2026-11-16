"""Put each pothole on the road segment it belongs to."""

from collections.abc import Sequence
from dataclasses import dataclass

from app.clustering.clusters import Cluster
from app.routing.segment_locator import SegmentLocator

DEFAULT_MAX_SEGMENT_DISTANCE_M = 25.0
"""How far from a street a pothole may be and still count as being on it.

GPS in a phone is off by several meters, and a street is wider than its center line.
"""


@dataclass(frozen=True, slots=True)
class PlacedCluster:
    """A pothole and the road segment it is on, if any is near enough."""

    cluster: Cluster
    segment_id: int | None
    distance_m: float | None
    """Distance from the pothole to the segment."""
    fraction: float | None
    """Where along the segment the pothole is: 0 at its start, 1 at its end."""


def place_clusters(
    clusters: Sequence[Cluster],
    locator: SegmentLocator | None,
    max_distance_m: float = DEFAULT_MAX_SEGMENT_DISTANCE_M,
) -> list[PlacedCluster]:
    """Find the segment of every pothole, in the same order.

    A pothole with no segment within ``max_distance_m`` keeps its place on the map but
    does not touch the cost of any street. Without a locator (no road graph) no pothole
    gets a segment.
    """
    placed: list[PlacedCluster] = []
    for cluster in clusters:
        match = (
            locator.locate(cluster.latitude, cluster.longitude, max_distance_m)
            if locator is not None
            else None
        )
        if match is None:
            placed.append(PlacedCluster(cluster, None, None, None))
        else:
            placed.append(
                PlacedCluster(cluster, match.segment_id, match.distance_m, match.fraction)
            )
    return placed
