"""Measure the trained model on the test split, which it never saw during training.

Precision and recall are the ones Ultralytics reports at the confidence where F1 is highest.
The result is written to ``metrics.json`` so it can go into the model card.

Command line::

    python -m training.evaluate --weights training/runs/pothole/weights/best.pt \
        --data training/data/pothole/data.yaml
"""

import argparse
import json
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from training.train import IMAGE_SIZE
from training.yolo import UltralyticsMissingError, load_yolo


@dataclass(slots=True, frozen=True)
class EvalMetrics:
    """Quality of the detector on one split."""

    split: str
    image_size: int
    map50: float
    map50_95: float
    precision: float
    recall: float

    @property
    def f1(self) -> float:
        total = self.precision + self.recall
        return 0.0 if total == 0 else 2 * self.precision * self.recall / total


def extract_metrics(raw: Any, split: str, image_size: int) -> EvalMetrics:
    """Read the numbers from what ``YOLO.val`` returns (``raw.box``)."""
    box = raw.box
    return EvalMetrics(
        split=split,
        image_size=image_size,
        map50=float(box.map50),
        map50_95=float(box.map),
        precision=float(box.mp),
        recall=float(box.mr),
    )


def evaluate(
    weights: Path, data: Path, split: str = "test", image_size: int = IMAGE_SIZE
) -> EvalMetrics:
    """Run validation of ``weights`` on one split of the dataset."""
    if not weights.is_file():
        raise FileNotFoundError(f"no existe {weights}")
    if not data.is_file():
        raise FileNotFoundError(f"no existe {data}")
    model = load_yolo(str(weights))
    raw = model.val(data=str(data), split=split, imgsz=image_size, plots=False)
    return extract_metrics(raw, split, image_size)


def metrics_to_json(metrics: EvalMetrics) -> str:
    """The metrics (with F1) as indented JSON."""
    values = asdict(metrics)
    values["f1"] = metrics.f1
    return json.dumps({key: _rounded(value) for key, value in values.items()}, indent=2) + "\n"


def format_metrics(metrics: EvalMetrics) -> str:
    return (
        f"Evaluación en {metrics.split} (imgsz {metrics.image_size}): "
        f"mAP50 {metrics.map50:.3f}, mAP50-95 {metrics.map50_95:.3f}, "
        f"precisión {metrics.precision:.3f}, exhaustividad {metrics.recall:.3f}, "
        f"F1 {metrics.f1:.3f}"
    )


def _rounded(value: object) -> object:
    return round(value, 4) if isinstance(value, float) else value


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evalúa el detector de baches.")
    parser.add_argument("--weights", type=Path, required=True)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--split", default="test", choices=["train", "val", "test"])
    parser.add_argument("--imgsz", type=int, default=IMAGE_SIZE)
    parser.add_argument("--output", type=Path, default=None, help="dónde guardar metrics.json")
    args = parser.parse_args(argv)
    try:
        metrics = evaluate(args.weights, args.data, args.split, args.imgsz)
    except (FileNotFoundError, UltralyticsMissingError) as error:
        print(error)
        return 1
    print(format_metrics(metrics))
    output = args.output or args.weights.parent.parent / "metrics.json"
    output.write_text(metrics_to_json(metrics), encoding="utf-8")
    print(f"Métricas guardadas en {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
