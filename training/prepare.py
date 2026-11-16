"""Build the single dataset used for training from one or more downloaded sources.

Every source is audited first. Then all its images are grouped by photo (so the copies made by
augmentation stay together), the groups are shared between train, val and test, and the images
and labels are copied to ``<output>/images|labels/<split>/``. Labels keep only potholes, as
class 0. A ``data.yaml`` for Ultralytics and a ``manifest.json`` with the counts and licenses
are written next to them.

Command line::

    python -m training.prepare --source training/data/raw/potholes --output training/data/pothole
"""

import argparse
import json
import shutil
import sys
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

from training.audit import AuditReport, audit_source, format_audit, label_path_for, list_images
from training.classes import read_class_names
from training.groups import group_key
from training.labels import format_label_text, parse_label_text
from training.remap import POTHOLE_CLASS_NAME, build_class_map, remap_boxes
from training.split import DEFAULT_RATIOS, SPLITS, assign_splits

DATA_YAML_NAME = "data.yaml"
MANIFEST_NAME = "manifest.json"


class PrepareError(RuntimeError):
    """The dataset cannot be prepared."""


@dataclass(slots=True)
class PrepareResult:
    """What was written: image and box counts per split, and the audit of every source."""

    output: Path
    images: dict[str, int] = field(default_factory=lambda: dict.fromkeys(SPLITS, 0))
    boxes: dict[str, int] = field(default_factory=lambda: dict.fromkeys(SPLITS, 0))
    reports: list[AuditReport] = field(default_factory=list)


@dataclass(slots=True, frozen=True)
class _Item:
    source: str
    image: Path
    label: Path
    group: str


def prepare_dataset(
    sources: Sequence[Path],
    output: Path,
    ratios: tuple[float, float, float] = DEFAULT_RATIOS,
    seed: int = 42,
) -> PrepareResult:
    """Audit the sources and write the merged dataset to ``output``."""
    if not sources:
        raise PrepareError("hace falta al menos una fuente")
    names = [source.name for source in sources]
    if len(set(names)) != len(names):
        raise PrepareError("dos fuentes tienen el mismo nombre de carpeta: " + ", ".join(names))
    if output.exists() and any(output.iterdir()):
        raise PrepareError(f"{output} ya existe y no está vacía; bórrala o elige otra carpeta")

    result = PrepareResult(output=output)
    items: list[_Item] = []
    class_maps: dict[str, dict[int, int]] = {}
    for source in sources:
        report = audit_source(source)
        result.reports.append(report)
        if not report.ok:
            raise PrepareError(f"la fuente {source.name} tiene problemas:\n{format_audit(report)}")
        class_maps[source.name] = build_class_map(
            read_class_names((source / "data.yaml").read_text(encoding="utf-8"))
        )
        for split_dir in sorted(p for p in source.iterdir() if (p / "images").is_dir()):
            for image in list_images(split_dir):
                key = f"{source.name}/{group_key(image.name)}"
                items.append(_Item(source.name, image, label_path_for(image), key))

    assignment = assign_splits((item.group for item in items), ratios=ratios, seed=seed)
    for item in sorted(items, key=lambda entry: (entry.source, entry.image.name)):
        split = assignment[item.group]
        boxes = _read_potholes(item, class_maps[item.source])
        _write_item(item, split, boxes, output)
        result.images[split] += 1
        result.boxes[split] += len(boxes)

    (output / DATA_YAML_NAME).write_text(_data_yaml(output), encoding="utf-8")
    (output / MANIFEST_NAME).write_text(
        json.dumps(_manifest(result, seed, ratios), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return result


def format_result(result: PrepareResult) -> str:
    """The counts of a finished preparation as text."""
    lines = [f"Dataset escrito en {result.output}"]
    for split in SPLITS:
        lines.append(
            f"  {split}: {result.images[split]} imágenes, {result.boxes[split]} cajas de bache"
        )
    return "\n".join(lines)


def _read_potholes(item: _Item, class_map: dict[int, int]) -> list[str]:
    if not item.label.is_file():
        return []
    boxes = remap_boxes(parse_label_text(item.label.read_text(encoding="utf-8")), class_map)
    return [format_label_text([box]).strip() for box in boxes]


def _write_item(item: _Item, split: str, boxes: list[str], output: Path) -> None:
    images_dir = output / "images" / split
    labels_dir = output / "labels" / split
    images_dir.mkdir(parents=True, exist_ok=True)
    labels_dir.mkdir(parents=True, exist_ok=True)
    new_name = f"{item.source}__{item.image.name}"
    shutil.copy2(item.image, images_dir / new_name)
    text = "\n".join(boxes) + "\n" if boxes else ""
    (labels_dir / f"{Path(new_name).stem}.txt").write_text(text, encoding="utf-8")


def _data_yaml(output: Path) -> str:
    return (
        f"path: {output.resolve().as_posix()}\n"
        "train: images/train\n"
        "val: images/val\n"
        "test: images/test\n"
        "nc: 1\n"
        f"names: ['{POTHOLE_CLASS_NAME}']\n"
    )


def _manifest(
    result: PrepareResult, seed: int, ratios: tuple[float, float, float]
) -> dict[str, object]:
    return {
        "seed": seed,
        "ratios": list(ratios),
        "images": result.images,
        "boxes": result.boxes,
        "sources": [
            {
                "name": report.source.name,
                "license": report.license,
                "classes": report.class_names,
                "images": report.total_images,
            }
            for report in result.reports
        ],
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Prepara el dataset de baches para entrenar.")
    parser.add_argument("--source", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--audit-only", action="store_true", help="solo revisa las fuentes, no escribe nada"
    )
    args = parser.parse_args(argv)

    if args.audit_only:
        reports = [audit_source(source) for source in args.source]
        for report in reports:
            print(format_audit(report))
        return 0 if all(report.ok for report in reports) else 1
    try:
        result = prepare_dataset(args.source, args.output, seed=args.seed)
    except PrepareError as error:
        print(error, file=sys.stderr)
        return 1
    for report in result.reports:
        print(format_audit(report))
    print(format_result(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
