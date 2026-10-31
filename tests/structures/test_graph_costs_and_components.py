"""Edge costs with the damage factor k, and connected components."""

import math

import pytest

from app.structures.graph import Edge, GraphError, RoadGraph


@pytest.mark.parametrize(("k", "expected"), [(0.0, 110.0), (1.0, 330.0), (3.0, 770.0)])
def test_cost_grows_with_the_damage_factor(k: float, expected: float) -> None:
    edge = Edge(target=2, segment_id=1002, length_m=110.0, damage_score=2.0, reversed=False)

    assert edge.cost(k) == pytest.approx(expected)


def test_cost_of_an_undamaged_edge_is_its_length() -> None:
    edge = Edge(target=1, segment_id=1001, length_m=110.0, damage_score=0.0, reversed=False)

    assert edge.cost(3.0) == 110.0


@pytest.mark.parametrize("k", [0.0, 0.5, 1.0, 3.0, 10.0])
def test_cost_is_never_below_the_length(sample_graph: RoadGraph, k: float) -> None:
    for index in range(sample_graph.node_count):
        for edge in sample_graph.neighbors(index):
            assert edge.cost(k) >= edge.length_m


@pytest.mark.parametrize("k", [-1.0, math.nan, math.inf])
def test_rejects_an_invalid_damage_factor(k: float) -> None:
    edge = Edge(target=1, segment_id=1001, length_m=110.0, damage_score=0.0, reversed=False)

    with pytest.raises(GraphError, match="damage factor"):
        edge.cost(k)


def test_components_separate_the_loose_parking_lot(sample_graph: RoadGraph) -> None:
    sets = sample_graph.components()

    assert sets.count == 2
    streets = [sample_graph.index_of(node_id) for node_id in (101, 102, 103, 104, 105)]
    parking = [sample_graph.index_of(node_id) for node_id in (201, 202)]
    assert all(sets.connected(streets[0], node) for node in streets)
    assert sets.connected(parking[0], parking[1])
    assert not sets.connected(streets[0], parking[0])


def test_the_largest_component_is_the_street_network(sample_graph: RoadGraph) -> None:
    sets = sample_graph.components()

    root = sets.largest_root()

    assert sets.size(root) == 5
    assert sets.connected(root, sample_graph.index_of(101))


def test_components_ignore_one_way_rules(sample_graph: RoadGraph) -> None:
    sets = sample_graph.components()
    dead_end = sample_graph.index_of(104)  # reachable, but no edge leaves it

    assert sets.connected(dead_end, sample_graph.index_of(101))


def test_components_of_an_empty_graph() -> None:
    assert RoadGraph().components().count == 0
