import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from fake_yolo import FakeYolo

from training import evaluate as evaluate_module
from training.evaluate import (
    EvalMetrics,
    evaluate,
    extract_metrics,
    format_metrics,
    metrics_to_json,
)


def _raw(map50: float = 0.6, map5095: float = 0.3, mp: float = 0.7, mr: float = 0.5) -> object:
    return SimpleNamespace(box=SimpleNamespace(map50=map50, map=map5095, mp=mp, mr=mr))


def test_extract_metrics_reads_the_ultralytics_fields() -> None:
    metrics = extract_metrics(_raw(), "test", 416)
    assert (metrics.map50, metrics.map50_95, metrics.precision, metrics.recall) == (
        0.6,
        0.3,
        0.7,
        0.5,
    )
    assert metrics.split == "test"


def test_f1_is_the_harmonic_mean() -> None:
    metrics = EvalMetrics("test", 416, 0.6, 0.3, precision=0.8, recall=0.4)
    assert metrics.f1 == pytest.approx(0.5333, abs=1e-3)


def test_f1_is_zero_when_precision_and_recall_are_zero() -> None:
    assert EvalMetrics("test", 416, 0, 0, 0, 0).f1 == 0.0


def test_json_has_rounded_values_and_f1() -> None:
    data = json.loads(metrics_to_json(extract_metrics(_raw(map50=0.123456), "test", 416)))
    assert data["map50"] == 0.1235
    assert data["f1"] == pytest.approx(0.5833, abs=1e-4)
    assert data["image_size"] == 416


def test_text_report_mentions_every_metric() -> None:
    text = format_metrics(extract_metrics(_raw(), "val", 320))
    for word in ("val", "320", "mAP50", "precisión", "exhaustividad", "F1"):
        assert word in text


def test_evaluate_asks_yolo_to_validate_on_the_split(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    weights = tmp_path / "best.pt"
    data = tmp_path / "data.yaml"
    weights.write_bytes(b"w")
    data.write_text("nc: 1\n", encoding="utf-8")
    fake = FakeYolo(str(weights))
    fake.metrics = _raw()
    monkeypatch.setattr(evaluate_module, "load_yolo", lambda path: fake)
    metrics = evaluate(weights, data, split="test")
    assert metrics.map50 == 0.6
    assert fake.calls[0][1]["split"] == "test"
    assert fake.calls[0][1]["imgsz"] == 416


def test_evaluate_needs_existing_files(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        evaluate(tmp_path / "best.pt", tmp_path / "data.yaml")


def test_main_writes_metrics_next_to_the_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    run = tmp_path / "run"
    (run / "weights").mkdir(parents=True)
    weights = run / "weights" / "best.pt"
    weights.write_bytes(b"w")
    data = tmp_path / "data.yaml"
    data.write_text("nc: 1\n", encoding="utf-8")
    fake = FakeYolo(str(weights))
    fake.metrics = _raw()
    monkeypatch.setattr(evaluate_module, "load_yolo", lambda path: fake)
    code = evaluate_module.main(["--weights", str(weights), "--data", str(data)])
    assert code == 0
    assert json.loads((run / "metrics.json").read_text(encoding="utf-8"))["map50"] == 0.6
    assert "mAP50" in capsys.readouterr().out


def test_main_reports_missing_files(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code = evaluate_module.main(
        ["--weights", str(tmp_path / "x.pt"), "--data", str(tmp_path / "d.yaml")]
    )
    assert code == 1
    assert "no existe" in capsys.readouterr().out
