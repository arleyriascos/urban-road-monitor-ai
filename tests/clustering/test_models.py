import math
from datetime import UTC, datetime

import pytest

from app.clustering.models import ClusteringError, Detection, Severity

NOW = datetime(2026, 11, 16, 12, 0, tzinfo=UTC)


def make(**changes: object) -> Detection:
    values: dict[str, object] = {
        "id": 1,
        "latitude": 1.2136,
        "longitude": -77.2811,
        "severity": Severity.MODERADO,
        "confidence": 0.8,
        "detected_at": NOW,
    }
    values.update(changes)
    return Detection(**values)  # type: ignore[arg-type]


def test_a_valid_detection_keeps_its_data() -> None:
    detection = make()

    assert detection.id == 1
    assert detection.severity is Severity.MODERADO
    assert detection.detected_at == NOW


def test_severities_are_ranked_from_leve_to_grave() -> None:
    assert [s.rank for s in (Severity.LEVE, Severity.MODERADO, Severity.GRAVE)] == [0, 1, 2]
    assert Severity("grave") is Severity.GRAVE


def test_an_unknown_severity_is_not_accepted() -> None:
    with pytest.raises(ValueError, match="critico"):
        Severity("critico")


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"latitude": 91.0}, "latitude"),
        ({"latitude": math.nan}, "latitude"),
        ({"longitude": -181.0}, "longitude"),
        ({"longitude": math.inf}, "longitude"),
        ({"confidence": 1.01}, "confidence"),
        ({"confidence": -0.1}, "confidence"),
        ({"confidence": math.nan}, "confidence"),
        ({"detected_at": datetime(2026, 11, 16, 12, 0)}, "time zone"),
    ],
)
def test_an_invalid_detection_is_rejected_and_says_which_one(
    changes: dict[str, object], message: str
) -> None:
    with pytest.raises(ClusteringError, match=f"detection 1.*{message}"):
        make(**changes)


def test_the_limits_of_the_ranges_are_valid() -> None:
    make(latitude=90.0, longitude=180.0, confidence=1.0)
    make(latitude=-90.0, longitude=-180.0, confidence=0.0)
