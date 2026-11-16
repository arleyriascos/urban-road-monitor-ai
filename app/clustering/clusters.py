"""Turn the detections into potholes: one cluster per pothole, with its summary."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from app.clustering.dbscan import NOISE, dbscan
from app.clustering.models import ClusteringError, Detection, Severity
from app.clustering.summary import (
    DEFAULT_HALF_LIFE_DAYS,
    centroid,
    combined_confidence,
    vote_severity,
)

DEFAULT_EPS_M = 5.0
"""Detections closer than this are the same pothole."""

DEFAULT_MIN_POINTS = 2
"""How many detections make a pothole confirmed."""


class ClusterStatus(StrEnum):
    """Whether more than one sighting backs the pothole."""

    CONFIRMED = "confirmed"
    UNCONFIRMED = "unconfirmed"


@dataclass(frozen=True, slots=True)
class Cluster:
    """One pothole, built from the detections that point at it."""

    detection_ids: tuple[int, ...]
    latitude: float
    longitude: float
    severity: Severity
    confidence: float
    status: ClusterStatus
    first_detected_at: datetime
    last_detected_at: datetime

    @property
    def count(self) -> int:
        """How many detections back this pothole."""
        return len(self.detection_ids)


def build_clusters(
    detections: Sequence[Detection],
    as_of: datetime,
    eps_m: float = DEFAULT_EPS_M,
    min_points: int = DEFAULT_MIN_POINTS,
    half_life_days: float = DEFAULT_HALF_LIFE_DAYS,
) -> list[Cluster]:
    """Group the detections into potholes.

    Detections that DBSCAN joins form a confirmed pothole. A detection that nobody else
    confirms is not thrown away: it becomes an unconfirmed pothole of its own, because a
    lone sighting may be real and the next trip that passes there will confirm it.
    Clusters come out in the order DBSCAN finds them, lone detections after the group
    that precedes them in the input.
    """
    if len({d.id for d in detections}) != len(detections):
        raise ClusteringError("detection ids must be unique")
    labels = dbscan([(d.latitude, d.longitude) for d in detections], eps_m, min_points)
    groups: dict[int, list[Detection]] = {}
    next_single = -1
    for detection, label in zip(detections, labels, strict=True):
        if label == NOISE:
            groups[next_single] = [detection]
            next_single -= 1
        else:
            groups.setdefault(label, []).append(detection)
    clusters = [_summarize(group, as_of, half_life_days) for group in groups.values()]
    return clusters


def _summarize(group: list[Detection], as_of: datetime, half_life_days: float) -> Cluster:
    latitude, longitude = centroid(group)
    times = [d.detected_at for d in group]
    return Cluster(
        detection_ids=tuple(d.id for d in group),
        latitude=latitude,
        longitude=longitude,
        severity=vote_severity(group),
        confidence=combined_confidence(group, as_of, half_life_days),
        status=ClusterStatus.CONFIRMED if len(group) >= 2 else ClusterStatus.UNCONFIRMED,
        first_detected_at=min(times),
        last_detected_at=max(times),
    )
