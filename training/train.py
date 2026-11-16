"""Train the pothole detector (YOLOv8n, one class) on the prepared dataset.

Command line::

    python -m training.train --data training/data/pothole/data.yaml
"""

import argparse
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from training.yolo import UltralyticsMissingError, load_yolo

BASE_MODEL = "yolov8n.pt"
IMAGE_SIZE = 416


@dataclass(slots=True, frozen=True)
class TrainSettings:
    """What the training run uses. The defaults are the ones decided for the project."""

    data: Path
    model: str = BASE_MODEL
    epochs: int = 50
    image_size: int = IMAGE_SIZE
    batch: int = 16
    seed: int = 42
    patience: int = 15
    project: Path = Path("training/runs")
    name: str = "pothole"
    device: str | None = None


def train_arguments(settings: TrainSettings) -> dict[str, Any]:
    """The keyword arguments for ``YOLO.train``."""
    if settings.epochs < 1:
        raise ValueError("epochs debe ser al menos 1")
    if settings.image_size < 32 or settings.image_size % 32:
        raise ValueError("imgsz debe ser múltiplo de 32 (por ejemplo 320 o 416)")
    arguments: dict[str, Any] = {
        "data": str(settings.data),
        "epochs": settings.epochs,
        "imgsz": settings.image_size,
        "batch": settings.batch,
        "seed": settings.seed,
        "patience": settings.patience,
        "project": str(settings.project),
        "name": settings.name,
        "exist_ok": False,
        "single_cls": True,
        "deterministic": True,
    }
    if settings.device is not None:
        arguments["device"] = settings.device
    return arguments


def run_training(settings: TrainSettings) -> Path:
    """Train and return the folder of the run (it holds ``weights/best.pt``)."""
    if not settings.data.is_file():
        raise FileNotFoundError(f"no existe {settings.data}; corre primero training.prepare")
    model = load_yolo(settings.model)
    results = model.train(**train_arguments(settings))
    return Path(results.save_dir)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Entrena el detector de baches.")
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--model", default=BASE_MODEL)
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--imgsz", type=int, default=IMAGE_SIZE)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--name", default="pothole")
    parser.add_argument("--device", default=None)
    args = parser.parse_args(argv)
    settings = TrainSettings(
        data=args.data,
        model=args.model,
        epochs=args.epochs,
        image_size=args.imgsz,
        batch=args.batch,
        seed=args.seed,
        name=args.name,
        device=args.device,
    )
    try:
        run_dir = run_training(settings)
    except (FileNotFoundError, UltralyticsMissingError, ValueError) as error:
        print(error)
        return 1
    print(f"Entrenamiento terminado. Pesos en {run_dir / 'weights' / 'best.pt'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
