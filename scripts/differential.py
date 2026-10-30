#!/usr/bin/env python3
"""Compare legal move sets and per-move depth-2 counts with python-chess.

Requires optional `pip install chess==1.11.2`. Engine execution itself does not.
The seed, sample count, and executable are explicit for reproducibility.
"""
import argparse
import random
import subprocess
import sys
import time
try:
    import chess
except ImportError:
    sys.exit("Install the optional validation dependency: pip install chess==1.11.2")

CURATED = [
    "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1",
    "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1",
    "r3k2r/Pppp1ppp/1b3nbN/nP6/BBP1P3/q4N2/Pp1P2PP/R2Q1RK1 w kq - 0 1",
    "rnbq1k1r/pp1Pbppp/2p5/8/2B5/8/PPP1NnPP/RNBQK2R w KQ - 1 8",
    "k3r3/8/8/3pP3/8/8/8/4K3 w - d6 0 2",
    "7k/8/8/3pP3/4K3/8/8/8 w - d6 0 2",
    "n1n1n1nk/1P1P1P1P/8/8/8/8/p1p1p1p1/K1N1N1N1 w - - 0 1",
    # Synthetic impossible history, but checks EP can block a slider check.
    "5b1k/8/8/3pP3/1K6/8/8/8 w - d6 0 2",
]


def compare(executable, board):
    fen = board.fen(en_passant="fen")
    run = subprocess.run([executable, "perft", "2", "--fen", fen, "--divide"],
                         capture_output=True, text=True, timeout=10)
    if run.returncode:
        raise AssertionError(f"engine rejected {fen}: {run.stderr}")
    actual = {}
    total = None
    for line in run.stdout.splitlines():
        if ": " in line:
            move, value = line.split(": ", 1)
            actual[move] = int(value)
        elif line.startswith("nodes "):
            total = int(line.split()[1])
    expected = {}
    for m in list(board.legal_moves):
        board.push(m)
        expected[m.uci()] = board.legal_moves.count()
        board.pop()
    if actual != expected or total != sum(expected.values()):
        missing = expected.keys() - actual.keys()
        extra = actual.keys() - expected.keys()
        different = {k: (expected[k], actual[k]) for k in expected.keys() & actual.keys()
                     if expected[k] != actual[k]}
        raise AssertionError(f"FEN={fen}\nmissing={missing}\nextra={extra}\ncounts={different}\n"
                             f"expected total={sum(expected.values())}, actual={total}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("engine", help="path to the built StockBear executable")
    ap.add_argument("--samples", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=20261030)
    args = ap.parse_args()
    if args.samples < 1:
        ap.error("samples must be positive")
    randomizer = random.Random(args.seed)
    start = time.monotonic()
    for fen in CURATED:
        compare(args.engine, chess.Board(fen))
    count = 0
    board = chess.Board()
    while count < args.samples:
        if board.is_game_over() or board.ply() >= 180:
            board.reset()
        if board.ply() % 3 == 0:
            compare(args.engine, board)
            count += 1
        moves = list(board.legal_moves)
        if moves:
            board.push(randomizer.choice(moves))
        else:
            board.reset()
    print(f"PASS {count} seeded legal positions + {len(CURATED)} curated positions; "
          f"exact move sets and per-move depth-2 counts vs python-chess {chess.__version__}; "
          f"seed={args.seed}; seconds={time.monotonic()-start:.2f}")

if __name__ == "__main__":
    main()
