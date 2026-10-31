"""Examples of the union-find: each test shows one behavior."""

import pytest

from app.structures.union_find import UnionFind, UnionFindError


def test_starts_with_every_element_in_its_own_set() -> None:
    sets = UnionFind(4)

    assert len(sets) == 4
    assert sets.count == 4
    assert [sets.find(x) for x in range(4)] == [0, 1, 2, 3]
    assert not sets.connected(0, 1)


def test_union_joins_two_sets() -> None:
    sets = UnionFind(4)

    assert sets.union(0, 1)

    assert sets.connected(0, 1)
    assert not sets.connected(0, 2)
    assert sets.count == 3
    assert sets.size(1) == 2


def test_union_of_elements_already_joined_returns_false() -> None:
    sets = UnionFind(3)
    sets.union(0, 1)
    sets.union(1, 2)

    assert not sets.union(0, 2)
    assert sets.count == 1


def test_connection_is_transitive() -> None:
    sets = UnionFind(5)
    sets.union(0, 1)
    sets.union(1, 2)
    sets.union(3, 4)

    assert sets.connected(0, 2)
    assert not sets.connected(2, 3)
    assert sets.size(0) == 3
    assert sets.size(4) == 2


def test_the_larger_set_keeps_its_root() -> None:
    sets = UnionFind(5)
    sets.union(3, 4)
    sets.union(4, 2)  # {2, 3, 4} with root 3

    sets.union(0, 4)  # {0} is smaller, so it hangs under root 3

    assert sets.find(0) == 3


def test_on_equal_sizes_the_lower_root_wins() -> None:
    sets = UnionFind(4)

    sets.union(3, 1)

    assert sets.find(3) == 1


def test_find_compresses_the_path() -> None:
    sets = UnionFind(4)
    sets.union(0, 1)
    sets.union(2, 3)
    sets.union(1, 3)  # root 0; 3 hangs from 2, and 2 from 0

    root = sets.find(3)

    assert root == 0
    assert sets._parent[3] == 0  # after find, 3 points straight at the root


def test_largest_root_points_at_the_biggest_set() -> None:
    sets = UnionFind(6)
    sets.union(4, 5)
    sets.union(1, 2)
    sets.union(2, 3)

    assert sets.find(sets.largest_root()) == sets.find(1)
    assert sets.size(sets.largest_root()) == 3


def test_largest_root_breaks_ties_with_the_lowest_root() -> None:
    sets = UnionFind(4)
    sets.union(2, 3)
    sets.union(0, 1)

    assert sets.largest_root() == 0


def test_stays_valid_after_many_unions() -> None:
    sets = UnionFind(10)
    for a, b in [(0, 1), (2, 3), (1, 3), (5, 6), (7, 8), (6, 8), (9, 9)]:
        sets.union(a, b)

    assert sets.is_valid()
    assert sets.count == 4


@pytest.mark.parametrize("element", [-1, 3])
def test_rejects_elements_outside_the_range(element: int) -> None:
    sets = UnionFind(3)

    with pytest.raises(UnionFindError, match="outside"):
        sets.find(element)


def test_rejects_a_negative_number_of_elements() -> None:
    with pytest.raises(UnionFindError, match="negative"):
        UnionFind(-2)


def test_largest_root_needs_at_least_one_element() -> None:
    sets = UnionFind(0)

    with pytest.raises(UnionFindError, match="no elements"):
        sets.largest_root()
