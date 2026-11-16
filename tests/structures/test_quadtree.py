import math
import random

import pytest

from app.structures.quadtree import Quadtree, QuadtreeError

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
