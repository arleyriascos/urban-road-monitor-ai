"""Summaries of the detections that belong to one pothole: where it is and how bad it is."""

import math
from collections.abc import Sequence

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
