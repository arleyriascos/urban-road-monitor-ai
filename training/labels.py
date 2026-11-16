"""Read and write YOLO label files.

A label file has one box per line: ``class x_center y_center width height``, with the four
numbers between 0 and 1 relative to the size of the image.
"""

import math
from dataclasses import dataclass


class LabelError(ValueError):
    """A label file has a line that is not a valid YOLO box."""


@dataclass(frozen=True, slots=True)
class LabelBox:
    """One bounding box, in the coordinates of a YOLO label file."""

    class_id: int
    x_center: float
    y_center: float
    width: float
    height: float


def parse_label_text(text: str) -> list[LabelBox]:
    """Read every box of a label file. Blank lines are ignored.

    Raises LabelError, naming the line, at the first line that is not a valid box.
    """
    boxes: list[LabelBox] = []
    for number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        try:
            boxes.append(_parse_line(line))
        except LabelError as error:
            raise LabelError(f"línea {number}: {error}") from None
    return boxes


def format_label_text(boxes: list[LabelBox]) -> str:
    """Write boxes as the text of a label file. No boxes gives an empty text (background)."""
    lines = [
        f"{box.class_id} {box.x_center:.6f} {box.y_center:.6f} {box.width:.6f} {box.height:.6f}"
        for box in boxes
    ]
    return "".join(f"{line}\n" for line in lines)


def _parse_line(line: str) -> LabelBox:
    fields = line.split()
    if len(fields) > 5:
        raise LabelError(
            f"tiene {len(fields)} valores y solo se aceptan cajas de 5 "
            "(¿es un polígono de segmentación?)"
        )
    if len(fields) < 5:
        raise LabelError(f"tiene {len(fields)} valores y se esperaban 5")

    if not (fields[0].isascii() and fields[0].isdigit()):
        raise LabelError(f"la clase '{fields[0]}' no es un entero mayor o igual a 0")
    try:
        x_center, y_center, width, height = (float(value) for value in fields[1:])
    except ValueError:
        raise LabelError("las coordenadas no son números") from None

    named = (
        ("x_center", x_center),
        ("y_center", y_center),
        ("width", width),
        ("height", height),
    )
    for name, value in named:
        if not (math.isfinite(value) and 0.0 <= value <= 1.0):
            raise LabelError(f"{name} vale {value} y debe estar entre 0 y 1")
    if width == 0.0 or height == 0.0:
        raise LabelError("la caja tiene ancho o alto igual a 0")

    return LabelBox(int(fields[0]), x_center, y_center, width, height)
