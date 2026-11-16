"""A stand-in for Ultralytics' YOLO, to test the scripts without installing it."""

from pathlib import Path
from typing import Any


class FakeResults:
    def __init__(self, save_dir: Path) -> None:
        self.save_dir = save_dir


class FakeYolo:
    """Records the calls it receives and returns canned answers."""

    def __init__(self, weights: str, run_dir: Path | None = None) -> None:
        self.weights = weights
        self.run_dir = run_dir or Path("runs/fake")
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.metrics: Any = None
        self.export_path = "model.onnx"

    def train(self, **kwargs: Any) -> FakeResults:
        self.calls.append(("train", kwargs))
        return FakeResults(self.run_dir)

    def val(self, **kwargs: Any) -> Any:
        self.calls.append(("val", kwargs))
        return self.metrics

    def export(self, **kwargs: Any) -> str:
        self.calls.append(("export", kwargs))
        return self.export_path
