import random
import string
from typing import Any

from .common import Generator, ints, pair_count, size, wants_true

PUNCTUATION = " ,.:;!?-'\"@#"


def valid_palindrome(rng: random.Random, i: int) -> list[Any]:
    n = size(rng, i, 3000)
    alnum = string.ascii_letters + string.digits
    half = [rng.choice(alnum) for _ in range(max(1, n // 2))]
    core = half + ([rng.choice(alnum)] if rng.random() < 0.5 else []) + half[::-1]
    core = [c.upper() if rng.random() < 0.3 else c.lower() for c in core]
    if not wants_true(i):
        k = rng.randrange(len(half))
        mirror = core[len(core) - 1 - k].lower()
        core[k] = rng.choice([c for c in alnum if c.lower() != mirror])
    elif rng.random() < 0.1:
        return ["".join(rng.choice(PUNCTUATION) for _ in range(n))]
    chars: list[str] = []
    for c in core:
        chars.append(c)
        if rng.random() < 0.2:
            chars.append(rng.choice(PUNCTUATION))
    return ["".join(chars)]


def two_sum_sorted(rng: random.Random, i: int) -> list[Any]:
    n = size(rng, i, 3000, low=2)
    for _ in range(200):
        numbers = sorted(ints(rng, n, -1000, 1000))
        a, b = sorted(rng.sample(range(n), 2))
        target = numbers[a] + numbers[b]
        if pair_count(numbers, target) == 1:
            return [numbers, target]
    rest = sorted(ints(rng, n - 2, -998, 998))
    if rng.random() < 0.5:
        low = rest[0]
        return [[low - 2, low - 1] + rest, 2 * low - 3]
    high = rest[-1]
    return [rest + [high + 1, high + 2], 2 * high + 3]


def three_sum(rng: random.Random, i: int) -> list[Any]:
    n = size(rng, i, 800, low=3)
    span = rng.choice([3, 10, 100, 10**5])
    return [ints(rng, n, -span, span)]


def container_with_most_water(rng: random.Random, i: int) -> list[Any]:
    n = size(rng, i, 5000, low=2)
    return [ints(rng, n, 0, rng.choice([10, 10**4]))]


GENERATORS: dict[str, Generator] = {
    "valid-palindrome": valid_palindrome,
    "two-sum-ii-input-array-is-sorted": two_sum_sorted,
    "3sum": three_sum,
    "container-with-most-water": container_with_most_water,
}
