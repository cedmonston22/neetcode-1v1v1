import random
from typing import Any

from .common import Generator, ints, size


def reverse_linked_list(rng: random.Random, i: int) -> list[Any]:
    return [ints(rng, size(rng, i, 5000, low=0), -5000, 5000)]


def merge_two_sorted_lists(rng: random.Random, i: int) -> list[Any]:
    a = sorted(ints(rng, size(rng, i, 50, low=0), -100, 100))
    b = sorted(ints(rng, size(rng, i, 50, low=0), -100, 100))
    return [a, b]


def reorder_list(rng: random.Random, i: int) -> list[Any]:
    return [ints(rng, size(rng, i, 5000), 1, 1000)]


def remove_nth_from_end(rng: random.Random, i: int) -> list[Any]:
    length = size(rng, i, 30)
    return [ints(rng, length, 0, 100), rng.randint(1, length)]


def digits(rng: random.Random, length: int) -> list[int]:
    if length == 1:
        return [rng.randint(0, 9)]
    return ints(rng, length - 1, 0, 9) + [rng.randint(1, 9)]


def add_two_numbers(rng: random.Random, i: int) -> list[Any]:
    if rng.random() < 0.2:
        return [[9] * size(rng, i, 100), [9] * size(rng, i, 100)]
    return [digits(rng, size(rng, i, 100)), digits(rng, size(rng, i, 100))]


def find_duplicate(rng: random.Random, i: int) -> list[Any]:
    n = size(rng, i, 5000)
    duplicate = rng.randint(1, n)
    copies = rng.choice([2, 2, 2, rng.randint(2, n + 1)])
    others = [v for v in rng.sample(range(1, n + 1), min(n, n + 1 - copies + 1)) if v != duplicate]
    nums = [duplicate] * copies + others[: n + 1 - copies]
    rng.shuffle(nums)
    return [nums]


GENERATORS: dict[str, Generator] = {
    "reverse-linked-list": reverse_linked_list,
    "merge-two-sorted-lists": merge_two_sorted_lists,
    "reorder-list": reorder_list,
    "remove-nth-node-from-end-of-list": remove_nth_from_end,
    "add-two-numbers": add_two_numbers,
    "find-the-duplicate-number": find_duplicate,
}
