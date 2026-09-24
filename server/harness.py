import contextlib
import io
import json
import sys
import threading
import traceback
from collections import deque
from collections.abc import Iterable
from typing import Any, Optional

MAX_LIST_NODES = 200_000
MAX_STDOUT_CHARS = 2_000
MAX_ERROR_CHARS = 2_000
WORKER_STACK_BYTES = 128 * 1024 * 1024
RECURSION_LIMIT = 100_000
USER_ERRORS = (Exception, SystemExit, KeyboardInterrupt)

PRELUDE = """
from typing import *
import collections, heapq, math, bisect, itertools, functools, string, re
from collections import *
"""


class ListNode:
    def __init__(self, val: int = 0, next: Optional["ListNode"] = None) -> None:
        self.val = val
        self.next = next


class TreeNode:
    def __init__(
        self,
        val: int = 0,
        left: Optional["TreeNode"] = None,
        right: Optional["TreeNode"] = None,
    ) -> None:
        self.val = val
        self.left = left
        self.right = right


def build_list(values: list[Any]) -> Optional[ListNode]:
    dummy = ListNode()
    tail = dummy
    for value in values:
        tail.next = ListNode(value)
        tail = tail.next
    return dummy.next


def list_to_values(head: Optional[ListNode]) -> list[Any]:
    values: list[Any] = []
    while head is not None:
        if len(values) >= MAX_LIST_NODES:
            raise ValueError("returned linked list has a cycle or is too long")
        values.append(head.val)
        head = head.next
    return values


def build_tree(values: list[Any]) -> Optional[TreeNode]:
    if not values or values[0] is None:
        return None
    root = TreeNode(values[0])
    queue: deque[TreeNode] = deque([root])
    i = 1
    while queue and i < len(values):
        node = queue.popleft()
        if i < len(values) and values[i] is not None:
            node.left = TreeNode(values[i])
            queue.append(node.left)
        i += 1
        if i < len(values) and values[i] is not None:
            node.right = TreeNode(values[i])
            queue.append(node.right)
        i += 1
    return root


def tree_to_values(root: Optional[TreeNode]) -> list[Any]:
    if root is None:
        return []
    values: list[Any] = []
    queue: deque[Optional[TreeNode]] = deque([root])
    seen: set[int] = set()
    while queue:
        node = queue.popleft()
        if node is None:
            values.append(None)
            continue
        if id(node) in seen:
            raise ValueError("returned tree has a cycle")
        seen.add(id(node))
        values.append(node.val)
        queue.append(node.left)
        queue.append(node.right)
    while values and values[-1] is None:
        values.pop()
    return values


def deserialize(type_name: str, raw: str) -> Any:
    value = json.loads(raw)
    if type_name == "ListNode":
        return build_list(value)
    if type_name == "TreeNode":
        return build_tree(value)
    return value


def to_plain(type_name: str, value: Any) -> Any:
    if type_name == "ListNode":
        if value is not None and not isinstance(value, ListNode):
            raise TypeError(f"expected ListNode, got {type(value).__name__}")
        return list_to_values(value)
    if type_name == "TreeNode":
        if value is not None and not isinstance(value, TreeNode):
            raise TypeError(f"expected TreeNode, got {type(value).__name__}")
        return tree_to_values(value)
    if type_name == "integer" and isinstance(value, float) and value.is_integer():
        return int(value)
    return _plain_containers(value)


def _plain_containers(value: Any) -> Any:
    if isinstance(value, (str, bytes, dict)) or not isinstance(value, Iterable):
        return value
    return [_plain_containers(v) for v in value]


def dumps(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"))


def normalize(value: Any, mode: str) -> Any:
    if mode == "unordered" and isinstance(value, list):
        return sorted(value, key=dumps)
    if mode == "unordered_nested" and isinstance(value, list):
        inner = [sorted(v, key=dumps) if isinstance(v, list) else v for v in value]
        return sorted(inner, key=dumps)
    return value


def outputs_match(expected_raw: str, actual_raw: str, mode: str) -> bool:
    expected = normalize(json.loads(expected_raw), mode)
    actual = normalize(json.loads(actual_raw), mode)
    return dumps(expected) == dumps(actual)


def _format_user_error(error: BaseException) -> str:
    frames = [
        frame
        for frame in traceback.extract_tb(error.__traceback__)
        if frame.filename == "solution.py"
    ]
    lines = [f"line {frame.lineno}: {frame.line}" for frame in frames[-3:]]
    lines.append(f"{type(error).__name__}: {error}")
    return "\n".join(lines)[-MAX_ERROR_CHARS:]


def load_solution_class(source: str) -> Any:
    namespace: dict[str, Any] = {"ListNode": ListNode, "TreeNode": TreeNode}
    exec(PRELUDE, namespace)
    exec(compile(source, "solution.py", "exec"), namespace)
    solution = namespace.get("Solution")
    if solution is None:
        raise NameError("no class named Solution was defined")
    return solution


def run_one(solution_class: Any, spec: dict[str, Any], test: dict[str, Any]) -> dict[str, Any]:
    params: list[dict[str, str]] = spec["params"]
    return_type: str = spec["returnType"]
    captured = io.StringIO()
    result: dict[str, Any] = {"actual": None, "error": None, "stdout": ""}
    try:
        args = [deserialize(p["type"], raw) for p, raw in zip(params, test["input"])]
        with contextlib.redirect_stdout(captured):
            returned = getattr(solution_class(), spec["method"])(*args)
        if return_type == "void":
            actual = to_plain(params[0]["type"], args[0])
        else:
            actual = to_plain(return_type, returned)
        result["actual"] = dumps(actual)
    except USER_ERRORS as error:
        result["error"] = _format_user_error(error)
    result["stdout"] = captured.getvalue()[:MAX_STDOUT_CHARS]
    return result


def run_all(spec: dict[str, Any], source: str, results_path: str) -> None:
    with open(results_path, "w", encoding="utf-8") as out:
        try:
            solution_class = load_solution_class(source)
        except USER_ERRORS as error:
            out.write(dumps({"compileError": _format_user_error(error)}) + "\n")
            return
        for index, test in enumerate(spec["tests"]):
            result = run_one(solution_class, spec, test)
            result["index"] = index
            out.write(dumps(result) + "\n")
            out.flush()


def main(spec_path: str, solution_path: str, results_path: str) -> int:
    with open(spec_path, encoding="utf-8") as f:
        spec: dict[str, Any] = json.load(f)
    with open(solution_path, encoding="utf-8") as f:
        source = f.read()
    sys.setrecursionlimit(RECURSION_LIMIT)
    threading.stack_size(WORKER_STACK_BYTES)
    worker = threading.Thread(target=run_all, args=(spec, source, results_path))
    worker.start()
    worker.join()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2], sys.argv[3]))
