import random
import string
from typing import Any, Callable

from .common import (
    balanced_tree,
    bst_from,
    distinct_ints,
    ints,
    lowercase,
    pair_count,
    random_tree,
    tree,
)
from .stack import evaluate_rpn, valid_parens_string
from server.harness import TreeNode

StressGenerator = Callable[[random.Random], list[Any]]


def right_chain(values: list[int]) -> TreeNode | None:
    root: TreeNode | None = None
    for value in reversed(values):
        node = TreeNode(value)
        node.right = root
        root = node
    return root


def contains_duplicate_distinct(rng: random.Random) -> list[Any]:
    return [distinct_ints(rng, 100_000, -10**9, 10**9)]


def contains_duplicate_at_end(rng: random.Random) -> list[Any]:
    nums = distinct_ints(rng, 100_000, -10**9, 10**9)
    nums[-1] = nums[-2]
    return [nums]


def valid_anagram_large(rng: random.Random) -> list[Any]:
    s = lowercase(rng, 50_000)
    t = list(s)
    rng.shuffle(t)
    return [s, "".join(t)]


def two_sum_answer_at_end(rng: random.Random) -> list[Any]:
    while True:
        nums = distinct_ints(rng, 50_000, -5 * 10**8, 5 * 10**8)
        target = nums[-1] + nums[-2]
        if pair_count(nums, target) == 1:
            return [nums, target]


def group_anagrams_large(rng: random.Random) -> list[Any]:
    bases = [lowercase(rng, rng.randint(1, 100)) for _ in range(2_000)]
    strs: list[str] = []
    for _ in range(10_000):
        letters = list(rng.choice(bases))
        rng.shuffle(letters)
        strs.append("".join(letters))
    return [strs]


def top_k_large(rng: random.Random) -> list[Any]:
    values = distinct_ints(rng, 440, -10**4, 10**4)
    nums = [v for f, v in enumerate(values, start=1) for _ in range(f)]
    rng.shuffle(nums)
    return [nums, rng.randint(1, 440)]


def product_except_self_large(rng: random.Random) -> list[Any]:
    nums = [rng.choice([1, -1]) for _ in range(100_000)]
    for index in rng.sample(range(100_000), 20):
        nums[index] = rng.choice([2, -2])
    return [nums]


def longest_consecutive_one_run(rng: random.Random) -> list[Any]:
    start = rng.randint(-10**9, 10**9 - 100_000)
    nums = list(range(start, start + 100_000))
    rng.shuffle(nums)
    return [nums]


def valid_palindrome_large(rng: random.Random) -> list[Any]:
    half = "".join(rng.choice(string.ascii_letters + string.digits + " ,.") for _ in range(100_000))
    return [half + half[::-1]]


def two_sum_sorted_answer_at_end(rng: random.Random) -> list[Any]:
    rest = sorted(ints(rng, 29_998, -998, 998))
    high = rest[-1]
    return [rest + [high + 1, high + 2], 2 * high + 3]


def three_sum_large(rng: random.Random) -> list[Any]:
    return [ints(rng, 1_500, -10**5, 10**5)]


def container_large(rng: random.Random) -> list[Any]:
    return [ints(rng, 100_000, 0, 10**4)]


def best_time_large(rng: random.Random) -> list[Any]:
    return [ints(rng, 100_000, 0, 10**4)]


def longest_substring_large(rng: random.Random) -> list[Any]:
    return [lowercase(rng, 50_000, string.ascii_letters + string.digits + " !?.,;:")]


def character_replacement_large(rng: random.Random) -> list[Any]:
    return [lowercase(rng, 100_000, "ABCDE"), rng.randint(1_000, 20_000)]


def permutation_absent(rng: random.Random) -> list[Any]:
    s1 = lowercase(rng, 5_000)
    s2 = lowercase(rng, 10_000, "abcdefghijklmnopqrstuvwxy")
    return [s1 + "z", s2]


def valid_parentheses_large(rng: random.Random) -> list[Any]:
    return [valid_parens_string(rng, 5_000)]


def evaluate_rpn_large(rng: random.Random) -> list[Any]:
    return evaluate_rpn(rng, 25)


def daily_temperatures_falling(rng: random.Random) -> list[Any]:
    temps = sorted(ints(rng, 99_999, 30, 99), reverse=True)
    return [temps + [100]]


def car_fleet_large(rng: random.Random) -> list[Any]:
    target = 10**6
    return [target, distinct_ints(rng, 100_000, 0, target - 1), ints(rng, 100_000, 1, 10**6)]


def binary_search_large(rng: random.Random) -> list[Any]:
    nums = sorted(distinct_ints(rng, 10_000, -9999, 9999))
    return [nums, nums[-1]]


def search_2d_large(rng: random.Random) -> list[Any]:
    flat = sorted(distinct_ints(rng, 10_000, -10**4, 10**4))
    return [[flat[r * 100 : (r + 1) * 100] for r in range(100)], flat[-1]]


def koko_tight(rng: random.Random) -> list[Any]:
    piles = ints(rng, 10_000, 10**8, 10**9)
    return [piles, len(piles)]


def koko_loose(rng: random.Random) -> list[Any]:
    piles = ints(rng, 10_000, 10**8, 10**9)
    return [piles, len(piles) + 7]


def find_min_rotated_large(rng: random.Random) -> list[Any]:
    nums = sorted(distinct_ints(rng, 5_000, -5000, 5000))
    k = rng.randint(1, 4_999)
    return [nums[k:] + nums[:k]]


def search_rotated_large(rng: random.Random) -> list[Any]:
    nums = sorted(distinct_ints(rng, 5_000, -10**4, 10**4))
    k = rng.randint(1, 4_999)
    rotated = nums[k:] + nums[:k]
    return [rotated, rotated[k - 1] if k else rotated[0]]


def reverse_list_large(rng: random.Random) -> list[Any]:
    return [ints(rng, 5_000, -5000, 5000)]


def reorder_list_large(rng: random.Random) -> list[Any]:
    return [ints(rng, 50_000, 1, 1000)]


def find_duplicate_large(rng: random.Random) -> list[Any]:
    n = 100_000
    nums = rng.sample(range(1, n + 1), n)
    nums.append(nums[-1])
    return [nums]


def max_depth_chain(rng: random.Random) -> list[Any]:
    return [tree(right_chain(ints(rng, 10_000, -100, 100)))]


def diameter_chain(rng: random.Random) -> list[Any]:
    return [tree(right_chain(ints(rng, 10_000, -100, 100)))]


def balanced_large(rng: random.Random) -> list[Any]:
    return [tree(balanced_tree(ints(rng, 5_000, -10**4, 10**4)))]


def good_nodes_large(rng: random.Random) -> list[Any]:
    return [tree(random_tree(rng, ints(rng, 100_000, -10**4, 10**4)))]


def validate_bst_skewed(rng: random.Random) -> list[Any]:
    return [tree(right_chain(sorted(distinct_ints(rng, 10_000, -(2**31), 2**31 - 1))))]


def kth_smallest_large(rng: random.Random) -> list[Any]:
    values = distinct_ints(rng, 10_000, 0, 10**4)
    return [tree(bst_from(values)), 10_000]


STRESS: dict[str, list[StressGenerator]] = {
    "contains-duplicate": [contains_duplicate_distinct, contains_duplicate_at_end],
    "valid-anagram": [valid_anagram_large],
    "two-sum": [two_sum_answer_at_end],
    "group-anagrams": [group_anagrams_large],
    "top-k-frequent-elements": [top_k_large],
    "product-of-array-except-self": [product_except_self_large],
    "longest-consecutive-sequence": [longest_consecutive_one_run],
    "valid-palindrome": [valid_palindrome_large],
    "two-sum-ii-input-array-is-sorted": [two_sum_sorted_answer_at_end],
    "3sum": [three_sum_large],
    "container-with-most-water": [container_large],
    "best-time-to-buy-and-sell-stock": [best_time_large],
    "longest-substring-without-repeating-characters": [longest_substring_large],
    "longest-repeating-character-replacement": [character_replacement_large],
    "permutation-in-string": [permutation_absent],
    "valid-parentheses": [valid_parentheses_large],
    "evaluate-reverse-polish-notation": [evaluate_rpn_large],
    "daily-temperatures": [daily_temperatures_falling],
    "car-fleet": [car_fleet_large],
    "binary-search": [binary_search_large],
    "search-a-2d-matrix": [search_2d_large],
    "koko-eating-bananas": [koko_tight, koko_loose],
    "find-minimum-in-rotated-sorted-array": [find_min_rotated_large],
    "search-in-rotated-sorted-array": [search_rotated_large],
    "reverse-linked-list": [reverse_list_large],
    "reorder-list": [reorder_list_large],
    "find-the-duplicate-number": [find_duplicate_large],
    "maximum-depth-of-binary-tree": [max_depth_chain],
    "diameter-of-binary-tree": [diameter_chain],
    "balanced-binary-tree": [balanced_large],
    "count-good-nodes-in-binary-tree": [good_nodes_large],
    "validate-binary-search-tree": [validate_bst_skewed],
    "kth-smallest-element-in-a-bst": [kth_smallest_large],
}
