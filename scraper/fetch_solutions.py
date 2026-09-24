import json
import sys
from pathlib import Path
from typing import Any

import requests

TREE_URL = "https://api.github.com/repos/neetcode-gh/leetcode/git/trees/main?recursive=1"
RAW_URL = "https://raw.githubusercontent.com/neetcode-gh/leetcode/main/{path}"
ROOT = Path(__file__).resolve().parent.parent
RAW_PROBLEMS_PATH = ROOT / "data" / "raw_problems.json"
SOLUTIONS_DIR = Path(__file__).resolve().parent / "solutions"


def python_paths_by_id(session: requests.Session) -> dict[int, str]:
    response = session.get(TREE_URL, timeout=30)
    response.raise_for_status()
    tree: list[dict[str, Any]] = response.json()["tree"]
    paths: dict[int, str] = {}
    for entry in tree:
        path: str = entry["path"]
        if not path.startswith("python/") or not path.endswith(".py"):
            continue
        prefix = path.removeprefix("python/").split("-", 1)[0]
        if prefix.isdigit():
            paths.setdefault(int(prefix), path)
    return paths


def main() -> int:
    problems: list[dict[str, Any]] = json.loads(RAW_PROBLEMS_PATH.read_text(encoding="utf-8"))
    session = requests.Session()
    paths = python_paths_by_id(session)
    SOLUTIONS_DIR.mkdir(exist_ok=True)

    missing: list[str] = []
    for problem in problems:
        path = paths.get(problem["id"])
        if path is None:
            missing.append(problem["slug"])
            print(f"MISSING {problem['slug']}", file=sys.stderr)
            continue
        response = session.get(RAW_URL.format(path=path), timeout=30)
        response.raise_for_status()
        (SOLUTIONS_DIR / f"{problem['slug']}.py").write_text(response.text, encoding="utf-8")
        print(f"ok      {problem['slug']} <- {path}")

    print(f"\nsaved {len(problems) - len(missing)} solutions, missing {len(missing)}")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
