import json
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient
from starlette.testclient import WebSocketTestSession

from server.main import Hub, create_app
from server.rooms import ProblemBank

ROOT = Path(__file__).resolve().parent.parent
ALL_PROBLEMS: list[dict[str, Any]] = json.loads((ROOT / "data" / "problems.json").read_text(encoding="utf-8"))
BINARY_SEARCH = next(p for p in ALL_PROBLEMS if p["slug"] == "binary-search")
REFERENCE = (ROOT / "scraper" / "solutions" / "binary-search.py").read_text(encoding="utf-8")


def client(match_seconds: float = 30, lobby_grace_seconds: float = 30) -> TestClient:
    hub = Hub(
        ProblemBank([BINARY_SEARCH]),
        match_seconds=match_seconds,
        countdown_seconds=0,
        lobby_grace_seconds=lobby_grace_seconds,
    )
    return TestClient(create_app(hub))


def receive_until(ws: WebSocketTestSession, predicate: Any, limit: int = 50) -> dict[str, Any]:
    for _ in range(limit):
        message: dict[str, Any] = ws.receive_json()
        if predicate(message):
            return message
    raise AssertionError("expected message never arrived")


def is_phase(phase: str) -> Any:
    return lambda m: m["type"] == "state" and m["phase"] == phase


def test_pages_and_room_api() -> None:
    with client() as c:
        assert c.get("/").status_code == 200
        code = c.post("/api/rooms").json()["code"]
        assert c.get(f"/room/{code}").status_code == 200
        assert c.get(f"/api/rooms/{code}").json()["players"] == []
        assert c.get("/api/rooms/ZZZZ").status_code == 404
        assert c.get("/api/info").json()["lanUrl"].startswith("http://")


def test_unknown_room_is_rejected() -> None:
    with client() as c, c.websocket_connect("/ws/NOPE?name=a&token=t-a") as ws:
        message = ws.receive_json()
        assert message["type"] == "error" and message["fatal"]


def test_full_match_run_submit_and_win() -> None:
    with client() as c:
        code = c.post("/api/rooms").json()["code"]
        with c.websocket_connect(f"/ws/{code}?name=alice&token=t-alice") as alice, c.websocket_connect(f"/ws/{code}?name=bob&token=t-bob") as bob:
            receive_until(alice, lambda m: m["type"] == "state" and len(m["players"]) == 2)

            alice.send_json({"type": "ready", "ready": True})
            bob.send_json({"type": "ready", "ready": True})
            state = receive_until(alice, is_phase("playing"))
            assert state["problem"]["slug"] == "binary-search"
            total = state["totalTests"]
            assert total == len(BINARY_SEARCH["examples"]) + len(BINARY_SEARCH["tests"])

            bob.send_json({"type": "code", "code": "class Solution:\n    pass # bob typing"})
            bob.send_json({"type": "ready", "ready": True})
            receive_until(bob, lambda m: m["type"] == "error")
            codes = {p["name"]: p["code"] for p in state["players"]}
            assert codes["bob"] == ""
            assert codes["alice"] == BINARY_SEARCH["starterCode"]

            wrong = "class Solution:\n    def search(self, nums, target):\n        return -1\n"
            alice.send_json({"type": "run", "code": wrong})
            run = receive_until(alice, lambda m: m["type"] == "result")
            assert run["kind"] == "run"
            assert run["total"] == len(BINARY_SEARCH["examples"])
            assert len(run["cases"]) == run["total"]

            alice.send_json({"type": "submit", "code": wrong})
            submit = receive_until(alice, lambda m: m["type"] == "result")
            assert submit["kind"] == "submit" and submit["total"] == total
            assert 0 < submit["passed"] < total
            assert len(submit["cases"]) == 1 and not submit["cases"][0]["passed"]
            progress = receive_until(
                bob,
                lambda m: m["type"] == "state" and next(p for p in m["players"] if p["name"] == "alice")["submissions"] == 1,
            )
            assert next(p for p in progress["players"] if p["name"] == "alice")["bestPassed"] == submit["passed"]
            assert next(p for p in progress["players"] if p["name"] == "alice")["code"] == ""
            assert "bob typing" in next(p for p in progress["players"] if p["name"] == "bob")["code"]

            bob.send_json({"type": "submit", "code": REFERENCE})
            finished = receive_until(bob, is_phase("finished"))
            assert finished["winner"] == "bob"
            assert finished["endReason"] == "solved"
            assert REFERENCE in next(p["code"] for p in finished["players"] if p["name"] == "bob")

            alice.send_json({"type": "lobby"})
            back = receive_until(bob, is_phase("lobby"))
            assert all(not p["ready"] for p in back["players"])


def test_match_ends_when_time_runs_out() -> None:
    with client(match_seconds=1.5) as c:
        code = c.post("/api/rooms").json()["code"]
        with c.websocket_connect(f"/ws/{code}?name=a&token=t-a") as a, c.websocket_connect(f"/ws/{code}?name=b&token=t-b") as b:
            a.send_json({"type": "ready", "ready": True})
            b.send_json({"type": "ready", "ready": True})
            receive_until(a, is_phase("playing"))
            finished = receive_until(a, is_phase("finished"))
            assert finished["endReason"] == "time"
            assert finished["winner"] is None


def test_bad_messages_get_errors_without_disconnecting() -> None:
    with client() as c:
        code = c.post("/api/rooms").json()["code"]
        with c.websocket_connect(f"/ws/{code}?name=a&token=t-a") as a:
            a.send_text("not json")
            assert receive_until(a, lambda m: m["type"] == "error")["message"]
            a.send_json({"type": "submit", "code": "x"})
            assert "not running" in receive_until(a, lambda m: m["type"] == "error")["message"]
            a.send_json({"type": "settings", "topics": "Trees", "difficulties": []})
            assert receive_until(a, lambda m: m["type"] == "error")
            a.send_json({"type": "ready", "ready": True})
            state = receive_until(a, lambda m: m["type"] == "state" and m["players"][0]["ready"])
            assert state["phase"] == "lobby"


def test_same_name_reconnect_takes_over_seat() -> None:
    with client() as c:
        code = c.post("/api/rooms").json()["code"]
        with c.websocket_connect(f"/ws/{code}?name=a&token=t-a") as first:
            receive_until(first, lambda m: m["type"] == "welcome")
            with c.websocket_connect(f"/ws/{code}?name=a&token=t-a") as second:
                kicked = receive_until(first, lambda m: m["type"] == "error")
                assert kicked["fatal"]
                state = receive_until(second, lambda m: m["type"] == "state")
                assert [p["name"] for p in state["players"]] == ["a"]


def test_refreshing_in_the_lobby_keeps_your_seat() -> None:
    with client(lobby_grace_seconds=30) as c:
        code = c.post("/api/rooms").json()["code"]
        with c.websocket_connect(f"/ws/{code}?name=a&token=t-a") as a, c.websocket_connect(f"/ws/{code}?name=b&token=t-b") as b:
            receive_until(a, lambda m: m["type"] == "state" and len(m["players"]) == 2)
            b.send_json({"type": "ready", "ready": True})
            receive_until(b, lambda m: m["type"] == "state" and m["players"][1]["ready"])
            a.close()
            state = receive_until(b, lambda m: m["type"] == "state" and not m["players"][0]["connected"])
            assert state["phase"] == "lobby"
            assert [p["name"] for p in state["players"]] == ["a", "b"]
            with c.websocket_connect(f"/ws/{code}?name=a&token=t-a") as again:
                state = receive_until(again, lambda m: m["type"] == "state")
                assert state["phase"] == "lobby"
                assert state["players"][0]["connected"]


def test_disconnected_lobby_player_is_dropped_after_grace() -> None:
    with client(lobby_grace_seconds=0.2) as c:
        code = c.post("/api/rooms").json()["code"]
        with c.websocket_connect(f"/ws/{code}?name=b&token=t-b") as b:
            with c.websocket_connect(f"/ws/{code}?name=a&token=t-a"):
                receive_until(b, lambda m: m["type"] == "state" and len(m["players"]) == 2)
            state = receive_until(b, lambda m: m["type"] == "state" and len(m["players"]) == 1)
            assert state["players"][0]["name"] == "b"


def test_someone_else_cannot_take_your_name() -> None:
    with client() as c:
        code = c.post("/api/rooms").json()["code"]
        with c.websocket_connect(f"/ws/{code}?name=a&token=t-a") as a:
            receive_until(a, lambda m: m["type"] == "welcome")
            with c.websocket_connect(f"/ws/{code}?name=a&token=intruder") as intruder:
                message = intruder.receive_json()
                assert message["type"] == "error" and message["fatal"]


def test_default_match_length_is_five_minutes_and_adjustable() -> None:
    from server.main import MATCH_SECONDS

    assert MATCH_SECONDS == 300
    with client(match_seconds=MATCH_SECONDS) as c:
        code = c.post("/api/rooms").json()["code"]
        with c.websocket_connect(f"/ws/{code}?name=a&token=t-a") as a:
            state = receive_until(a, lambda m: m["type"] == "state")
            assert state["matchSeconds"] == 300
            assert (state["minMinutes"], state["maxMinutes"]) == (1, 10)
            a.send_json({"type": "settings", "topics": state["topics"], "difficulties": state["difficulties"], "minutes": 7})
            assert receive_until(a, lambda m: m["type"] == "state")["matchSeconds"] == 420
            a.send_json({"type": "settings", "topics": state["topics"], "difficulties": state["difficulties"], "minutes": 12})
            assert "1-10 minutes" in receive_until(a, lambda m: m["type"] == "error")["message"]
            a.send_json({"type": "settings", "topics": state["topics"], "difficulties": state["difficulties"], "minutes": "5"})
            assert "whole number" in receive_until(a, lambda m: m["type"] == "error")["message"]
