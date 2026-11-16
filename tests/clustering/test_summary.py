from datetime import UTC, datetime

import pytest

from app.clustering.models import ClusteringError, Detection, Severity
from app.clustering.summary import centroid, vote_severity

NOW = datetime(2026, 11, 16, 12, 0, tzinfo=UTC)


def seen(
    lat: float = 1.2136,
    lon: float = -77.2811,
    severity: Severity = Severity.LEVE,
    confidence: float = 0.8,
    id: int = 1,
) -> Detection:
    return Detection(id, lat, lon, severity, confidence, NOW)


def test_the_centroid_of_one_detection_is_that_detection() -> None:
    assert centroid([seen(1.5, -77.5)]) == pytest.approx((1.5, -77.5))


def test_the_centroid_is_the_average_place() -> None:
    result = centroid([seen(1.0, -77.0), seen(2.0, -78.0), seen(3.0, -76.0)])

    assert result == pytest.approx((2.0, -77.0))


def test_the_centroid_works_across_the_180_degree_line() -> None:
    lat, lon = centroid([seen(0.0, 179.9999), seen(0.0, -179.9999)])

    assert lat == 0.0
    assert abs(abs(lon) - 180.0) < 1e-3


def test_the_centroid_of_no_detections_is_an_error() -> None:
    with pytest.raises(ClusteringError, match="centroid"):
        centroid([])


def test_the_severity_is_the_one_with_most_confidence_behind_it() -> None:
    detections = [
        seen(severity=Severity.LEVE, confidence=0.5, id=1),
        seen(severity=Severity.LEVE, confidence=0.5, id=2),
        seen(severity=Severity.GRAVE, confidence=0.9, id=3),
    ]

    assert vote_severity(detections) is Severity.LEVE


def test_one_sure_detection_can_outweigh_two_unsure_ones() -> None:
    detections = [
        seen(severity=Severity.LEVE, confidence=0.4, id=1),
        seen(severity=Severity.LEVE, confidence=0.4, id=2),
        seen(severity=Severity.MODERADO, confidence=0.95, id=3),
    ]

    assert vote_severity(detections) is Severity.MODERADO


def test_a_tie_goes_to_the_worse_severity() -> None:
    detections = [
        seen(severity=Severity.LEVE, confidence=0.5, id=1),
        seen(severity=Severity.MODERADO, confidence=0.5, id=2),
    ]

    assert vote_severity(detections) is Severity.MODERADO


def test_a_group_without_any_confidence_still_has_a_severity() -> None:
    detections = [
        seen(severity=Severity.LEVE, confidence=0.0, id=1),
        seen(severity=Severity.GRAVE, confidence=0.0, id=2),
    ]

    assert vote_severity(detections) is Severity.GRAVE


def test_the_order_of_the_detections_does_not_change_the_vote() -> None:
    detections = [
        seen(severity=Severity.LEVE, confidence=0.6, id=1),
        seen(severity=Severity.MODERADO, confidence=0.6, id=2),
        seen(severity=Severity.GRAVE, confidence=0.3, id=3),
    ]

    assert vote_severity(detections) is vote_severity(detections[::-1])


def test_the_severity_of_no_detections_is_an_error() -> None:
    with pytest.raises(ClusteringError, match="severity"):
        vote_severity([])
