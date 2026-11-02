"""A segment is never shorter than the straight line between its nodes."""

import math
import random

import pytest

from app.geo import haversine_m
from app.structures.graph import LENGTH_TOLERANCE_M, GraphError, RoadGraph


def straight_line_m(graph: RoadGraph, first_id: int, second_id: int) -> float:
    a = graph.coordinates(graph.index_of(first_id))
    b = graph.coordinates(graph.index_of(second_id))
    return haversine_m(*a, *b)


def test_a_length_a_few_millimeters_short_is_raised_to_the_straight_line(
    sample_graph: RoadGraph,
) -> None:
    straight = straight_line_m(sample_graph, 101, 105)

    sample_graph.add_segment(2001, 101, 105, round(straight - 0.004, 2), 0.0, False)

    edge = next(e for e in sample_graph.neighbors(0) if e.segment_id == 2001)
    assert edge.length_m == pytest.approx(straight, abs=1e-9)
    assert edge.length_m >= straight


def test_both_directions_of_a_two_way_segment_get_the_corrected_length(
    sample_graph: RoadGraph,
) -> None:
    straight = straight_line_m(sample_graph, 101, 105)

    sample_graph.add_segment(2001, 101, 105, straight - 0.004, 0.0, False)

    forward = next(
        e for e in sample_graph.neighbors(sample_graph.index_of(101)) if e.segment_id == 2001
    )
    backward = next(
        e for e in sample_graph.neighbors(sample_graph.index_of(105)) if e.segment_id == 2001
    )
    assert forward.length_m == backward.length_m >= straight


def test_a_length_above_the_straight_line_is_kept_as_given(sample_graph: RoadGraph) -> None:
    straight = straight_line_m(sample_graph, 101, 105)

    sample_graph.add_segment(2001, 101, 105, straight + 40.0, 0.0, True)

    edge = next(e for e in sample_graph.neighbors(0) if e.segment_id == 2001)
    assert edge.length_m == straight + 40.0


def test_a_length_exactly_the_tolerance_short_is_accepted(sample_graph: RoadGraph) -> None:
    straight = straight_line_m(sample_graph, 101, 105)

    sample_graph.add_segment(2001, 101, 105, straight - LENGTH_TOLERANCE_M, 0.0, True)

    assert sample_graph.segment_count == 6


def test_a_length_16_centimeters_short_is_raised_to_the_straight_line(
    sample_graph: RoadGraph,
) -> None:
    straight = straight_line_m(sample_graph, 101, 105)

    sample_graph.add_segment(2001, 101, 105, straight - 0.16, 0.0, True)

    edge = next(e for e in sample_graph.neighbors(0) if e.segment_id == 2001)
    assert edge.length_m == pytest.approx(straight, abs=1e-9)


def test_rejects_a_length_shorter_than_the_straight_line(sample_graph: RoadGraph) -> None:
    straight = straight_line_m(sample_graph, 101, 105)

    with pytest.raises(GraphError, match="in a straight line"):
        sample_graph.add_segment(2001, 101, 105, straight - LENGTH_TOLERANCE_M - 0.05, 0.0, False)

    assert sample_graph.segment_count == 5  # nothing was added
    assert sample_graph.edge_count == 8


def test_rejects_the_unrealistic_lengths_of_the_old_sample_network(
    sample_graph: RoadGraph,
) -> None:
    with pytest.raises(GraphError, match="in a straight line"):
        sample_graph.add_segment(2002, 101, 102, 110.0, 0.0, False)


def test_a_segment_between_two_nodes_at_the_same_place_may_have_zero_length() -> None:
    graph = RoadGraph()
    graph.add_node(1, 1.2, -77.2)
    graph.add_node(2, 1.2, -77.2)

    graph.add_segment(1, 1, 2, 0.0, 0.0, True)

    assert graph.neighbors(0)[0].length_m == 0.0


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_accepts_segments_rounded_the_way_the_backend_importer_rounds_them(seed: int) -> None:
    """The importer measures with 7-decimal coordinates and stores nodes with 6 decimals."""
    rng = random.Random(seed)
    graph = RoadGraph()

    for index in range(2_000):
        latitude = round(rng.uniform(1.19, 1.24), 7)
        longitude = round(rng.uniform(-77.30, -77.24), 7)
        meters = rng.uniform(3.0, 150.0)
        angle = rng.uniform(0.0, 2 * math.pi)
        end_latitude = round(latitude + meters * math.cos(angle) / 111_195.0, 7)
        end_longitude = round(longitude + meters * math.sin(angle) / 111_195.0, 7)
        length_m = round(haversine_m(latitude, longitude, end_latitude, end_longitude), 2)

        start, end = 2 * index, 2 * index + 1
        graph.add_node(start, round(latitude, 6), round(longitude, 6))
        graph.add_node(end, round(end_latitude, 6), round(end_longitude, 6))
        graph.add_segment(index, start, end, length_m, 0.0, False)

    assert graph.segment_count == 2_000
