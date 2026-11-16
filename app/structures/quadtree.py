"""Quadtree: a map divided into quarters to find nearby points without measuring them all.

Each node covers a rectangle of the map (a range of latitudes and a range of longitudes).
It keeps its points until it holds more than its capacity; then it splits into four
quarters and hands its points down to them. A search starts at the root and enters only
the quarters that can hold what it looks for, so it skips most of the map: the cost
grows with the number of points found and with the depth of the tree, not with the
number of points stored.

Points on the line between two quarters go to the north and east one, so every point
has exactly one place. Points that sit at exactly the same spot can never be separated
by splitting, so a node at the maximum depth keeps them all instead of splitting again.

The longitudes are treated as a flat range from -180 to 180: a Quadtree that must cover
the antimeridian is not supported. Pasto is far from it.
"""

import math
from collections.abc import Sequence
from dataclasses import dataclass

from app.geo import BoundingBox, bounding_box, haversine_m, min_distance_to_box_m

WORLD: BoundingBox = (-90.0, -180.0, 90.0, 180.0)

_PADDING_DEGREES = 1e-6
"""Margin around a set of points, so even a single point gives the tree an area."""


def bounds_around(points: Sequence[tuple[float, float]]) -> BoundingBox:
    """The smallest rectangle that holds every (latitude, longitude) point, with a margin.

    Points on the edge of a Quadtree are accepted, but the margin keeps them off the
    edge anyway, and keeps the rectangle from being flat when all points are the same.
    The rectangle never goes beyond the world.
    """
    if not points:
        raise QuadtreeError("cannot wrap an empty list of points")
    latitudes = [lat for lat, _ in points]
    longitudes = [lon for _, lon in points]
    return (
        max(-90.0, min(latitudes) - _PADDING_DEGREES),
        max(-180.0, min(longitudes) - _PADDING_DEGREES),
        min(90.0, max(latitudes) + _PADDING_DEGREES),
        min(180.0, max(longitudes) + _PADDING_DEGREES),
    )


"""The default area of a Quadtree: the whole Earth."""

DEFAULT_CAPACITY = 8
"""Points a node keeps before it splits."""

DEFAULT_MAX_DEPTH = 24
"""Deepest level of the tree. At 24 levels a quarter of the world is about 2 meters wide."""


class QuadtreeError(ValueError):
    """Raised for a point outside the area of the tree or for an invalid setting."""


@dataclass(frozen=True, slots=True)
class QuadHit[T]:
    """A stored point returned by a search."""

    latitude: float
    longitude: float
    value: T
    """What was stored with the point."""
    order: int
    """How many points were inserted before this one: 0 for the first. Searches return
    points in tree order, and this lets a caller put them back in insertion order."""


@dataclass(frozen=True, slots=True)
class QuadMatch[T]:
    """A stored point found by a search around a place, with how far it is."""

    hit: QuadHit[T]
    distance_m: float


@dataclass(frozen=True, slots=True)
class QuadStats:
    """The shape of the tree, to check that it stays balanced."""

    points: int
    nodes: int
    leaves: int
    depth: int
    """Number of levels below the root (0 when the root has not split)."""


class _Node[T]:
    """One rectangle of the map: either a leaf with points or four quarters."""

    __slots__ = ("box", "children", "depth", "mid_lat", "mid_lon", "points")

    def __init__(self, box: BoundingBox, depth: int) -> None:
        self.box = box
        self.depth = depth
        self.mid_lat = (box[0] + box[2]) / 2
        self.mid_lon = (box[1] + box[3]) / 2
        self.points: list[tuple[float, float, int, T]] = []
        """The points of a leaf as (latitude, longitude, order, value), in arrival order."""
        self.children: tuple[_Node[T], _Node[T], _Node[T], _Node[T]] | None = None
        """South-west, south-east, north-west, north-east; None while this is a leaf."""

    def quarter_of(self, latitude: float, longitude: float) -> int:
        """Index in ``children`` of the quarter that owns the point."""
        return (2 if latitude >= self.mid_lat else 0) + (1 if longitude >= self.mid_lon else 0)

    def split(self) -> None:
        """Turn this leaf into four quarters and move its points down."""
        min_lat, min_lon, max_lat, max_lon = self.box
        next_depth = self.depth + 1
        self.children = (
            _Node((min_lat, min_lon, self.mid_lat, self.mid_lon), next_depth),
            _Node((min_lat, self.mid_lon, self.mid_lat, max_lon), next_depth),
            _Node((self.mid_lat, min_lon, max_lat, self.mid_lon), next_depth),
            _Node((self.mid_lat, self.mid_lon, max_lat, max_lon), next_depth),
        )
        for point in self.points:
            self.children[self.quarter_of(point[0], point[1])].points.append(point)
        self.points = []


class Quadtree[T]:
    """Points on the map, each carrying a value, with fast searches by area."""

    def __init__(
        self,
        bounds: BoundingBox = WORLD,
        capacity: int = DEFAULT_CAPACITY,
        max_depth: int = DEFAULT_MAX_DEPTH,
    ) -> None:
        min_lat, min_lon, max_lat, max_lon = bounds
        if not all(math.isfinite(v) for v in bounds) or min_lat >= max_lat or min_lon >= max_lon:
            raise QuadtreeError(f"the bounds must be a rectangle with some area, got {bounds}")
        if capacity < 1:
            raise QuadtreeError(f"capacity must be at least 1, got {capacity}")
        if max_depth < 0:
            raise QuadtreeError(f"max_depth must not be negative, got {max_depth}")
        self._bounds = bounds
        self._capacity = capacity
        self._max_depth = max_depth
        self._root: _Node[T] = _Node(bounds, 0)
        self._size = 0

    @property
    def bounds(self) -> BoundingBox:
        return self._bounds

    def __len__(self) -> int:
        return self._size

    def insert(self, latitude: float, longitude: float, value: T) -> None:
        """Store a point with its value."""
        min_lat, min_lon, max_lat, max_lon = self._bounds
        if not (min_lat <= latitude <= max_lat and min_lon <= longitude <= max_lon):
            raise QuadtreeError(
                f"the point ({latitude}, {longitude}) is outside the bounds {self._bounds}"
            )
        node = self._root
        while node.children is not None:
            node = node.children[node.quarter_of(latitude, longitude)]
        node.points.append((latitude, longitude, self._size, value))
        self._size += 1
        while len(node.points) > self._capacity and node.depth < self._max_depth:
            node.split()
            assert node.children is not None
            # All points may have fallen in one quarter; keep splitting that one.
            node = max(node.children, key=lambda child: len(child.points))

    def query_box(self, box: BoundingBox) -> list[QuadHit[T]]:
        """Every point inside the rectangle, edges included, in tree order."""
        min_lat, min_lon, max_lat, max_lon = box
        found: list[QuadHit[T]] = []
        pending = [self._root]
        while pending:
            node = pending.pop()
            n_min_lat, n_min_lon, n_max_lat, n_max_lon = node.box
            if (
                n_max_lat < min_lat
                or n_min_lat > max_lat
                or n_max_lon < min_lon
                or n_min_lon > max_lon
            ):
                continue
            if node.children is not None:
                pending.extend(node.children)
                continue
            found.extend(
                QuadHit(latitude, longitude, value, order)
                for latitude, longitude, order, value in node.points
                if min_lat <= latitude <= max_lat and min_lon <= longitude <= max_lon
            )
        return found

    def query_radius(
        self, latitude: float, longitude: float, radius_m: float
    ) -> list[QuadMatch[T]]:
        """Every point within radius_m meters of a place, with its distance, in tree order.

        The tree first takes the points of the rectangle that surrounds the circle,
        which is quick, and then measures only those with the haversine distance.
        """
        if not (math.isfinite(radius_m) and radius_m >= 0):
            raise QuadtreeError(f"radius_m must be a number >= 0, got {radius_m}")
        matches: list[QuadMatch[T]] = []
        for hit in self.query_box(bounding_box(latitude, longitude, radius_m)):
            distance = haversine_m(latitude, longitude, hit.latitude, hit.longitude)
            if distance <= radius_m:
                matches.append(QuadMatch(hit, distance))
        return matches

    def nearest(
        self, latitude: float, longitude: float, max_distance_m: float = math.inf
    ) -> QuadMatch[T] | None:
        """The stored point closest to a place, or None if none is within max_distance_m.

        If two points are equally close, the one inserted first wins, so the answer does
        not depend on how the tree happens to be split. The search enters the quarter
        nearest to the place first and skips every quarter that is already farther than
        the best point found.
        """
        if math.isnan(max_distance_m) or max_distance_m < 0:
            raise QuadtreeError(f"max_distance_m must be a number >= 0, got {max_distance_m}")
        best: QuadMatch[T] | None = None

        def visit(node: _Node[T]) -> None:
            nonlocal best
            if node.children is None:
                for point_lat, point_lon, order, value in node.points:
                    distance = haversine_m(latitude, longitude, point_lat, point_lon)
                    if distance > max_distance_m:
                        continue
                    if (
                        best is None
                        or distance < best.distance_m
                        or (distance == best.distance_m and order < best.hit.order)
                    ):
                        best = QuadMatch(QuadHit(point_lat, point_lon, value, order), distance)
                return
            ranked = sorted(
                (min_distance_to_box_m(latitude, longitude, child.box), index)
                for index, child in enumerate(node.children)
            )
            for bound, index in ranked:
                limit = max_distance_m if best is None else min(max_distance_m, best.distance_m)
                # A small margin, so a rounding error never hides a point that ties the best.
                if bound > limit * (1 + 1e-9) + 1e-9:
                    break
                visit(node.children[index])

        visit(self._root)
        return best

    def stats(self) -> QuadStats:
        """Count the nodes and find the deepest level."""
        nodes = leaves = deepest = 0
        pending = [self._root]
        while pending:
            node = pending.pop()
            nodes += 1
            deepest = max(deepest, node.depth)
            if node.children is None:
                leaves += 1
            else:
                pending.extend(node.children)
        return QuadStats(points=self._size, nodes=nodes, leaves=leaves, depth=deepest)
