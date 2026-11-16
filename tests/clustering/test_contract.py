import math

import pytest
from pydantic import ValidationError

from app.clustering.contract import ClusterRequest, DetectionIn
from app.clustering.models import Severity

DETECTION = {
    "id": 5,
    "latitude": 1.2136,
    "longitude": -77.2811,
    "severity": "grave",
    "confidence": 0.9,
    "detectedAt": "2026-11-16T12:00:00Z",
}


def test_a_detection_in_camel_case_is_read() -> None:
    detection = DetectionIn.model_validate(DETECTION)

    assert detection.id == 5
    assert detection.severity is Severity.GRAVE
    assert detection.detected_at.utcoffset() is not None


def test_a_request_only_needs_the_detections() -> None:
    request = ClusterRequest.model_validate({"detections": [DETECTION]})

    assert request.graph_version is None
    assert request.as_of is None
    assert request.eps_m is None
    assert request.min_points is None


def test_an_empty_list_of_detections_is_valid() -> None:
    assert ClusterRequest.model_validate({"detections": []}).detections == []


@pytest.mark.parametrize(
    "changes",
    [
        {"latitude": 91},
        {"longitude": -181},
        {"latitude": math.nan},
        {"confidence": 1.5},
        {"confidence": -0.1},
        {"severity": "critico"},
        {"detectedAt": "2026-11-16T12:00:00"},
        {"detectedAt": "yesterday"},
        {"id": "x"},
        {"extra": 1},
    ],
)
def test_a_bad_detection_is_rejected(changes: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        DetectionIn.model_validate({**DETECTION, **changes})


@pytest.mark.parametrize(
    "changes",
    [
        {"epsM": 0},
        {"epsM": 5000},
        {"minPoints": 0},
        {"graphVersion": ""},
        {"asOf": "2026-11-16T12:00:00"},
        {"unknown": True},
    ],
)
def test_a_bad_setting_is_rejected(changes: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        ClusterRequest.model_validate({"detections": [], **changes})
