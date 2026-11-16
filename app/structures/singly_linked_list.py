"""Singly linked list.

The road graph keeps the edges that leave each intersection in one of these lists:
that is its adjacency list. Every link holds a value and a pointer to the next link,
and the last link points to nothing. The list also remembers its last link, so adding
at the end does not have to walk the whole list.

Complexity: ``push_back`` and ``len`` are O(1); iterating over the list and checking
its invariants (``is_valid``) are O(n).
"""

from collections.abc import Iterator


class _Node[T]:
    """One link of the list: a value and the next link (``None`` at the end)."""

    __slots__ = ("next", "value")

    def __init__(self, value: T) -> None:
        self.value = value
        self.next: _Node[T] | None = None


class SinglyLinkedList[T]:
    """List of values of one type, linked from the first to the last."""

    def __init__(self) -> None:
        self._head: _Node[T] | None = None
        """First link, or ``None`` when the list is empty."""
        self._tail: _Node[T] | None = None
        """Last link, or ``None`` when the list is empty."""
        self._size = 0

    def __len__(self) -> int:
        return self._size

    def __iter__(self) -> Iterator[T]:
        """Walk the list from the first value to the last."""
        node = self._head
        while node is not None:
            yield node.value
            node = node.next

    def is_empty(self) -> bool:
        """Tell whether the list has no values."""
        return self._size == 0

    def push_back(self, value: T) -> None:
        """Add a value after the last one."""
        node = _Node(value)
        if self._tail is None:
            self._head = node
        else:
            self._tail.next = node
        self._tail = node
        self._size += 1

    def is_valid(self) -> bool:
        """Check the invariants of the list.

        An empty list has no first and no last link. Otherwise, walking from the first
        link must reach exactly as many links as the size says, with no loop, and the
        last one reached must be the remembered last link.
        It is O(n), so it is meant for tests and for the presentation.
        """
        if self._head is None or self._tail is None:
            return self._head is None and self._tail is None and self._size == 0
        count = 0
        last: _Node[T] | None = None
        node: _Node[T] | None = self._head
        while node is not None:
            count += 1
            if count > self._size:
                return False  # more links than the size says, or a loop
            last = node
            node = node.next
        return count == self._size and last is self._tail
