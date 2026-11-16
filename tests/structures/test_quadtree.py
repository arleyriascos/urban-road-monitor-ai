import math
import random

import pytest

from app.geo import haversine_m
from app.structures.quadtree import Quadtree, QuadtreeError, bounds_around

Point = tuple[float, float]

PASTO = (1.15, -77.35, 1.27, -77.22)


def test_a_new_tree_is_empty() -> None:
    tree: Quadtree[int] = Quadtree(PASTO)

    assert len(tree) == 0
    assert tree.stats().points == 0
    assert tree.stats().depth == 0


def test_insert_counts_the_points() -> None:
    tree: Quadtree[str] = Quadtree(PASTO)

    tree.insert(1.2136, -77.2811, "a")
    tree.insert(1.2150, -77.2790, "b")

    assert len(tree) == 2


def test_the_tree_splits_after_its_capacity_and_keeps_every_point() -> None:
    tree: Quadtree[int] = Quadtree(PASTO, capacity=4)
    rng = random.Random(1)
    for i in range(200):
        tree.insert(rng.uniform(1.15, 1.27), rng.uniform(-77.35, -77.22), i)

    stats = tree.stats()

    assert stats.points == 200
    assert stats.depth >= 3
    splits = stats.nodes - stats.leaves
    assert stats.nodes == 1 + 4 * splits  # every split adds four quarters


def test_points_on_the_edges_of_the_bounds_are_accepted() -> None:
    tree: Quadtree[int] = Quadtree(PASTO)

    tree.insert(1.15, -77.35, 0)
    tree.insert(1.27, -77.22, 1)

    assert len(tree) == 2


@pytest.mark.parametrize(
    ("latitude", "longitude"),
    [(1.14, -77.30), (1.28, -77.30), (1.20, -77.36), (1.20, -77.21), (math.nan, -77.3)],
)
def test_a_point_outside_the_bounds_is_rejected(latitude: float, longitude: float) -> None:
    tree: Quadtree[int] = Quadtree(PASTO)

    with pytest.raises(QuadtreeError, match="outside the bounds"):
        tree.insert(latitude, longitude, 0)
    assert len(tree) == 0


def test_points_at_the_same_spot_stop_splitting_at_the_maximum_depth() -> None:
    tree: Quadtree[int] = Quadtree(PASTO, capacity=2, max_depth=6)
    for i in range(50):
        tree.insert(1.2136, -77.2811, i)

    stats = tree.stats()

    assert stats.points == 50
    assert stats.depth == 6


def test_a_tree_of_random_points_stays_shallow() -> None:
    tree: Quadtree[int] = Quadtree(PASTO)
    rng = random.Random(3)
    for i in range(20_000):
        tree.insert(rng.uniform(1.15, 1.27), rng.uniform(-77.35, -77.22), i)

    assert tree.stats().depth <= 12


@pytest.mark.parametrize(
    "bounds",
    [
        (1.0, -77.0, 1.0, -76.0),
        (2.0, -77.0, 1.0, -76.0),
        (1.0, -77.0, 2.0, -77.0),
        (math.nan, 0, 1, 1),
    ],
)
def test_bounds_without_area_are_rejected(bounds: tuple[float, float, float, float]) -> None:
    with pytest.raises(QuadtreeError, match="bounds"):
        Quadtree(bounds)


def test_invalid_settings_are_rejected() -> None:
    with pytest.raises(QuadtreeError, match="capacity"):
        Quadtree(PASTO, capacity=0)
    with pytest.raises(QuadtreeError, match="max_depth"):
        Quadtree(PASTO, max_depth=-1)


def _random_points(count: int, seed: int) -> list[Point]:
    rng = random.Random(seed)
    return [(rng.uniform(1.15, 1.27), rng.uniform(-77.35, -77.22)) for _ in range(count)]


def test_query_box_finds_the_points_inside_and_only_those() -> None:
    points = _random_points(500, seed=5)
    tree: Quadtree[int] = Quadtree(PASTO, capacity=4)
    for i, (latitude, longitude) in enumerate(points):
        tree.insert(latitude, longitude, i)

    box = (1.19, -77.30, 1.22, -77.27)
    found = {hit.value for hit in tree.query_box(box)}

    expected = {
        i
        for i, (lat, lon) in enumerate(points)
        if box[0] <= lat <= box[2] and box[1] <= lon <= box[3]
    }
    assert found == expected
    assert 0 < len(found) < 500


def test_query_box_matches_a_plain_search_for_many_random_boxes() -> None:
    points = _random_points(1_000, seed=6)
    tree: Quadtree[int] = Quadtree(PASTO)
    for i, (latitude, longitude) in enumerate(points):
        tree.insert(latitude, longitude, i)
    rng = random.Random(7)

    for _ in range(200):
        lat = rng.uniform(1.14, 1.28)
        lon = rng.uniform(-77.36, -77.21)
        box = (lat, lon, lat + rng.uniform(0, 0.05), lon + rng.uniform(0, 0.05))
        found = sorted(hit.value for hit in tree.query_box(box))
        expected = [
            i
            for i, (la, lo) in enumerate(points)
            if box[0] <= la <= box[2] and box[1] <= lo <= box[3]
        ]
        assert found == expected


def test_query_box_includes_the_points_on_its_edges() -> None:
    tree: Quadtree[str] = Quadtree(PASTO)
    tree.insert(1.20, -77.30, "corner")
    tree.insert(1.21, -77.30, "edge")

    found = {hit.value for hit in tree.query_box((1.20, -77.30, 1.21, -77.29))}

    assert found == {"corner", "edge"}


def test_query_box_returns_the_point_data_and_the_order_of_insertion() -> None:
    tree: Quadtree[str] = Quadtree(PASTO)
    tree.insert(1.2136, -77.2811, "first")
    tree.insert(1.2150, -77.2790, "second")

    hits = sorted(tree.query_box(PASTO), key=lambda hit: hit.order)

    assert [(h.latitude, h.longitude, h.value, h.order) for h in hits] == [
        (1.2136, -77.2811, "first", 0),
        (1.2150, -77.2790, "second", 1),
    ]


def test_query_box_of_an_empty_tree_or_far_away_finds_nothing() -> None:
    tree: Quadtree[int] = Quadtree(PASTO)
    assert tree.query_box(PASTO) == []
    tree.insert(1.2, -77.3, 0)
    assert tree.query_box((1.25, -77.25, 1.26, -77.24)) == []


def test_query_box_finds_every_point_stacked_at_the_same_spot() -> None:
    tree: Quadtree[int] = Quadtree(PASTO, capacity=2, max_depth=5)
    for i in range(30):
        tree.insert(1.2136, -77.2811, i)

    assert len(tree.query_box((1.2136, -77.2811, 1.2136, -77.2811))) == 30


def test_query_radius_finds_the_points_within_the_distance_and_how_far_they_are() -> None:
    tree: Quadtree[str] = Quadtree(PASTO)
    tree.insert(1.2136, -77.2811, "center")
    tree.insert(1.21363, -77.2811, "3 m north")
    tree.insert(1.21366, -77.2811, "6.7 m north")
    tree.insert(1.2136, -77.28117, "7.8 m west")

    matches = tree.query_radius(1.2136, -77.2811, 5.0)

    found = {match.hit.value: match.distance_m for match in matches}
    assert set(found) == {"center", "3 m north"}
    assert found["center"] == 0.0
    assert found["3 m north"] == pytest.approx(3.3, abs=0.1)


def test_query_radius_includes_a_point_at_exactly_the_radius() -> None:
    tree: Quadtree[int] = Quadtree(PASTO)
    tree.insert(1.2140, -77.2810, 0)
    radius = haversine_m(1.2136, -77.2811, 1.2140, -77.2810)

    assert len(tree.query_radius(1.2136, -77.2811, radius)) == 1
    assert tree.query_radius(1.2136, -77.2811, radius * 0.999) == []


def test_query_radius_matches_a_plain_search_for_many_random_circles() -> None:
    points = _random_points(2_000, seed=8)
    tree: Quadtree[int] = Quadtree(PASTO)
    for i, (latitude, longitude) in enumerate(points):
        tree.insert(latitude, longitude, i)
    rng = random.Random(9)

    for _ in range(200):
        lat = rng.uniform(1.15, 1.27)
        lon = rng.uniform(-77.35, -77.22)
        radius = rng.choice([0.0, 5.0, 50.0, 500.0, 3_000.0])
        found = sorted(match.hit.value for match in tree.query_radius(lat, lon, radius))
        expected = [
            i for i, (la, lo) in enumerate(points) if haversine_m(lat, lon, la, lo) <= radius
        ]
        assert found == expected


@pytest.mark.parametrize("radius", [-1.0, math.nan, math.inf])
def test_query_radius_rejects_a_radius_that_is_not_a_distance(radius: float) -> None:
    tree: Quadtree[int] = Quadtree(PASTO)

    with pytest.raises(QuadtreeError, match="radius_m"):
        tree.query_radius(1.2, -77.3, radius)


def test_query_radius_around_a_place_outside_the_bounds_still_works() -> None:
    tree: Quadtree[int] = Quadtree(PASTO)
    tree.insert(1.15, -77.35, 0)

    assert len(tree.query_radius(1.1499, -77.3501, 100.0)) == 1


def test_nearest_of_an_empty_tree_is_none() -> None:
    tree: Quadtree[int] = Quadtree(PASTO)

    assert tree.nearest(1.2, -77.3) is None


def test_nearest_gives_the_closest_point_and_its_distance() -> None:
    tree: Quadtree[str] = Quadtree(PASTO)
    tree.insert(1.2136, -77.2811, "near")
    tree.insert(1.2200, -77.2700, "far")

    match = tree.nearest(1.2137, -77.2811)

    assert match is not None
    assert match.hit.value == "near"
    assert match.distance_m == pytest.approx(haversine_m(1.2137, -77.2811, 1.2136, -77.2811))


def test_nearest_respects_the_maximum_distance() -> None:
    tree: Quadtree[str] = Quadtree(PASTO)
    tree.insert(1.2136, -77.2811, "a")

    assert tree.nearest(1.2137, -77.2811, max_distance_m=5.0) is None
    assert tree.nearest(1.2137, -77.2811, max_distance_m=20.0) is not None


def test_nearest_of_two_equally_close_points_is_the_first_inserted() -> None:
    tree: Quadtree[str] = Quadtree(PASTO, capacity=1)
    tree.insert(1.2140, -77.2811, "first")
    tree.insert(1.2140, -77.2811, "second")
    tree.insert(1.2200, -77.2700, "other")

    match = tree.nearest(1.2141, -77.2811)

    assert match is not None
    assert match.hit.value == "first"


def test_nearest_matches_a_plain_search_for_many_random_places() -> None:
    points = _random_points(1_500, seed=12)
    # Repeated points make ties, which the tree must settle the same way as the plain search.
    points += points[:50]
    tree: Quadtree[int] = Quadtree(PASTO, capacity=4)
    for i, (latitude, longitude) in enumerate(points):
        tree.insert(latitude, longitude, i)
    rng = random.Random(13)

    for _ in range(300):
        lat = rng.uniform(1.14, 1.28)
        lon = rng.uniform(-77.36, -77.21)
        limit = rng.choice([math.inf, 50.0, 500.0])
        expected = min(
            ((haversine_m(lat, lon, la, lo), i) for i, (la, lo) in enumerate(points)),
        )
        match = tree.nearest(lat, lon, limit)
        if expected[0] > limit:
            assert match is None
        else:
            assert match is not None
            assert (match.distance_m, match.hit.order) == expected


def test_nearest_rejects_a_maximum_distance_that_is_not_a_distance() -> None:
    tree: Quadtree[int] = Quadtree(PASTO)

    with pytest.raises(QuadtreeError, match="max_distance_m"):
        tree.nearest(1.2, -77.3, -1.0)
    with pytest.raises(QuadtreeError, match="max_distance_m"):
        tree.nearest(1.2, -77.3, math.nan)


def test_nearest_in_a_big_tree_is_close_to_the_place() -> None:
    points = _random_points(20_000, seed=14)
    tree: Quadtree[int] = Quadtree(PASTO)
    for i, (latitude, longitude) in enumerate(points):
        tree.insert(latitude, longitude, i)

    match = tree.nearest(1.2136, -77.2811)

    assert match is not None
    assert match.distance_m < 100


def test_bounds_around_wrap_the_points_with_a_small_margin() -> None:
    south, west, north, east = bounds_around([(1.2, -77.3), (1.3, -77.2)])

    assert south < 1.2 < 1.3 < north
    assert west < -77.3 < -77.2 < east
    assert north - 1.3 < 1e-5


def test_bounds_around_one_point_still_have_an_area() -> None:
    south, west, north, east = bounds_around([(1.2, -77.3)])

    assert south < north
    assert west < east


def test_bounds_around_never_leave_the_world() -> None:
    assert bounds_around([(90.0, 180.0), (-90.0, -180.0)]) == (-90.0, -180.0, 90.0, 180.0)


def test_bounds_around_no_points_are_an_error() -> None:
    with pytest.raises(QuadtreeError, match="empty"):
        bounds_around([])
