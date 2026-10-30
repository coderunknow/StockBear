#!/usr/bin/env python3
"""Independently regenerate the checked-in perft expectations with python-chess.

Optional development tool: pip install chess==1.11.2. It is NOT an engine
runtime dependency. Usage: python scripts/reference_perft.py
"""
from pathlib import Path
import re
import sys
import time
try:
    import chess
except ImportError:
    sys.exit("Install the optional validation dependency: pip install chess==1.11.2")

PATTERN = re.compile(r'^PERFT\("([^"]+)",\s*"([^"]+)",\s*(\d+),\s*(\d+)ULL\)')


def perft(board, depth):
    if depth == 0:
        return 1
    if depth == 1:
        return board.legal_moves.count()
    nodes = 0
    for move in board.legal_moves:
        board.push(move)
        nodes += perft(board, depth - 1)
        board.pop()
    return nodes


def main():
    path = Path(__file__).resolve().parents[1] / "benchmarks" / "positions" / "perft.inc"
    ok = True
    cases = 0
    print(f"Reference: python-chess {chess.__version__}", flush=True)
    for line in path.read_text(encoding="utf-8").splitlines():
        m = PATTERN.match(line)
        if not m:
            continue
        name, fen, depth, expected = m.groups()
        b = chess.Board(fen)
        if not b.is_valid():
            print(f"FAIL {name}: invalid reference position (status {b.status()})", flush=True)
            ok = False
            continue
        started = time.monotonic()
        actual = perft(b, int(depth))
        passed = actual == int(expected)
        print(f"{'PASS' if passed else 'FAIL'} {name}: depth={depth} expected={expected} "
              f"reference={actual} seconds={time.monotonic()-started:.3f}", flush=True)
        ok &= passed
        cases += 1
    if not cases:
        sys.exit("No reference positions found")
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
