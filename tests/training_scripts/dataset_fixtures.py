"""Tiny datasets written to a temporary folder, shared by the tests of the training scripts.

The images are just a few bytes: the scripts never open them, they only copy them.
"""

from pathlib import Path

POTHOLE_YAML = "train: ../train/images\nval: ../valid/images\nnc: 1\nnames: ['pothole']\n"
LICENSED_YAML = POTHOLE_YAML + "roboflow:\n  license: CC BY 4.0\n"
DAMAGE_YAML = "nc: 4\nnames: ['D00', 'D10', 'D20', 'D40']\n"

POTHOLE_BOX = "0 0.500000 0.500000 0.200000 0.100000\n"


def write_image(split_dir: Path, name: str, label_text: str | None) -> None:
    """Write a fake image and, unless label_text is None, its label file."""
    (split_dir / "images").mkdir(parents=True, exist_ok=True)
    (split_dir / "labels").mkdir(parents=True, exist_ok=True)
    (split_dir / "images" / name).write_bytes(b"fake image " + name.encode())
    if label_text is not None:
        stem = Path(name).stem
        (split_dir / "labels" / f"{stem}.txt").write_text(label_text, encoding="utf-8")


def make_source(root: Path, yaml_text: str = POTHOLE_YAML) -> Path:
    """A valid source: 3 original photos, one of them with two augmented copies, one background."""
    root.mkdir(parents=True, exist_ok=True)
    (root / "data.yaml").write_text(yaml_text, encoding="utf-8")
    train = root / "train"
    write_image(train, "a_jpg.rf.111.jpg", POTHOLE_BOX)
    write_image(train, "a_jpg.rf.222.jpg", POTHOLE_BOX)
    write_image(train, "a_jpg.rf.333.jpg", POTHOLE_BOX)
    write_image(train, "b_jpg.rf.111.jpg", POTHOLE_BOX + POTHOLE_BOX)
    write_image(train, "c_jpg.rf.111.jpg", "")
    return root


def make_big_source(root: Path, photos: int = 30, copies: int = 3) -> Path:
    """A source with many photos and several copies each, spread over its own folders."""
    root.mkdir(parents=True, exist_ok=True)
    (root / "data.yaml").write_text(POTHOLE_YAML, encoding="utf-8")
    for photo in range(photos):
        folder = root / ("train" if photo % 5 else "valid")
        for copy in range(copies):
            write_image(folder, f"photo{photo:03d}_jpg.rf.copy{copy}.jpg", POTHOLE_BOX)
    return root
