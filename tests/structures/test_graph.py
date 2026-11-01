"""Nodes, edges and validation of the road graph."""

import dataclasses
import math

import pytest

from app.structures.graph import Edge, GraphError, RoadGraph


def test_counts_nodes_segments_and_edges(sample_graph: RoadGraph) -> None:
    assert sample_graph.node_count == 7
    assert sample_graph.segment_count == 5
    # Three two-way segments give two edges each; two one-way segments give one.
    assert sample_graph.edge_count == 8


def test_gives_consecutive_indexes_in_insertion_order(sample_graph: RoadGraph) -> None:
    assert [sample_graph.index_of(node_id) for node_id in (101, 102, 202)] == [0, 1, 6]
    assert sample_graph.node_id(3) == 104


def test_keeps_the_coordinates_of_each_node(sample_graph: RoadGraph) -> None:
    index = sample_graph.index_of(105)

    assert sample_graph.coordinates(index) == (1.2130, -77.2790)


def test_a_two_way_segment_creates_edges_in_both_directions(sample_graph: RoadGraph) -> None:
    a = sample_graph.index_of(101)
    b = sample_graph.index_of(102)

    forward = [edge for edge in sample_graph.neighbors(a) if edge.segment_id == 1001]
    backward = [edge for edge in sample_graph.neighbors(b) if edge.segment_id == 1001]

    assert forward == [Edge(b, 1001, 112.0, 0.0, False)]
    assert backward == [Edge(a, 1001, 112.0, 0.0, True)]


def test_a_one_way_segment_creates_a_single_edge(sample_graph: RoadGraph) -> None:
    start = sample_graph.index_of(102)
    end = sample_graph.index_of(104)

    assert Edge(end, 1003, 101.0, 0.0, False) in sample_graph.neighbors(start)
    assert sample_graph.neighbors(end) == ()


def test_a_flipped_one_way_street_only_goes_from_its_first_node(
    sample_graph: RoadGraph,
) -> None:
    south = sample_graph.index_of(105)
    north = sample_graph.index_of(103)

    assert [edge.target for edge in sample_graph.neighbors(south)] == [north]
    assert all(edge.segment_id != 1004 for edge in sample_graph.neighbors(north))


def test_neighbors_keep_the_order_in_which_segments_were_added(
    sample_graph: RoadGraph,
) -> None:
    middle = sample_graph.index_of(102)

    segments = [(edge.segment_id, edge.reversed) for edge in sample_graph.neighbors(middle)]

    assert segments == [(1001, True), (1002, False), (1003, False)]


def test_neighbors_cannot_change_the_graph(sample_graph: RoadGraph) -> None:
    edges = sample_graph.neighbors(0)

    assert isinstance(edges, tuple)
    with pytest.raises(dataclasses.FrozenInstanceError):
        edges[0].length_m = 1.0


def test_an_empty_graph_has_no_nodes() -> None:
    graph = RoadGraph()

    assert (graph.node_count, graph.edge_count, graph.segment_count) == (0, 0, 0)
    assert not graph.has_node(101)


def test_rejects_a_repeated_node(sample_graph: RoadGraph) -> None:
    with pytest.raises(GraphError, match="already added"):
        sample_graph.add_node(101, 1.0, -77.0)


@pytest.mark.parametrize(
    ("latitude", "longitude"),
    [(91.0, -77.0), (1.0, -181.0), (math.nan, -77.0), (1.0, math.inf)],
)
def test_rejects_invalid_coordinates(latitude: float, longitude: float) -> None:
    graph = RoadGraph()

    with pytest.raises(GraphError, match="invalid"):
        graph.add_node(1, latitude, longitude)


def test_rejects_a_repeated_segment(sample_graph: RoadGraph) -> None:
    with pytest.raises(GraphError, match="already added"):
        sample_graph.add_segment(1001, 101, 102, 112.0, 0.0, False)


def test_rejects_a_segment_with_an_unknown_node(sample_graph: RoadGraph) -> None:
    with pytest.raises(GraphError, match="not in the graph"):
        sample_graph.add_segment(2000, 101, 999, 50.0, 0.0, False)

    assert sample_graph.segment_count == 5  # nothing was added


@pytest.mark.parametrize(
    ("length_m", "damage_score"),
    [(-1.0, 0.0), (math.nan, 0.0), (300.0, -0.5), (300.0, math.inf)],
)
def test_rejects_negative_or_invalid_lengths_and_damage(
    sample_graph: RoadGraph, length_m: float, damage_score: float
) -> None:
    with pytest.raises(GraphError, match="invalid"):
        sample_graph.add_segment(2000, 101, 103, length_m, damage_score, False)


def test_rejects_unknown_ids_and_indexes(sample_graph: RoadGraph) -> None:
    with pytest.raises(GraphError, match="not in the graph"):
        sample_graph.index_of(999)
    with pytest.raises(GraphError, match="outside"):
        sample_graph.node_id(7)
    with pytest.raises(GraphError, match="outside"):
        sample_graph.neighbors(-1)
