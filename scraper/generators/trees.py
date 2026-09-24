import copy
import random
from typing import Any, Optional

from server.harness import TreeNode

from .common import (
    Generator,
    all_nodes,
    balanced_tree,
    bst_from,
    chain_tree,
    distinct_ints,
    ints,
    is_balanced,
    is_subtree,
    random_tree,
    size,
    tree,
    wants_true,
)


def shaped_tree(rng: random.Random, values: list[int]) -> Optional[TreeNode]:
    if rng.random() < 0.15:
        return chain_tree(rng, values)
    return random_tree(rng, values)


def invert_tree(rng: random.Random, i: int) -> list[Any]:
    return [tree(shaped_tree(rng, ints(rng, size(rng, i, 100, low=0), -100, 100)))]


def max_depth(rng: random.Random, i: int) -> list[Any]:
    return [tree(shaped_tree(rng, ints(rng, size(rng, i, 2000, low=0), -100, 100)))]


def diameter(rng: random.Random, i: int) -> list[Any]:
    return [tree(shaped_tree(rng, ints(rng, size(rng, i, 2000), -100, 100)))]


def balanced(rng: random.Random, i: int) -> list[Any]:
    if wants_true(i):
        values = ints(rng, size(rng, i, 2000, low=0), -10**4, 10**4)
        return [tree(balanced_tree(values))]
    while True:
        values = ints(rng, size(rng, i, 2000, low=3), -10**4, 10**4)
        if rng.random() < 0.5:
            root = balanced_tree(values)
            assert root is not None
            leaf = rng.choice([n for n in all_nodes(root) if n.left is None and n.right is None])
            leaf.left = TreeNode(0, TreeNode(1))
        else:
            root = shaped_tree(rng, values)
        if not is_balanced(root):
            return [tree(root)]


def same_tree(rng: random.Random, i: int) -> list[Any]:
    p = shaped_tree(rng, ints(rng, size(rng, i, 100, low=0), -10, 10))
    roll = rng.random()
    if roll < 0.5:
        q = copy.deepcopy(p)
    elif roll < 0.75 and p is not None:
        q = copy.deepcopy(p)
        rng.choice(all_nodes(q)).val += rng.choice([-1, 1])
    else:
        q = shaped_tree(rng, ints(rng, size(rng, i, 100, low=0), -10, 10))
    return [tree(p), tree(q)]


def subtree(rng: random.Random, i: int) -> list[Any]:
    root = shaped_tree(rng, ints(rng, size(rng, i, 1000), 0, 4))
    assert root is not None
    if wants_true(i):
        return [tree(root), tree(copy.deepcopy(rng.choice(all_nodes(root))))]
    while True:
        if rng.random() < 0.6:
            sub = copy.deepcopy(rng.choice(all_nodes(root)))
            rng.choice(all_nodes(sub)).val += 1
        else:
            sub = shaped_tree(rng, ints(rng, size(rng, i, 10), 0, 4))
        if not is_subtree(root, sub):
            return [tree(root), tree(sub)]


def level_order(rng: random.Random, i: int) -> list[Any]:
    return [tree(shaped_tree(rng, ints(rng, size(rng, i, 2000, low=0), -1000, 1000)))]


def right_side_view(rng: random.Random, i: int) -> list[Any]:
    return [tree(shaped_tree(rng, ints(rng, size(rng, i, 100, low=0), -100, 100)))]


def good_nodes(rng: random.Random, i: int) -> list[Any]:
    span = rng.choice([5, 10**4])
    return [tree(shaped_tree(rng, ints(rng, size(rng, i, 3000), -span, span)))]


def validate_bst(rng: random.Random, i: int) -> list[Any]:
    n = size(rng, i, 3000)
    values = distinct_ints(rng, n, -(2**31), 2**31 - 1) if rng.random() < 0.5 else distinct_ints(rng, n, -n * 2, n * 2)
    roll = rng.random()
    if roll < 0.45:
        return [tree(bst_from(values))]
    if roll < 0.8:
        root = bst_from(values)
        assert root is not None
        node = rng.choice(all_nodes(root))
        node.val = rng.choice(values)
        return [tree(root)]
    return [tree(random_tree(rng, values))]


def kth_smallest(rng: random.Random, i: int) -> list[Any]:
    n = size(rng, i, 3000)
    values = distinct_ints(rng, n, 0, 10**4)
    return [tree(bst_from(values)), rng.randint(1, n)]


def preorder(root: Optional[TreeNode], out: list[int]) -> list[int]:
    stack = [root] if root else []
    while stack:
        node = stack.pop()
        out.append(node.val)
        if node.right:
            stack.append(node.right)
        if node.left:
            stack.append(node.left)
    return out


def inorder(root: Optional[TreeNode], out: list[int]) -> list[int]:
    stack: list[TreeNode] = []
    node = root
    while stack or node:
        while node:
            stack.append(node)
            node = node.left
        node = stack.pop()
        out.append(node.val)
        node = node.right
    return out


def construct_from_traversals(rng: random.Random, i: int) -> list[Any]:
    root = shaped_tree(rng, distinct_ints(rng, size(rng, i, 3000), -3000, 3000))
    return [preorder(root, []), inorder(root, [])]


GENERATORS: dict[str, Generator] = {
    "invert-binary-tree": invert_tree,
    "maximum-depth-of-binary-tree": max_depth,
    "diameter-of-binary-tree": diameter,
    "balanced-binary-tree": balanced,
    "same-tree": same_tree,
    "subtree-of-another-tree": subtree,
    "binary-tree-level-order-traversal": level_order,
    "binary-tree-right-side-view": right_side_view,
    "count-good-nodes-in-binary-tree": good_nodes,
    "validate-binary-search-tree": validate_bst,
    "kth-smallest-element-in-a-bst": kth_smallest,
    "construct-binary-tree-from-preorder-and-inorder-traversal": construct_from_traversals,
}
