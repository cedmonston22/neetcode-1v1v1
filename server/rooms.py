import json
import random
import string
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

TOPICS = [
    "Arrays & Hashing",
    "Two Pointers",
    "Sliding Window",
    "Stack",
    "Binary Search",
    "Linked List",
    "Trees",
]
DIFFICULTIES = ["Easy", "Medium"]
MIN_PLAYERS = 2
MAX_PLAYERS = 3
MAX_NAME_LENGTH = 20
MAX_CODE_LENGTH = 50_000
MIN_MATCH_MINUTES = 1
MAX_MATCH_MINUTES = 10


class RoomError(Exception):
    pass


class ProblemBank:
    def __init__(self, problems: list[dict[str, Any]]) -> None:
        self.problems = problems

    @classmethod
    def load(cls, path: Path) -> "ProblemBank":
        return cls(json.loads(path.read_text(encoding="utf-8")))

    def pool(self, topics: list[str], difficulties: list[str]) -> list[dict[str, Any]]:
        return [p for p in self.problems if p["topic"] in topics and p["difficulty"] in difficulties]

    def pick(
        self,
        topics: list[str],
        difficulties: list[str],
        recent: list[str],
        rng: random.Random,
    ) -> dict[str, Any]:
        pool = self.pool(topics, difficulties)
        if not pool:
            raise RoomError("no problems match the selected topics and difficulties")
        fresh = [p for p in pool if p["slug"] not in recent]
        return rng.choice(fresh or pool)


@dataclass
class Player:
    name: str
    token: str
    connected: bool = True
    ready: bool = False
    code: str = ""
    best_passed: int = 0
    best_at: float | None = None
    submissions: int = 0
    solved_at: float | None = None
    busy: bool = False

    def reset_progress(self) -> None:
        self.ready = False
        self.code = ""
        self.best_passed = 0
        self.best_at = None
        self.submissions = 0
        self.solved_at = None
        self.busy = False


@dataclass
class Room:
    code: str
    match_seconds: float
    countdown_seconds: float
    players: dict[str, Player] = field(default_factory=dict)
    topics: list[str] = field(default_factory=lambda: list(TOPICS))
    difficulties: list[str] = field(default_factory=lambda: list(DIFFICULTIES))
    phase: str = "lobby"
    problem: dict[str, Any] | None = None
    match_id: int = 0
    countdown_ends_at: float | None = None
    started_at: float | None = None
    deadline: float | None = None
    winner: str | None = None
    end_reason: str | None = None
    recent: list[str] = field(default_factory=list)
    pending: dict[str, float] = field(default_factory=dict)

    def join(self, name: str, token: str) -> Player:
        name = name.strip()
        if not name or len(name) > MAX_NAME_LENGTH:
            raise RoomError(f"name must be 1-{MAX_NAME_LENGTH} characters")
        if not token:
            raise RoomError("missing player token")
        existing = self.players.get(name)
        if existing is not None:
            if existing.token != token:
                raise RoomError(f"someone in this room is already called {name}; pick another name")
            existing.connected = True
            return existing
        if self.phase != "lobby":
            raise RoomError("a match is in progress; wait for it to finish")
        if len(self.players) >= MAX_PLAYERS:
            raise RoomError(f"room is full ({MAX_PLAYERS} players max)")
        player = Player(name=name, token=token)
        self.players[name] = player
        return player

    def disconnect(self, name: str) -> None:
        player = self.players.get(name)
        if player is not None:
            player.connected = False

    def remove_if_gone(self, name: str) -> bool:
        player = self.players.get(name)
        if self.phase != "lobby" or player is None or player.connected:
            return False
        del self.players[name]
        return True

    def connected_count(self) -> int:
        return sum(1 for p in self.players.values() if p.connected)

    def set_settings(self, topics: list[str], difficulties: list[str], minutes: int | None = None) -> None:
        if self.phase != "lobby":
            raise RoomError("settings can only change in the lobby")
        if minutes is not None and not MIN_MATCH_MINUTES <= minutes <= MAX_MATCH_MINUTES:
            raise RoomError(f"match length must be {MIN_MATCH_MINUTES}-{MAX_MATCH_MINUTES} minutes")
        self.topics = [t for t in TOPICS if t in topics]
        self.difficulties = [d for d in DIFFICULTIES if d in difficulties]
        if minutes is not None:
            self.match_seconds = minutes * 60

    def set_ready(self, name: str, ready: bool) -> None:
        if self.phase != "lobby":
            raise RoomError("not in the lobby")
        self.players[name].ready = ready

    def can_start(self, bank: ProblemBank) -> bool:
        players = list(self.players.values())
        return (
            self.phase == "lobby"
            and len(players) >= MIN_PLAYERS
            and all(p.ready and p.connected for p in players)
            and bool(bank.pool(self.topics, self.difficulties))
        )

    def begin_countdown(self, problem: dict[str, Any], now: float) -> None:
        self.problem = problem
        self.match_id += 1
        self.phase = "countdown"
        self.countdown_ends_at = now + self.countdown_seconds
        self.winner = None
        self.end_reason = None
        self.pending.clear()
        self.recent = (self.recent + [problem["slug"]])[-10:]
        for player in self.players.values():
            player.code = problem["starterCode"]

    def start_playing(self, now: float) -> None:
        self.phase = "playing"
        self.started_at = now
        self.deadline = now + self.match_seconds

    def total_tests(self) -> int:
        if self.problem is None:
            return 0
        return len(self.problem["examples"]) + len(self.problem["tests"])

    def update_code(self, name: str, code: str) -> None:
        if self.phase not in ("countdown", "playing"):
            raise RoomError("no match in progress")
        if len(code) > MAX_CODE_LENGTH:
            raise RoomError("code is too long")
        self.players[name].code = code

    def is_open(self, now: float) -> bool:
        return self.phase == "playing" and self.deadline is not None and now < self.deadline

    def begin_submission(self, name: str, now: float) -> float:
        if not self.is_open(now) or self.started_at is None:
            raise RoomError("the match is not running")
        elapsed = now - self.started_at
        self.pending[name] = elapsed
        return elapsed

    def cancel_submission(self, name: str) -> None:
        self.pending.pop(name, None)
        self.settle()

    def record_submission(self, name: str, passed: int, submitted_at: float) -> None:
        self.pending.pop(name, None)
        if self.phase != "playing":
            return
        player = self.players[name]
        player.submissions += 1
        if passed > player.best_passed:
            player.best_passed = passed
            player.best_at = submitted_at
        if passed == self.total_tests() and (player.solved_at is None or submitted_at < player.solved_at):
            player.solved_at = submitted_at
        self.settle()

    def first_solver(self) -> Player | None:
        solved = [p for p in self.players.values() if p.solved_at is not None]
        return min(solved, key=lambda p: p.solved_at or 0.0) if solved else None

    def settle(self) -> None:
        if self.phase != "playing":
            return
        first = self.first_solver()
        if first is None or first.solved_at is None:
            return
        if any(t < first.solved_at for t in self.pending.values()):
            return
        self.finish(first.name, "solved")

    def finish_by_time(self) -> None:
        if self.phase != "playing":
            return
        first = self.first_solver()
        if first is not None:
            self.finish(first.name, "solved")
            return
        ranked = sorted(
            (p for p in self.players.values() if p.best_passed > 0),
            key=lambda p: (-p.best_passed, p.best_at if p.best_at is not None else float("inf")),
        )
        self.finish(ranked[0].name if ranked else None, "time")

    def finish(self, winner: str | None, reason: str) -> None:
        self.phase = "finished"
        self.winner = winner
        self.end_reason = reason

    def back_to_lobby(self) -> None:
        if self.phase != "finished":
            raise RoomError("the match has not finished")
        self.phase = "lobby"
        self.problem = None
        self.countdown_ends_at = None
        self.started_at = None
        self.deadline = None
        self.winner = None
        self.end_reason = None
        self.pending.clear()
        for name in [n for n, p in self.players.items() if not p.connected]:
            del self.players[name]
        for player in self.players.values():
            player.reset_progress()

    def snapshot(self, now: float, bank: ProblemBank, viewer: str | None) -> dict[str, Any]:
        in_match = self.phase in ("countdown", "playing", "finished")
        show_problem = self.phase in ("playing", "finished")
        problem = self.problem if show_problem else None

        def visible_code(p: Player) -> str:
            if self.phase == "finished" or (show_problem and p.name == viewer):
                return p.code
            return ""

        return {
            "type": "state",
            "room": self.code,
            "phase": self.phase,
            "serverNow": now,
            "countdownEndsAt": self.countdown_ends_at,
            "startedAt": self.started_at,
            "deadline": self.deadline,
            "matchSeconds": self.match_seconds,
            "topics": self.topics,
            "difficulties": self.difficulties,
            "allTopics": TOPICS,
            "allDifficulties": DIFFICULTIES,
            "poolSize": len(bank.pool(self.topics, self.difficulties)),
            "minPlayers": MIN_PLAYERS,
            "maxPlayers": MAX_PLAYERS,
            "minMinutes": MIN_MATCH_MINUTES,
            "maxMinutes": MAX_MATCH_MINUTES,
            "winner": self.winner,
            "endReason": self.end_reason,
            "totalTests": self.total_tests(),
            "problem": None
            if problem is None
            else {
                "slug": problem["slug"],
                "title": problem["title"],
                "difficulty": problem["difficulty"],
                "topic": problem["topic"],
                "content": problem["content"],
                "starterCode": problem["starterCode"],
                "exampleCount": len(problem["examples"]),
            },
            "players": [
                {
                    "name": p.name,
                    "connected": p.connected,
                    "ready": p.ready,
                    "code": visible_code(p),
                    "bestPassed": p.best_passed,
                    "bestAt": p.best_at,
                    "submissions": p.submissions,
                    "solvedAt": p.solved_at,
                    "busy": p.busy and in_match,
                }
                for p in self.players.values()
            ],
        }


def new_room_code(existing: set[str], rng: random.Random) -> str:
    while True:
        code = "".join(rng.choice(string.ascii_uppercase) for _ in range(4))
        if code not in existing:
            return code
