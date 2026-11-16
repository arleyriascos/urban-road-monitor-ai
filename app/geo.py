"""Geographic helpers shared by the graph, the search and the click locator."""

import itertools
import math
from collections.abc import Sequence
from typing import NamedTuple

EARTH_RADIUS_M = 6_371_008.8
"""Mean Earth radius in meters. It is the same value the backend uses, so both
services measure the same distance between two points."""


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distance in meters between two (latitude, longitude) points in degrees.

    It is the length of the shortest path over the Earth's surface, so no street
    between the two points can be shorter. A* uses it as its heuristic.
    """
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    h = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(min(1.0, math.sqrt(h)))


BoundingBox = tuple[float, float, float, float]
"""A map rectangle: (min_latitude, min_longitude, max_latitude, max_longitude), in degrees."""


def bounding_box(latitude: float, longitude: float, radius_m: float) -> BoundingBox:
    """Smallest latitude and longitude rectangle that holds every point within radius_m.

    The Quadtree uses it to leave out whole areas of the map before it measures any
    distance. Every point whose haversine distance to the center is at most radius_m
    is inside the rectangle, so no point is lost. The reverse is not true: the corners
    of the rectangle are farther than radius_m, so the caller still measures.

    Near a pole the rectangle takes every longitude, because there a small circle
    goes all the way around the Earth.
    """
    if radius_m < 0:
        raise ValueError(f"radius_m must not be negative, got {radius_m}")
    angle = radius_m / EARTH_RADIUS_M
    phi = math.radians(latitude)
    min_lat = max(-90.0, math.degrees(phi - angle))
    max_lat = min(90.0, math.degrees(phi + angle))
    if abs(phi) + angle >= math.pi / 2:
        return (min_lat, -180.0, max_lat, 180.0)
    d_lon = math.degrees(math.asin(math.sin(angle) / math.cos(phi)))
    return (min_lat, longitude - d_lon, max_lat, longitude + d_lon)


def min_distance_to_box_m(latitude: float, longitude: float, box: BoundingBox) -> float:
    """A distance that no point inside the box is closer than; 0 if the point is inside.

    The Quadtree uses it to decide which areas to visit first when it looks for the
    nearest point, and to skip every area that cannot beat the best one found. It is
    a lower bound, not the exact distance: it uses the smallest gap in latitude and
    in longitude that the box leaves and the smallest cosine the box has, so it never
    says an area is farther than it really is. That is all the search needs from it.
    """
    min_lat, min_lon, max_lat, max_lon = box
    gap_lat = max(min_lat - latitude, 0.0, latitude - max_lat)
    # Longitude wraps around: the box may be closer going the other way round the Earth.
    gap_lon = min(
        max(min_lon - shifted, 0.0, shifted - max_lon)
        for shifted in (longitude - 360.0, longitude, longitude + 360.0)
    )
    gap_lon = min(gap_lon, 180.0)
    if gap_lat == 0.0 and gap_lon == 0.0:
        return 0.0
    smallest_cos = min(math.cos(math.radians(min_lat)), math.cos(math.radians(max_lat)))
    # The two terms of haversine, each with the smallest difference the box allows.
    h = (
        math.sin(math.radians(gap_lat) / 2) ** 2
        + math.cos(math.radians(latitude))
        * max(smallest_cos, 0.0)
        * math.sin(math.radians(gap_lon) / 2) ** 2
    )
    return 2 * EARTH_RADIUS_M * math.asin(min(1.0, math.sqrt(h)))


class SegmentProjection(NamedTuple):
    """The point of a segment that is closest to a place."""

    latitude: float
    longitude: float
    fraction: float
    """Where it falls along the segment: 0 at the start, 1 at the end."""
    distance_m: float
    """Distance from the place to that point."""


def project_on_segment(
    latitude: float,
    longitude: float,
    start: tuple[float, float],
    end: tuple[float, float],
) -> SegmentProjection:
    """Find the point of the segment start-end that is closest to a place.

    A segment is short (tens of meters up to a few hundred), so the surroundings of the
    place are flattened onto a plane measured in meters: east-west degrees are shrunk by
    the cosine of the latitude. On that plane the closest point is found with a dot
    product and kept between the two ends. The distance returned is the real one, from
    the haversine formula, to the point found.
    """
    cos_lat = math.cos(math.radians(latitude))

    def east_north(lat: float, lon: float) -> tuple[float, float]:
        delta_lon = (lon - longitude + 180.0) % 360.0 - 180.0
        return (
            math.radians(delta_lon) * cos_lat * EARTH_RADIUS_M,
            math.radians(lat - latitude) * EARTH_RADIUS_M,
        )

    start_x, start_y = east_north(*start)
    end_x, end_y = east_north(*end)
    run_x = end_x - start_x
    run_y = end_y - start_y
    length_sq = run_x * run_x + run_y * run_y
    if length_sq == 0.0:
        fraction = 0.0
    else:
        # The place is the origin, so the vector from the start to it is (-start_x, -start_y).
        fraction = (-start_x * run_x - start_y * run_y) / length_sq
        fraction = min(1.0, max(0.0, fraction))
    near_lat = start[0] + fraction * (end[0] - start[0])
    delta_lon = (end[1] - start[1] + 180.0) % 360.0 - 180.0
    near_lon = (start[1] + fraction * delta_lon + 180.0) % 360.0 - 180.0
    return SegmentProjection(
        near_lat, near_lon, fraction, haversine_m(latitude, longitude, near_lat, near_lon)
    )


def project_on_polyline(
    latitude: float, longitude: float, points: Sequence[tuple[float, float]]
) -> SegmentProjection:
    """Find the point of a line made of several straight pieces that is closest to a place.

    ``fraction`` in the result is measured along the whole line, by length: 0 at the first
    point and 1 at the last. On a tie the earlier piece wins. A line of one point is a
    point; an empty line has no closest point and is an error.
    """
    if not points:
        raise ValueError("a polyline needs at least one point")
    if len(points) == 1:
        only = points[0]
        return SegmentProjection(
            only[0], only[1], 0.0, haversine_m(latitude, longitude, only[0], only[1])
        )
    lengths = [haversine_m(*a, *b) for a, b in itertools.pairwise(points)]
    total = math.fsum(lengths)
    best: SegmentProjection | None = None
    best_travelled = 0.0
    travelled = 0.0
    for (start, end), length in zip(itertools.pairwise(points), lengths, strict=True):
        found = project_on_segment(latitude, longitude, start, end)
        if best is None or found.distance_m < best.distance_m:
            best = found
            best_travelled = travelled + found.fraction * length
        travelled += length
    assert best is not None
    fraction = best_travelled / total if total > 0 else 0.0
    return SegmentProjection(best.latitude, best.longitude, fraction, best.distance_m)
