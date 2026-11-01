"""Examples of the stack: each test shows one behavior."""

import pytest

from app.structures.stack import Stack, StackError


def test_a_new_stack_is_empty() -> None:
    stack: Stack[int] = Stack()

    assert stack.is_empty()
    assert len(stack) == 0


def test_pops_items_in_reverse_order() -> None:
    stack: Stack[str] = Stack()
    for item in ("origin", "middle", "destination"):
        stack.push(item)

    assert [stack.pop() for _ in range(3)] == ["destination", "middle", "origin"]
    assert stack.is_empty()


def test_peek_returns_the_top_without_removing_it() -> None:
    stack: Stack[int] = Stack()
    stack.push(1)
    stack.push(2)

    assert stack.peek() == 2
    assert len(stack) == 2


def test_len_follows_push_and_pop() -> None:
    stack: Stack[int] = Stack()

    stack.push(10)
    stack.push(20)
    assert len(stack) == 2

    stack.pop()
    assert len(stack) == 1
    assert not stack.is_empty()


def test_holds_the_same_item_more_than_once() -> None:
    stack: Stack[int] = Stack()
    stack.push(7)
    stack.push(7)

    assert [stack.pop(), stack.pop()] == [7, 7]


def test_can_be_used_again_after_being_emptied() -> None:
    stack: Stack[int] = Stack()
    stack.push(1)
    stack.pop()

    stack.push(2)

    assert stack.pop() == 2


def test_rejects_popping_an_empty_stack() -> None:
    stack: Stack[int] = Stack()

    with pytest.raises(StackError, match="empty"):
        stack.pop()


def test_rejects_peeking_an_empty_stack() -> None:
    stack: Stack[int] = Stack()

    with pytest.raises(StackError, match="empty"):
        stack.peek()
