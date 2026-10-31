"""Random operations on the heap, compared with a slow but obvious reference.

The reference is a dictionary item -> priority whose minimum is found with
``min``. The seeds are fixed, so every run performs the same operations.
"""

import random

import pytest

from app.structures.min_heap import IndexedMinHeap

CAPACITY = 60
OPERATIONS = 2000


def reference_min(waiting: dict[int, float]) -> tuple[int, float]:
    item = min(waiting, key=lambda candidate: (waiting[candidate], candidate))
    return item, waiting[item]


@pytest.mark.parametrize("seed", [1, 2, 3, 4, 5])
def test_matches_the_reference_after_every_operation(seed: int) -> None:
    rng = random.Random(seed)
    heap = IndexedMinHeap(CAPACITY)
    waiting: dict[int, float] = {}

    for _ in range(OPERATIONS):
        action = rng.random()
        outside = [item for item in range(CAPACITY) if item not in waiting]
        if action < 0.45 and outside:
            item = rng.choice(outside)
            priority = float(rng.randint(0, 50))  # small range: many ties
            heap.push(item, priority)
            waiting[item] = priority
        elif action < 0.75 and waiting:
            item = rng.choice(sorted(waiting))
            priority = waiting[item] - rng.randint(0, 20)
            heap.decrease_key(item, priority)
            waiting[item] = priority
        elif waiting:
            expected = reference_min(waiting)
            assert heap.pop_min() == expected
            del waiting[expected[0]]

        assert len(heap) == len(waiting)
        assert heap.is_valid()
        if waiting:
            assert heap.peek_min() == reference_min(waiting)

    remaining = [heap.pop_min() for _ in range(len(heap))]
    assert remaining == sorted(waiting.items(), key=lambda pair: (pair[1], pair[0]))
