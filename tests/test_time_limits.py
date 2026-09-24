import json
from pathlib import Path
from typing import Any

import pytest

from server.runner import run_solution

ROOT = Path(__file__).resolve().parent.parent
PROBLEMS: dict[str, dict[str, Any]] = {
    p["slug"]: p for p in json.loads((ROOT / "data" / "problems.json").read_text(encoding="utf-8"))
}

BRUTE_FORCE: dict[str, str] = {
    "contains-duplicate": """
class Solution:
    def containsDuplicate(self, nums):
        for i in range(len(nums)):
            for j in range(i + 1, len(nums)):
                if nums[i] == nums[j]:
                    return True
        return False
""",
    "two-sum": """
class Solution:
    def twoSum(self, nums, target):
        for i in range(len(nums)):
            for j in range(i + 1, len(nums)):
                if nums[i] + nums[j] == target:
                    return [i, j]
""",
    "product-of-array-except-self": """
class Solution:
    def productExceptSelf(self, nums):
        out = []
        for i in range(len(nums)):
            p = 1
            for j in range(len(nums)):
                if i != j:
                    p *= nums[j]
            out.append(p)
        return out
""",
    "longest-consecutive-sequence": """
class Solution:
    def longestConsecutive(self, nums):
        seen = set(nums)
        best = 0
        for n in nums:
            length = 1
            while n + length in seen:
                length += 1
            best = max(best, length)
        return best
""",
    "two-sum-ii-input-array-is-sorted": """
class Solution:
    def twoSum(self, numbers, target):
        for i in range(len(numbers)):
            for j in range(i + 1, len(numbers)):
                if numbers[i] + numbers[j] == target:
                    return [i + 1, j + 1]
""",
    "container-with-most-water": """
class Solution:
    def maxArea(self, height):
        best = 0
        for i in range(len(height)):
            for j in range(i + 1, len(height)):
                best = max(best, (j - i) * min(height[i], height[j]))
        return best
""",
    "best-time-to-buy-and-sell-stock": """
class Solution:
    def maxProfit(self, prices):
        best = 0
        for i in range(len(prices)):
            for j in range(i + 1, len(prices)):
                best = max(best, prices[j] - prices[i])
        return best
""",
    "daily-temperatures": """
class Solution:
    def dailyTemperatures(self, temperatures):
        out = [0] * len(temperatures)
        for i in range(len(temperatures)):
            for j in range(i + 1, len(temperatures)):
                if temperatures[j] > temperatures[i]:
                    out[i] = j - i
                    break
        return out
""",
    "koko-eating-bananas": """
class Solution:
    def minEatingSpeed(self, piles, h):
        k = 1
        while sum((p + k - 1) // k for p in piles) > h:
            k += 1
        return k
""",
    "find-the-duplicate-number": """
class Solution:
    def findDuplicate(self, nums):
        for i in range(len(nums)):
            for j in range(i + 1, len(nums)):
                if nums[i] == nums[j]:
                    return nums[i]
""",
    "3sum": """
class Solution:
    def threeSum(self, nums):
        found = set()
        n = len(nums)
        for i in range(n):
            for j in range(i + 1, n):
                for k in range(j + 1, n):
                    if nums[i] + nums[j] + nums[k] == 0:
                        found.add(tuple(sorted((nums[i], nums[j], nums[k]))))
        return [list(t) for t in found]
""",
    "diameter-of-binary-tree": """
class Solution:
    def diameterOfBinaryTree(self, root):
        def height(node):
            return 0 if not node else 1 + max(height(node.left), height(node.right))
        if not root:
            return 0
        through = height(root.left) + height(root.right)
        return max(through, self.diameterOfBinaryTree(root.left), self.diameterOfBinaryTree(root.right))
""",
}

ACCEPTABLE: dict[str, str] = {
    "contains-duplicate": """
class Solution:
    def containsDuplicate(self, nums):
        nums = sorted(nums)
        return any(a == b for a, b in zip(nums, nums[1:]))
""",
    "longest-consecutive-sequence": """
class Solution:
    def longestConsecutive(self, nums):
        nums = sorted(set(nums))
        best = run = 0
        for i, n in enumerate(nums):
            run = run + 1 if i and nums[i - 1] == n - 1 else 1
            best = max(best, run)
        return best
""",
    "top-k-frequent-elements": """
class Solution:
    def topKFrequent(self, nums, k):
        return [n for n, _ in Counter(nums).most_common(k)]
""",
    "two-sum": """
class Solution:
    def twoSum(self, nums, target):
        order = sorted(range(len(nums)), key=lambda i: nums[i])
        lo, hi = 0, len(nums) - 1
        while lo < hi:
            s = nums[order[lo]] + nums[order[hi]]
            if s == target:
                return [order[lo], order[hi]]
            if s < target:
                lo += 1
            else:
                hi -= 1
""",
    "maximum-depth-of-binary-tree": """
class Solution:
    def maxDepth(self, root):
        if not root:
            return 0
        return 1 + max(self.maxDepth(root.left), self.maxDepth(root.right))
""",
}


@pytest.mark.parametrize("slug", sorted(BRUTE_FORCE))
def test_brute_force_cannot_fully_pass(slug: str) -> None:
    problem = PROBLEMS[slug]
    tests = problem["examples"] + problem["tests"]
    report = run_solution(BRUTE_FORCE[slug], problem, tests)
    assert report.timed_out, f"{slug}: brute force finished all {report.total} tests in time"
    assert report.passed < report.total
    assert report.passed >= len(problem["examples"])


@pytest.mark.parametrize("slug", sorted(ACCEPTABLE))
def test_reasonable_alternatives_still_pass(slug: str) -> None:
    problem = PROBLEMS[slug]
    tests = problem["examples"] + problem["tests"]
    report = run_solution(ACCEPTABLE[slug], problem, tests)
    assert not report.timed_out
    assert report.passed == report.total, [o.error for o in report.outcomes if not o.passed][:2]
