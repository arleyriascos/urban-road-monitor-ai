from pathlib import Path

import pytest
from fake_yolo import FakeYolo

from training import train
from training.train import TrainSettings, run_training, train_arguments
from training.yolo import UltralyticsMissingError, load_yolo


def test_default_arguments_follow_the_project_decisions() -> None:
    arguments = train_arguments(TrainSettings(data=Path("data.yaml")))
    assert arguments["epochs"] == 50
    assert arguments["imgsz"] == 416
    assert arguments["single_cls"] is True
    assert arguments["seed"] == 42
    assert "device" not in arguments


def test_device_is_passed_only_when_given() -> None:
    arguments = train_arguments(TrainSettings(data=Path("data.yaml"), device="0"))
    assert arguments["device"] == "0"


@pytest.mark.parametrize("size", [0, 31, 400, 415])
def test_image_size_must_be_a_multiple_of_32(size: int) -> None:
    with pytest.raises(ValueError, match="múltiplo de 32"):
        train_arguments(TrainSettings(data=Path("data.yaml"), image_size=size))


def test_epochs_must_be_positive() -> None:
    with pytest.raises(ValueError, match="epochs"):
        train_arguments(TrainSettings(data=Path("data.yaml"), epochs=0))


def test_run_training_calls_yolo_and_returns_the_run_folder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    data = tmp_path / "data.yaml"
    data.write_text("nc: 1\n", encoding="utf-8")
    fake = FakeYolo("yolov8n.pt", run_dir=tmp_path / "run")
    monkeypatch.setattr(train, "load_yolo", lambda weights: fake)
    assert run_training(TrainSettings(data=data)) == tmp_path / "run"
    assert fake.calls[0][0] == "train"
    assert fake.calls[0][1]["data"] == str(data)


def test_run_training_needs_the_prepared_dataset(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="training.prepare"):
        run_training(TrainSettings(data=tmp_path / "missing.yaml"))


def test_main_reports_a_missing_dataset(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert train.main(["--data", str(tmp_path / "missing.yaml")]) == 1
    assert "training.prepare" in capsys.readouterr().out


def test_main_prints_where_the_weights_are(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    data = tmp_path / "data.yaml"
    data.write_text("nc: 1\n", encoding="utf-8")
    monkeypatch.setattr(train, "load_yolo", lambda weights: FakeYolo(weights, tmp_path / "run"))
    assert train.main(["--data", str(data), "--epochs", "3"]) == 0
    assert "best.pt" in capsys.readouterr().out


def test_load_yolo_explains_how_to_install_ultralytics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import importlib

    def refuse(name: str) -> None:
        raise ModuleNotFoundError(name)

    monkeypatch.setattr(importlib, "import_module", refuse)
    with pytest.raises(UltralyticsMissingError, match="requirements.txt"):
        load_yolo("yolov8n.pt")
