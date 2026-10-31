"""Indexed binary min-heap with decrease-key.

Items are the integers 0 to capacity - 1 (the internal node indexes of the
graph). Each item is in the heap at most once, and the ``pos`` array keeps the
position of every item so its priority can be lowered in O(log n).

Complexity: push, pop_min and decrease_key are O(log n); contains, priority_of
and peek_min are O(1).
"""

import math

NOT_IN_HEAP = -1


class HeapError(ValueError):
    """Raised when an operation would break the heap."""


class IndexedMinHeap:
    """Min-heap of integer items ordered by (priority, item)."""

    def __init__(self, capacity: int) -> None:
        if capacity < 0:
            raise HeapError(f"capacity must not be negative, got {capacity}")
        self._heap: list[int] = []
        """Items in heap order: the parent of position i is (i - 1) // 2."""
        self._pos: list[int] = [NOT_IN_HEAP] * capacity
        """Position of each item in ``_heap``, or NOT_IN_HEAP."""
        self._priority: list[float] = [math.inf] * capacity
        """Current priority of each item that is in the heap."""

    @property
    def capacity(self) -> int:
        """Number of different items the heap accepts."""
        return len(self._pos)

    def __len__(self) -> int:
        return len(self._heap)

    def is_empty(self) -> bool:
        """Tell whether the heap has no items."""
        return not self._heap

    def contains(self, item: int) -> bool:
        """Tell whether the item is waiting in the heap."""
        self._check_item(item)
        return self._pos[item] != NOT_IN_HEAP

    def priority_of(self, item: int) -> float:
        """Return the current priority of an item that is in the heap."""
        self._check_item(item)
        if self._pos[item] == NOT_IN_HEAP:
            raise HeapError(f"item {item} is not in the heap")
        return self._priority[item]

    def push(self, item: int, priority: float) -> None:
        """Insert an item that is not in the heap yet."""
        self._check_item(item)
        self._check_priority(priority)
        if self._pos[item] != NOT_IN_HEAP:
            raise HeapError(f"item {item} is already in the heap; use decrease_key")
        self._priority[item] = priority
        self._heap.append(item)
        self._pos[item] = len(self._heap) - 1
        self._sift_up(len(self._heap) - 1)

    def peek_min(self) -> tuple[int, float]:
        """Return the item with the lowest priority without removing it."""
        if not self._heap:
            raise HeapError("the heap is empty")
        item = self._heap[0]
        return item, self._priority[item]

    def pop_min(self) -> tuple[int, float]:
        """Remove and return the item with the lowest priority."""
        if not self._heap:
            raise HeapError("the heap is empty")
        top = self._heap[0]
        last = self._heap.pop()
        self._pos[top] = NOT_IN_HEAP
        if self._heap:
            self._heap[0] = last
            self._pos[last] = 0
            self._sift_down(0)
        return top, self._priority[top]

    def decrease_key(self, item: int, priority: float) -> None:
        """Lower the priority of an item that is in the heap and move it up."""
        self._check_item(item)
        self._check_priority(priority)
        position = self._pos[item]
        if position == NOT_IN_HEAP:
            raise HeapError(f"item {item} is not in the heap; use push")
        if priority > self._priority[item]:
            raise HeapError(
                f"new priority {priority} is higher than the current {self._priority[item]}"
            )
        self._priority[item] = priority
        self._sift_up(position)

    def _less(self, i: int, j: int) -> bool:
        """Compare the items at positions i and j; ties go to the lower item."""
        a, b = self._heap[i], self._heap[j]
        return (self._priority[a], a) < (self._priority[b], b)

    def _swap(self, i: int, j: int) -> None:
        heap = self._heap
        heap[i], heap[j] = heap[j], heap[i]
        self._pos[heap[i]] = i
        self._pos[heap[j]] = j

    def _sift_up(self, i: int) -> None:
        while i > 0:
            parent = (i - 1) // 2
            if not self._less(i, parent):
                return
            self._swap(i, parent)
            i = parent

    def _sift_down(self, i: int) -> None:
        size = len(self._heap)
        while True:
            left = 2 * i + 1
            right = left + 1
            smallest = i
            if left < size and self._less(left, smallest):
                smallest = left
            if right < size and self._less(right, smallest):
                smallest = right
            if smallest == i:
                return
            self._swap(i, smallest)
            i = smallest

    def _check_item(self, item: int) -> None:
        if not 0 <= item < len(self._pos):
            raise HeapError(f"item {item} is outside 0..{len(self._pos) - 1}")

    @staticmethod
    def _check_priority(priority: float) -> None:
        if math.isnan(priority):
            raise HeapError("priority must be a number, got NaN")
