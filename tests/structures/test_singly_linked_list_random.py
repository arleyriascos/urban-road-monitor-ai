"""Random operations on the singly linked list, compared with a slow but obvious reference.

The reference is a plain Python list. Several lists grow at the same time, so a mistake
that mixes up the links of two lists would show. The seeds are fixed, so every run
performs the same operations.
"""

import random

import pytest

from app.structures.singly_linked_list import SinglyLinkedList

OPERATIONS = 1500
LISTS = 4


@pytest.mark.parametrize("seed", [1, 2, 3, 4, 5])
def test_matches_the_reference_after_every_operation(seed: int) -> None:
    rng = random.Random(seed)
    lists: list[SinglyLinkedList[int]] = [SinglyLinkedList() for _ in range(LISTS)]
    references: list[list[int]] = [[] for _ in range(LISTS)]

    for _ in range(OPERATIONS):
        which = rng.randrange(LISTS)
        value = rng.randint(0, 99)
        lists[which].push_back(value)
        references[which].append(value)

        assert list(lists[which]) == references[which]
        assert len(lists[which]) == len(references[which])
        assert lists[which].is_empty() == (not references[which])
        assert lists[which].is_valid()

    for items, reference in zip(lists, references, strict=True):
        assert list(items) == reference
        assert list(items) == reference  # walking does not change the list
        assert items.is_valid()


@pytest.mark.parametrize("seed", [11, 12, 13])
def test_a_walk_in_progress_sees_the_values_added_after_it_started(seed: int) -> None:
    """The walk follows the links, so it reaches a value added in the middle of the walk."""
    rng = random.Random(seed)
    items: SinglyLinkedList[int] = SinglyLinkedList()
    for value in range(rng.randint(1, 20)):
        items.push_back(value)

    seen: list[int] = []
    added = False
    for value in items:
        seen.append(value)
        if not added:
            items.push_back(-1)
            added = True

    assert seen == [*range(len(items) - 1), -1]
    assert items.is_valid()
