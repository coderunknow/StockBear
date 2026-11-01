#!/usr/bin/env python3
"""Smoke-test paired openings, PGN legality and honest unadjudicated reporting.
Requires optional chess==1.11.2 and a built StockBear executable.
"""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import chess.pgn

engine = str(Path(sys.argv[1]).resolve())
root = Path(__file__).resolve().parents[2]
with tempfile.TemporaryDirectory() as tmp:
    pgn, log = Path(tmp)/"match.pgn", Path(tmp)/"match.jsonl"
    # A node budget instead of the clock: on a shared runner the engine can miss
    # a 500 ms allotment and forfeit, which would fail this smoke test for a
    # reason it is not testing. `go nodes` removes the clock from the equation.
    cmd = [sys.executable, str(root/"scripts/tournament.py"), "--engine-a", engine,
           "--engine-b", engine, "--games", "2", "--nodes", "2000",
           "--hash", "1", "--threads", "1", "--max-plies", "20", "--pgn", str(pgn), "--jsonl", str(log)]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, (result.stdout, result.stderr)
    records = [json.loads(line) for line in log.read_text().splitlines()]
    # The budget must be recorded, otherwise a reader cannot tell whether the
    # match was played to a clock or to a node limit.
    assert records[0]["configuration"]["nodes_per_move"] == 2000, records[0]
    assert records[-1]["summary"]["config"]["nodes_per_move"] == 2000, records[-1]
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

# An ablation flag that the engine would reject must fail before any game is
# played: recording it as effective would report an experiment that never ran.
with tempfile.TemporaryDirectory() as tmp:
    cmd = [sys.executable, str(root/"scripts/tournament.py"), "--engine-a", engine,
           "--engine-b", engine, "--games", "2", "--base-ms", "100", "--inc-ms", "0",
           "--hash", "1", "--a-option", "NullMove=flase",
           "--pgn", str(Path(tmp)/"m.pgn"), "--jsonl", str(Path(tmp)/"m.jsonl")]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    assert result.returncode != 0, result.stdout
    assert "expects true or false" in result.stderr, result.stderr
    # A negative node budget is rejected during argument parsing.
    cmd = [sys.executable, str(root/"scripts/tournament.py"), "--engine-a", engine,
           "--engine-b", engine, "--nodes", "-5"]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    assert result.returncode != 0 and "invalid clock" in result.stderr, result.stderr
    # A non-finite SPRT hypothesis is rejected during argument parsing.
    cmd = [sys.executable, str(root/"scripts/tournament.py"), "--engine-a", engine,
           "--engine-b", engine, "--sprt-elo", "nan"]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    assert result.returncode != 0 and "finite positive Elo" in result.stderr, result.stderr
print("PASS tournament rejects invalid option values and SPRT hypotheses")
