import json
from collections import Counter
from pathlib import Path
from typing import Any, Callable

import pytest

from scraper.generators.common import pair_count
from server.harness import build_tree, tree_to_values
from server.runner import run_solution

ROOT = Path(__file__).resolve().parent.parent
PROBLEMS: dict[str, dict[str, Any]] = {
    p["slug"]: p for p in json.loads((ROOT / "data" / "problems.json").read_text(encoding="utf-8"))
}
INT_MIN, INT_MAX = -(2**31), 2**31 - 1


def cases(slug: str) -> list[tuple[list[Any], Any]]:
    problem = PROBLEMS[slug]
    return [
        ([json.loads(raw) for raw in test["input"]], json.loads(test["output"]))
        for test in problem["examples"] + problem["tests"]
    ]


def check_two_sum(args: list[Any], _: Any) -> None:
    assert pair_count(args[0], args[1]) == 1
    assert -(10**9) <= args[1] <= 10**9 and all(-(10**9) <= x <= 10**9 for x in args[0])


def check_subtree(args: list[Any], _: Any) -> None:
    root, sub = (sum(1 for v in tree if v is not None) for tree in args)
    assert 1 <= root <= 2000 and 1 <= sub <= 1000


def check_two_sum_sorted(args: list[Any], _: Any) -> None:
    numbers, target = args
    assert numbers == sorted(numbers) and all(-1000 <= x <= 1000 for x in numbers)
    assert pair_count(numbers, target) == 1


def check_top_k(args: list[Any], _: Any) -> None:
    nums, k = args
    freqs = sorted(Counter(nums).values(), reverse=True)
    assert 1 <= k <= len(freqs)
    assert k == len(freqs) or freqs[k - 1] > freqs[k]


def check_product(args: list[Any], output: Any) -> None:
    assert all(-30 <= x <= 30 for x in args[0])
    assert all(INT_MIN <= x <= INT_MAX for x in output)


def check_sudoku(args: list[Any], _: Any) -> None:
    board = args[0]
    assert len(board) == 9 and all(len(row) == 9 for row in board)
    assert all(cell in "123456789." and len(cell) == 1 for row in board for cell in row)


def check_find_duplicate(args: list[Any], _: Any) -> None:
    nums = args[0]
    n = len(nums) - 1
    assert all(1 <= x <= n for x in nums)
    repeated = [v for v, c in Counter(nums).items() if c > 1]
    assert len(repeated) == 1


def check_unique_sorted(args: list[Any], _: Any) -> None:
    assert args[0] == sorted(set(args[0]))


def check_matrix(args: list[Any], _: Any) -> None:
    flat = [x for row in args[0] for x in row]
    assert flat == sorted(flat) and len({len(row) for row in args[0]}) == 1


def check_koko(args: list[Any], _: Any) -> None:
    piles, h = args
    assert len(piles) <= h <= 10**9 and all(1 <= p <= 10**9 for p in piles)


def check_car_fleet(args: list[Any], _: Any) -> None:
    target, position, speed = args
    assert len(set(position)) == len(position) == len(speed)
    assert all(0 <= p < target for p in position) and all(s > 0 for s in speed)


def check_add_two_numbers(args: list[Any], _: Any) -> None:
    for digits in args:
        assert 1 <= len(digits) <= 100 and all(0 <= d <= 9 for d in digits)
        assert len(digits) == 1 or digits[-1] != 0


def check_remove_nth(args: list[Any], _: Any) -> None:
    assert 1 <= args[1] <= len(args[0])


def check_rpn(args: list[Any], output: Any) -> None:
    assert INT_MIN <= output <= INT_MAX


def check_kth(args: list[Any], _: Any) -> None:
    size = sum(1 for v in args[0] if v is not None)
    assert 1 <= args[1] <= size


def check_construct(args: list[Any], output: Any) -> None:
    preorder, inorder = args
    assert len(set(preorder)) == len(preorder) and sorted(preorder) == sorted(inorder)
    assert tree_to_values(build_tree(output)) == output


def check_rotated_unique(args: list[Any], _: Any) -> None:
    nums = args[0]
    assert len(set(nums)) == len(nums)
    drops = sum(1 for a, b in zip(nums, nums[1:]) if a > b)
    assert drops <= 1


def check_merge_sorted(args: list[Any], _: Any) -> None:
    assert all(lst == sorted(lst) for lst in args)


CHECKS: dict[str, Callable[[list[Any], Any], None]] = {
    "two-sum": check_two_sum,
    "two-sum-ii-input-array-is-sorted": check_two_sum_sorted,
    "top-k-frequent-elements": check_top_k,
    "product-of-array-except-self": check_product,
    "valid-sudoku": check_sudoku,
    "find-the-duplicate-number": check_find_duplicate,
    "binary-search": check_unique_sorted,
    "search-a-2d-matrix": check_matrix,
    "koko-eating-bananas": check_koko,
    "car-fleet": check_car_fleet,
    "add-two-numbers": check_add_two_numbers,
    "remove-nth-node-from-end-of-list": check_remove_nth,
    "evaluate-reverse-polish-notation": check_rpn,
    "kth-smallest-element-in-a-bst": check_kth,
    "construct-binary-tree-from-preorder-and-inorder-traversal": check_construct,
    "find-minimum-in-rotated-sorted-array": check_rotated_unique,
    "search-in-rotated-sorted-array": check_rotated_unique,
    "merge-two-sorted-lists": check_merge_sorted,
    "subtree-of-another-tree": check_subtree,
}

BOOLEAN_PROBLEMS = [slug for slug, p in PROBLEMS.items() if p["returnType"] == "boolean"]


@pytest.mark.parametrize("slug", sorted(CHECKS))
def test_inputs_respect_constraints(slug: str) -> None:
    for args, output in cases(slug):
        CHECKS[slug](args, output)


@pytest.mark.parametrize("slug", BOOLEAN_PROBLEMS)
def test_constant_answer_cannot_pass_most_tests(slug: str) -> None:
    outputs = Counter(output for _, output in cases(slug))
    assert max(outputs.values()) / sum(outputs.values()) <= 0.6, outputs


def test_every_problem_has_starter_code_and_enough_tests() -> None:
    assert len(PROBLEMS) == 44
    for slug, problem in PROBLEMS.items():
        assert "class Solution" in problem["starterCode"], slug
        assert len(problem["examples"]) + len(problem["tests"]) >= (8 if slug == "generate-parentheses" else 20), slug


@pytest.mark.parametrize("slug", sorted(PROBLEMS))
def test_reference_passes_within_player_time_limit(slug: str) -> None:
    problem = PROBLEMS[slug]
    code = (ROOT / "scraper" / "solutions" / f"{slug}.py").read_text(encoding="utf-8")
    assert problem["timeLimit"] <= 10
    report = run_solution(code, problem, problem["examples"] + problem["tests"])
    assert not report.timed_out
    assert report.passed == report.total
