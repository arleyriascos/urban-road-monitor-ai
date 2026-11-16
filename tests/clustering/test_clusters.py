from datetime import UTC, datetime, timedelta

import pytest

from app.clustering.clusters import ClusterStatus, build_clusters
from app.clustering.models import ClusteringError, Detection, Severity

NOW = datetime(2026, 11, 16, 12, 0, tzinfo=UTC)
STEP = 0.00001  # about 1.1 m of latitude


def seen(
    id: int,
    lat: float,
    lon: float = -77.2811,
    severity: Severity = Severity.LEVE,
    confidence: float = 0.5,
    at: datetime = NOW,
) -> Detection:
    return Detection(id, lat, lon, severity, confidence, at)


def test_no_detections_give_no_clusters() -> None:
    assert build_clusters([], NOW) == []


def test_close_detections_make_one_confirmed_pothole() -> None:
    detections = [seen(1, 1.2136), seen(2, 1.2136 + STEP), seen(3, 1.2136 + 2 * STEP)]

    (cluster,) = build_clusters(detections, NOW)

    assert cluster.detection_ids == (1, 2, 3)
    assert cluster.count == 3
    assert cluster.status is ClusterStatus.CONFIRMED
    assert cluster.latitude == pytest.approx(1.2136 + STEP)
    assert cluster.confidence == pytest.approx(0.875)


def test_a_lone_detection_becomes_an_unconfirmed_pothole() -> None:
    (cluster,) = build_clusters([seen(7, 1.2136, confidence=0.9)], NOW)

    assert cluster.detection_ids == (7,)
    assert cluster.status is ClusterStatus.UNCONFIRMED
    assert cluster.confidence == pytest.approx(0.9)


def test_every_detection_ends_in_exactly_one_cluster() -> None:
    detections = [
        seen(1, 1.2136),
        seen(2, 1.2136 + STEP),
        seen(3, 1.2200),
        seen(4, 1.2300),
        seen(5, 1.2300 + STEP),
    ]

    clusters = build_clusters(detections, NOW)

    ids = sorted(i for c in clusters for i in c.detection_ids)
    assert ids == [1, 2, 3, 4, 5]
    assert [c.status for c in clusters] == [
        ClusterStatus.CONFIRMED,
        ClusterStatus.UNCONFIRMED,
        ClusterStatus.CONFIRMED,
    ]


def test_the_time_span_goes_from_the_first_to_the_last_sighting() -> None:
    early = NOW - timedelta(days=10)
    detections = [seen(1, 1.2136, at=NOW), seen(2, 1.2136 + STEP, at=early)]

    (cluster,) = build_clusters(detections, NOW)

    assert cluster.first_detected_at == early
    assert cluster.last_detected_at == NOW


def test_the_severity_is_voted_inside_each_cluster() -> None:
    detections = [
        seen(1, 1.2136, severity=Severity.GRAVE, confidence=0.9),
        seen(2, 1.2136 + STEP, severity=Severity.LEVE, confidence=0.3),
        seen(3, 1.2300, severity=Severity.LEVE),
    ]

    grave, leve = build_clusters(detections, NOW)

    assert grave.severity is Severity.GRAVE
    assert leve.severity is Severity.LEVE


def test_the_settings_change_what_counts_as_the_same_pothole() -> None:
    detections = [seen(1, 1.2136), seen(2, 1.2136 + 8 * STEP)]  # about 9 m apart

    assert len(build_clusters(detections, NOW, eps_m=5.0)) == 2
    assert len(build_clusters(detections, NOW, eps_m=12.0)) == 1
    assert len(build_clusters(detections, NOW, eps_m=12.0, min_points=3)) == 2


def test_the_half_life_reaches_the_confidence() -> None:
    old = seen(1, 1.2136, confidence=0.8, at=NOW - timedelta(days=30))

    (cluster,) = build_clusters([old], NOW, half_life_days=30.0)

    assert cluster.confidence == pytest.approx(0.4)


def test_repeated_ids_are_rejected() -> None:
    with pytest.raises(ClusteringError, match="unique"):
        build_clusters([seen(1, 1.2136), seen(1, 1.2200)], NOW)
