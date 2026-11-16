import pytest

from training.classes import ClassNamesError, read_class_names, read_license

ROBOFLOW_YAML = """\
train: ../train/images
val: ../valid/images
test: ../test/images

nc: 1
names: ['pothole']

roboflow:
  workspace: some-workspace
  project: potholes
  version: 3
  license: CC BY 4.0
  url: https://universe.roboflow.com/some-workspace/potholes/dataset/3
"""


def test_reads_an_inline_list() -> None:
    assert read_class_names(ROBOFLOW_YAML) == ["pothole"]


def test_reads_an_inline_list_with_several_classes() -> None:
    assert read_class_names('names: ["D00", "D10", "D20", "D40"]') == [
        "D00",
        "D10",
        "D20",
        "D40",
    ]


def test_reads_an_inline_list_without_quotes() -> None:
    assert read_class_names("names: [crack, pothole]") == ["crack", "pothole"]


def test_reads_an_inline_map() -> None:
    assert read_class_names("names: {1: pothole, 0: crack}") == ["crack", "pothole"]


def test_reads_a_block_list() -> None:
    yaml_text = "nc: 2\nnames:\n  - crack\n  - 'pothole'\nother: 1\n"
    assert read_class_names(yaml_text) == ["crack", "pothole"]


def test_reads_a_block_list_without_indentation() -> None:
    assert read_class_names("names:\n- crack\n- pothole\n") == ["crack", "pothole"]


def test_reads_a_block_map() -> None:
    yaml_text = "path: .\nnames:\n  0: crack\n  1: pothole\ntrain: train/images\n"
    assert read_class_names(yaml_text) == ["crack", "pothole"]


def test_ignores_comments() -> None:
    assert read_class_names("names: ['pothole']  # one class") == ["pothole"]


def test_a_hash_inside_quotes_is_part_of_the_name() -> None:
    assert read_class_names("names: ['pothole #1']") == ["pothole #1"]


def test_fails_without_names() -> None:
    with pytest.raises(ClassNamesError, match="no tiene la clave"):
        read_class_names("nc: 1\n")


def test_fails_with_an_empty_list() -> None:
    with pytest.raises(ClassNamesError, match="vacía"):
        read_class_names("names: []\n")
    with pytest.raises(ClassNamesError, match="vacía"):
        read_class_names("names:\ntrain: x\n")


def test_fails_with_gaps_in_the_numbers() -> None:
    with pytest.raises(ClassNamesError, match="sin huecos"):
        read_class_names("names:\n  0: crack\n  2: pothole\n")


def test_fails_when_the_shapes_are_mixed() -> None:
    with pytest.raises(ClassNamesError, match="mezcla"):
        read_class_names("names:\n  - crack\n  1: pothole\n")


def test_fails_with_something_that_is_not_a_list() -> None:
    with pytest.raises(ClassNamesError, match="no se entiende"):
        read_class_names("names: pothole\n")


def test_reads_the_license() -> None:
    assert read_license(ROBOFLOW_YAML) == "CC BY 4.0"


def test_reads_a_quoted_license() -> None:
    assert read_license("roboflow:\n  license: 'CC BY 4.0'  # from the author\n") == "CC BY 4.0"


def test_license_is_none_when_missing() -> None:
    assert read_license("names: ['pothole']\n") is None
