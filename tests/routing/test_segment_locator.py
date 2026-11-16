import math
import random

import pytest

from app.geo import project_on_polyline
from app.routing.segment_locator import SegmentLocator, SegmentLocatorError

STEP = 0.00001  # about 1.1 meters of latitude

Point = tuple[float, float]


def street_north(lat: float, lon: float, meters: int) -> list[Point]:
    return [(lat, lon), (lat + meters * STEP, lon)]


def test_a_place_on_a_segment_finds_it_with_distance_zero() -> None:
    locator = SegmentLocator({7: street_north(1.2, -77.3, 100)})

    match = locator.locate(1.2 + 50 * STEP, -77.3, 10.0)

    assert match is not None
    assert match.segment_id == 7
    assert match.distance_m == pytest.approx(0.0, abs=0.01)
    assert match.fraction == pytest.approx(0.5, abs=0.01)


def test_the_nearest_of_two_streets_wins() -> None:
    locator = SegmentLocator(
        {1: street_north(1.2, -77.3, 100), 2: street_north(1.2, -77.3 + 0.0002, 100)}
    )

    near_second = locator.locate(1.2 + 40 * STEP, -77.3 + 0.00018, 50.0)
    near_first = locator.locate(1.2 + 40 * STEP, -77.3 + 0.00003, 50.0)

    assert near_second is not None and near_second.segment_id == 2
    assert near_first is not None and near_first.segment_id == 1


def test_a_place_farther_than_the_limit_has_no_segment() -> None:
    locator = SegmentLocator({1: street_north(1.2, -77.3, 100)})

    assert locator.locate(1.2, -77.3 + 0.001, 20.0) is None  # about 110 m away
    assert locator.locate(1.2, -77.3 + 0.001, 200.0) is not None


def test_a_tie_goes_to_the_lowest_segment_id() -> None:
    line = street_north(1.2, -77.3, 100)
    locator = SegmentLocator({9: line, 3: line, 5: line})

    match = locator.locate(1.2 + 30 * STEP, -77.3 + 0.00005, 100.0)

    assert match is not None
    assert match.segment_id == 3


def test_a_segment_of_one_point_is_a_point() -> None:
    locator = SegmentLocator({1: [(1.2, -77.3)]})

    match = locator.locate(1.2 + 3 * STEP, -77.3, 10.0)

    assert match is not None
    assert match.distance_m == pytest.approx(3.3, abs=0.1)


def test_the_answer_is_the_same_as_measuring_every_segment() -> None:
    rng = random.Random(21)
    lines: dict[int, list[Point]] = {}
    for segment_id in range(1, 301):
        lat = 1.2 + rng.uniform(0, 0.01)
        lon = -77.3 + rng.uniform(0, 0.01)
        corners = rng.randint(2, 5)
        lines[segment_id] = [
            (lat + rng.uniform(-0.0008, 0.0008), lon + rng.uniform(-0.0008, 0.0008))
            for _ in range(corners)
        ]
    locator = SegmentLocator(lines)

    for _ in range(300):
        lat = 1.2 + rng.uniform(-0.001, 0.011)
        lon = -77.3 + rng.uniform(-0.001, 0.011)
        limit = rng.choice([5.0, 30.0, 150.0])
        expected = min(
            (project_on_polyline(lat, lon, line).distance_m, segment_id)
            for segment_id, line in lines.items()
        )
        match = locator.locate(lat, lon, limit)
        if expected[0] > limit:
            assert match is None
        else:
            assert match is not None
            assert match.segment_id == expected[1]
            assert match.distance_m == pytest.approx(expected[0])


def test_settings_are_checked() -> None:
    with pytest.raises(SegmentLocatorError, match="at least one"):
        SegmentLocator({})
    with pytest.raises(SegmentLocatorError, match="has no points"):
        SegmentLocator({4: []})
    with pytest.raises(SegmentLocatorError, match="step_m"):
        SegmentLocator({1: [(1.2, -77.3)]}, step_m=0.0)
    locator = SegmentLocator({1: [(1.2, -77.3)]})
    with pytest.raises(SegmentLocatorError, match="max_distance_m"):
        locator.locate(1.2, -77.3, -1.0)
    with pytest.raises(SegmentLocatorError, match="max_distance_m"):
        locator.locate(1.2, -77.3, math.nan)
