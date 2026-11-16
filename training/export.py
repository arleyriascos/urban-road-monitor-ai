"""Convert the trained weights to a format the browser can run, and describe the result.

ONNX (run with onnxruntime-web) works with any Ultralytics version. TensorFlow.js only exists
up to the version pinned in requirements.txt, and is kept as an option in case the ONNX model
runs too slowly on the phones.

Command line::

    python -m training.export --weights training/runs/pothole/weights/best.pt --format onnx
"""

import argparse
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from training.remap import POTHOLE_CLASS_NAME
from training.train import IMAGE_SIZE
from training.yolo import UltralyticsMissingError, load_yolo

FORMATS = ("onnx", "tfjs")
INFO_NAME = "model_info.json"


def export_arguments(fmt: str, image_size: int, half: bool) -> dict[str, Any]:
    """The keyword arguments for ``YOLO.export``."""
    if fmt not in FORMATS:
        raise ValueError(f"formato desconocido: {fmt}; usa uno de {', '.join(FORMATS)}")
    if image_size < 32 or image_size % 32:
        raise ValueError("imgsz debe ser múltiplo de 32")
    arguments: dict[str, Any] = {"format": fmt, "imgsz": image_size, "half": half}
    if fmt == "onnx":
        arguments["simplify"] = True
        arguments["dynamic"] = False
    return arguments


def model_info(fmt: str, image_size: int, half: bool, size_bytes: int) -> dict[str, Any]:
    """What the frontend needs to know to load the model."""
    return {
        "format": fmt,
        "input_size": image_size,
        "classes": [POTHOLE_CLASS_NAME],
        "half_precision": half,
        "size_bytes": size_bytes,
    }


def export_model(
    weights: Path, fmt: str = "onnx", image_size: int = IMAGE_SIZE, half: bool = False
) -> Path:
    """Export the weights and write ``model_info.json`` next to the result."""
    if not weights.is_file():
        raise FileNotFoundError(f"no existe {weights}")
    arguments = export_arguments(fmt, image_size, half)
    exported = Path(str(load_yolo(str(weights)).export(**arguments)))
    if not exported.exists():
        raise FileNotFoundError(f"la exportación no dejó {exported}")
    info = model_info(fmt, image_size, half, _size_of(exported))
    info_path = (exported if exported.is_dir() else exported.parent) / INFO_NAME
    info_path.write_text(json.dumps(info, indent=2) + "\n", encoding="utf-8")
    return exported


def _size_of(path: Path) -> int:
    if path.is_file():
        return path.stat().st_size
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Exporta el detector para el navegador.")
    parser.add_argument("--weights", type=Path, required=True)
    parser.add_argument("--format", default="onnx", choices=FORMATS)
    parser.add_argument("--imgsz", type=int, default=IMAGE_SIZE)
    parser.add_argument("--half", action="store_true", help="precisión de 16 bits (pesa la mitad)")
    args = parser.parse_args(argv)
    try:
        exported = export_model(args.weights, args.format, args.imgsz, args.half)
    except (FileNotFoundError, UltralyticsMissingError, ValueError) as error:
        print(error)
        return 1
    print(f"Modelo exportado en {exported} ({_size_of(exported) / 1_000_000:.1f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
