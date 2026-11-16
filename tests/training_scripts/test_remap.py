import pytest

from training.labels import LabelBox
from training.remap import NoPotholeClassError, build_class_map, remap_boxes


def test_a_single_pothole_class_maps_to_zero() -> None:
    assert build_class_map(["pothole"]) == {0: 0}


def test_names_are_compared_without_case_or_spaces() -> None:
    assert build_class_map([" Potholes "]) == {0: 0}
    assert build_class_map(["Bache"]) == {0: 0}


def test_picks_the_pothole_among_other_classes() -> None:
    names = ["D00", "D10", "D20", "D40"]
    assert build_class_map(names) == {3: 0}


def test_several_pothole_classes_all_map_to_zero() -> None:
    names = ["crack", "pothole", "Pothole-Big"]
    assert build_class_map(names, aliases={"pothole", "pothole-big"}) == {1: 0, 2: 0}


def test_fails_when_no_class_is_a_pothole() -> None:
    with pytest.raises(NoPotholeClassError, match="crack, manhole"):
        build_class_map(["crack", "manhole"])


def test_fails_with_no_classes_at_all() -> None:
    with pytest.raises(NoPotholeClassError, match="ninguna"):
        build_class_map([])


def test_remap_keeps_potholes_and_drops_the_rest() -> None:
    boxes = [
        LabelBox(0, 0.1, 0.1, 0.1, 0.1),
        LabelBox(3, 0.5, 0.5, 0.2, 0.2),
        LabelBox(1, 0.9, 0.9, 0.1, 0.1),
        LabelBox(3, 0.3, 0.7, 0.05, 0.05),
    ]
    assert remap_boxes(boxes, {3: 0}) == [
        LabelBox(0, 0.5, 0.5, 0.2, 0.2),
        LabelBox(0, 0.3, 0.7, 0.05, 0.05),
    ]


def test_remap_of_an_image_without_potholes_is_empty() -> None:
    assert remap_boxes([LabelBox(1, 0.5, 0.5, 0.2, 0.2)], {3: 0}) == []
