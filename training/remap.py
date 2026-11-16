"""Keep only the pothole class of a dataset and number it 0.

Public datasets name their classes in different ways: "pothole", "potholes", or a code such as
"D40" in the road damage datasets. The model needs a single class, so every class that is a
pothole becomes class 0 and the boxes of any other class are dropped.
"""

from collections.abc import Collection

from training.labels import LabelBox

POTHOLE_CLASS_NAME = "pothole"
POTHOLE_ALIASES = frozenset({"pothole", "potholes", "bache", "baches", "d40"})
"""Lowercase names that count as a pothole. D40 is the pothole code of the road damage sets."""


class NoPotholeClassError(ValueError):
    """None of the classes of a dataset is a pothole."""


def build_class_map(names: list[str], aliases: Collection[str] = POTHOLE_ALIASES) -> dict[int, int]:
    """Map the class numbers of a dataset to the single pothole class (0).

    Classes that are not potholes are left out of the map. Raises NoPotholeClassError if
    there is no pothole class at all.
    """
    wanted = {alias.lower() for alias in aliases}
    class_map = {number: 0 for number, name in enumerate(names) if name.strip().lower() in wanted}
    if not class_map:
        raise NoPotholeClassError(
            f"ninguna clase del dataset es un bache (clases: {', '.join(names) or 'ninguna'})"
        )
    return class_map


def remap_boxes(boxes: list[LabelBox], class_map: dict[int, int]) -> list[LabelBox]:
    """Keep the boxes whose class is in the map and give them their new class number."""
    return [
        LabelBox(class_map[box.class_id], box.x_center, box.y_center, box.width, box.height)
        for box in boxes
        if box.class_id in class_map
    ]
