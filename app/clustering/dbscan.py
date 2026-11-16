"""DBSCAN: group points that are close to each other, and leave the isolated ones alone.

DBSCAN (density-based spatial clustering) needs two settings:

* ``eps_m``: how close two points must be, in meters, to count as neighbors.
* ``min_points``: how many points a place needs around it (itself included) to count
  as dense.

A point with at least ``min_points`` points within ``eps_m`` is a *core* point. Starting
from a core point that has no cluster yet, the algorithm opens a new cluster and keeps
adding the neighbors of every core point it reaches, so a cluster can grow into any
shape, such as the line of detections left by a car that drove past one pothole. A point
that is near a core point but is not core itself (a *border* point) joins the first
cluster that reaches it. A point that no cluster reaches is *noise*.

Looking for the neighbors of every point would cost one distance per pair of points. The
Quadtree answers each search by visiting only the nearby quarters of the map.
"""

import math
from collections import deque
from collections.abc import Sequence

from app.clustering.models import ClusteringError
from app.structures.quadtree import Quadtree

NOISE = -1
"""The label of a point that belongs to no cluster."""

_UNVISITED = -2

_PADDING_DEGREES = 1e-6
"""Margin around the points, so even a single point gives the Quadtree an area."""

Point = tuple[float, float]
"""A (latitude, longitude) pair in degrees."""


def _tree_around(points: Sequence[Point]) -> Quadtree[int]:
    latitudes = [lat for lat, _ in points]
    longitudes = [lon for _, lon in points]
    bounds = (
        max(-90.0, min(latitudes) - _PADDING_DEGREES),
        max(-180.0, min(longitudes) - _PADDING_DEGREES),
        min(90.0, max(latitudes) + _PADDING_DEGREES),
        min(180.0, max(longitudes) + _PADDING_DEGREES),
    )
    tree: Quadtree[int] = Quadtree(bounds)
    for index, (latitude, longitude) in enumerate(points):
        tree.insert(latitude, longitude, index)
    return tree


def dbscan(points: Sequence[Point], eps_m: float, min_points: int) -> list[int]:
    """Label each point with its cluster number, or NOISE.

    Clusters are numbered 0, 1, 2... in the order the algorithm finds them, going through
    the points in the order given, so the same input always gives the same labels.
    """
    if not (math.isfinite(eps_m) and eps_m > 0):
        raise ClusteringError(f"eps_m must be a number > 0, got {eps_m}")
    if min_points < 1:
        raise ClusteringError(f"min_points must be at least 1, got {min_points}")
    if not points:
        return []

    tree = _tree_around(points)

    def neighbors(index: int) -> list[int]:
        latitude, longitude = points[index]
        found = tree.query_radius(latitude, longitude, eps_m)
        return sorted(match.hit.value for match in found)

    labels = [_UNVISITED] * len(points)
    cluster = 0
    for start in range(len(points)):
        if labels[start] != _UNVISITED:
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
                labels[index] = cluster  # a border point: near a core point, but not core
            if labels[index] != _UNVISITED:
                continue
            labels[index] = cluster
            reached = neighbors(index)
            if len(reached) >= min_points:
                pending.extend(reached)
        cluster += 1
    return labels
