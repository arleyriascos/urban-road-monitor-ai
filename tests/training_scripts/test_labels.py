import pytest

from training.labels import (
    LabelBox,
    LabelError,
    count_polygon_lines,
    format_label_text,
    parse_label_text,
)


def test_reads_boxes_and_skips_blank_lines() -> None:
    text = "0 0.5 0.5 0.2 0.1\n\n  \n0 0.25 0.75 0.5 0.5\n"
    assert parse_label_text(text) == [
        LabelBox(0, 0.5, 0.5, 0.2, 0.1),
        LabelBox(0, 0.25, 0.75, 0.5, 0.5),
    ]


def test_an_empty_file_has_no_boxes() -> None:
    assert parse_label_text("") == []
    assert parse_label_text("\n\n") == []


def test_accepts_the_limits_of_the_range() -> None:
    assert parse_label_text("0 0 1 1 1") == [LabelBox(0, 0.0, 1.0, 1.0, 1.0)]


def test_error_names_the_line() -> None:
    with pytest.raises(LabelError, match="línea 2"):
        parse_label_text("0 0.5 0.5 0.2 0.1\n0 0.5 0.5 0.2\n")


def test_rejects_segmentation_polygons() -> None:
    with pytest.raises(LabelError, match="polígono"):
        parse_label_text("0 0.1 0.1 0.2 0.2 0.3 0.3")


@pytest.mark.parametrize("class_text", ["-1", "1.5", "abc", "²"])
def test_rejects_invalid_class(class_text: str) -> None:
    with pytest.raises(LabelError, match="clase"):
        parse_label_text(f"{class_text} 0.5 0.5 0.2 0.1")


@pytest.mark.parametrize(
    "line",
    [
        "0 1.01 0.5 0.2 0.1",
        "0 0.5 -0.1 0.2 0.1",
        "0 0.5 0.5 1.5 0.1",
        "0 nan 0.5 0.2 0.1",
        "0 0.5 inf 0.2 0.1",
    ],
)
def test_rejects_values_out_of_range(line: str) -> None:
    with pytest.raises(LabelError, match="entre 0 y 1"):
        parse_label_text(line)


def test_rejects_text_that_is_not_a_number() -> None:
    with pytest.raises(LabelError, match="no son números"):
        parse_label_text("0 a b c d")


@pytest.mark.parametrize("line", ["0 0.5 0.5 0 0.1", "0 0.5 0.5 0.2 0"])
def test_rejects_boxes_without_area(line: str) -> None:
    with pytest.raises(LabelError, match="igual a 0"):
        parse_label_text(line)


def test_writes_and_reads_back_the_same_boxes() -> None:
    boxes = [LabelBox(0, 0.123456, 0.5, 0.25, 0.125), LabelBox(3, 0.9, 0.1, 0.05, 0.05)]
    assert parse_label_text(format_label_text(boxes)) == boxes


def test_writing_no_boxes_gives_an_empty_text() -> None:
    assert format_label_text([]) == ""


def test_a_polygon_becomes_the_smallest_box_that_holds_it() -> None:
    boxes = parse_label_text("1 0.2 0.3 0.6 0.3 0.4 0.7", polygons_as_boxes=True)
    assert len(boxes) == 1
    box = boxes[0]
    assert box.class_id == 1
    assert (box.x_center, box.y_center) == pytest.approx((0.4, 0.5))
    assert (box.width, box.height) == pytest.approx((0.4, 0.4))


def test_polygons_and_boxes_can_share_a_file() -> None:
    text = "0 0.5 0.5 0.2 0.1\n0 0.1 0.1 0.3 0.1 0.2 0.4\n"
    boxes = parse_label_text(text, polygons_as_boxes=True)
    assert [box.class_id for box in boxes] == [0, 0]
    assert boxes[0] == LabelBox(0, 0.5, 0.5, 0.2, 0.1)


@pytest.mark.parametrize(
    "line",
    [
        "0 0.1 0.1 0.3 0.1 0.2",
        "0 0.1 0.1 0.3 0.1 0.2 0.4 0.5",
        "0 0.1 0.1 0.3 1.2 0.2 0.4",
        "0 0.1 0.1 0.3 x 0.2 0.4",
        "0 0.3 0.1 0.3 0.4 0.3 0.7",
        "a 0.1 0.1 0.3 0.1 0.2 0.4",
    ],
)
def test_invalid_polygons_are_still_rejected(line: str) -> None:
    with pytest.raises(LabelError, match="línea 1"):
        parse_label_text(line, polygons_as_boxes=True)


def test_polygons_are_rejected_unless_asked() -> None:
    with pytest.raises(LabelError, match="polígono"):
        parse_label_text("0 0.1 0.1 0.3 0.1 0.2 0.4")


def test_count_polygon_lines() -> None:
    text = "0 0.5 0.5 0.2 0.1\n0 0.1 0.1 0.3 0.1 0.2 0.4\n\n0 0.1 0.1 0.3 0.1 0.2 0.4\n"
    assert count_polygon_lines(text) == 2
    assert count_polygon_lines("") == 0
