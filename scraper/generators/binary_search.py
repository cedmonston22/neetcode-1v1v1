import random
from typing import Any

from .common import Generator, distinct_ints, ints, size, wants_true


def pick_target(rng: random.Random, values: list[int], lo: int, hi: int, present: bool) -> int:
    if present:
        return rng.choice(values)
    taken = set(values)
    while True:
        target = rng.randint(lo, hi)
        if target not in taken:
            return target


def rotate(rng: random.Random, values: list[int]) -> list[int]:
    k = rng.randint(0, len(values) - 1)
    return values[k:] + values[:k]


def binary_search(rng: random.Random, i: int) -> list[Any]:
    n = size(rng, i, 5000)
    nums = sorted(distinct_ints(rng, n, -9999, 9999))
    return [nums, pick_target(rng, nums, -9999, 9999, wants_true(i))]


def search_2d_matrix(rng: random.Random, i: int) -> list[Any]:
    m = size(rng, i, 70)
    n = size(rng, i, 70)
    flat = sorted(distinct_ints(rng, m * n, -10**4, 10**4))
    matrix = [flat[r * n : (r + 1) * n] for r in range(m)]
    return [matrix, pick_target(rng, flat, -10**4, 10**4, wants_true(i))]


def koko_eating_bananas(rng: random.Random, i: int) -> list[Any]:
    n = size(rng, i, 3000)
    piles = ints(rng, n, 1, rng.choice([20, 10**9]))
    h = rng.randint(n, rng.choice([n + 5, n * 10, 10**9]))
    return [piles, h]


def find_min_rotated(rng: random.Random, i: int) -> list[Any]:
    n = size(rng, i, 5000)
    return [rotate(rng, sorted(distinct_ints(rng, n, -5000, 5000)))]


def search_rotated(rng: random.Random, i: int) -> list[Any]:
    n = size(rng, i, 5000)
    nums = rotate(rng, sorted(distinct_ints(rng, n, -10**4, 10**4)))
    return [nums, pick_target(rng, nums, -10**4, 10**4, wants_true(i))]


GENERATORS: dict[str, Generator] = {
    "binary-search": binary_search,
    "search-a-2d-matrix": search_2d_matrix,
    "koko-eating-bananas": koko_eating_bananas,
    "find-minimum-in-rotated-sorted-array": find_min_rotated,
    "search-in-rotated-sorted-array": search_rotated,
}
