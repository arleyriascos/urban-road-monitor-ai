"""Random operations on the stack, compared with a slow but obvious reference.

The reference keeps the newest item at the front of a list (``insert(0, ...)``
and ``pop(0)``). The seeds are fixed, so every run performs the same operations.
"""

import random

import pytest

from app.structures.stack import Stack, StackError

OPERATIONS = 2000


@pytest.mark.parametrize("seed", [1, 2, 3, 4, 5])
def test_matches_the_reference_after_every_operation(seed: int) -> None:
    rng = random.Random(seed)
    stack: Stack[int] = Stack()
    reference: list[int] = []

    for _ in range(OPERATIONS):
        action = rng.random()
        if action < 0.55:
            item = rng.randint(0, 99)
            stack.push(item)
            reference.insert(0, item)
        elif action < 0.9:
            if reference:
                assert stack.pop() == reference.pop(0)
            else:
                with pytest.raises(StackError):
                    stack.pop()
        elif reference:
            assert stack.peek() == reference[0]
        else:
            with pytest.raises(StackError):
                stack.peek()

        assert len(stack) == len(reference)
        assert stack.is_empty() == (not reference)
