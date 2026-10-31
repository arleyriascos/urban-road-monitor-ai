"""Examples of the indexed min-heap: each test shows one behavior."""

import math

import pytest

from app.structures.min_heap import HeapError, IndexedMinHeap


def test_pops_items_from_lowest_to_highest_priority() -> None:
    heap = IndexedMinHeap(5)
    for item, priority in [(0, 7.0), (1, 2.5), (2, 9.0), (3, 0.5), (4, 4.0)]:
        heap.push(item, priority)

    popped = [heap.pop_min() for _ in range(5)]

    assert popped == [(3, 0.5), (1, 2.5), (4, 4.0), (0, 7.0), (2, 9.0)]
    assert heap.is_empty()


def test_breaks_ties_with_the_lower_item() -> None:
    heap = IndexedMinHeap(4)
    for item in (3, 1, 2, 0):
        heap.push(item, 5.0)

    assert [heap.pop_min()[0] for _ in range(4)] == [0, 1, 2, 3]


def test_peek_returns_the_minimum_without_removing_it() -> None:
    heap = IndexedMinHeap(3)
    heap.push(2, 1.0)
    heap.push(0, 3.0)

    assert heap.peek_min() == (2, 1.0)
    assert len(heap) == 2


def test_decrease_key_moves_an_item_to_the_top() -> None:
    heap = IndexedMinHeap(4)
    for item, priority in [(0, 10.0), (1, 20.0), (2, 30.0), (3, 40.0)]:
        heap.push(item, priority)

    heap.decrease_key(3, 5.0)

    assert heap.priority_of(3) == 5.0
    assert heap.pop_min() == (3, 5.0)
    assert heap.is_valid()


def test_decrease_key_accepts_the_same_priority() -> None:
    heap = IndexedMinHeap(2)
    heap.push(1, 4.0)

    heap.decrease_key(1, 4.0)

    assert heap.priority_of(1) == 4.0


def test_contains_follows_push_and_pop() -> None:
    heap = IndexedMinHeap(3)
    assert not heap.contains(1)

    heap.push(1, 2.0)
    assert heap.contains(1)

    heap.pop_min()
    assert not heap.contains(1)


def test_an_item_can_return_after_being_popped() -> None:
    heap = IndexedMinHeap(2)
    heap.push(0, 1.0)
    heap.pop_min()

    heap.push(0, 8.0)

    assert heap.pop_min() == (0, 8.0)


def test_accepts_infinite_priorities() -> None:
    heap = IndexedMinHeap(2)
    heap.push(0, math.inf)
    heap.push(1, 3.0)

    assert heap.pop_min() == (1, 3.0)
    assert heap.pop_min() == (0, math.inf)


def test_rejects_pushing_an_item_twice() -> None:
    heap = IndexedMinHeap(2)
    heap.push(0, 1.0)

    with pytest.raises(HeapError, match="already in the heap"):
        heap.push(0, 0.5)


def test_rejects_raising_a_priority_with_decrease_key() -> None:
    heap = IndexedMinHeap(2)
    heap.push(0, 1.0)

    with pytest.raises(HeapError, match="higher than the current"):
        heap.decrease_key(0, 2.0)


def test_rejects_decrease_key_on_a_missing_item() -> None:
    heap = IndexedMinHeap(2)

    with pytest.raises(HeapError, match="not in the heap"):
        heap.decrease_key(1, 0.0)


def test_rejects_priority_of_a_missing_item() -> None:
    heap = IndexedMinHeap(2)

    with pytest.raises(HeapError, match="not in the heap"):
        heap.priority_of(0)


def test_rejects_popping_or_peeking_an_empty_heap() -> None:
    heap = IndexedMinHeap(1)

    with pytest.raises(HeapError, match="empty"):
        heap.pop_min()
    with pytest.raises(HeapError, match="empty"):
        heap.peek_min()


@pytest.mark.parametrize("item", [-1, 3])
def test_rejects_items_outside_the_capacity(item: int) -> None:
    heap = IndexedMinHeap(3)

    with pytest.raises(HeapError, match="outside"):
        heap.push(item, 1.0)


def test_rejects_nan_priorities() -> None:
    heap = IndexedMinHeap(1)

    with pytest.raises(HeapError, match="NaN"):
        heap.push(0, math.nan)


def test_rejects_a_negative_capacity() -> None:
    with pytest.raises(HeapError, match="negative"):
        IndexedMinHeap(-1)


def test_an_empty_heap_of_capacity_zero_is_valid() -> None:
    heap = IndexedMinHeap(0)

    assert heap.capacity == 0
    assert heap.is_empty()
    assert heap.is_valid()
