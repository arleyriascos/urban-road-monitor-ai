"""Union-Find (disjoint sets) with path compression and union by size.

Elements are the integers 0 to n - 1. Each set is a tree whose root represents
it. Path compression makes every node on a ``find`` path point straight at the
root, and union by size hangs the smaller tree under the larger one. Together
they make ``find`` and ``union`` run in amortized O(alpha(n)), almost constant.
"""


class UnionFindError(ValueError):
    """Raised when an element is outside the structure."""


class UnionFind:
    """Disjoint sets over the elements 0 to n - 1."""

    def __init__(self, n: int) -> None:
        if n < 0:
            raise UnionFindError(f"the number of elements must not be negative, got {n}")
        self._parent: list[int] = list(range(n))
        """Parent of each element; a root is its own parent."""
        self._size: list[int] = [1] * n
        """Number of elements in the set of each root (only meaningful for roots)."""
        self._count = n

    def __len__(self) -> int:
        return len(self._parent)

    def find(self, x: int) -> int:
        """Return the root of the set of x, compressing the path on the way."""
        self._check(x)
        root = x
        while self._parent[root] != root:
            root = self._parent[root]
        while self._parent[x] != root:
            self._parent[x], x = root, self._parent[x]
        return root

    def union(self, a: int, b: int) -> bool:
        """Join the sets of a and b. Return False if they were already joined.

        The larger set keeps its root; on a tie, the lower root wins, so the
        result does not depend on chance.
        """
        root_a = self.find(a)
        root_b = self.find(b)
        if root_a == root_b:
            return False
        if (self._size[root_a], -root_a) < (self._size[root_b], -root_b):
            root_a, root_b = root_b, root_a
        self._parent[root_b] = root_a
        self._size[root_a] += self._size[root_b]
        self._count -= 1
        return True

    def connected(self, a: int, b: int) -> bool:
        """Tell whether a and b are in the same set."""
        return self.find(a) == self.find(b)

    def _check(self, x: int) -> None:
        if not 0 <= x < len(self._parent):
            raise UnionFindError(f"element {x} is outside 0..{len(self._parent) - 1}")
