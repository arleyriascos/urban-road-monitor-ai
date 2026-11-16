"""Find which images are copies of the same photo.

Roboflow exports each augmented copy of a photo (flipped, rotated, brighter) as a separate
file named ``<original>_jpg.rf.<hash>.jpg``. Every copy of a photo shares what comes before
``.rf.``, and that is the group key. If one copy goes to training and another to validation,
the model has already seen the validation photo, and the measures look better than they are.
"""

from pathlib import PurePath

ROBOFLOW_MARK = ".rf."


def group_key(filename: str) -> str:
    """Return the key shared by every copy of the same photo.

    Files that do not follow the Roboflow naming are their own group.
    """
    name = PurePath(filename).name
    if ROBOFLOW_MARK in name:
        return name.split(ROBOFLOW_MARK, 1)[0]
    return PurePath(name).stem
