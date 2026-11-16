import math

import pytest
from pydantic import ValidationError

from app.graph.payload import GraphSegmentIn

BASE = {
    "id": 1,
    "fromNodeId": 10,
    "toNodeId": 11,
    "lengthM": 55.0,
    "damageScore": 0.2,
    "isOneway": False,
}


def test_a_segment_without_geometry_is_still_valid() -> None:
    segment = GraphSegmentIn.model_validate(BASE)

    assert segment.geometry is None


def test_a_segment_keeps_the_geometry_it_receives() -> None:
    segment = GraphSegmentIn.model_validate(
        {**BASE, "geometry": [[1.2, -77.3], [1.2001, -77.3], [1.2001, -77.2999]]}
    )

    assert segment.geometry == [(1.2, -77.3), (1.2001, -77.3), (1.2001, -77.2999)]


@pytest.mark.parametrize(
    "geometry",
    [
        [],
        [[1.2, -77.3]],
        [[91.0, -77.3], [1.2, -77.3]],
        [[1.2, -77.3], [1.2, -181.0]],
        [[1.2, -77.3], [1.2]],
        [[1.2, -77.3], [1.2, "x"]],
        [[1.2, -77.3], [math.nan, -77.3]],
    ],
)
def test_a_bad_geometry_is_rejected(geometry: object) -> None:
    with pytest.raises(ValidationError):
        GraphSegmentIn.model_validate({**BASE, "geometry": geometry})


def test_a_very_long_geometry_is_rejected() -> None:
    points = [[1.2 + i * 1e-6, -77.3] for i in range(2001)]

    with pytest.raises(ValidationError):
        GraphSegmentIn.model_validate({**BASE, "geometry": points})
