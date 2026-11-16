"""Share groups of photos between training, validation and test.

The split works on groups, never on single images: every copy of a photo goes to the same
place (see training.groups). The result depends only on the set of keys and the seed, so the
same dataset gives the same split every time.
"""

import math
import random
from collections.abc import Iterable

SPLITS = ("train", "val", "test")
DEFAULT_RATIOS = (0.8, 0.1, 0.1)
"""Share of the groups that go to train, val and test."""


class SplitError(ValueError):
    """The groups cannot be shared as asked."""


def assign_splits(
    keys: Iterable[str],
    ratios: tuple[float, float, float] = DEFAULT_RATIOS,
    seed: int = 42,
) -> dict[str, str]:
    """Return the split ("train", "val" or "test") of every group key.

    Validation and test get at least one group each. The share of images in each split is
    close to the ratios, but not exact, because groups have different numbers of copies.
    """
    train_ratio, val_ratio, test_ratio = ratios
    if min(ratios) <= 0 or not math.isclose(sum(ratios), 1.0, abs_tol=1e-9):
        raise SplitError(f"los porcentajes deben ser mayores que 0 y sumar 1: {ratios}")

    groups = sorted(set(keys))
    if len(groups) < len(SPLITS):
        raise SplitError(
            f"hay {len(groups)} grupos de fotos y hacen falta al menos {len(SPLITS)} "
            "para repartirlos en train, val y test"
        )
    random.Random(seed).shuffle(groups)

    total = len(groups)
    val_count = max(1, round(total * val_ratio))
    test_count = max(1, round(total * test_ratio))
    train_count = total - val_count - test_count
    if train_count < 1:
        raise SplitError("los grupos no alcanzan para dejar al menos uno en train")

    assignment: dict[str, str] = {}
    for position, key in enumerate(groups):
        if position < train_count:
            assignment[key] = "train"
        elif position < train_count + val_count:
            assignment[key] = "val"
        else:
            assignment[key] = "test"
    return assignment
