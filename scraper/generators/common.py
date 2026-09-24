import random
import string
from collections import Counter
from typing import Any, Callable, Optional

from server.harness import TreeNode, tree_to_values

Generator = Callable[[random.Random, int], list[Any]]

TINY_TESTS = 8
MEDIUM_TESTS = 20


def size(rng: random.Random, i: int, cap: int, low: int = 1) -> int:
    if i < TINY_TESTS:
        return rng.randint(low, max(low, min(cap, 6)))
    if i < MEDIUM_TESTS:
        return rng.randint(low, max(low, min(cap, 60)))
    return rng.randint(max(low, cap // 2), cap)


def ints(rng: random.Random, n: int, lo: int, hi: int) -> list[int]:
    return [rng.randint(lo, hi) for _ in range(n)]


def distinct_ints(rng: random.Random, n: int, lo: int, hi: int) -> list[int]:
    return rng.sample(range(lo, hi + 1), n)


def lowercase(rng: random.Random, n: int, alphabet: str = string.ascii_lowercase) -> str:
    return "".join(rng.choice(alphabet) for _ in range(n))


def pair_count(values: list[int], target: int) -> int:
    counts = Counter(values)
    total = 0
    for x, c in counts.items():
        y = target - x
        if x < y:
            total += c * counts.get(y, 0)
        elif x == y:
            total += c * (c - 1) // 2
    return total


def random_tree(rng: random.Random, values: list[int]) -> Optional[TreeNode]:
    if not values:
        return None
    root = TreeNode(values[0])
    open_slots: list[tuple[TreeNode, str]] = [(root, "left"), (root, "right")]
    for value in values[1:]:
        index = rng.randrange(len(open_slots))
        open_slots[index], open_slots[-1] = open_slots[-1], open_slots[index]
        parent, side = open_slots.pop()
        child = TreeNode(value)
        setattr(parent, side, child)
        open_slots.append((child, "left"))
        open_slots.append((child, "right"))
    return root


def chain_tree(rng: random.Random, values: list[int]) -> Optional[TreeNode]:
    if not values:
        return None
    root = TreeNode(values[0])
    node = root
    for value in values[1:]:
        child = TreeNode(value)
        if rng.random() < 0.5:
            node.left = child
        else:
            node.right = child
        node = child
    return root


def bst_from(values: list[int]) -> Optional[TreeNode]:
    root: Optional[TreeNode] = None
    for value in values:
        if root is None:
            root = TreeNode(value)
            continue
        node = root
        while True:
            if value < node.val:
                if node.left is None:
                    node.left = TreeNode(value)
                    break
                node = node.left
            else:
                if node.right is None:
                    node.right = TreeNode(value)
                    break
                node = node.right
    return root


def balanced_tree(values: list[int]) -> Optional[TreeNode]:
    if not values:
        return None
    mid = len(values) // 2
    node = TreeNode(values[mid])
    node.left = balanced_tree(values[:mid])
    node.right = balanced_tree(values[mid + 1 :])
    return node


def all_nodes(root: Optional[TreeNode]) -> list[TreeNode]:
    nodes: list[TreeNode] = []
    stack = [root] if root else []
    while stack:
        node = stack.pop()
        nodes.append(node)
        if node.left:
            stack.append(node.left)
        if node.right:
            stack.append(node.right)
    return nodes


def tree(root: Optional[TreeNode]) -> list[Any]:
    return tree_to_values(root)


def wants_true(i: int) -> bool:
    return i % 2 == 0


def height(root: Optional[TreeNode]) -> int:
    if root is None:
        return 0
    return 1 + max(height(root.left), height(root.right))


def is_balanced(root: Optional[TreeNode]) -> bool:
    if root is None:
        return True
    return (
        abs(height(root.left) - height(root.right)) <= 1
        and is_balanced(root.left)
        and is_balanced(root.right)
    )


def is_subtree(root: Optional[TreeNode], sub: Optional[TreeNode]) -> bool:
    target = tree_to_values(sub)
    return any(tree_to_values(node) == target for node in all_nodes(root))


def valid_parens(s: str) -> bool:
    closers = {")": "(", "]": "[", "}": "{"}
    stack: list[str] = []
    for c in s:
        if c in closers:
            if not stack or stack.pop() != closers[c]:
                return False
        else:
            stack.append(c)
    return not stack
