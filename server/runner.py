import json
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from server.harness import outputs_match

HARNESS_PATH = Path(__file__).resolve().with_name("harness.py")
DEFAULT_TIME_LIMIT_SECONDS = 6.0


@dataclass
class TestOutcome:
    index: int
    passed: bool
    actual: str | None
    error: str | None
    stdout: str


@dataclass
class RunReport:
    total: int
    passed: int = 0
    outcomes: list[TestOutcome] = field(default_factory=list)
    compile_error: str | None = None
    timed_out: bool = False
    time_limit: float = DEFAULT_TIME_LIMIT_SECONDS
    crash: str | None = None


def build_spec(problem: dict[str, Any], tests: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "method": problem["method"],
        "params": problem["params"],
        "returnType": problem["returnType"],
        "tests": [{"input": test["input"]} for test in tests],
    }


def run_solution(
    code: str,
    problem: dict[str, Any],
    tests: list[dict[str, Any]],
    time_limit: float | None = None,
) -> RunReport:
    if time_limit is None:
        time_limit = float(problem.get("timeLimit", DEFAULT_TIME_LIMIT_SECONDS))
    report = RunReport(total=len(tests), time_limit=time_limit)
    with tempfile.TemporaryDirectory(prefix="ncv-") as tmp:
        tmp_path = Path(tmp)
        spec_path = tmp_path / "spec.json"
        solution_path = tmp_path / "solution.py"
        results_path = tmp_path / "results.jsonl"
        spec_path.write_text(json.dumps(build_spec(problem, tests)), encoding="utf-8")
        solution_path.write_text(code, encoding="utf-8")

        try:
            completed = subprocess.run(
                [sys.executable, "-I", str(HARNESS_PATH), str(spec_path), str(solution_path), str(results_path)],
                cwd=tmp,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                timeout=time_limit,
            )
            if completed.returncode != 0:
                report.crash = (completed.stderr or f"exit code {completed.returncode}")[-2000:]
        except subprocess.TimeoutExpired:
            report.timed_out = True

        lines = results_path.read_text(encoding="utf-8").splitlines() if results_path.exists() else []

    compare = problem.get("compare", "exact")
    for position, line in enumerate(lines):
        try:
            record: dict[str, Any] = json.loads(line)
        except json.JSONDecodeError:
            if position == len(lines) - 1 and (report.timed_out or report.crash):
                break
            raise
        if "compileError" in record:
            report.compile_error = record["compileError"]
            continue
        expected = tests[record["index"]].get("output")
        actual = record["actual"]
        outcome = TestOutcome(
            index=record["index"],
            passed=expected is not None and actual is not None and outputs_match(expected, actual, compare),
            actual=record["actual"],
            error=record["error"],
            stdout=record["stdout"],
        )
        report.outcomes.append(outcome)
    report.passed = sum(1 for o in report.outcomes if o.passed)
    return report
