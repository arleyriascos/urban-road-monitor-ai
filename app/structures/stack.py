"""Stack (last in, first out).

The route search uses it to put the path in travel order. The search walks the
path backwards, from the destination to the origin, so it pushes each step as
it finds it; popping them gives the steps from the origin to the destination.

Complexity: push, pop, peek and len are O(1) (push is amortized).
"""


class StackError(ValueError):
    """Raised when an operation needs an item and the stack is empty."""


class Stack[T]:
    """Stack of items of one type."""

    def __init__(self) -> None:
        self._items: list[T] = []
        """Items from the bottom of the stack to the top (the last one)."""

    def __len__(self) -> int:
        return len(self._items)

    def is_empty(self) -> bool:
        """Tell whether the stack has no items."""
        return not self._items

    def push(self, item: T) -> None:
        """Put an item on top of the stack."""
        self._items.append(item)

    def pop(self) -> T:
        """Remove and return the item on top."""
        if not self._items:
            raise StackError("the stack is empty")
        return self._items.pop()

    def peek(self) -> T:
        """Return the item on top without removing it."""
        if not self._items:
            raise StackError("the stack is empty")
        return self._items[-1]
