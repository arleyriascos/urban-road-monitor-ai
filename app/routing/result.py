"""What a route search returns."""

from dataclasses import dataclass
from typing import Literal

Algorithm = Literal["dijkstra", "a_star"]


@dataclass(frozen=True, slots=True)
class RouteStep:
    """One road segment crossed by the route."""

    segment_id: int
    """Id of the segment in ``road_segments``."""
    reversed: bool
    """True if the route crosses the segment against the order of its geometry."""
    length_m: float
    """Length of the segment in meters."""
    damage_score: float
    """Damage of the segment."""
    cost: float
    """Cost of crossing it with the damage factor k of the search."""


@dataclass(frozen=True, slots=True)
class RouteResult:
    """A route between two nodes, with the data to draw it and to compare algorithms."""

    algorithm: Algorithm
    steps: tuple[RouteStep, ...]
    """Segments in travel order. Empty if the origin and the destination are the same node."""
    node_indexes: tuple[int, ...]
    """Internal indexes of the nodes from the origin to the destination."""
    total_length_m: float
    total_cost: float
    explored_nodes: int
    """Nodes taken out of the heap by the search. A* takes out fewer than Dijkstra."""
