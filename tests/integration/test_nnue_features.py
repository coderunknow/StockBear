#!/usr/bin/env python3
"""Differential test: the engine's feature function against an independent one.

The training pipeline consumes feature indices produced in Python
(`scripts/nnue_features.py`); the engine consumes the indices produced by
`src/evaluation/nnue.cpp`. If the two disagree, a network is trained on one
feature space and evaluated in another: nothing crashes, the network simply
plays badly. This test pins the engine side against a small, deliberately
independent implementation written here (stdlib only, no numpy, no import of the
engine's own mirror) so that a change to either side is caught.

Usage: test_nnue_features.py <path-to-stockbear>
"""
import os
import subprocess
import sys
import tempfile

EXE = sys.argv[1]

KIND = {
    "P": 0, "N": 1, "B": 2, "R": 3, "Q": 4, "K": 5,
    "p": 6, "n": 7, "b": 8, "r": 9, "q": 10, "k": 11,
}

FENS = [
    "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
    "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR b KQkq - 0 1",
    "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1",
    "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1",
    "4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1",
    "8/P6k/8/8/8/8/7p/5K2 w - - 0 1",
    "r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1",
    "8/8/8/8/8/8/6k1/4K2R w K - 0 1",
    "4k3/8/8/8/8/8/8/4K3 w - - 0 1",
    "7k/8/8/8/8/8/8/K7 b - - 0 1",
    "rnbq1bnr/ppppkppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQ - 2 3",
]


def features(placement, perspective):
    """Sorted feature indices of one perspective, computed from scratch."""
    board = {}
    rank, file = 7, 0
    for ch in placement:
        if ch == "/":
            rank -= 1
            file = 0
        elif ch.isdigit():
            file += int(ch)
        else:
            board[rank * 8 + file] = KIND[ch]
            file += 1
    out = []
    for square, kind in board.items():
        relative = square if perspective == 0 else square ^ 56
        out.append(kind * 64 + relative)
    return sorted(out)


def run_engine(fens):
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "fens.txt")
        with open(path, "w", encoding="ascii") as handle:
            handle.write("\n".join(fens) + "\n")
        proc = subprocess.run([EXE, "nnue", "--features", "--input", path],
                              capture_output=True, text=True, timeout=60)
    if proc.returncode != 0:
        sys.exit(f"engine failed: {proc.returncode}\n{proc.stderr}")
    return [line for line in proc.stdout.splitlines() if ":" in line]


def main():
    lines = run_engine(FENS)
    if len(lines) != 2 * len(FENS):
        sys.exit(f"expected {2 * len(FENS)} feature lines, got {len(lines)}")
    failures = 0
    for index, fen in enumerate(FENS):
        placement = fen.split()[0]
        for perspective in (0, 1):
            line = lines[2 * index + perspective]
            tag, _, payload = line.partition(":")
            if tag != str(perspective):
                sys.exit(f"unexpected perspective tag {tag!r} for {fen}")
            got = [int(value) for value in payload.split(",") if value]
            want = features(placement, perspective)
            if got != want:
                failures += 1
                print(f"MISMATCH {fen} perspective {perspective}")
                print(f"  engine: {got}")
                print(f"  mirror: {want}")
    if failures:
        sys.exit(f"{failures} feature mismatches")
    print(f"feature differential: {len(FENS)} positions, 2 perspectives each, 0 mismatches")


if __name__ == "__main__":
    main()
