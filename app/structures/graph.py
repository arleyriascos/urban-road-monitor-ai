"""Directed road graph stored as an adjacency list.

Each node of ``road_nodes`` gets an internal index from 0 to n - 1, so the
graph, the min-heap and the union-find can work with plain lists. The database
ids only appear when data enters or leaves the graph.

A one-way segment becomes one edge, from its first node to its last node (the
importer already flips OpenStreetMap ``oneway=-1`` streets). A two-way segment
becomes two edges with the same length and damage.
"""

import math
from collections.abc import Sequence
from dataclasses import dataclass


class GraphError(ValueError):
    """Raised when the graph would receive invalid data."""


@dataclass(frozen=True, slots=True)
class Edge:
    """One direction of a road segment, stored in the list of its start node."""

    target: int
    """Internal index of the node where the edge ends."""
    segment_id: int
    """Id of the segment in ``road_segments``."""
    length_m: float
    """Length of the segment in meters."""
    damage_score: float
    """Damage of the segment, from ``road_segments.damage_score``."""
    reversed: bool
    """True if the edge goes against the order of the segment geometry."""


class RoadGraph:
    """Road network of Pasto as a directed graph with an adjacency list."""

    def __init__(self) -> None:
        self._index_of: dict[int, int] = {}
        """Database node id -> internal index."""
        self._node_ids: list[int] = []
        """Internal index -> database node id."""
        self._latitudes: list[float] = []
        self._longitudes: list[float] = []
        self._adjacency: list[list[Edge]] = []
        """Edges that leave each node."""
        self._segment_ids: set[int] = set()
        self._edge_count = 0

    @property
    def node_count(self) -> int:
        return len(self._node_ids)

    @property
    def edge_count(self) -> int:
        return self._edge_count

    @property
    def segment_count(self) -> int:
        return len(self._segment_ids)

    def add_node(self, node_id: int, latitude: float, longitude: float) -> int:
        """Add an intersection and return its internal index."""
        if node_id in self._index_of:
            raise GraphError(f"node {node_id} was already added")
        if not (math.isfinite(latitude) and -90 <= latitude <= 90):
            raise GraphError(f"node {node_id} has an invalid latitude: {latitude}")
        if not (math.isfinite(longitude) and -180 <= longitude <= 180):
            raise GraphError(f"node {node_id} has an invalid longitude: {longitude}")
        index = len(self._node_ids)
        self._index_of[node_id] = index
        self._node_ids.append(node_id)
        self._latitudes.append(latitude)
        self._longitudes.append(longitude)
        self._adjacency.append([])
        return index

    def has_node(self, node_id: int) -> bool:
        return node_id in self._index_of

    def index_of(self, node_id: int) -> int:
        """Internal index of a database node id."""
        try:
            return self._index_of[node_id]
        except KeyError:
            raise GraphError(f"node {node_id} is not in the graph") from None

    def node_id(self, index: int) -> int:
        """Database node id of an internal index."""
        self._check_index(index)
        return self._node_ids[index]

    def coordinates(self, index: int) -> tuple[float, float]:
        """Latitude and longitude of a node."""
        self._check_index(index)
        return self._latitudes[index], self._longitudes[index]

    def add_segment(
        self,
        segment_id: int,
        from_node_id: int,
        to_node_id: int,
        length_m: float,
        damage_score: float,
        is_oneway: bool,
    ) -> None:
        """Add a road segment as one edge (one-way) or two edges (two-way)."""
        if segment_id in self._segment_ids:
            raise GraphError(f"segment {segment_id} was already added")
        if not (math.isfinite(length_m) and length_m >= 0):
            raise GraphError(f"segment {segment_id} has an invalid length: {length_m}")
        if not (math.isfinite(damage_score) and damage_score >= 0):
            raise GraphError(f"segment {segment_id} has an invalid damage: {damage_score}")
        start = self._index_for_segment(segment_id, from_node_id)
        end = self._index_for_segment(segment_id, to_node_id)

        self._segment_ids.add(segment_id)
        self._adjacency[start].append(Edge(end, segment_id, length_m, damage_score, False))
        self._edge_count += 1
        if not is_oneway:
            self._adjacency[end].append(Edge(start, segment_id, length_m, damage_score, True))
            self._edge_count += 1

    def neighbors(self, index: int) -> Sequence[Edge]:
        """Edges that leave a node, in the order they were added."""
        self._check_index(index)
        return tuple(self._adjacency[index])

    def _index_for_segment(self, segment_id: int, node_id: int) -> int:
        index = self._index_of.get(node_id)
        if index is None:
            raise GraphError(f"segment {segment_id} uses node {node_id}, which is not in the graph")
        return index

    def _check_index(self, index: int) -> None:
        if not 0 <= index < len(self._node_ids):
            raise GraphError(f"index {index} is outside 0..{len(self._node_ids) - 1}")
