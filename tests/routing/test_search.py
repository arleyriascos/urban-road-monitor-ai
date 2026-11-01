"""Examples of Dijkstra and A*: each test shows one behavior.

Every behavior that does not depend on the algorithm runs with both.
"""

import dataclasses
import math
from collections.abc import Callable

import pytest

from app.routing.errors import NoRouteError
from app.routing.result import RouteResult
from app.routing.search import a_star, dijkstra
from app.structures.graph import GraphError, RoadGraph

SearchFunction = Callable[[RoadGraph, int, int, float], RouteResult]

both_algorithms = pytest.mark.parametrize("search", [dijkstra, a_star], ids=["dijkstra", "a_star"])


def index(graph: RoadGraph, node_id: int) -> int:
    return graph.index_of(node_id)


@both_algorithms
def test_follows_the_streets_from_origin_to_destination(
    sample_graph: RoadGraph, search: SearchFunction
) -> None:
    result = search(sample_graph, index(sample_graph, 101), index(sample_graph, 103), 0.0)

    assert [sample_graph.node_id(i) for i in result.node_indexes] == [101, 102, 103]
    assert [step.segment_id for step in result.steps] == [1001, 1002]
    assert [step.reversed for step in result.steps] == [False, False]
    assert result.total_length_m == pytest.approx(224.0)
    assert result.total_cost == pytest.approx(224.0)


@both_algorithms
def test_damage_makes_a_segment_cost_more_when_k_grows(
    sample_graph: RoadGraph, search: SearchFunction
) -> None:
    origin, destination = index(sample_graph, 101), index(sample_graph, 103)

    # Segment 1001 has no damage; segment 1002 has damage 2.0.
    assert search(sample_graph, origin, destination, 0.0).total_cost == pytest.approx(224.0)
    assert search(sample_graph, origin, destination, 1.0).total_cost == pytest.approx(112 + 336)
    assert search(sample_graph, origin, destination, 3.0).total_cost == pytest.approx(112 + 784)


@both_algorithms
def test_the_steps_carry_their_own_cost(sample_graph: RoadGraph, search: SearchFunction) -> None:
    result = search(sample_graph, index(sample_graph, 101), index(sample_graph, 103), 1.0)

    first, second = result.steps
    assert (first.length_m, first.damage_score, first.cost) == (112.0, 0.0, 112.0)
    assert (second.length_m, second.damage_score) == (112.0, 2.0)
    assert second.cost == pytest.approx(336.0)
    assert result.total_cost == pytest.approx(first.cost + second.cost)


@both_algorithms
def test_steps_come_in_travel_order_with_the_direction_of_each_segment(
    sample_graph: RoadGraph, search: SearchFunction
) -> None:
    # 105 -> 103 is the one-way street; the other two segments are crossed backwards.
    result = search(sample_graph, index(sample_graph, 105), index(sample_graph, 101), 0.0)

    assert [sample_graph.node_id(i) for i in result.node_indexes] == [105, 103, 102, 101]
    assert [step.segment_id for step in result.steps] == [1004, 1002, 1001]
    assert [step.reversed for step in result.steps] == [False, True, True]


@both_algorithms
def test_a_two_way_street_can_be_crossed_in_both_directions(
    sample_graph: RoadGraph, search: SearchFunction
) -> None:
    a, b = index(sample_graph, 101), index(sample_graph, 102)

    assert search(sample_graph, a, b, 1.0).steps[0].reversed is False
    assert search(sample_graph, b, a, 1.0).steps[0].reversed is True


@both_algorithms
def test_a_one_way_street_can_only_be_crossed_in_its_direction(
    sample_graph: RoadGraph, search: SearchFunction
) -> None:
    middle, dead_end = index(sample_graph, 102), index(sample_graph, 104)

    assert search(sample_graph, middle, dead_end, 1.0).steps[0].segment_id == 1003
    with pytest.raises(NoRouteError):
        search(sample_graph, dead_end, middle, 1.0)


@both_algorithms
def test_the_same_origin_and_destination_give_a_route_without_steps(
    sample_graph: RoadGraph, search: SearchFunction
) -> None:
    node = index(sample_graph, 102)

    result = search(sample_graph, node, node, 1.0)

    assert result.steps == ()
    assert result.node_indexes == (node,)
    assert result.total_length_m == 0.0
    assert result.total_cost == 0.0
    assert result.explored_nodes == 1


@both_algorithms
def test_no_route_when_one_way_streets_block_the_way(
    sample_graph: RoadGraph, search: SearchFunction
) -> None:
    south, west = index(sample_graph, 105), index(sample_graph, 101)

    with pytest.raises(NoRouteError) as error:
        search(sample_graph, west, south, 1.0)  # 105 only has an exit, no street leads to it

    assert (error.value.source, error.value.target) == (west, south)
    assert "one-way" in str(error.value)


@both_algorithms
def test_no_route_to_a_loose_piece_of_road(sample_graph: RoadGraph, search: SearchFunction) -> None:
    with pytest.raises(NoRouteError):
        search(sample_graph, index(sample_graph, 101), index(sample_graph, 201), 1.0)


@both_algorithms
def test_the_damage_factor_chooses_between_the_short_road_and_the_clean_detour(
    diamond_graph: RoadGraph, search: SearchFunction
) -> None:
    origin, destination = index(diamond_graph, 301), index(diamond_graph, 302)

    shortest = search(diamond_graph, origin, destination, 0.0)
    balanced = search(diamond_graph, origin, destination, 1.0)
    avoiding = search(diamond_graph, origin, destination, 3.0)

    assert [step.segment_id for step in shortest.steps] == [3001]
    assert [step.segment_id for step in balanced.steps] == [3001]
    assert [step.segment_id for step in avoiding.steps] == [3002, 3003]
    assert avoiding.total_length_m == pytest.approx(316.0)
    assert avoiding.total_cost == pytest.approx(316.0)


@both_algorithms
def test_the_result_reports_the_algorithm_and_what_it_explored(
    sample_graph: RoadGraph, search: SearchFunction
) -> None:
    result = search(sample_graph, index(sample_graph, 101), index(sample_graph, 102), 1.0)

    assert result.algorithm == search.__name__
    assert result.explored_nodes == 2  # the origin and the destination
    assert result.explored_nodes < sample_graph.node_count


@both_algorithms
def test_the_result_cannot_be_modified(sample_graph: RoadGraph, search: SearchFunction) -> None:
    result = search(sample_graph, index(sample_graph, 101), index(sample_graph, 102), 1.0)

    with pytest.raises(dataclasses.FrozenInstanceError):
        result.total_cost = 0.0  # type: ignore[misc]
    with pytest.raises(dataclasses.FrozenInstanceError):
        result.steps[0].cost = 0.0  # type: ignore[misc]


@both_algorithms
@pytest.mark.parametrize("k", [-1.0, math.nan, math.inf])
def test_rejects_an_invalid_damage_factor(
    sample_graph: RoadGraph, search: SearchFunction, k: float
) -> None:
    with pytest.raises(GraphError, match="damage factor"):
        search(sample_graph, 0, 1, k)


@both_algorithms
def test_rejects_the_damage_factor_even_when_no_edge_is_crossed(
    sample_graph: RoadGraph, search: SearchFunction
) -> None:
    with pytest.raises(GraphError, match="damage factor"):
        search(sample_graph, 0, 0, -1.0)


@both_algorithms
@pytest.mark.parametrize(("source", "target"), [(-1, 0), (0, 7), (7, 0), (0, -1)])
def test_rejects_nodes_outside_the_graph(
    sample_graph: RoadGraph, search: SearchFunction, source: int, target: int
) -> None:
    with pytest.raises(GraphError, match="outside"):
        search(sample_graph, source, target, 1.0)


def test_both_algorithms_agree_on_every_pair_of_the_sample_network(
    sample_graph: RoadGraph,
) -> None:
    for k in (0.0, 1.0, 3.0):
        for source in range(sample_graph.node_count):
            for target in range(sample_graph.node_count):
                try:
                    expected = dijkstra(sample_graph, source, target, k)
                except NoRouteError:
                    with pytest.raises(NoRouteError):
                        a_star(sample_graph, source, target, k)
                    continue
                found = a_star(sample_graph, source, target, k)
                assert found.total_cost == pytest.approx(expected.total_cost, rel=1e-9)
