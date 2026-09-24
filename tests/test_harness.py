import pytest

from server.harness import (
    build_list,
    build_tree,
    deserialize,
    list_to_values,
    outputs_match,
    to_plain,
    tree_to_values,
)


@pytest.mark.parametrize("values", [[], [1], [1, 2, 3, 4, 5]])
def test_list_round_trip(values: list[int]) -> None:
    assert list_to_values(build_list(values)) == values


@pytest.mark.parametrize(
    "values",
    [
        [],
        [1],
        [3, 9, 20, None, None, 15, 7],
        [1, 2, 3, None, 5, None, 4],
        [1, None, 2, None, 3],
    ],
)
def test_tree_round_trip(values: list[int | None]) -> None:
    assert tree_to_values(build_tree(values)) == values


def test_cyclic_list_is_rejected() -> None:
    head = build_list([1, 2, 3])
    assert head is not None and head.next is not None and head.next.next is not None
    head.next.next.next = head
    with pytest.raises(ValueError):
        list_to_values(head)


def test_deserialize_scalars_and_arrays() -> None:
    assert deserialize("integer[]", "[2,7,11,15]") == [2, 7, 11, 15]
    assert deserialize("string", '"anagram"') == "anagram"
    assert deserialize("boolean", "true") is True
    assert deserialize("character[][]", '[["5","."]]') == [["5", "."]]


def test_to_plain_converts_tuples_and_integral_floats() -> None:
    assert to_plain("list<list<integer>>", [(1, 2), (3,)]) == [[1, 2], [3]]
    assert to_plain("integer", 3.0) == 3


def test_to_plain_rejects_wrong_node_type() -> None:
    with pytest.raises(TypeError):
        to_plain("ListNode", [1, 2])


def test_exact_compare() -> None:
    assert outputs_match("[0,1]", "[0,1]", "exact")
    assert not outputs_match("[0,1]", "[1,0]", "exact")


def test_bool_and_int_are_not_equal() -> None:
    assert not outputs_match("true", "1", "exact")
    assert not outputs_match("1", "true", "exact")


def test_unordered_compare() -> None:
    assert outputs_match("[1,2]", "[2,1]", "unordered")
    assert not outputs_match("[1,2]", "[2,2]", "unordered")


def test_unordered_nested_compare() -> None:
    expected = '[["bat"],["nat","tan"],["ate","eat","tea"]]'
    actual = '[["eat","tea","ate"],["bat"],["tan","nat"]]'
    assert outputs_match(expected, actual, "unordered_nested")
    assert not outputs_match(expected, actual, "unordered")
