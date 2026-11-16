"""Find which road segment a place belongs to, such as a pothole that was detected.

Looking at every segment for every pothole would be slow. Instead, each segment is cut
into sample points about ``SAMPLE_STEP_M`` meters apart and the points go into a Quadtree.
A search asks the Quadtree for the samples near the place, and measures the exact distance
only to the few segments those samples belong to.

The answer is the same as measuring every segment: if a segment passes within ``D`` meters
of a place, its closest point is at most half a step from one of its samples, so that
sample is within ``D`` plus a step, and the search looks that far.
"""

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from app.geo import project_on_polyline, sample_polyline
from app.routing.errors import RoutingError
from app.structures.quadtree import Quadtree, bounds_around

SAMPLE_STEP_M = 10.0
"""Distance between the sample points of a segment."""

Point = tuple[float, float]


class SegmentLocatorError(RoutingError):
    """The segments given to the locator cannot be used."""


@dataclass(frozen=True, slots=True)
class SegmentMatch:
    """The segment closest to a place, and the point of it that is closest."""

    segment_id: int
    latitude: float
    longitude: float
    fraction: float
    """Where the closest point falls along the segment: 0 at its start, 1 at its end."""
    distance_m: float
    """Distance from the place to that point."""


class SegmentLocator:
    """Finds the road segment nearest to a place."""

    def __init__(
        self, segments: Mapping[int, Sequence[Point]], step_m: float = SAMPLE_STEP_M
    ) -> None:
        if not (math.isfinite(step_m) and step_m > 0):
            raise SegmentLocatorError(f"step_m must be a number > 0, got {step_m}")
        if not segments:
            raise SegmentLocatorError("the locator needs at least one segment")
        for segment_id, line in segments.items():
            if len(line) < 1:
                raise SegmentLocatorError(f"segment {segment_id} has no points")
        self._step_m = step_m
        self._lines = {segment_id: tuple(line) for segment_id, line in segments.items()}
        samples = {
            segment_id: sample_polyline(line, step_m) for segment_id, line in self._lines.items()
        }
        every_point = [point for points in samples.values() for point in points]
        self._tree: Quadtree[int] = Quadtree(bounds_around(every_point))
        for segment_id, points in samples.items():
            for latitude, longitude in points:
                self._tree.insert(latitude, longitude, segment_id)

    @property
    def segment_count(self) -> int:
        return len(self._lines)

    def locate(
        self, latitude: float, longitude: float, max_distance_m: float
    ) -> SegmentMatch | None:
        """The segment closest to the place, or None if none passes within max_distance_m.

        On a tie the segment with the lowest id wins.
        """
        if math.isnan(max_distance_m) or max_distance_m < 0:
            raise SegmentLocatorError(f"max_distance_m must be a number >= 0, got {max_distance_m}")
        reach = max_distance_m + self._step_m
        candidates = {
            match.hit.value for match in self._tree.query_radius(latitude, longitude, reach)
        }
        best: SegmentMatch | None = None
        for segment_id in sorted(candidates):
            found = project_on_polyline(latitude, longitude, self._lines[segment_id])
            if found.distance_m > max_distance_m:
                continue
            if best is None or found.distance_m < best.distance_m:
                best = SegmentMatch(
                    segment_id, found.latitude, found.longitude, found.fraction, found.distance_m
                )
        return best
