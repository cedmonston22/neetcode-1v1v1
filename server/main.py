import asyncio
import json
import logging
import os
import random
import socket
import time
from pathlib import Path
from typing import Any, Callable, Coroutine

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from server.rooms import Player, ProblemBank, Room, RoomError, new_room_code
from server.runner import RunReport, run_solution

ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = ROOT / "static"
PROBLEMS_PATH = ROOT / "data" / "problems.json"
PORT = int(os.environ.get("NCV_PORT", "8000"))
MATCH_SECONDS = float(os.environ.get("NCV_MATCH_SECONDS", "300"))
COUNTDOWN_SECONDS = float(os.environ.get("NCV_COUNTDOWN_SECONDS", "3"))
LOBBY_GRACE_SECONDS = 15.0
EMPTY_ROOM_TTL_SECONDS = 3600.0
MAX_PREVIEW_CHARS = 600

logger = logging.getLogger("ncv")


def lan_ip() -> str:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
        try:
            probe.connect(("10.255.255.255", 1))
            return str(probe.getsockname()[0])
        except OSError:
            return "127.0.0.1"


def preview(raw: str | None) -> str | None:
    if raw is None or len(raw) <= MAX_PREVIEW_CHARS:
        return raw
    return raw[:MAX_PREVIEW_CHARS] + f"... ({len(raw)} chars)"


def report_payload(
    kind: str,
    report: RunReport,
    tests: list[dict[str, Any]],
    problem: dict[str, Any],
) -> dict[str, Any]:
    names = [p["name"] for p in problem["params"]]
    cases: list[dict[str, Any]] = []
    for outcome in report.outcomes:
        if kind == "submit" and (outcome.passed or cases):
            continue
        test = tests[outcome.index]
        cases.append(
            {
                "index": outcome.index,
                "passed": outcome.passed,
                "input": [{"name": n, "value": preview(v)} for n, v in zip(names, test["input"])],
                "expected": preview(test["output"]),
                "actual": preview(outcome.actual),
                "error": outcome.error,
                "stdout": outcome.stdout,
            }
        )
    return {
        "type": "result",
        "kind": kind,
        "passed": report.passed,
        "total": report.total,
        "compileError": report.compile_error,
        "timedOut": report.timed_out,
        "timeLimit": report.time_limit,
        "crash": report.crash,
        "cases": cases,
    }


class Hub:
    def __init__(
        self,
        bank: ProblemBank,
        match_seconds: float,
        countdown_seconds: float,
        clock: Callable[[], float] = time.time,
        lobby_grace_seconds: float = LOBBY_GRACE_SECONDS,
    ) -> None:
        self.bank = bank
        self.match_seconds = match_seconds
        self.countdown_seconds = countdown_seconds
        self.clock = clock
        self.lobby_grace_seconds = lobby_grace_seconds
        self.rooms: dict[str, Room] = {}
        self.sockets: dict[str, dict[str, WebSocket]] = {}
        self.submits: dict[str, set[asyncio.Task[None]]] = {}
        self.tasks: set[asyncio.Task[None]] = set()
        self.rng = random.Random()

    def spawn(self, coro: Coroutine[Any, Any, None]) -> asyncio.Task[None]:
        task = asyncio.create_task(coro)
        self.tasks.add(task)
        task.add_done_callback(self._task_done)
        return task

    def _task_done(self, task: asyncio.Task[None]) -> None:
        self.tasks.discard(task)
        if not task.cancelled() and task.exception() is not None:
            logger.error("background task failed", exc_info=task.exception())

    def create_room(self) -> Room:
        code = new_room_code(set(self.rooms), self.rng)
        room = Room(code=code, match_seconds=self.match_seconds, countdown_seconds=self.countdown_seconds)
        self.rooms[code] = room
        self.sockets[code] = {}
        self.submits[code] = set()
        return room

    async def send(self, ws: WebSocket, message: dict[str, Any]) -> None:
        try:
            await ws.send_json(message)
        except (RuntimeError, WebSocketDisconnect) as error:
            logger.info("dropping message to closed socket: %s", error)

    async def send_to(self, room: Room, name: str, message: dict[str, Any]) -> None:
        ws = self.sockets.get(room.code, {}).get(name)
        if ws is not None:
            await self.send(ws, message)

    async def broadcast(self, room: Room) -> None:
        now = self.clock()
        sockets = list(self.sockets.get(room.code, {}).items())
        await asyncio.gather(*(self.send(ws, room.snapshot(now, self.bank, name)) for name, ws in sockets))

    async def attach(self, room: Room, name: str, token: str, ws: WebSocket) -> Player:
        player = room.join(name, token)
        previous = self.sockets[room.code].get(player.name)
        self.sockets[room.code][player.name] = ws
        if previous is not None:
            await self.send(previous, {"type": "error", "message": "you connected from another tab", "fatal": True})
            try:
                await previous.close(code=4409)
            except RuntimeError:
                pass
        await self.broadcast(room)
        return player

    async def detach(self, room: Room, name: str, ws: WebSocket) -> None:
        sockets = self.sockets.get(room.code, {})
        if sockets.get(name) is not ws:
            return
        del sockets[name]
        room.disconnect(name)
        await self.broadcast(room)
        if room.phase == "lobby":
            self.spawn(self._drop_after_grace(room, name))
        if room.connected_count() == 0:
            self.spawn(self._expire_if_empty(room))

    async def _drop_after_grace(self, room: Room, name: str) -> None:
        await asyncio.sleep(self.lobby_grace_seconds)
        if room.remove_if_gone(name):
            await self.broadcast(room)
            await self.maybe_start(room)

    async def _expire_if_empty(self, room: Room) -> None:
        await asyncio.sleep(EMPTY_ROOM_TTL_SECONDS)
        if room.connected_count() == 0 and self.rooms.get(room.code) is room:
            del self.rooms[room.code]
            del self.sockets[room.code]
            del self.submits[room.code]

    async def handle(self, room: Room, name: str, message: dict[str, Any]) -> None:
        kind = message.get("type")
        if kind == "settings":
            topics = message.get("topics")
            difficulties = message.get("difficulties")
            if not _is_str_list(topics) or not _is_str_list(difficulties):
                raise RoomError("topics and difficulties must be lists of strings")
            minutes = message.get("minutes")
            if minutes is not None and (isinstance(minutes, bool) or not isinstance(minutes, int)):
                raise RoomError("minutes must be a whole number")
            room.set_settings(topics, difficulties, minutes)
            await self.broadcast(room)
            await self.maybe_start(room)
        elif kind == "ready":
            room.set_ready(name, bool(message.get("ready")))
            await self.broadcast(room)
            await self.maybe_start(room)
        elif kind == "code":
            room.update_code(name, _require_str(message, "code"))
        elif kind in ("run", "submit"):
            code = _require_str(message, "code")
            self.start_evaluation(room, name, kind, code)
            await self.broadcast(room)
        elif kind == "lobby":
            room.back_to_lobby()
            await self.broadcast(room)
        else:
            raise RoomError(f"unknown message type: {kind!r}")

    async def maybe_start(self, room: Room) -> None:
        if not room.can_start(self.bank):
            return
        problem = self.bank.pick(room.topics, room.difficulties, room.recent, self.rng)
        room.begin_countdown(problem, self.clock())
        await self.broadcast(room)
        self.spawn(self._run_match(room, room.match_id))

    async def _run_match(self, room: Room, match_id: int) -> None:
        await asyncio.sleep(self.countdown_seconds)
        if room.match_id != match_id or room.phase != "countdown":
            return
        room.start_playing(self.clock())
        await self.broadcast(room)
        await asyncio.sleep(room.match_seconds)
        if room.match_id != match_id or room.phase != "playing":
            return
        in_flight = list(self.submits.get(room.code, ()))
        if in_flight:
            await asyncio.wait(in_flight)
        if room.match_id != match_id or room.phase != "playing":
            return
        room.finish_by_time()
        await self.broadcast(room)

    def start_evaluation(self, room: Room, name: str, kind: str, code: str) -> None:
        player = room.players[name]
        now = self.clock()
        if not room.is_open(now) or room.problem is None:
            raise RoomError("the match is not running")
        if player.busy:
            raise RoomError("your last run is still going")
        room.update_code(name, code)
        submitted_at = room.begin_submission(name, now) if kind == "submit" else 0.0
        player.busy = True
        task = self.spawn(self._evaluate(room, name, kind, code, room.problem, room.match_id, submitted_at))
        if kind == "submit":
            submits = self.submits.setdefault(room.code, set())
            submits.add(task)
            task.add_done_callback(submits.discard)

    async def _evaluate(
        self,
        room: Room,
        name: str,
        kind: str,
        code: str,
        problem: dict[str, Any],
        match_id: int,
        submitted_at: float,
    ) -> None:
        tests = problem["examples"] if kind == "run" else problem["examples"] + problem["tests"]
        report: RunReport | None = None
        try:
            report = await asyncio.to_thread(run_solution, code, problem, tests)
        except Exception:
            logger.exception("runner failed for %s in room %s", name, room.code)
            await self.send_to(room, name, {"type": "error", "message": "the code runner failed; check the server log"})
        finally:
            if room.match_id == match_id and name in room.players:
                room.players[name].busy = False
        if room.match_id != match_id:
            return
        if report is None:
            if kind == "submit":
                room.cancel_submission(name)
            await self.broadcast(room)
            return
        await self.send_to(room, name, report_payload(kind, report, tests, problem))
        if kind == "submit":
            room.record_submission(name, report.passed, submitted_at)
        await self.broadcast(room)


def _is_str_list(value: object) -> bool:
    return isinstance(value, list) and all(isinstance(v, str) for v in value)


def _require_str(message: dict[str, Any], key: str) -> str:
    value = message.get(key)
    if not isinstance(value, str):
        raise RoomError(f"{key} must be a string")
    return value


def create_app(hub: Hub) -> FastAPI:
    app = FastAPI(title="NeetCode 1v1v1")
    app.state.hub = hub
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/")
    async def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/room/{code}")
    async def room_page(code: str) -> FileResponse:
        return FileResponse(STATIC_DIR / "room.html")

    @app.get("/api/info")
    async def info() -> dict[str, Any]:
        return {"lanUrl": f"http://{lan_ip()}:{PORT}", "matchSeconds": hub.match_seconds}

    @app.post("/api/rooms")
    async def create_room() -> dict[str, str]:
        return {"code": hub.create_room().code}

    @app.get("/api/rooms/{code}")
    async def room_info(code: str) -> dict[str, Any]:
        room = hub.rooms.get(code.upper())
        if room is None:
            raise HTTPException(status_code=404, detail="room not found")
        return {"code": room.code, "phase": room.phase, "players": list(room.players)}

    @app.websocket("/ws/{code}")
    async def websocket_endpoint(ws: WebSocket, code: str, name: str = "", token: str = "") -> None:
        await ws.accept()
        room = hub.rooms.get(code.upper())
        if room is None:
            await hub.send(ws, {"type": "error", "message": "room not found", "fatal": True})
            await ws.close(code=4404)
            return
        try:
            player = await hub.attach(room, name, token, ws)
        except RoomError as error:
            await hub.send(ws, {"type": "error", "message": str(error), "fatal": True})
            await ws.close(code=4400)
            return
        await hub.send(ws, {"type": "welcome", "name": player.name})
        try:
            while True:
                raw = await ws.receive_text()
                try:
                    message = json.loads(raw)
                    if not isinstance(message, dict):
                        raise RoomError("message must be a JSON object")
                    await hub.handle(room, player.name, message)
                except (RoomError, json.JSONDecodeError) as error:
                    await hub.send(ws, {"type": "error", "message": str(error)})
        except WebSocketDisconnect:
            pass
        finally:
            await hub.detach(room, player.name, ws)

    return app


app = create_app(Hub(ProblemBank.load(PROBLEMS_PATH), MATCH_SECONDS, COUNTDOWN_SECONDS))
