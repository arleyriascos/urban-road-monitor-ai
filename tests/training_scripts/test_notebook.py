import json
import re
from pathlib import Path

NOTEBOOK = Path(__file__).parents[2] / "training" / "colab" / "entrenar_baches.ipynb"
MODULES = ("prepare", "train", "evaluate", "export")


def _notebook() -> dict[str, object]:
    return json.loads(NOTEBOOK.read_text(encoding="utf-8"))  # type: ignore[no-any-return]


def _code_text() -> str:
    cells = _notebook()["cells"]
    assert isinstance(cells, list)
    return "\n".join("".join(cell["source"]) for cell in cells if cell["cell_type"] == "code")


def test_notebook_is_valid_and_has_no_saved_outputs() -> None:
    notebook = _notebook()
    assert notebook["nbformat"] == 4
    cells = notebook["cells"]
    assert isinstance(cells, list)
    for cell in cells:
        if cell["cell_type"] == "code":
            assert cell["outputs"] == []
            assert cell["execution_count"] is None


def test_notebook_runs_every_script_of_the_package() -> None:
    text = _code_text()
    for module in MODULES:
        assert f"python -m training.{module}" in text


def test_every_module_the_notebook_runs_exists() -> None:
    root = NOTEBOOK.parents[1]
    for module in MODULES:
        assert (root / f"{module}.py").is_file()


def test_notebook_has_no_keys_or_tokens() -> None:
    text = NOTEBOOK.read_text(encoding="utf-8")
    assert not re.search(r"api[_-]?key\s*=|ghp_|github_pat_|AIza|token\s*=", text, re.IGNORECASE)


def test_datasets_are_unzipped_with_python_not_with_a_shell_loop() -> None:
    # A "!for" line did not expand {DATASETS_DIR}: the zips were never found.
    text = _code_text()
    assert "!for" not in text
    assert "zipfile.ZipFile" in text
    assert "DATASETS_DIR.glob" in text
