"""The only place that imports Ultralytics.

Ultralytics is heavy and is installed only where the model is trained (Colab), not in the
Render service nor in the normal test run. Importing it here, at call time, keeps every other
module importable without it and lets the tests replace it with a fake.
"""

import importlib
from typing import Any


class UltralyticsMissingError(RuntimeError):
    """Ultralytics is not installed in this environment."""


def load_yolo(weights: str) -> Any:
    """Open a YOLO model from a ``.pt`` file or a base name such as ``yolov8n.pt``."""
    try:
        module = importlib.import_module("ultralytics")
    except ModuleNotFoundError as error:
        raise UltralyticsMissingError(
            "falta ultralytics; instálalo con: pip install -r training/requirements.txt"
        ) from error
    return module.YOLO(weights)
