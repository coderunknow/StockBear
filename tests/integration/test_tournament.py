#!/usr/bin/env python3
"""Smoke-test paired openings, PGN legality and honest unadjudicated reporting.
Requires optional chess==1.11.2 and a built StockBear executable.
"""
import json
import importlib.util
import time
from pathlib import Path
import subprocess
import sys
import tempfile
import chess.pgn

engine = str(Path(sys.argv[1]).resolve())
root = Path(__file__).resolve().parents[2]
with tempfile.TemporaryDirectory() as tmp:
    pgn, log = Path(tmp)/"match.pgn", Path(tmp)/"match.jsonl"
    cmd = [sys.executable, str(root/"scripts/tournament.py"), "--engine-a", engine,
           "--engine-b", engine, "--games", "2", "--base-ms", "500", "--inc-ms", "5",
           "--hash", "1", "--threads", "1", "--max-plies", "20", "--pgn", str(pgn), "--jsonl", str(log)]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, (result.stdout, result.stderr)
    records = [json.loads(line) for line in log.read_text().splitlines()]
    games = [item for item in records if "game" in item]
    assert len(games) == 2 and games[0]["opening"] == games[1]["opening"], games
    assert all(item["result"] == "*" and item["termination"] == "UNADJUDICATED_MAX_PLIES" for item in games), games
    summary = records[-1]["summary"]
    assert summary["games"] == 0 and summary["unadjudicated"] == 2, summary
    with pgn.open(encoding="utf-8") as stream:
        for _ in range(2):
            game = chess.pgn.read_game(stream)
            assert game is not None and not game.errors
            board = game.board()
            for move in game.mainline_moves():
                assert move in board.legal_moves, (board.fen(), move)
                board.push(move)
            assert game.headers["Result"] == "*"
        assert chess.pgn.read_game(stream) is None
print("PASS tournament paired openings, legal PGN and unadjudicated results")

# A flag fall is not necessarily a win: FIDE 6.9 requires opponent mate
# reachability. This harness does not have a general solver, so censor it.
spec = importlib.util.spec_from_file_location("tournament", root/"scripts/tournament.py")
tournament = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tournament)
class SlowEngine:
    name = "test engine"
    def new_game(self): pass
    def bestmove(self, *args):
        time.sleep(.01)
        return "e2e4"
a, b = SlowEngine(), SlowEngine()
game, record = tournament.play_game(a, b, 0, ("empty", []), 1, 0, 2)
assert record["result"] == "*" and record["score_a"] is None, record
assert record["termination"].startswith("UNADJUDICATED_TIME_FORFEIT"), record
assert record["engine_a_color"] == "white"
print("PASS timeout remains unadjudicated without FIDE mate reachability")
