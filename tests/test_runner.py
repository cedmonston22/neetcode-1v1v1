from typing import Any

from server.runner import run_solution

TWO_SUM: dict[str, Any] = {
    "method": "twoSum",
    "params": [{"name": "nums", "type": "integer[]"}, {"name": "target", "type": "integer"}],
    "returnType": "integer[]",
    "compare": "unordered",
}

TWO_SUM_TESTS: list[dict[str, Any]] = [
    {"input": ["[2,7,11,15]", "9"], "output": "[0,1]"},
    {"input": ["[3,2,4]", "6"], "output": "[1,2]"},
    {"input": ["[3,3]", "6"], "output": "[0,1]"},
]

REORDER: dict[str, Any] = {
    "method": "reorderList",
    "params": [{"name": "head", "type": "ListNode"}],
    "returnType": "void",
    "compare": "exact",
}

GOOD_TWO_SUM = """
class Solution:
    def twoSum(self, nums: List[int], target: int) -> List[int]:
        seen = {}
        for i, n in enumerate(nums):
            if target - n in seen:
                return [i, seen[target - n]]
            seen[n] = i
"""


def test_passing_solution() -> None:
    report = run_solution(GOOD_TWO_SUM, TWO_SUM, TWO_SUM_TESTS)
    assert report.passed == 3
    assert report.total == 3
    assert report.compile_error is None
    assert not report.timed_out


def test_wrong_answer() -> None:
    code = GOOD_TWO_SUM.replace("return [i, seen[target - n]]", "return [0, 0]")
    report = run_solution(code, TWO_SUM, TWO_SUM_TESTS)
    assert report.passed == 0
    assert report.outcomes[0].actual == "[0,0]"


def test_runtime_error_is_reported_per_test() -> None:
    code = """
class Solution:
    def twoSum(self, nums, target):
        if target == 6:
            raise ValueError("boom")
        return [0, 1]
"""
    report = run_solution(code, TWO_SUM, TWO_SUM_TESTS)
    assert report.passed == 1
    error = report.outcomes[1].error
    assert error is not None and "ValueError: boom" in error and "line 5" in error


def test_syntax_error() -> None:
    report = run_solution("class Solution:\n    def twoSum(self\n", TWO_SUM, TWO_SUM_TESTS)
    assert report.compile_error is not None
    assert "SyntaxError" in report.compile_error
    assert report.passed == 0


def test_missing_solution_class() -> None:
    report = run_solution("x = 1\n", TWO_SUM, TWO_SUM_TESTS)
    assert report.compile_error is not None and "Solution" in report.compile_error


def test_infinite_loop_times_out_but_keeps_earlier_results() -> None:
    code = """
class Solution:
    def twoSum(self, nums, target):
        if target == 6:
            while True:
                pass
        return [0, 1]
"""
    report = run_solution(code, TWO_SUM, TWO_SUM_TESTS, time_limit=2)
    assert report.timed_out
    assert report.passed == 1
    assert report.total == 3


def test_stdout_is_captured_not_mixed_into_results() -> None:
    code = GOOD_TWO_SUM.replace("seen = {}", "seen = {}\n        print('debug', nums)")
    report = run_solution(code, TWO_SUM, TWO_SUM_TESTS[:1])
    assert report.passed == 1
    assert report.outcomes[0].stdout.startswith("debug [2, 7, 11, 15]")


def test_void_problem_checks_mutated_argument() -> None:
    code = """
class Solution:
    def reorderList(self, head: Optional[ListNode]) -> None:
        nodes = []
        while head:
            nodes.append(head)
            head = head.next
        i, j = 0, len(nodes) - 1
        order = []
        while i <= j:
            order.append(nodes[i])
            if i != j:
                order.append(nodes[j])
            i += 1
            j -= 1
        for a, b in zip(order, order[1:]):
            a.next = b
        order[-1].next = None
"""
    tests = [{"input": ["[1,2,3,4]"], "output": "[1,4,2,3]"}, {"input": ["[1,2,3,4,5]"], "output": "[1,5,2,4,3]"}]
    report = run_solution(code, REORDER, tests)
    assert report.passed == 2


def test_generation_mode_returns_actual_without_grading() -> None:
    tests = [{"input": ["[1,2,3]", "5"], "output": None}]
    report = run_solution(GOOD_TWO_SUM, TWO_SUM, tests)
    assert report.outcomes[0].actual == "[2,1]"


GROUP_ANAGRAMS: dict[str, Any] = {
    "method": "groupAnagrams",
    "params": [{"name": "strs", "type": "string[]"}],
    "returnType": "list<list<string>>",
    "compare": "unordered_nested",
}

MAX_DEPTH: dict[str, Any] = {
    "method": "maxDepth",
    "params": [{"name": "root", "type": "TreeNode"}],
    "returnType": "integer",
    "compare": "exact",
}


def test_patching_the_grader_cannot_fake_a_pass() -> None:
    code = """
import __main__
__main__.outputs_match = lambda *a: True
class Solution:
    def twoSum(self, nums, target):
        return [42]
"""
    assert run_solution(code, TWO_SUM, TWO_SUM_TESTS).passed == 0


def test_expected_outputs_are_not_readable_by_user_code() -> None:
    code = """
import json
class Solution:
    def twoSum(self, nums, target):
        spec = json.load(open("spec.json"))
        test = next(t for t in spec["tests"] if json.loads(t["input"][0]) == nums)
        return json.loads(test.get("output") or "[42]")
"""
    assert run_solution(code, TWO_SUM, TWO_SUM_TESTS).passed == 0


def test_dict_values_and_sets_are_accepted_as_lists() -> None:
    code = """
class Solution:
    def groupAnagrams(self, strs):
        groups = defaultdict(list)
        for s in strs:
            groups[tuple(sorted(s))].append(s)
        return groups.values()
"""
    tests = [{"input": ['["eat","tea","tan","ate","nat","bat"]'], "output": '[["bat"],["nat","tan"],["ate","eat","tea"]]'}]
    assert run_solution(code, GROUP_ANAGRAMS, tests).passed == 1


def test_deep_recursion_through_lru_cache_does_not_overflow() -> None:
    code = """
class Solution:
    def maxDepth(self, root):
        @functools.lru_cache(None)
        def depth(node):
            return 0 if node is None else 1 + max(depth(node.left), depth(node.right))
        return depth(root)
"""
    chain = "[" + ",".join(["1"] + ["null", "1"] * 2999) + "]"
    report = run_solution(code, MAX_DEPTH, [{"input": [chain], "output": "3000"}])
    assert report.crash is None
    assert report.passed == 1, report.outcomes[0].error


def test_sys_exit_is_reported_as_an_error() -> None:
    code = """
import sys
class Solution:
    def twoSum(self, nums, target):
        sys.exit(0)
"""
    report = run_solution(code, TWO_SUM, TWO_SUM_TESTS)
    assert report.passed == 0
    assert len(report.outcomes) == 3
    error = report.outcomes[0].error
    assert error is not None and "SystemExit" in error


def test_input_does_not_hang() -> None:
    code = """
class Solution:
    def twoSum(self, nums, target):
        input()
        return [0, 1]
"""
    report = run_solution(code, TWO_SUM, TWO_SUM_TESTS, time_limit=3)
    assert not report.timed_out
    error = report.outcomes[0].error
    assert error is not None and "EOFError" in error
