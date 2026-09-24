import html
import json
import re
import sys
import time
from pathlib import Path
from typing import Any

import requests

from neetcode_list import TOPICS

GRAPHQL_URL = "https://leetcode.com/graphql"
OUT_PATH = Path(__file__).resolve().parent.parent / "data" / "raw_problems.json"
REQUEST_DELAY_SECONDS = 1.0

QUERY = """
query questionData($titleSlug: String!) {
  question(titleSlug: $titleSlug) {
    questionFrontendId
    title
    titleSlug
    difficulty
    isPaidOnly
    content
    exampleTestcases
    metaData
    codeSnippets { langSlug code }
  }
}
"""

HEADERS = {
    "Content-Type": "application/json",
    "Referer": "https://leetcode.com/problems/",
    "User-Agent": "Mozilla/5.0",
}


def fetch_question(session: requests.Session, slug: str) -> dict[str, Any]:
    response = session.post(
        GRAPHQL_URL,
        json={"query": QUERY, "variables": {"titleSlug": slug}},
        headers=HEADERS,
        timeout=20,
    )
    response.raise_for_status()
    payload: dict[str, Any] = response.json()
    question = payload.get("data", {}).get("question")
    if question is None:
        raise ValueError(f"no question returned for {slug}: {payload.get('errors')}")
    return question


def extract_outputs(content: str) -> list[str]:
    text = html.unescape(re.sub(r"<[^>]+>", "", content))
    return [m.strip() for m in re.findall(r"Output:\s*(.+)", text)]


def split_inputs(example_testcases: str, param_count: int) -> list[list[str]]:
    lines = [line for line in example_testcases.split("\n") if line.strip()]
    if param_count == 0 or len(lines) % param_count != 0:
        raise ValueError(f"{len(lines)} input lines not divisible by {param_count} params")
    return [lines[i : i + param_count] for i in range(0, len(lines), param_count)]


def build_problem(question: dict[str, Any], topic: str) -> dict[str, Any]:
    meta: dict[str, Any] = json.loads(question["metaData"])
    snippet = next(
        (s["code"] for s in question["codeSnippets"] or [] if s["langSlug"] == "python3"),
        None,
    )
    if snippet is None:
        raise ValueError("no python3 snippet")

    inputs = split_inputs(question["exampleTestcases"], len(meta["params"]))
    outputs = extract_outputs(question["content"])
    if len(inputs) != len(outputs):
        raise ValueError(f"{len(inputs)} example inputs but {len(outputs)} outputs")

    return {
        "id": int(question["questionFrontendId"]),
        "slug": question["titleSlug"],
        "title": question["title"],
        "difficulty": question["difficulty"],
        "topic": topic,
        "content": question["content"],
        "starterCode": snippet,
        "meta": meta,
        "examples": [{"input": i, "output": o} for i, o in zip(inputs, outputs)],
    }


def main() -> int:
    session = requests.Session()
    problems: list[dict[str, Any]] = []
    skipped: list[str] = []
    failed: list[str] = []

    for topic, slugs in TOPICS.items():
        for slug in slugs:
            try:
                question = fetch_question(session, slug)
                if question["isPaidOnly"]:
                    skipped.append(f"{slug} (premium)")
                elif question["difficulty"] not in ("Easy", "Medium"):
                    skipped.append(f"{slug} ({question['difficulty']})")
                else:
                    problems.append(build_problem(question, topic))
                    print(f"ok      {slug}")
            except (requests.RequestException, ValueError, KeyError) as error:
                failed.append(f"{slug}: {error}")
                print(f"FAILED  {slug}: {error}", file=sys.stderr)
            time.sleep(REQUEST_DELAY_SECONDS)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(problems, indent=2), encoding="utf-8")

    print(f"\nsaved {len(problems)} problems to {OUT_PATH}")
    for line in skipped:
        print(f"skipped {line}")
    for line in failed:
        print(f"failed  {line}", file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
