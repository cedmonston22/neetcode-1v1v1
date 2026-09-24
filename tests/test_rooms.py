import random
from typing import Any

import pytest

from server.rooms import MAX_PLAYERS, ProblemBank, Room, RoomError, new_room_code


def make_problem(slug: str, topic: str = "Stack", difficulty: str = "Easy") -> dict[str, Any]:
    return {
        "slug": slug,
        "title": slug,
        "topic": topic,
        "difficulty": difficulty,
        "content": "",
        "starterCode": "class Solution: pass",
        "examples": [{"input": ["1"], "output": "1"}],
        "tests": [{"input": ["2"], "output": "2"}, {"input": ["3"], "output": "3"}],
    }


BANK = ProblemBank(
    [
        make_problem("a"),
        make_problem("b", topic="Trees", difficulty="Medium"),
        make_problem("c", topic="Trees", difficulty="Easy"),
    ]
)


def lobby(*names: str) -> Room:
    room = Room(code="ABCD", match_seconds=600, countdown_seconds=3)
    for name in names:
        room.join(name, token(name))
    return room


def token(name: str) -> str:
    return f"token-{name}"


def start(room: Room, now: float = 100.0) -> None:
    for player in room.players.values():
        player.ready = True
    assert room.can_start(BANK)
    room.begin_countdown(BANK.problems[0], now)
    room.start_playing(now + 3)


def test_pool_filters_by_topic_and_difficulty() -> None:
    assert [p["slug"] for p in BANK.pool(["Trees"], ["Medium"])] == ["b"]
    assert [p["slug"] for p in BANK.pool(["Trees"], ["Easy", "Medium"])] == ["b", "c"]
    assert BANK.pool([], ["Easy"]) == []


def test_pick_avoids_recent_problems_until_pool_exhausted() -> None:
    rng = random.Random(0)
    assert BANK.pick(["Trees"], ["Easy", "Medium"], ["b"], rng)["slug"] == "c"
    assert BANK.pick(["Trees"], ["Easy", "Medium"], ["b", "c"], rng)["slug"] in {"b", "c"}


def test_pick_with_empty_pool_raises() -> None:
    with pytest.raises(RoomError):
        BANK.pick(["Sliding Window"], ["Easy"], [], random.Random(0))


def test_one_v_one_is_enough_to_start() -> None:
    room = lobby("alice")
    room.players["alice"].ready = True
    assert not room.can_start(BANK)
    room.join("bob", token("bob"))
    assert not room.can_start(BANK)
    room.set_ready("bob", True)
    assert room.can_start(BANK)


def test_room_caps_at_three_players() -> None:
    room = lobby("a", "b", "c")
    assert len(room.players) == MAX_PLAYERS
    with pytest.raises(RoomError):
        room.join("d", token("d"))


def test_cannot_start_when_pool_is_empty() -> None:
    room = lobby("a", "b")
    room.set_settings(["Sliding Window"], ["Medium"])
    for p in room.players.values():
        p.ready = True
    assert not room.can_start(BANK)


def test_settings_ignore_unknown_values() -> None:
    room = lobby("a")
    room.set_settings(["Trees", "Bogus"], ["Hard", "Easy"])
    assert room.topics == ["Trees"]
    assert room.difficulties == ["Easy"]


def test_new_players_cannot_join_mid_match_but_can_reconnect() -> None:
    room = lobby("a", "b")
    start(room)
    with pytest.raises(RoomError):
        room.join("c", token("c"))
    room.disconnect("a")
    assert not room.players["a"].connected
    assert room.join("a", token("a")).connected


def test_lobby_disconnect_keeps_seat_until_removed() -> None:
    room = lobby("a", "b", "c")
    room.set_ready("b", True)
    room.set_ready("c", True)
    room.disconnect("a")
    assert list(room.players) == ["a", "b", "c"]
    assert not room.can_start(BANK)
    assert room.join("a", token("a")).connected
    assert not room.remove_if_gone("a")
    room.disconnect("a")
    assert room.remove_if_gone("a")
    assert list(room.players) == ["b", "c"]
    assert room.can_start(BANK)


def test_same_name_with_different_token_is_rejected() -> None:
    room = lobby("a")
    with pytest.raises(RoomError):
        room.join("a", "someone-else")


def submit(room: Room, name: str, passed: int, at: float) -> None:
    assert room.started_at is not None
    elapsed = room.begin_submission(name, room.started_at + at)
    room.record_submission(name, passed, elapsed)


def test_first_full_pass_wins_immediately() -> None:
    room = lobby("a", "b")
    start(room)
    submit(room, "a", 2, at=7)
    assert room.phase == "playing"
    submit(room, "b", 3, at=17)
    assert room.phase == "finished"
    assert room.winner == "b"
    assert room.end_reason == "solved"
    assert room.players["b"].solved_at == 17


def test_earlier_submission_wins_even_if_graded_later() -> None:
    room = lobby("a", "b")
    start(room)
    assert room.started_at is not None
    slow = room.begin_submission("a", room.started_at + 10)
    fast = room.begin_submission("b", room.started_at + 11)
    room.record_submission("b", 3, fast)
    assert room.phase == "playing"
    room.record_submission("a", 3, slow)
    assert room.winner == "a"


def test_later_pending_submission_does_not_block_a_win() -> None:
    room = lobby("a", "b")
    start(room)
    assert room.started_at is not None
    solved = room.begin_submission("a", room.started_at + 10)
    room.begin_submission("b", room.started_at + 11)
    room.record_submission("a", 3, solved)
    assert room.winner == "a"


def test_submissions_close_at_the_deadline() -> None:
    room = lobby("a", "b")
    start(room)
    assert room.deadline is not None
    with pytest.raises(RoomError):
        room.begin_submission("a", room.deadline)


def test_submission_made_before_deadline_counts_after_it() -> None:
    room = lobby("a", "b")
    start(room)
    assert room.deadline is not None and room.started_at is not None
    elapsed = room.begin_submission("a", room.deadline - 0.5)
    room.record_submission("a", 3, elapsed)
    room.finish_by_time()
    assert room.winner == "a" and room.end_reason == "solved"


def test_time_up_awards_most_tests_then_earliest() -> None:
    room = lobby("a", "b", "c")
    start(room)
    submit(room, "a", 2, at=97)
    submit(room, "b", 2, at=47)
    submit(room, "c", 1, at=7)
    submit(room, "b", 1, at=197)
    room.finish_by_time()
    assert room.winner == "b"
    assert room.end_reason == "time"


def test_time_up_with_no_progress_has_no_winner() -> None:
    room = lobby("a", "b")
    start(room)
    room.finish_by_time()
    assert room.phase == "finished"
    assert room.winner is None


def test_back_to_lobby_resets_and_drops_disconnected() -> None:
    room = lobby("a", "b", "c")
    start(room)
    room.disconnect("c")
    submit(room, "a", 3, at=47)
    room.back_to_lobby()
    assert room.phase == "lobby"
    assert list(room.players) == ["a", "b"]
    assert all(not p.ready and p.best_passed == 0 and p.code == "" for p in room.players.values())


def test_snapshot_hides_problem_during_countdown() -> None:
    room = lobby("a", "b")
    for p in room.players.values():
        p.ready = True
    room.begin_countdown(BANK.problems[0], 100)
    snap = room.snapshot(100, BANK, "a")
    assert snap["problem"] is None
    assert all(p["code"] == "" for p in snap["players"])


def test_opponent_code_is_hidden_until_the_match_ends() -> None:
    room = lobby("a", "b")
    start(room)
    room.update_code("a", "a's code")
    room.update_code("b", "b's code")
    codes = {p["name"]: p["code"] for p in room.snapshot(200, BANK, "a")["players"]}
    assert codes == {"a": "a's code", "b": ""}
    assert room.snapshot(200, BANK, "a")["totalTests"] == 3
    room.finish_by_time()
    codes = {p["name"]: p["code"] for p in room.snapshot(900, BANK, "a")["players"]}
    assert codes == {"a": "a's code", "b": "b's code"}


def test_room_codes_are_unique() -> None:
    rng = random.Random(1)
    codes: set[str] = set()
    for _ in range(200):
        codes.add(new_room_code(codes, rng))
    assert len(codes) == 200


def test_match_length_is_adjustable_from_one_to_ten_minutes() -> None:
    room = lobby("a", "b")
    room.set_settings(list(room.topics), list(room.difficulties), 1)
    assert room.match_seconds == 60
    room.set_settings(list(room.topics), list(room.difficulties), 10)
    assert room.match_seconds == 600
    for bad in (0, 11):
        with pytest.raises(RoomError):
            room.set_settings(list(room.topics), list(room.difficulties), bad)
    assert room.match_seconds == 600
    start(room, now=100)
    assert room.deadline == 103 + 600
