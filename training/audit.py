"""Check a downloaded dataset before it is used for training.

A source is a folder exported by Roboflow in the YOLOv8 format::

    <source>/data.yaml
    <source>/train/images/*.jpg   <source>/train/labels/*.txt
    <source>/valid/images/*.jpg   <source>/valid/labels/*.txt
    <source>/test/images/*.jpg    <source>/test/labels/*.txt

Any folder that has an ``images`` subfolder counts as a split, whatever its name. An image
without boxes (or without a label file) is a background image: the model learns from it that
there is no pothole there.
"""

from dataclasses import dataclass, field
from pathlib import Path

from training.classes import ClassNamesError, read_class_names, read_license
from training.labels import LabelError, parse_label_text
from training.remap import NoPotholeClassError, build_class_map, remap_boxes

IMAGE_SUFFIXES = frozenset({".jpg", ".jpeg", ".png", ".bmp", ".webp"})
MAX_LISTED_PROBLEMS = 20


@dataclass(slots=True)
class SplitStats:
    """What one folder of a source holds. Boxes are counted after keeping only potholes."""

    images: int = 0
    with_boxes: int = 0
    background: int = 0
    boxes: int = 0
    missing_label_files: int = 0
    labels_without_image: int = 0


@dataclass(slots=True)
class AuditReport:
    """The result of checking one source. Problems stop the preparation; warnings do not."""

    source: Path
    splits: dict[str, SplitStats] = field(default_factory=dict)
    class_names: list[str] = field(default_factory=list)
    license: str | None = None
    problems: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.problems

    @property
    def total_images(self) -> int:
        return sum(stats.images for stats in self.splits.values())

    @property
    def total_boxes(self) -> int:
        return sum(stats.boxes for stats in self.splits.values())


def find_split_dirs(root: Path) -> list[Path]:
    """The folders of a source that hold an ``images`` folder, in name order."""
    return sorted(
        child for child in root.iterdir() if child.is_dir() and (child / "images").is_dir()
    )


def list_images(split_dir: Path) -> list[Path]:
    """The image files of a split, in name order."""
    return sorted(
        path
        for path in (split_dir / "images").iterdir()
        if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
    )


def label_path_for(image: Path) -> Path:
    """Where the label file of an image lives: ``.../labels/<same name>.txt``."""
    return image.parent.parent / "labels" / f"{image.stem}.txt"


def audit_source(root: Path) -> AuditReport:
    """Read every label of a source and report what is wrong with it."""
    report = AuditReport(source=root)
    if not root.is_dir():
        report.problems.append(f"{root} no es una carpeta")
        return report

    class_map = _read_classes(root, report)
    split_dirs = find_split_dirs(root)
    if not split_dirs:
        report.problems.append("no hay ninguna carpeta con una subcarpeta images")
        return report

    for split_dir in split_dirs:
        report.splits[split_dir.name] = _audit_split(root, split_dir, class_map, report)

    if report.total_images == 0:
        report.problems.append("no se encontró ninguna imagen")
    elif report.total_boxes == 0:
        report.problems.append("ninguna imagen tiene cajas de baches")
    for name, stats in report.splits.items():
        if stats.missing_label_files:
            report.warnings.append(
                f"{name}: {stats.missing_label_files} imágenes sin archivo de etiquetas "
                "(se tratan como fondo)"
            )
        if stats.labels_without_image:
            report.warnings.append(
                f"{name}: {stats.labels_without_image} archivos de etiquetas sin imagen "
                "(se ignoran)"
            )
    return report


def format_audit(report: AuditReport) -> str:
    """The report as text for the person running the command."""
    lines = [f"Fuente: {report.source}"]
    if report.class_names:
        lines.append(f"Clases: {', '.join(report.class_names)}")
    lines.append(f"Licencia declarada en data.yaml: {report.license or 'no indica'}")
    for name, stats in report.splits.items():
        lines.append(
            f"  {name}: {stats.images} imágenes, {stats.with_boxes} con baches, "
            f"{stats.background} de fondo, {stats.boxes} cajas de bache"
        )
    for title, items in (("PROBLEMAS", report.problems), ("Avisos", report.warnings)):
        if not items:
            continue
        lines.append(f"{title}:")
        lines.extend(f"  - {item}" for item in items[:MAX_LISTED_PROBLEMS])
        if len(items) > MAX_LISTED_PROBLEMS:
            lines.append(f"  - y {len(items) - MAX_LISTED_PROBLEMS} más")
    lines.append("Resultado: " + ("correcta" if report.ok else "tiene problemas"))
    return "\n".join(lines)


def _read_classes(root: Path, report: AuditReport) -> dict[int, int]:
    """Read data.yaml and build the class map. Problems go to the report."""
    yaml_path = root / "data.yaml"
    if not yaml_path.is_file():
        report.problems.append("falta el archivo data.yaml")
        return {}
    text = yaml_path.read_text(encoding="utf-8")
    report.license = read_license(text)
    try:
        report.class_names = read_class_names(text)
        return build_class_map(report.class_names)
    except (ClassNamesError, NoPotholeClassError) as error:
        report.problems.append(str(error))
        return {}


def _audit_split(
    root: Path, split_dir: Path, class_map: dict[int, int], report: AuditReport
) -> SplitStats:
    stats = SplitStats()
    image_stems: set[str] = set()
    for image in list_images(split_dir):
        stats.images += 1
        image_stems.add(image.stem)
        label = label_path_for(image)
        if not label.is_file():
            stats.missing_label_files += 1
            stats.background += 1
            continue
        try:
            boxes = parse_label_text(label.read_text(encoding="utf-8"))
        except LabelError as error:
            report.problems.append(f"{label.relative_to(root).as_posix()}: {error}")
            continue
        unknown = {box.class_id for box in boxes if box.class_id >= len(report.class_names)}
        if report.class_names and unknown:
            numbers = ", ".join(str(number) for number in sorted(unknown))
            report.problems.append(
                f"{label.relative_to(root).as_posix()}: usa las clases {numbers}, "
                f"pero data.yaml solo tiene {len(report.class_names)}"
            )
            continue
        potholes = remap_boxes(boxes, class_map)
        if potholes:
            stats.with_boxes += 1
            stats.boxes += len(potholes)
        else:
            stats.background += 1

    labels_dir = split_dir / "labels"
    if labels_dir.is_dir():
        stats.labels_without_image = sum(
            1 for path in labels_dir.glob("*.txt") if path.stem not in image_stems
        )
    return stats
