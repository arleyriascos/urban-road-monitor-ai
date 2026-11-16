"""DBSCAN with the Quadtree must give the same labels as a plain version that measures
every pair of points. The plain version follows the same steps, so the labels match
exactly, not only up to renaming."""

import random
from collections import deque

import pytest

from app.clustering.dbscan import NOISE, dbscan
from app.geo import haversine_m

Point = tuple[float, float]
UNVISITED = -2


def plain_dbscan(points: list[Point], eps_m: float, min_points: int) -> list[int]:
    def neighbors(index: int) -> list[int]:
        return [
            other
            for other in range(len(points))
            if haversine_m(*points[index], *points[other]) <= eps_m
        ]

    labels = [UNVISITED] * len(points)
    cluster = 0
    for start in range(len(points)):
        if labels[start] != UNVISITED:
            continue
        around = neighbors(start)
        if len(around) < min_points:
            labels[start] = NOISE
            continue
        labels[start] = cluster
        pending = deque(around)
        while pending:
            index = pending.popleft()
            if labels[index] == NOISE:
                labels[index] = cluster
            if labels[index] != UNVISITED:
                continue
            labels[index] = cluster
            reached = neighbors(index)
            if len(reached) >= min_points:
                pending.extend(reached)
        cluster += 1
    return labels


def scattered_points(count: int, seed: int) -> list[Point]:
    """Detections like the real ones: a few potholes seen many times, plus loners."""
    rng = random.Random(seed)
    centers = [
        (1.2136 + rng.uniform(-0.003, 0.003), -77.2811 + rng.uniform(-0.003, 0.003))
        for _ in range(12)
    ]
    points: list[Point] = []
    for _ in range(count):
        if rng.random() < 0.8:
            lat, lon = rng.choice(centers)
            points.append((lat + rng.gauss(0, 0.00003), lon + rng.gauss(0, 0.00003)))
        else:
            points.append(
                (1.2136 + rng.uniform(-0.004, 0.004), -77.2811 + rng.uniform(-0.004, 0.004))
            )
    return points


@pytest.mark.parametrize("seed", range(8))
@pytest.mark.parametrize(
    ("eps_m", "min_points"), [(5.0, 2), (5.0, 3), (2.0, 2), (12.0, 4), (0.5, 1)]
)
def test_the_labels_are_the_same_as_the_plain_version(
    seed: int, eps_m: float, min_points: int
) -> None:
    points = scattered_points(300, seed)

    assert dbscan(points, eps_m, min_points) == plain_dbscan(points, eps_m, min_points)


def test_the_random_data_really_has_clusters_and_noise() -> None:
    labels = dbscan(scattered_points(300, 0), 5.0, 2)

    assert max(labels) >= 3
    assert NOISE in labels


def test_the_labels_are_the_same_when_every_point_is_the_same() -> None:
    points = [(1.2136, -77.2811)] * 25

    assert dbscan(points, 5.0, 3) == plain_dbscan(points, 5.0, 3)
