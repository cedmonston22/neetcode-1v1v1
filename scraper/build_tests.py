import json
import random
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scraper.generators import GENERATORS
from scraper.generators.stress import STRESS
from scraper.problem_config import COMPARE_MODES
from server.harness import dumps
from server.runner import run_solution

RAW_PROBLEMS_PATH = ROOT / "data" / "raw_problems.json"
OUT_PATH = ROOT / "data" / "problems.json"
SOLUTIONS_DIR = ROOT / "scraper" / "solutions"
GENERATED_PER_PROBLEM = 25
MIN_TOTAL_TESTS = 20
MIN_TOTAL_OVERRIDES: dict[str, int] = {"generate-parentheses": 8}
REFERENCE_TIME_LIMIT_SECONDS = 120.0
TIME_LIMIT_FACTOR = 4.0
MIN_TIME_LIMIT_SECONDS = 2.5
MAX_TIME_LIMIT_SECONDS = 10.0
TIMING_RUNS = 2


def problem_spec(raw: dict[str, Any]) -> dict[str, Any]:
    meta = raw["meta"]
    return {
        "id": raw["id"],
        "slug": raw["slug"],
        "title": raw["title"],
        "difficulty": raw["difficulty"],
        "topic": raw["topic"],
        "content": raw["content"],
        "starterCode": raw["starterCode"],
        "method": meta["name"],
        "params": [{"name": p["name"], "type": p["type"]} for p in meta["params"]],
        "returnType": meta["return"]["type"],
        "compare": COMPARE_MODES.get(raw["slug"], "exact"),
        "examples": raw["examples"],
    }


def generate_inputs(slug: str, seen: set[str]) -> list[list[str]]:
    generator = GENERATORS[slug]
    rng = random.Random(slug)
    candidates = [generator(rng, i) for i in range(GENERATED_PER_PROBLEM)]
    stress_rng = random.Random(f"{slug}:stress")
    candidates += [stress(stress_rng) for stress in STRESS.get(slug, [])]
    inputs: list[list[str]] = []
    for args in candidates:
        encoded = [dumps(arg) for arg in args]
        key = "\n".join(encoded)
        if key not in seen:
            seen.add(key)
            inputs.append(encoded)
    return inputs


def calibrate_time_limit(code: str, problem: dict[str, Any]) -> tuple[float, float]:
    everything = problem["examples"] + problem["tests"]
    slowest = 0.0
    for _ in range(TIMING_RUNS):
        started = time.perf_counter()
        run_solution(code, problem, everything, REFERENCE_TIME_LIMIT_SECONDS)
        slowest = max(slowest, time.perf_counter() - started)
    limit = min(MAX_TIME_LIMIT_SECONDS, max(MIN_TIME_LIMIT_SECONDS, TIME_LIMIT_FACTOR * slowest))
    return round(limit, 1), slowest


def build_problem(raw: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    problem = problem_spec(raw)
    errors: list[str] = []
    code = (SOLUTIONS_DIR / f"{raw['slug']}.py").read_text(encoding="utf-8")

    example_report = run_solution(code, problem, problem["examples"], REFERENCE_TIME_LIMIT_SECONDS)
    if example_report.passed != example_report.total:
        errors.append(f"reference fails examples ({example_report.passed}/{example_report.total})")

    seen = {"\n".join(json_normalize(x) for x in example["input"]) for example in problem["examples"]}
    inputs = generate_inputs(raw["slug"], seen)
    pending = [{"input": encoded, "output": None} for encoded in inputs]
    report = run_solution(code, problem, pending, REFERENCE_TIME_LIMIT_SECONDS)
    if report.timed_out or report.crash or report.compile_error:
        errors.append(f"reference run failed: timeout={report.timed_out} crash={report.crash} compile={report.compile_error}")

    tests: list[dict[str, Any]] = []
    for outcome in report.outcomes:
        if outcome.error is not None or outcome.actual is None:
            errors.append(f"reference errored on generated test {outcome.index}: {outcome.error}")
            continue
        tests.append({"input": inputs[outcome.index], "output": outcome.actual})

    problem["tests"] = tests
    total = len(problem["examples"]) + len(tests)
    minimum = MIN_TOTAL_OVERRIDES.get(raw["slug"], MIN_TOTAL_TESTS)
    if total < minimum:
        errors.append(f"only {total} tests, need {minimum}")
    if not errors:
        problem["timeLimit"], reference_seconds = calibrate_time_limit(code, problem)
        if reference_seconds * TIME_LIMIT_FACTOR > MAX_TIME_LIMIT_SECONDS:
            errors.append(f"reference takes {reference_seconds:.2f}s, too close to the {MAX_TIME_LIMIT_SECONDS}s cap")
    return problem, errors


def json_normalize(raw: str) -> str:
    return dumps(json.loads(raw))


def main() -> int:
    sys.setrecursionlimit(50_000)
    raw_problems: list[dict[str, Any]] = json.loads(RAW_PROBLEMS_PATH.read_text(encoding="utf-8"))
    problems: list[dict[str, Any]] = []
    failures = 0
    for raw in raw_problems:
        if raw["slug"] not in GENERATORS:
            print(f"FAILED  {raw['slug']}: no generator", file=sys.stderr)
            failures += 1
            continue
        problem, errors = build_problem(raw)
        total = len(problem["examples"]) + len(problem["tests"])
        if errors:
            failures += 1
            for error in errors:
                print(f"FAILED  {raw['slug']}: {error}", file=sys.stderr)
        else:
            problems.append(problem)
            print(f"ok      {raw['slug']}: {total} tests, {problem['timeLimit']}s limit")

    OUT_PATH.write_text(json.dumps(problems), encoding="utf-8")
    size_mb = OUT_PATH.stat().st_size / 1_000_000
    print(f"\nsaved {len(problems)} problems to {OUT_PATH} ({size_mb:.1f} MB), {failures} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
