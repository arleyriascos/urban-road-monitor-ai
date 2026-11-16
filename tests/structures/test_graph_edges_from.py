"""Walking the edges of a node with edges_from, and the adjacency lists behind it."""

import random

import pytest

from app.structures.graph import GraphError, RoadGraph


def test_gives_the_same_edges_as_neighbors_for_every_node(sample_graph: RoadGraph) -> None:
    for index in range(sample_graph.node_count):
        assert list(sample_graph.edges_from(index)) == list(sample_graph.neighbors(index))


def test_keeps_the_order_in_which_segments_were_added(sample_graph: RoadGraph) -> None:
    middle = sample_graph.index_of(102)

    segments = [(edge.segment_id, edge.reversed) for edge in sample_graph.edges_from(middle)]

    assert segments == [(1001, True), (1002, False), (1003, False)]


def test_a_node_without_outgoing_edges_gives_nothing(sample_graph: RoadGraph) -> None:
    dead_end = sample_graph.index_of(104)

    assert list(sample_graph.edges_from(dead_end)) == []


def test_a_two_way_segment_is_walked_from_both_ends(sample_graph: RoadGraph) -> None:
    a = sample_graph.index_of(101)
    b = sample_graph.index_of(102)

    assert [(e.target, e.reversed) for e in sample_graph.edges_from(a) if e.segment_id == 1001] == [
        (b, False)
    ]
    assert [(e.target, e.reversed) for e in sample_graph.edges_from(b) if e.segment_id == 1001] == [
        (a, True)
    ]


def test_every_call_starts_a_new_walk(sample_graph: RoadGraph) -> None:
    middle = sample_graph.index_of(102)

    first = list(sample_graph.edges_from(middle))
    second = list(sample_graph.edges_from(middle))

    assert first == second
    assert len(first) == 3


def test_walks_are_independent_of_each_other(sample_graph: RoadGraph) -> None:
    middle = sample_graph.index_of(102)

    outer = sample_graph.edges_from(middle)
    first_of_outer = next(outer)
    inner = list(sample_graph.edges_from(middle))

    assert first_of_outer == inner[0]
    assert list(outer) == inner[1:]


@pytest.mark.parametrize("index", [-1, 7, 100])
def test_rejects_an_index_outside_the_graph(sample_graph: RoadGraph, index: int) -> None:
    with pytest.raises(GraphError):
        sample_graph.edges_from(index)


@pytest.mark.parametrize("seed", [1, 2, 3, 4, 5])
def test_matches_a_reference_on_random_networks(seed: int) -> None:
    """Build a random network and compare the edges of every node with plain Python lists."""
    rng = random.Random(seed)
    nodes = rng.randint(5, 40)
    graph = RoadGraph()
    for node_id in range(nodes):
        graph.add_node(node_id, 1.0 + node_id * 0.0005, -77.0 + rng.random() * 0.0005)
    expected: list[list[tuple[int, int, bool]]] = [[] for _ in range(nodes)]

    for segment_id in range(rng.randint(nodes, nodes * 3)):
        start, end = rng.sample(range(nodes), 2)
        one_way = rng.random() < 0.4
        graph.add_segment(segment_id, start, end, 5000.0, rng.random(), one_way)
        expected[start].append((end, segment_id, False))
        if not one_way:
            expected[end].append((start, segment_id, True))

    for index in range(nodes):
        walked = [(e.target, e.segment_id, e.reversed) for e in graph.edges_from(index)]
        assert walked == expected[index]
    assert sum(len(edges) for edges in expected) == graph.edge_count
