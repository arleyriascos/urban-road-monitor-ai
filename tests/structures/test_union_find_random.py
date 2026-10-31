"""Random unions compared with a slow but obvious reference.

The reference keeps a label per element and relabels a whole set on every
union. The seeds are fixed, so every run performs the same operations.
"""

import random

import pytest

from app.structures.union_find import UnionFind

ELEMENTS = 80
OPERATIONS = 1500


@pytest.mark.parametrize("seed", [1, 2, 3, 4, 5])
def test_matches_the_reference_after_every_operation(seed: int) -> None:
    rng = random.Random(seed)
    sets = UnionFind(ELEMENTS)
    label = list(range(ELEMENTS))

    for _ in range(OPERATIONS):
        a = rng.randrange(ELEMENTS)
        b = rng.randrange(ELEMENTS)
        if rng.random() < 0.4:
            joined = label[a] != label[b]
            assert sets.union(a, b) == joined
            if joined:
                old, new = label[b], label[a]
                label = [new if value == old else value for value in label]
        else:
            assert sets.connected(a, b) == (label[a] == label[b])

        assert sets.count == len(set(label))
        assert sets.size(a) == label.count(label[a])

    assert sets.is_valid()
    largest = max(label.count(value) for value in set(label))
    assert sets.size(sets.largest_root()) == largest
