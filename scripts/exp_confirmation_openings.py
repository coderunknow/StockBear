#!/usr/bin/env python3
"""Generate a pre-registered exp-NNNN confirmation opening suite.

Deduplicate final chess positions and exclude every opening position used by
ANY existing suite in benchmarks/positions/ (dev4 exploratory, dev5/6/7
confirmations, and any earlier exp suites), so a confirmation suite is always
previously untouched. Names identify canonical four-ply opening families for
clustered analysis. The seed is fixed and this file is committed BEFORE any
candidate is run on the generated suite.

Usage:
    python3 scripts/exp_confirmation_openings.py --name exp0001 --seed 2026110501 --count 2200
"""
import argparse
import hashlib
from pathlib import Path
import random

import chess
from make_openings import draw

ROOT = Path(__file__).resolve().parents[1]
POSDIR = ROOT / "benchmarks/positions"


def key(moves):
    board = chess.Board()
    for move in moves:
        board.push_uci(move)
    return " ".join(board.fen().split()[:4])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True, help="e.g. exp0001 (used in the file name)")
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--count", type=int, default=2200)
    ap.add_argument("--plies", type=int, default=8)
    args = ap.parse_args()

    excluded = set()
    excluded_files = []
    for path in sorted(POSDIR.glob("openings*.txt")):
        excluded_files.append(path.name)
        for line in path.read_text().splitlines():
            if not line.startswith("#") and "|" in line:
                excluded.add(key(line.split("|", 1)[1].split()))
    rng = random.Random(args.seed)
    lines = [f"# {args.name} confirmation: seed {args.seed}, {args.count} paired openings, {args.plies} plies",
             "# Names cluster canonical four-ply families; final positions deduplicated.",
             "# Excludes: " + ", ".join(excluded_files)]
    seen = set(excluded)
    for i in range(args.count):
        while True:
            moves = draw(rng, args.plies)
            final = key(moves)
            if final not in seen:
                break
        seen.add(final)
        fam = " ".join(moves[:4])
        lines.append(f"{args.name.upper()} {i + 1:04d} ({fam})|{' '.join(moves)}")
    out = POSDIR / f"openings_{args.name}_confirmation.txt"
    out.write_text("\n".join(lines) + "\n")
    digest = hashlib.sha256(out.read_bytes()).hexdigest()
    print(f"wrote {out} lines={len(lines)} sha256={digest}")


if __name__ == "__main__":
    main()
