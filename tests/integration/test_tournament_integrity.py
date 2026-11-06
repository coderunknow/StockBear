#!/usr/bin/env python3
"""Regression tests for tournament game-integrity classification.

These drive ``tournament.play_game`` with fake engines so the exact failure
path is exercised deterministically, without needing a real engine to crash.

The defect they guard against (ported from the still-relevant PR #2 finding):
when a non-timeout engine error happened on the same move that the clock
expired, the harness used to record ``TIME_FORFEIT`` and hide the crash. The
DEV6 protocol requires ZERO time forfeits *and* ZERO engine failures, and a
misclassified crash sends root-cause analysis down the wrong path. A genuine
engine failure must therefore be reported as ``ENGINE_FAILURE`` even when the
flag also fell, while a ``TimeoutError`` (the forfeit deadline itself) stays a
time forfeit.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import chess  # noqa: E402
import tournament  # noqa: E402


class FakeEngine:
    def __init__(self, name, behavior):
        self.name = name
        self.behavior = behavior

    def new_game(self):
        pass

    def bestmove(self, moves, clocks, increment, color, nodes=0):
        return self.behavior(moves, clocks, increment, color, nodes)


OPENING = ("integrity-test", [])


def play(a, b, base_ms):
    return tournament.play_game(a, b, 0, OPENING, base_ms, 0, 10)


def crash(*_args):
    raise RuntimeError("engine crashed")


def timeout(*_args):
    raise TimeoutError("exceeded response deadline")


def illegal(*_args):
    return "e2e5"  # parses, but is not a legal move from the initial position


def legal(moves, _clocks, _increment, _color, _nodes=0):
    board = chess.Board()
    for text in moves:
        board.push_uci(text)
    return next(iter(board.legal_moves)).uci()


ok = FakeEngine("ok", legal)

# 1. A crash on a move whose clock also expired is an ENGINE_FAILURE, never a
#    TIME_FORFEIT. base_ms=0 makes the flag fall deterministically.
game, rec = play(FakeEngine("crasher", crash), ok, base_ms=0)
assert rec["termination"].startswith("ENGINE_FAILURE"), rec
assert rec["engine_failure"] is True, rec
assert "FORFEIT" not in rec["termination"].upper(), rec
assert rec["result"] == "0-1", rec  # White (engine A) crashed
assert game.headers["Termination"] == rec["termination"]

# 2. A TimeoutError is the forfeit deadline itself: it stays a TIME_FORFEIT and
#    is not counted as an engine failure.
game, rec = play(FakeEngine("slow", timeout), ok, base_ms=0)
assert rec["termination"].startswith("TIME_FORFEIT"), rec
assert rec["engine_failure"] is False, rec
assert rec["result"] == "0-1", rec

# 3. An illegal move is an engine failure even with plenty of clock remaining.
game, rec = play(FakeEngine("illegal", illegal), ok, base_ms=1000)
assert rec["termination"].startswith("ENGINE_FAILURE"), rec
assert rec["engine_failure"] is True, rec
assert "illegal move" in rec["termination"], rec

# 4. A normal legal move carries engine_failure=False.
game, rec = play(FakeEngine("legal", legal), ok, base_ms=1000)
assert rec["engine_failure"] is False, rec
assert rec["termination"] == "UNADJUDICATED_MAX_PLIES", rec
assert rec["plies"] == 10, rec

print("PASS tournament engine-failure classification and game integrity")
