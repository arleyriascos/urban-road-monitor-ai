import itertools
import math
import random

import pytest

from app.geo import (
    EARTH_RADIUS_M,
    bounding_box,
    haversine_m,
    min_distance_to_box_m,
    project_on_polyline,
    project_on_segment,
    sample_polyline,
)

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


def test_bounding_box_of_a_zero_radius_is_the_point_itself() -> None:
    assert bounding_box(1.2136, -77.2811, 0.0) == (1.2136, -77.2811, 1.2136, -77.2811)


def test_bounding_box_is_about_the_radius_in_every_direction() -> None:
    min_lat, min_lon, max_lat, max_lon = bounding_box(1.2136, -77.2811, 5.0)

    assert haversine_m(1.2136, -77.2811, max_lat, -77.2811) == pytest.approx(5.0, rel=1e-6)
    assert haversine_m(1.2136, -77.2811, min_lat, -77.2811) == pytest.approx(5.0, rel=1e-6)
    assert haversine_m(1.2136, -77.2811, 1.2136, max_lon) == pytest.approx(5.0, rel=1e-3)
    assert haversine_m(1.2136, -77.2811, 1.2136, min_lon) == pytest.approx(5.0, rel=1e-3)


def test_bounding_box_holds_every_point_within_the_radius() -> None:
    rng = random.Random(7)
    for _ in range(300):
        lat = rng.uniform(-80, 80)
        lon = rng.uniform(-170, 170)
        radius = rng.uniform(0, 50_000)
        min_lat, min_lon, max_lat, max_lon = bounding_box(lat, lon, radius)
        for _ in range(20):
            bearing = rng.uniform(0, 2 * math.pi)
            distance = rng.uniform(0, radius)
            # A point at a known distance and bearing from the center (spherical formula).
            angle = distance / EARTH_RADIUS_M
            phi1, lam1 = math.radians(lat), math.radians(lon)
            phi2 = math.asin(
                math.sin(phi1) * math.cos(angle)
                + math.cos(phi1) * math.sin(angle) * math.cos(bearing)
            )
            lam2 = lam1 + math.atan2(
                math.sin(bearing) * math.sin(angle) * math.cos(phi1),
                math.cos(angle) - math.sin(phi1) * math.sin(phi2),
            )
            assert min_lat - 1e-9 <= math.degrees(phi2) <= max_lat + 1e-9
            assert min_lon - 1e-9 <= math.degrees(lam2) <= max_lon + 1e-9


def test_bounding_box_takes_every_longitude_near_a_pole() -> None:
    min_lat, min_lon, max_lat, max_lon = bounding_box(89.9999, 10.0, 50_000)

    assert (min_lon, max_lon) == (-180.0, 180.0)
    assert max_lat == 90.0


def test_bounding_box_rejects_a_negative_radius() -> None:
    with pytest.raises(ValueError, match="radius_m"):
        bounding_box(1.0, 1.0, -1.0)


def test_distance_to_a_box_is_zero_inside_it() -> None:
    box = (1.20, -77.30, 1.23, -77.26)

    assert min_distance_to_box_m(1.21, -77.28, box) == 0.0
    assert min_distance_to_box_m(1.20, -77.30, box) == 0.0


def test_distance_to_a_box_straight_north_is_the_latitude_gap() -> None:
    box = (1.20, -77.30, 1.23, -77.26)

    assert min_distance_to_box_m(1.25, -77.28, box) == pytest.approx(
        haversine_m(1.25, -77.28, 1.23, -77.28), rel=1e-9
    )


def test_distance_to_a_box_is_never_more_than_the_distance_to_any_point_in_it() -> None:
    rng = random.Random(11)
    for _ in range(300):
        lat0 = rng.uniform(-70, 70)
        lon0 = rng.uniform(-170, 160)
        box = (lat0, lon0, lat0 + rng.uniform(0.0001, 2), lon0 + rng.uniform(0.0001, 5))
        query_lat = rng.uniform(-80, 80)
        query_lon = rng.uniform(-179, 179)
        bound = min_distance_to_box_m(query_lat, query_lon, box)
        for _ in range(20):
            lat = rng.uniform(box[0], box[2])
            lon = rng.uniform(box[1], box[3])
            assert bound <= haversine_m(query_lat, query_lon, lat, lon) + 1e-6


def test_distance_to_a_box_is_close_to_the_real_distance_for_a_small_box() -> None:
    box = (1.2136, -77.2811, 1.2137, -77.2810)
    corner_distance = haversine_m(1.2145, -77.2815, 1.2137, -77.2811)

    assert min_distance_to_box_m(1.2145, -77.2815, box) <= corner_distance
    assert min_distance_to_box_m(1.2145, -77.2815, box) > 0.9 * corner_distance


class TestProjectOnSegment:
    START = (1.2136, -77.2811)
    END = (1.2136, -77.2801)  # about 111 m to the east

    def test_a_place_beside_the_middle_projects_onto_the_middle(self) -> None:
        result = project_on_segment(1.21370, -77.2806, self.START, self.END)

        assert result.fraction == pytest.approx(0.5, abs=1e-3)
        assert result.latitude == pytest.approx(1.2136)
        assert result.distance_m == pytest.approx(
            haversine_m(1.2137, -77.2806, 1.2136, -77.2806), rel=1e-3
        )

    def test_a_place_past_the_end_projects_onto_the_end(self) -> None:
        result = project_on_segment(1.2136, -77.2790, self.START, self.END)

        assert result.fraction == 1.0
        assert (result.latitude, result.longitude) == pytest.approx(self.END)
        assert result.distance_m == pytest.approx(haversine_m(1.2136, -77.2790, *self.END))

    def test_a_place_before_the_start_projects_onto_the_start(self) -> None:
        result = project_on_segment(1.2136, -77.2820, self.START, self.END)

        assert result.fraction == 0.0
        assert (result.latitude, result.longitude) == pytest.approx(self.START)

    def test_a_place_on_the_segment_is_at_distance_zero(self) -> None:
        result = project_on_segment(1.2136, -77.2806, self.START, self.END)

        assert result.distance_m == pytest.approx(0.0, abs=1e-6)

    def test_a_segment_that_is_a_single_point_gives_that_point(self) -> None:
        result = project_on_segment(1.2140, -77.2811, self.START, self.START)

        assert result.fraction == 0.0
        assert result.distance_m == pytest.approx(haversine_m(1.2140, -77.2811, *self.START))

    def test_the_segment_can_cross_the_180_degree_line(self) -> None:
        result = project_on_segment(0.0001, 179.9999, (0.0, 179.999), (0.0, -179.999))

        assert 0.0 < result.fraction < 1.0
        assert result.distance_m == pytest.approx(
            haversine_m(0.0001, 179.9999, 0.0, 179.9999), rel=1e-2
        )

    def test_no_point_of_the_segment_is_closer_than_the_projection(self) -> None:
        rng = random.Random(21)
        for _ in range(200):
            lat = 1.2136 + rng.uniform(-0.0005, 0.0005)
            lon = -77.2806 + rng.uniform(-0.0008, 0.0008)
            result = project_on_segment(lat, lon, self.START, self.END)
            for i in range(0, 101):
                t = i / 100
                other = haversine_m(lat, lon, 1.2136, -77.2811 + t * 0.0010)
                assert result.distance_m <= other + 0.01


class TestProjectOnPolyline:
    # An "L": 111 m east, then 111 m north.
    L_SHAPE = [(1.2136, -77.2811), (1.2136, -77.2801), (1.2146, -77.2801)]

    def test_a_place_near_the_second_piece_projects_onto_it(self) -> None:
        result = project_on_polyline(1.2141, -77.2799, self.L_SHAPE)

        assert result.longitude == pytest.approx(-77.2801)
        assert result.latitude == pytest.approx(1.2141, abs=1e-6)
        assert result.fraction == pytest.approx(0.75, abs=0.01)

    def test_the_fraction_is_measured_along_the_whole_line(self) -> None:
        start = project_on_polyline(1.2136, -77.2811, self.L_SHAPE)
        corner = project_on_polyline(1.2130, -77.2801, self.L_SHAPE)
        end = project_on_polyline(1.2150, -77.2801, self.L_SHAPE)

        assert start.fraction == 0.0
        assert corner.fraction == pytest.approx(0.5, abs=0.01)
        assert end.fraction == 1.0

    def test_it_matches_a_search_over_many_samples_of_the_line(self) -> None:
        rng = random.Random(22)
        for _ in range(100):
            lat = 1.2141 + rng.uniform(-0.001, 0.001)
            lon = -77.2806 + rng.uniform(-0.001, 0.001)
            result = project_on_polyline(lat, lon, self.L_SHAPE)
            samples = [(1.2136, -77.2811 + i * 0.00001) for i in range(101)]
            samples += [(1.2136 + i * 0.00001, -77.2801) for i in range(101)]
            best = min(haversine_m(lat, lon, *p) for p in samples)
            assert result.distance_m <= best + 0.01
            assert result.distance_m >= best - 1.5

    def test_a_line_of_one_point_is_that_point(self) -> None:
        result = project_on_polyline(1.2140, -77.2811, [(1.2136, -77.2811)])

        assert result.fraction == 0.0
        assert result.distance_m == pytest.approx(haversine_m(1.2140, -77.2811, 1.2136, -77.2811))

    def test_a_line_without_points_is_an_error(self) -> None:
        with pytest.raises(ValueError, match="at least one point"):
            project_on_polyline(1.0, 1.0, [])


class TestSamplePolyline:
    L_SHAPE = [(1.2136, -77.2811), (1.2136, -77.2801), (1.2146, -77.2801)]

    def test_it_keeps_the_ends_and_the_corners(self) -> None:
        samples = sample_polyline(self.L_SHAPE, 10.0)

        assert samples[0] == self.L_SHAPE[0]
        assert samples[-1] == self.L_SHAPE[-1]
        assert self.L_SHAPE[1] in samples

    def test_no_two_neighbor_samples_are_farther_than_the_step(self) -> None:
        samples = sample_polyline(self.L_SHAPE, 10.0)

        gaps = [haversine_m(*a, *b) for a, b in itertools.pairwise(samples)]
        assert max(gaps) <= 10.0
        assert len(samples) > 20

    def test_a_short_piece_keeps_only_its_ends(self) -> None:
        assert sample_polyline([(1.0, 1.0), (1.00001, 1.0)], 10.0) == [(1.0, 1.0), (1.00001, 1.0)]

    def test_a_single_point_gives_itself(self) -> None:
        assert sample_polyline([(1.0, 1.0)], 10.0) == [(1.0, 1.0)]

    def test_it_can_cross_the_180_degree_line(self) -> None:
        samples = sample_polyline([(0.0, 179.9995), (0.0, -179.9995)], 20.0)

        assert all(-180.0 <= lon <= 180.0 for _, lon in samples)
        assert max(haversine_m(*a, *b) for a, b in itertools.pairwise(samples)) <= 20.0

    @pytest.mark.parametrize("step", [0.0, -1.0, math.nan, math.inf])
    def test_the_step_must_be_a_positive_distance(self, step: float) -> None:
        with pytest.raises(ValueError, match="step_m"):
            sample_polyline(self.L_SHAPE, step)

    def test_a_line_without_points_is_an_error(self) -> None:
        with pytest.raises(ValueError, match="at least one point"):
            sample_polyline([], 10.0)
