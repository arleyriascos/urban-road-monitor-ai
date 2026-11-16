from datetime import UTC, datetime, timedelta

import pytest

from app.clustering.models import ClusteringError, Detection, Severity
from app.clustering.summary import centroid, combined_confidence, vote_severity

NOW = datetime(2026, 11, 16, 12, 0, tzinfo=UTC)


def seen(
    lat: float = 1.2136,
    lon: float = -77.2811,
    severity: Severity = Severity.LEVE,
    confidence: float = 0.8,
    id: int = 1,
    at: datetime = NOW,
) -> Detection:
    return Detection(id, lat, lon, severity, confidence, at)


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


def test_the_confidence_of_one_fresh_detection_is_its_own() -> None:
    assert combined_confidence([seen(confidence=0.7)], NOW) == pytest.approx(0.7)


def test_each_new_detection_raises_the_confidence() -> None:
    one = combined_confidence([seen(confidence=0.5)], NOW)
    two = combined_confidence([seen(confidence=0.5, id=1), seen(confidence=0.5, id=2)], NOW)
    three = combined_confidence([seen(confidence=0.5, id=i) for i in range(3)], NOW)

    assert one < two < three < 1.0
    assert two == pytest.approx(0.75)
    assert three == pytest.approx(0.875)


def test_a_sure_detection_makes_the_confidence_one() -> None:
    assert combined_confidence([seen(confidence=1.0), seen(confidence=0.2, id=2)], NOW) == 1.0


def test_a_detection_loses_half_its_weight_after_the_half_life() -> None:
    old = seen(confidence=0.8, at=NOW - timedelta(days=30))

    assert combined_confidence([old], NOW) == pytest.approx(0.4)
    assert combined_confidence([old], NOW, half_life_days=15.0) == pytest.approx(0.2)


def test_an_old_pothole_fades_but_a_new_sighting_brings_it_back() -> None:
    old = seen(confidence=0.8, at=NOW - timedelta(days=90), id=1)
    new = seen(confidence=0.8, at=NOW, id=2)

    assert combined_confidence([old], NOW) < 0.1
    assert combined_confidence([old, new], NOW) > combined_confidence([new], NOW)


def test_a_detection_from_the_future_counts_in_full() -> None:
    future = seen(confidence=0.6, at=NOW + timedelta(days=5))

    assert combined_confidence([future], NOW) == pytest.approx(0.6)


def test_the_confidence_does_not_depend_on_the_order() -> None:
    detections = [seen(confidence=0.3, at=NOW - timedelta(days=i * 7), id=i) for i in range(1, 6)]

    assert combined_confidence(detections, NOW) == pytest.approx(
        combined_confidence(detections[::-1], NOW)
    )


@pytest.mark.parametrize("half_life", [0.0, -3.0, float("nan"), float("inf")])
def test_the_half_life_must_be_a_positive_number_of_days(half_life: float) -> None:
    with pytest.raises(ClusteringError, match="half_life_days"):
        combined_confidence([seen()], NOW, half_life_days=half_life)


def test_the_confidence_needs_detections_and_a_time_zone() -> None:
    with pytest.raises(ClusteringError, match="confidence"):
        combined_confidence([], NOW)
    with pytest.raises(ClusteringError, match="as_of"):
        combined_confidence([seen()], datetime(2026, 11, 16))
