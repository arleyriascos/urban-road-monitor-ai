from training.groups import group_key


def test_copies_of_a_roboflow_photo_share_the_key() -> None:
    first = group_key("road-12_jpg.rf.0a1b2c3d4e5f60718293a4b5c6d7e8f9.jpg")
    second = group_key("road-12_jpg.rf.ffffffffffffffffffffffffffffffff.jpg")
    assert first == second == "road-12_jpg"


def test_different_photos_have_different_keys() -> None:
    assert group_key("road-12_jpg.rf.aaa.jpg") != group_key("road-13_jpg.rf.aaa.jpg")


def test_a_file_without_the_roboflow_mark_is_its_own_group() -> None:
    assert group_key("IMG_0042.jpeg") == "IMG_0042"


def test_the_folder_does_not_matter() -> None:
    assert group_key("train/images/road-12_jpg.rf.aaa.jpg") == "road-12_jpg"


def test_a_name_with_dots_keeps_everything_before_the_mark() -> None:
    assert group_key("a.b.c_jpg.rf.xyz.jpg") == "a.b.c_jpg"
