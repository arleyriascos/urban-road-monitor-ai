"""Examples of the singly linked list: each test shows one behavior."""

from app.structures.singly_linked_list import SinglyLinkedList


def build(*values: int) -> SinglyLinkedList[int]:
    result: SinglyLinkedList[int] = SinglyLinkedList()
    for value in values:
        result.push_back(value)
    return result


def test_a_new_list_is_empty() -> None:
    items: SinglyLinkedList[int] = SinglyLinkedList()

    assert items.is_empty()
    assert len(items) == 0
    assert list(items) == []
    assert items.is_valid()


def test_walks_the_values_in_the_order_they_were_added() -> None:
    items = build(30, 10, 20)

    assert list(items) == [30, 10, 20]


def test_len_follows_push_back() -> None:
    items: SinglyLinkedList[int] = SinglyLinkedList()

    items.push_back(5)
    assert len(items) == 1
    assert not items.is_empty()

    items.push_back(6)
    assert len(items) == 2


def test_can_be_walked_more_than_once() -> None:
    items = build(1, 2, 3)

    assert list(items) == [1, 2, 3]
    assert list(items) == [1, 2, 3]
    assert len(items) == 3


def test_keeps_adding_at_the_end_after_being_walked() -> None:
    items = build(1, 2)
    assert list(items) == [1, 2]

    items.push_back(3)

    assert list(items) == [1, 2, 3]


def test_holds_the_same_value_more_than_once() -> None:
    items = build(7, 7, 7)

    assert list(items) == [7, 7, 7]
    assert len(items) == 3


def test_holds_values_of_any_type() -> None:
    edges: SinglyLinkedList[tuple[int, float]] = SinglyLinkedList()
    edges.push_back((4, 120.5))
    edges.push_back((9, 80.0))

    assert list(edges) == [(4, 120.5), (9, 80.0)]


def test_two_lists_do_not_share_their_values() -> None:
    first = build(1)
    second = build(2)

    first.push_back(3)

    assert list(first) == [1, 3]
    assert list(second) == [2]


def test_is_valid_after_every_push() -> None:
    items: SinglyLinkedList[int] = SinglyLinkedList()

    for value in range(25):
        items.push_back(value)
        assert items.is_valid()


def test_is_valid_notices_a_wrong_size() -> None:
    items = build(1, 2, 3)
    items._size = 2

    assert not items.is_valid()


def test_is_valid_notices_a_wrong_last_link() -> None:
    items = build(1, 2, 3)
    items._tail = items._head

    assert not items.is_valid()


def test_is_valid_notices_a_loop() -> None:
    items = build(1, 2, 3)
    assert items._head is not None and items._tail is not None
    items._tail.next = items._head

    assert not items.is_valid()


def test_is_valid_notices_a_missing_last_link() -> None:
    items = build(1, 2)
    items._tail = None

    assert not items.is_valid()


def test_is_valid_notices_an_empty_list_with_a_size() -> None:
    items: SinglyLinkedList[int] = SinglyLinkedList()
    items._size = 1

    assert not items.is_valid()
