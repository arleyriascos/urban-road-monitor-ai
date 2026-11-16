import json
from pathlib import Path

import pytest
from dataset_fixtures import (
    DAMAGE_YAML,
    LICENSED_YAML,
    POTHOLE_BOX,
    make_big_source,
    make_source,
    write_image,
)

from training.groups import group_key
from training.prepare import PrepareError, main, prepare_dataset


def _splits_of_groups(output: Path) -> dict[str, set[str]]:
    found: dict[str, set[str]] = {}
    for split in ("train", "val", "test"):
        folder = output / "images" / split
        if folder.is_dir():
            for image in folder.iterdir():
                found.setdefault(group_key(image.name), set()).add(split)
    return found


def test_copies_of_one_photo_always_share_a_split(tmp_path: Path) -> None:
    source = make_big_source(tmp_path / "big")
    prepare_dataset([source], tmp_path / "out")
    groups = _splits_of_groups(tmp_path / "out")
    assert len(groups) == 30
    assert all(len(splits) == 1 for splits in groups.values())


def test_counts_and_files_written(tmp_path: Path) -> None:
    source = make_big_source(tmp_path / "big")
    result = prepare_dataset([source], tmp_path / "out")
    assert sum(result.images.values()) == 90
    assert sum(result.boxes.values()) == 90
    assert all(count > 0 for count in result.images.values())
    out = tmp_path / "out"
    images = sum(1 for _ in (out / "images").rglob("*.jpg"))
    labels = sum(1 for _ in (out / "labels").rglob("*.txt"))
    assert images == labels == 90


def test_data_yaml_and_manifest(tmp_path: Path) -> None:
    source = make_source(tmp_path / "potholes", LICENSED_YAML)
    # make_source has only 3 photo groups: exactly enough for one per split
    prepare_dataset([source], tmp_path / "out")
    yaml_text = (tmp_path / "out" / "data.yaml").read_text(encoding="utf-8")
    assert "nc: 1" in yaml_text
    assert "names: ['pothole']" in yaml_text
    manifest = json.loads((tmp_path / "out" / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["sources"][0]["license"] == "CC BY 4.0"
    assert sum(manifest["images"].values()) == 5


def test_other_classes_are_dropped_and_potholes_become_class_zero(tmp_path: Path) -> None:
    source = tmp_path / "damage"
    source.mkdir()
    (source / "data.yaml").write_text(DAMAGE_YAML, encoding="utf-8")
    write_image(source / "train", "a_jpg.rf.1.jpg", "0 0.1 0.1 0.1 0.1\n3 0.5 0.5 0.2 0.1\n")
    write_image(source / "train", "b_jpg.rf.1.jpg", "1 0.5 0.5 0.2 0.1\n")
    write_image(source / "train", "c_jpg.rf.1.jpg", "3 0.4 0.4 0.2 0.2\n")
    prepare_dataset([source], tmp_path / "out")
    texts = sorted(
        path.read_text(encoding="utf-8") for path in (tmp_path / "out" / "labels").rglob("*.txt")
    )
    assert texts == [
        "",
        "0 0.400000 0.400000 0.200000 0.200000\n",
        "0 0.500000 0.500000 0.200000 0.100000\n",
    ]


def test_images_without_a_label_file_become_background(tmp_path: Path) -> None:
    source = make_source(tmp_path / "potholes")
    write_image(source / "train", "d_jpg.rf.1.jpg", None)
    prepare_dataset([source], tmp_path / "out")
    names = {path.name for path in (tmp_path / "out" / "labels").rglob("*.txt")}
    assert "potholes__d_jpg.rf.1.txt" in names


def test_two_sources_are_merged_and_keep_their_names(tmp_path: Path) -> None:
    first = make_source(tmp_path / "one")
    second = make_source(tmp_path / "two")
    result = prepare_dataset([first, second], tmp_path / "out")
    assert sum(result.images.values()) == 10
    names = {path.name for path in (tmp_path / "out" / "images").rglob("*.jpg")}
    assert "one__a_jpg.rf.111.jpg" in names
    assert "two__a_jpg.rf.111.jpg" in names


def test_same_seed_gives_the_same_dataset(tmp_path: Path) -> None:
    source = make_big_source(tmp_path / "big")
    prepare_dataset([source], tmp_path / "a", seed=3)
    prepare_dataset([source], tmp_path / "b", seed=3)
    first = sorted(str(p.relative_to(tmp_path / "a")) for p in (tmp_path / "a").rglob("*.jpg"))
    second = sorted(str(p.relative_to(tmp_path / "b")) for p in (tmp_path / "b").rglob("*.jpg"))
    assert first == second


def test_a_source_with_problems_stops_everything(tmp_path: Path) -> None:
    source = make_source(tmp_path / "potholes")
    write_image(source / "valid", "bad.jpg", "oops\n")
    with pytest.raises(PrepareError, match="tiene problemas"):
        prepare_dataset([source], tmp_path / "out")
    assert not (tmp_path / "out").exists()


def test_refuses_a_non_empty_output(tmp_path: Path) -> None:
    source = make_source(tmp_path / "potholes")
    out = tmp_path / "out"
    out.mkdir()
    (out / "something.txt").write_text("x", encoding="utf-8")
    with pytest.raises(PrepareError, match="ya existe"):
        prepare_dataset([source], out)


def test_refuses_no_sources_and_repeated_names(tmp_path: Path) -> None:
    with pytest.raises(PrepareError, match="al menos una"):
        prepare_dataset([], tmp_path / "out")
    first = make_source(tmp_path / "x" / "same")
    second = make_source(tmp_path / "y" / "same")
    with pytest.raises(PrepareError, match="mismo nombre"):
        prepare_dataset([first, second], tmp_path / "out")


def test_command_line_prepares_and_reports(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = make_big_source(tmp_path / "big")
    code = main(["--source", str(source), "--output", str(tmp_path / "out")])
    assert code == 0
    assert "Dataset escrito en" in capsys.readouterr().out


def test_command_line_audit_only_writes_nothing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = make_source(tmp_path / "potholes")
    assert main(["--source", str(source), "--output", str(tmp_path / "out"), "--audit-only"]) == 0
    assert not (tmp_path / "out").exists()
    assert "Resultado: correcta" in capsys.readouterr().out


def test_command_line_returns_one_on_problems(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = make_source(tmp_path / "potholes")
    (source / "data.yaml").unlink()
    assert main(["--source", str(source), "--output", str(tmp_path / "out")]) == 1
    assert "data.yaml" in capsys.readouterr().err


def test_box_constant_is_a_valid_label() -> None:
    assert POTHOLE_BOX.startswith("0 ")
