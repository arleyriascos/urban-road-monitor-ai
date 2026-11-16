import pytest

from training.split import DEFAULT_RATIOS, SPLITS, SplitError, assign_splits

KEYS = [f"photo{number:03d}" for number in range(100)]


def test_every_group_gets_one_known_split() -> None:
    assignment = assign_splits(KEYS)
    assert set(assignment) == set(KEYS)
    assert set(assignment.values()) <= set(SPLITS)


def test_the_shares_follow_the_ratios() -> None:
    counts = {name: 0 for name in SPLITS}
    for split in assign_splits(KEYS, DEFAULT_RATIOS).values():
        counts[split] += 1
    assert counts == {"train": 80, "val": 10, "test": 10}


def test_the_result_does_not_depend_on_the_order_or_on_repeated_keys() -> None:
    shuffled = [*reversed(KEYS), *KEYS[:10]]
    assert assign_splits(shuffled, seed=7) == assign_splits(KEYS, seed=7)


def test_the_seed_changes_the_split() -> None:
    assert assign_splits(KEYS, seed=1) != assign_splits(KEYS, seed=2)


def test_the_same_seed_gives_the_same_split() -> None:
    assert assign_splits(KEYS, seed=5) == assign_splits(KEYS, seed=5)


def test_small_sets_still_fill_val_and_test() -> None:
    assignment = assign_splits(["a", "b", "c"])
    assert sorted(assignment.values()) == ["test", "train", "val"]


def test_custom_ratios() -> None:
    assignment = assign_splits(KEYS, ratios=(0.6, 0.2, 0.2))
    values = list(assignment.values())
    assert (values.count("train"), values.count("val"), values.count("test")) == (60, 20, 20)


def test_fewer_than_three_groups_fail() -> None:
    with pytest.raises(SplitError, match="al menos 3"):
        assign_splits(["a", "b"])


@pytest.mark.parametrize("ratios", [(0.5, 0.5, 0.0), (0.8, 0.1, 0.2), (1.0, -0.5, 0.5)])
def test_invalid_ratios_fail(ratios: tuple[float, float, float]) -> None:
    with pytest.raises(SplitError, match="sumar 1"):
        assign_splits(KEYS, ratios=ratios)
