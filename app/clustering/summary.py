"""Summaries of the detections that belong to one pothole: where it is and how bad it is."""

import math
from collections.abc import Sequence
from datetime import datetime

from app.clustering.models import ClusteringError, Detection, Severity


def centroid(detections: Sequence[Detection]) -> tuple[float, float]:
    """The average place of the detections, as (latitude, longitude).

    Longitudes are averaged as offsets from the first detection, so a group that sits
    across the 180 degree line still gets a sensible center.
    """
    if not detections:
        raise ClusteringError("cannot compute the centroid of no detections")
    first_lon = detections[0].longitude
    latitude = math.fsum(d.latitude for d in detections) / len(detections)
    offset = math.fsum(((d.longitude - first_lon + 180.0) % 360.0) - 180.0 for d in detections)
    longitude = ((first_lon + offset / len(detections) + 180.0) % 360.0) - 180.0
    return latitude, longitude


def vote_severity(detections: Sequence[Detection]) -> Severity:
    """The severity most supported by the detections, weighing each by its confidence.

    A tie goes to the worse severity: it is better to repair a pothole too early than
    to leave a bad one waiting.
    """
    if not detections:
        raise ClusteringError("cannot vote the severity of no detections")
    weight = dict.fromkeys(Severity, 0.0)
    for detection in detections:
        weight[detection.severity] += detection.confidence
    return max(Severity, key=lambda severity: (weight[severity], severity.rank))


DEFAULT_HALF_LIFE_DAYS = 30.0
"""After this many days a detection counts half as much."""

_SECONDS_PER_DAY = 86_400.0


def combined_confidence(
    detections: Sequence[Detection],
    as_of: datetime,
    half_life_days: float = DEFAULT_HALF_LIFE_DAYS,
) -> float:
    """How sure we are that the pothole exists, from 0 to 1.

    Every detection adds evidence: the chance that all of them are wrong is the product of
    the chances that each one is wrong, so the confidence is ``1 - prod(1 - c_i)``. It
    grows with each new sighting and never passes 1. A detection loses weight as it gets
    old (it halves every ``half_life_days``), so a pothole nobody sees again slowly fades.
    A detection newer than ``as_of`` counts in full.
    """
    if not detections:
        raise ClusteringError("cannot compute the confidence of no detections")
    if as_of.tzinfo is None:
        raise ClusteringError("as_of must carry a time zone")
    if not (math.isfinite(half_life_days) and half_life_days > 0):
        raise ClusteringError(f"half_life_days must be a number > 0, got {half_life_days}")
    doubt = 1.0
    for detection in detections:
        age_days = max(0.0, (as_of - detection.detected_at).total_seconds() / _SECONDS_PER_DAY)
        weight = 0.5 ** (age_days / half_life_days)
        doubt *= 1.0 - detection.confidence * weight
    return min(1.0, max(0.0, 1.0 - doubt))
