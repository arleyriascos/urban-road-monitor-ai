import math

import pytest

from app.clustering.dbscan import NOISE, dbscan
from app.clustering.models import ClusteringError

# About 1.1 meters per 0.00001 degrees of latitude near Pasto.
STEP = 0.00001


def line(count: int, start_lat: float = 1.2136, lon: float = -77.2811) -> list[tuple[float, float]]:
    """Points one meter apart going north."""
    return [(start_lat + i * STEP, lon) for i in range(count)]


def test_no_points_give_no_labels() -> None:
    assert dbscan([], 5.0, 2) == []


def test_a_single_point_is_noise_when_two_are_needed() -> None:
    assert dbscan([(1.2136, -77.2811)], 5.0, 2) == [NOISE]


def test_a_single_point_is_its_own_cluster_when_one_is_enough() -> None:
    assert dbscan([(1.2136, -77.2811)], 5.0, 1) == [0]


def test_two_points_close_together_make_one_cluster() -> None:
    assert dbscan([(1.2136, -77.2811), (1.21361, -77.2811)], 5.0, 2) == [0, 0]


def test_two_points_far_apart_are_both_noise() -> None:
    assert dbscan([(1.2136, -77.2811), (1.2200, -77.2700)], 5.0, 2) == [NOISE, NOISE]


def test_two_separate_potholes_make_two_clusters_and_a_loner_is_noise() -> None:
    points = [
        (1.2136, -77.2811),
        (1.21361, -77.2811),
        (1.2200, -77.2700),
        (1.22001, -77.2700),
        (1.2300, -77.2600),
    ]

    assert dbscan(points, 5.0, 2) == [0, 0, 1, 1, NOISE]


def test_a_chain_of_points_one_meter_apart_is_one_cluster_even_if_it_is_long() -> None:
    labels = dbscan(line(40), 5.0, 2)  # 40 meters long, each point only sees its neighbors

    assert set(labels) == {0}


def test_a_gap_larger_than_eps_cuts_the_chain_in_two() -> None:
    points = line(10) + line(10, start_lat=1.2136 + 20 * STEP)  # a 11 m gap in between

    labels = dbscan(points, 5.0, 2)

    assert labels[:10] == [0] * 10
    assert labels[10:] == [1] * 10


def test_a_border_point_joins_the_cluster_that_reaches_it() -> None:
    # Three points 1 m apart are core points for min_points=3; the one 4 m beyond sees only
    # two points (itself and the last of the three), so it is a border point, not core.
    points = [*line(3), (1.2136 + 6 * STEP, -77.2811)]

    labels = dbscan(points, 4.5, 3)

    assert labels == [0, 0, 0, 0]


def test_a_point_that_is_not_dense_enough_stays_noise() -> None:
    points = [*line(3), (1.2136 + 40 * STEP, -77.2811)]

    assert dbscan(points, 4.5, 3) == [0, 0, 0, NOISE]


def test_the_same_input_always_gives_the_same_labels() -> None:
    points = line(5) + line(5, start_lat=1.2300)

    assert dbscan(points, 5.0, 2) == dbscan(points, 5.0, 2)


def test_duplicated_points_form_a_cluster() -> None:
    assert dbscan([(1.2136, -77.2811)] * 4, 5.0, 4) == [0, 0, 0, 0]


@pytest.mark.parametrize("eps", [0.0, -1.0, math.nan, math.inf])
def test_eps_must_be_a_positive_distance(eps: float) -> None:
    with pytest.raises(ClusteringError, match="eps_m"):
        dbscan([(1.0, 1.0)], eps, 2)


def test_min_points_must_be_at_least_one() -> None:
    with pytest.raises(ClusteringError, match="min_points"):
        dbscan([(1.0, 1.0)], 5.0, 0)
