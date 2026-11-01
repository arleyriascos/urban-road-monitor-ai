"""Examples of the click locator: each test shows one behavior."""

import math
import random

import pytest

from app.geo import haversine_m
from app.routing.errors import InvalidPointError, OutsideNetworkError
from app.routing.locator import DEFAULT_MAX_DISTANCE_M, NodeLocator
from app.structures.graph import GraphError, RoadGraph


def test_a_click_on_an_intersection_snaps_to_it(sample_graph: RoadGraph) -> None:
    locator = NodeLocator(sample_graph)
    latitude, longitude = sample_graph.coordinates(sample_graph.index_of(102))

    snapped = locator.snap(latitude, longitude)

    assert sample_graph.node_id(snapped.index) == 102
    assert snapped.distance_m == 0.0


def test_a_click_near_an_intersection_snaps_to_the_nearest_one(sample_graph: RoadGraph) -> None:
    locator = NodeLocator(sample_graph)

    snapped = locator.snap(1.21415, -77.27995)  # a few meters from 102

    assert sample_graph.node_id(snapped.index) == 102
    assert 0 < snapped.distance_m < 20


def test_the_distance_is_measured_to_the_chosen_node(sample_graph: RoadGraph) -> None:
    locator = NodeLocator(sample_graph)

    snapped = locator.snap(1.2143, -77.2812)
    latitude, longitude = sample_graph.coordinates(snapped.index)

    assert snapped.distance_m == pytest.approx(haversine_m(1.2143, -77.2812, latitude, longitude))


def test_on_a_tie_the_lowest_index_wins() -> None:
    graph = RoadGraph()
    graph.add_node(10, 1.2000, -77.2800)
    graph.add_node(11, 1.2000, -77.2800)  # same place as node 10
    graph.add_segment(1, 10, 11, 0.0, 0.0, False)

    snapped = NodeLocator(graph).snap(1.2000, -77.2800)

    assert snapped.index == 0


def test_only_the_main_component_counts(sample_graph: RoadGraph) -> None:
    locator = NodeLocator(sample_graph, max_distance_m=1_000_000.0)
    parking = sample_graph.coordinates(sample_graph.index_of(201))

    snapped = locator.snap(*parking)  # a click right on the loose parking lot

    assert locator.main_component_size == 5
    assert sample_graph.node_id(snapped.index) not in (201, 202)
    assert snapped.distance_m > 1_000


def test_rejects_a_click_far_from_the_network(sample_graph: RoadGraph) -> None:
    locator = NodeLocator(sample_graph)

    with pytest.raises(OutsideNetworkError) as error:
        locator.snap(1.2200, -77.2700)  # the parking lot area, far from every street node

    assert (error.value.latitude, error.value.longitude) == (1.2200, -77.2700)
    assert error.value.distance_m > DEFAULT_MAX_DISTANCE_M
    assert error.value.max_distance_m == DEFAULT_MAX_DISTANCE_M
    assert "from the road network" in str(error.value)


def test_the_limit_is_inclusive_and_can_be_changed(sample_graph: RoadGraph) -> None:
    latitude, longitude = 1.2143, -77.2812
    distance = NodeLocator(sample_graph, max_distance_m=1_000_000.0).snap(latitude, longitude)

    assert NodeLocator(sample_graph, max_distance_m=distance.distance_m).snap(latitude, longitude)
    with pytest.raises(OutsideNetworkError):
        NodeLocator(sample_graph, max_distance_m=distance.distance_m - 0.001).snap(
            latitude, longitude
        )


@pytest.mark.parametrize(
    ("latitude", "longitude"),
    [
        (91.0, -77.0),
        (-91.0, -77.0),
        (1.2, 181.0),
        (1.2, -181.0),
        (math.nan, -77.0),
        (1.2, math.inf),
    ],
)
def test_rejects_invalid_coordinates(
    sample_graph: RoadGraph, latitude: float, longitude: float
) -> None:
    with pytest.raises(InvalidPointError):
        NodeLocator(sample_graph).snap(latitude, longitude)


@pytest.mark.parametrize("limit", [0.0, -5.0, math.nan, math.inf])
def test_rejects_an_invalid_limit(sample_graph: RoadGraph, limit: float) -> None:
    with pytest.raises(GraphError, match="max_distance_m"):
        NodeLocator(sample_graph, max_distance_m=limit)


def test_rejects_an_empty_graph() -> None:
    with pytest.raises(GraphError, match="no nodes"):
        NodeLocator(RoadGraph())


def test_the_nearest_node_is_never_beaten_by_another_node_of_the_network(
    sample_graph: RoadGraph,
) -> None:
    rng = random.Random(11)
    locator = NodeLocator(sample_graph, max_distance_m=1_000_000.0)
    main_network = [sample_graph.index_of(node_id) for node_id in (101, 102, 103, 104, 105)]

    for _ in range(300):
        latitude = rng.uniform(1.2120, 1.2160)
        longitude = rng.uniform(-77.2830, -77.2780)
        snapped = locator.snap(latitude, longitude)

        assert snapped.index in main_network
        for other in main_network:
            other_latitude, other_longitude = sample_graph.coordinates(other)
            assert haversine_m(latitude, longitude, other_latitude, other_longitude) >= (
                snapped.distance_m - 1e-9
            )
