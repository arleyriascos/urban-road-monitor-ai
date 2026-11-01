import math

import pytest

from app.geo import EARTH_RADIUS_M, haversine_m

# Values calculated with the backend's own haversineDistance (src/osm/geo.ts),
# to make sure both services measure distances the same way.
BACKEND_VALUES = [
    ((1.2136, -77.2811), (1.2150, -77.2790), 280.6000628712524),
    ((1.2140, -77.2810), (1.2141, -77.2800), 111.7248352085182),
    ((0.0, 0.0), (1.0, 0.0), 111195.0802335329),
    ((1.2, -77.28), (1.3, -77.19), 14958.174149277991),
]


@pytest.mark.parametrize(("a", "b", "expected"), BACKEND_VALUES)
def test_matches_the_backend_distance(
    a: tuple[float, float], b: tuple[float, float], expected: float
) -> None:
    assert haversine_m(*a, *b) == pytest.approx(expected, rel=1e-9)


def test_distance_to_the_same_point_is_zero() -> None:
    assert haversine_m(1.2136, -77.2811, 1.2136, -77.2811) == 0.0


def test_distance_is_symmetric() -> None:
    forward = haversine_m(1.2136, -77.2811, 1.2150, -77.2790)
    backward = haversine_m(1.2150, -77.2790, 1.2136, -77.2811)

    assert forward == pytest.approx(backward, rel=1e-12)


def test_one_degree_of_latitude_is_about_111_kilometers() -> None:
    assert haversine_m(0.0, 0.0, 1.0, 0.0) == pytest.approx(
        EARTH_RADIUS_M * math.pi / 180, rel=1e-12
    )


def test_a_degree_of_longitude_is_shorter_away_from_the_equator() -> None:
    at_equator = haversine_m(0.0, 0.0, 0.0, 1.0)
    in_pasto = haversine_m(1.2, -77.0, 1.2, -76.0)

    assert in_pasto < at_equator
    assert in_pasto == pytest.approx(at_equator * math.cos(math.radians(1.2)), rel=1e-4)


def test_half_the_earth_is_the_longest_distance() -> None:
    assert haversine_m(0.0, 0.0, 0.0, 180.0) == pytest.approx(math.pi * EARTH_RADIUS_M, rel=1e-12)


def test_never_exceeds_the_antipodal_distance_because_of_rounding() -> None:
    assert haversine_m(90.0, 0.0, -90.0, 0.0) <= math.pi * EARTH_RADIUS_M * (1 + 1e-12)
