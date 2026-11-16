import json
from pathlib import Path

import pytest
from fake_yolo import FakeYolo

from training import export as export_module
from training.export import export_arguments, export_model, model_info


def test_onnx_arguments() -> None:
    assert export_arguments("onnx", 416, False) == {
        "format": "onnx",
        "imgsz": 416,
        "half": False,
        "simplify": True,
        "dynamic": False,
    }


def test_tfjs_arguments_have_no_onnx_options() -> None:
    assert export_arguments("tfjs", 320, True) == {"format": "tfjs", "imgsz": 320, "half": True}


def test_unknown_format_and_bad_size_fail() -> None:
    with pytest.raises(ValueError, match="formato desconocido"):
        export_arguments("coreml", 416, False)
    with pytest.raises(ValueError, match="múltiplo de 32"):
        export_arguments("onnx", 400, False)


def test_model_info_lists_what_the_frontend_needs() -> None:
    info = model_info("onnx", 416, False, 123)
    assert info == {
        "format": "onnx",
        "input_size": 416,
        "classes": ["pothole"],
        "half_precision": False,
        "size_bytes": 123,
    }


def _fake_export(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, produced: Path) -> FakeYolo:
    fake = FakeYolo("best.pt")
    fake.export_path = str(produced)
    monkeypatch.setattr(export_module, "load_yolo", lambda path: fake)
    return fake


def test_export_writes_model_info_next_to_a_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    weights = tmp_path / "best.pt"
    weights.write_bytes(b"w")
    produced = tmp_path / "best.onnx"
    produced.write_bytes(b"x" * 10)
    fake = _fake_export(tmp_path, monkeypatch, produced)
    assert export_model(weights) == produced
    assert fake.calls[0][1]["format"] == "onnx"
    info = json.loads((tmp_path / "model_info.json").read_text(encoding="utf-8"))
    assert info["size_bytes"] == 10


def test_export_of_a_folder_writes_info_inside_and_counts_its_size(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    weights = tmp_path / "best.pt"
    weights.write_bytes(b"w")
    produced = tmp_path / "best_web_model"
    produced.mkdir()
    (produced / "model.json").write_bytes(b"1234")
    (produced / "group1-shard1of1.bin").write_bytes(b"123456")
    _fake_export(tmp_path, monkeypatch, produced)
    export_model(weights, "tfjs")
    info = json.loads((produced / "model_info.json").read_text(encoding="utf-8"))
    assert info["size_bytes"] == 10


def test_export_fails_when_nothing_was_produced(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    weights = tmp_path / "best.pt"
    weights.write_bytes(b"w")
    _fake_export(tmp_path, monkeypatch, tmp_path / "ghost.onnx")
    with pytest.raises(FileNotFoundError, match="no dejó"):
        export_model(weights)


def test_export_needs_the_weights(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        export_model(tmp_path / "best.pt")


def test_main_prints_the_result_and_reports_errors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    weights = tmp_path / "best.pt"
    weights.write_bytes(b"w")
    produced = tmp_path / "best.onnx"
    produced.write_bytes(b"x")
    _fake_export(tmp_path, monkeypatch, produced)
    assert export_module.main(["--weights", str(weights)]) == 0
    assert "Modelo exportado" in capsys.readouterr().out
    assert export_module.main(["--weights", str(tmp_path / "none.pt")]) == 1
    assert "no existe" in capsys.readouterr().out
