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


def parse_cases(lines):
    """Fail closed: every PERFT row must be recognized and validated."""
    cases = []
    for number, line in enumerate(lines, 1):
        stripped = line.strip()
        if not re.match(r"^PERFT\b", stripped):
            continue
        match = PATTERN.fullmatch(stripped)
        if not match:
            raise ValueError(f"unparsable perft row {number}: {line}")
        cases.append(match.groups())
    if not cases:
        raise ValueError("No reference positions found")
    return cases


def main():
    path = Path(__file__).resolve().parents[1] / "benchmarks" / "positions" / "perft.inc"
    ok = True
    try:
        cases = parse_cases(path.read_text(encoding="utf-8").splitlines())
    except ValueError as exc:
        sys.exit(str(exc))
    print(f"Reference: python-chess {chess.__version__}", flush=True)
    for name, fen, depth, expected in cases:
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
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
