import random
from typing import Any

from .common import Generator, distinct_ints, ints, lowercase, pair_count, size, wants_true


def contains_duplicate(rng: random.Random, i: int) -> list[Any]:
    if not wants_true(i):
        return [distinct_ints(rng, size(rng, i, 3000), -10**9, 10**9)]
    n = size(rng, i, 3000, low=2)
    nums = ints(rng, n, -10**9, 10**9)
    a, b = rng.sample(range(n), 2)
    nums[a] = nums[b]
    return [nums]


def valid_anagram(rng: random.Random, i: int) -> list[Any]:
    n = size(rng, i, 3000)
    alphabet = "abc" if rng.random() < 0.3 else "abcdefghijklmnopqrstuvwxyz"
    s = lowercase(rng, n, alphabet)
    t = list(s)
    rng.shuffle(t)
    if wants_true(i):
        return [s, "".join(t)]
    if rng.random() < 0.7:
        k = rng.randrange(n)
        t[k] = rng.choice([c for c in alphabet if c != t[k]])
    else:
        t.append(rng.choice(alphabet))
    return [s, "".join(t)]


def two_sum(rng: random.Random, i: int) -> list[Any]:
    n = size(rng, i, 3000, low=2)
    span = 5 * 10**8 if rng.random() < 0.5 else max(10, n * 3)
    while True:
        nums = ints(rng, n, -span, span)
        a, b = rng.sample(range(n), 2)
        target = nums[a] + nums[b]
        if pair_count(nums, target) == 1:
            return [nums, target]


def group_anagrams(rng: random.Random, i: int) -> list[Any]:
    n = size(rng, i, 1500)
    bases = [lowercase(rng, rng.randint(0, 6), "abcde") for _ in range(max(1, n // 3))]
    strs: list[str] = []
    for _ in range(n):
        letters = list(rng.choice(bases))
        rng.shuffle(letters)
        strs.append("".join(letters))
    return [strs]


def top_k_frequent(rng: random.Random, i: int) -> list[Any]:
    unique = size(rng, i, 60)
    values = distinct_ints(rng, unique, -10**4, 10**4)
    freqs = rng.sample(range(1, 80), unique)
    nums = [v for v, f in zip(values, freqs) for _ in range(f)]
    rng.shuffle(nums)
    return [nums, rng.randint(1, unique)]


def product_except_self(rng: random.Random, i: int) -> list[Any]:
    n = size(rng, i, 3000, low=2)
    nums = [rng.choice([1, -1]) for _ in range(n)]
    budget = 2**31 - 1
    product = 1
    for index in rng.sample(range(n), min(n, rng.randint(0, 25))):
        value = rng.randint(-30, 30)
        if value == 0:
            if rng.random() < 0.3:
                nums[index] = 0
            continue
        if product * abs(value) <= budget:
            product *= abs(value)
            nums[index] = value
    return [nums]


def valid_sudoku(rng: random.Random, i: int) -> list[Any]:
    digits = list("123456789")
    rng.shuffle(digits)
    band_rows = [b * 3 + r for b in rng.sample(range(3), 3) for r in rng.sample(range(3), 3)]
    stack_cols = [s * 3 + c for s in rng.sample(range(3), 3) for c in rng.sample(range(3), 3)]
    board = [
        [digits[(r * 3 + r // 3 + c) % 9] for c in stack_cols]
        for r in band_rows
    ]
    keep = rng.randint(15, 45)
    cells = [(r, c) for r in range(9) for c in range(9)]
    kept = set(rng.sample(cells, keep))
    grid = [[board[r][c] if (r, c) in kept else "." for c in range(9)] for r in range(9)]
    if not wants_true(i):
        r, c = rng.choice(sorted(kept))
        empties = [
            (rr, cc)
            for rr in range(9)
            for cc in range(9)
            if grid[rr][cc] == "."
            and (rr == r or cc == c or (rr // 3 == r // 3 and cc // 3 == c // 3))
        ]
        if empties:
            rr, cc = rng.choice(empties)
            grid[rr][cc] = grid[r][c]
    return [grid]


def longest_consecutive(rng: random.Random, i: int) -> list[Any]:
    n = size(rng, i, 5000, low=0)
    nums: list[int] = []
    while len(nums) < n:
        run = rng.randint(1, max(1, n // 3))
        start = rng.randint(-10**9, 10**9 - run)
        nums.extend(range(start, start + run))
        if rng.random() < 0.3:
            nums.append(start)
    nums = nums[:n]
    rng.shuffle(nums)
    return [nums]


GENERATORS: dict[str, Generator] = {
    "contains-duplicate": contains_duplicate,
    "valid-anagram": valid_anagram,
    "two-sum": two_sum,
    "group-anagrams": group_anagrams,
    "top-k-frequent-elements": top_k_frequent,
    "product-of-array-except-self": product_except_self,
    "valid-sudoku": valid_sudoku,
    "longest-consecutive-sequence": longest_consecutive,
}
