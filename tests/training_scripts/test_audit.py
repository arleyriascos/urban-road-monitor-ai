from pathlib import Path

from dataset_fixtures import (
    DAMAGE_YAML,
    LICENSED_YAML,
    POTHOLE_BOX,
    make_source,
    write_image,
)

from training.audit import audit_source, format_audit, label_path_for, list_images


def test_a_valid_source_has_no_problems(tmp_path: Path) -> None:
    report = audit_source(make_source(tmp_path / "potholes"))
    assert report.ok
    assert report.warnings == []
    assert report.class_names == ["pothole"]
    assert report.total_images == 5
    stats = report.splits["train"]
    assert (stats.images, stats.with_boxes, stats.background, stats.boxes) == (5, 4, 1, 5)


def test_reads_the_declared_license(tmp_path: Path) -> None:
    report = audit_source(make_source(tmp_path / "potholes", LICENSED_YAML))
    assert report.license == "CC BY 4.0"
    assert "Licencia declarada en data.yaml: CC BY 4.0" in format_audit(report)


def test_a_source_that_is_not_a_folder(tmp_path: Path) -> None:
    report = audit_source(tmp_path / "missing")
    assert not report.ok
    assert "no es una carpeta" in report.problems[0]


def test_missing_data_yaml_is_a_problem(tmp_path: Path) -> None:
    source = make_source(tmp_path / "potholes")
    (source / "data.yaml").unlink()
    report = audit_source(source)
    assert "falta el archivo data.yaml" in report.problems


def test_a_dataset_without_a_pothole_class_is_a_problem(tmp_path: Path) -> None:
    source = make_source(tmp_path / "potholes")
    (source / "data.yaml").write_text("names: ['crack', 'manhole']\n", encoding="utf-8")
    report = audit_source(source)
    assert any("ninguna clase del dataset es un bache" in problem for problem in report.problems)


def test_a_source_without_split_folders(tmp_path: Path) -> None:
    source = tmp_path / "empty"
    source.mkdir()
    (source / "data.yaml").write_text("names: ['pothole']\n", encoding="utf-8")
    report = audit_source(source)
    assert any("images" in problem for problem in report.problems)


def test_a_source_without_images(tmp_path: Path) -> None:
    source = tmp_path / "empty"
    (source / "train" / "images").mkdir(parents=True)
    (source / "data.yaml").write_text("names: ['pothole']\n", encoding="utf-8")
    report = audit_source(source)
    assert "no se encontró ninguna imagen" in report.problems


def test_a_source_where_no_image_has_potholes(tmp_path: Path) -> None:
    source = tmp_path / "negatives"
    source.mkdir()
    (source / "data.yaml").write_text("names: ['pothole']\n", encoding="utf-8")
    write_image(source / "train", "a.jpg", "")
    report = audit_source(source)
    assert "ninguna imagen tiene cajas de baches" in report.problems


def test_an_invalid_label_names_the_file_and_the_line(tmp_path: Path) -> None:
    source = make_source(tmp_path / "potholes")
    write_image(source / "valid", "bad.jpg", "0 0.5 0.5 0.2 0.1\n0 2 0.5 0.2 0.1\n")
    report = audit_source(source)
    assert not report.ok
    assert any("valid/labels/bad.txt: línea 2" in problem for problem in report.problems)


def test_a_class_number_outside_data_yaml_is_a_problem(tmp_path: Path) -> None:
    source = make_source(tmp_path / "potholes")
    write_image(source / "valid", "odd.jpg", "5 0.5 0.5 0.2 0.1\n")
    report = audit_source(source)
    assert any("usa las clases 5" in problem for problem in report.problems)


def test_images_without_label_file_are_background_with_a_warning(tmp_path: Path) -> None:
    source = make_source(tmp_path / "potholes")
    write_image(source / "train", "no-label.jpg", None)
    report = audit_source(source)
    assert report.ok
    assert report.splits["train"].missing_label_files == 1
    assert report.splits["train"].background == 2
    assert any("sin archivo de etiquetas" in warning for warning in report.warnings)


def test_labels_without_image_are_a_warning(tmp_path: Path) -> None:
    source = make_source(tmp_path / "potholes")
    (source / "train" / "labels" / "orphan.txt").write_text(POTHOLE_BOX, encoding="utf-8")
    report = audit_source(source)
    assert report.ok
    assert report.splits["train"].labels_without_image == 1
    assert any("sin imagen" in warning for warning in report.warnings)


def test_boxes_of_other_classes_are_not_counted(tmp_path: Path) -> None:
    source = tmp_path / "damage"
    source.mkdir()
    (source / "data.yaml").write_text(DAMAGE_YAML, encoding="utf-8")
    write_image(source / "train", "a.jpg", "0 0.5 0.5 0.2 0.1\n3 0.2 0.2 0.1 0.1\n")
    write_image(source / "train", "b.jpg", "1 0.5 0.5 0.2 0.1\n")
    report = audit_source(source)
    stats = report.splits["train"]
    assert report.ok
    assert (stats.with_boxes, stats.background, stats.boxes) == (1, 1, 1)


def test_the_text_report_lists_at_most_twenty_problems(tmp_path: Path) -> None:
    source = make_source(tmp_path / "potholes")
    for number in range(25):
        write_image(source / "valid", f"bad{number:02d}.jpg", "x\n")
    text = format_audit(audit_source(source))
    assert "y 5 más" in text
    assert "Resultado: tiene problemas" in text


def test_list_images_ignores_other_files_and_label_path_matches(tmp_path: Path) -> None:
    source = make_source(tmp_path / "potholes")
    (source / "train" / "images" / "notes.txt").write_text("x", encoding="utf-8")
    images = list_images(source / "train")
    assert len(images) == 5
    assert label_path_for(images[0]) == source / "train" / "labels" / f"{images[0].stem}.txt"


def test_polygons_are_accepted_as_boxes_with_a_warning(tmp_path: Path) -> None:
    source = make_source(tmp_path / "potholes")
    write_image(source / "valid", "poly.jpg", "0 0.1 0.1 0.3 0.1 0.2 0.4\n")
    report = audit_source(source)
    assert report.ok
    assert report.splits["valid"].polygon_lines == 1
    assert report.splits["valid"].boxes == 1
    assert any("polígonos" in warning for warning in report.warnings)
