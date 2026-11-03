#!/usr/bin/env python3
"""Generate the pre-registered dev7 confirmation suite without engine scores.

Deduplicate final chess positions and exclude positions used by the dev4
exploratory suite and the dev5 confirmation suite. Names identify canonical
four-ply opening families for clustered analysis. Seed 2026110307 is fixed and
committed BEFORE any dev6 candidate is run on this suite.
"""
import hashlib
from pathlib import Path
import random

import chess
from make_openings import draw

ROOT = Path(__file__).resolve().parents[1]


def key(moves):
    board = chess.Board()
    for move in moves:
        board.push_uci(move)
    return " ".join(board.fen().split()[:4])


def main():
    excluded = set()
    for name in ("openings_dev4.txt", "openings_dev5_confirmation.txt", "openings_dev6_confirmation.txt"):
        path = ROOT / "benchmarks/positions" / name
        if not path.exists():
            continue
        for line in path.read_text().splitlines():
            if not line.startswith("#") and "|" in line:
                excluded.add(key(line.split("|", 1)[1].split()))
    rng = random.Random(2026110307)
    lines = ["# dev7 confirmation: seed 2026110307, 2200 paired openings, 8 plies",
             "# Names cluster canonical four-ply families; final positions deduplicated.",
             "# Excludes openings_dev4.txt, openings_dev5_confirmation.txt and openings_dev6_confirmation.txt positions."]
    seen = set(excluded)
    for i in range(2200):
        while True:
            moves = draw(rng, 8)
            final = key(moves)
            if final not in seen:
                break
        seen.add(final)
        fam = " ".join(moves[:4])
        lines.append(f"Dev7 {i + 1:04d} ({fam})|{' '.join(moves)}")
    out = ROOT / "benchmarks/positions/openings_dev7_confirmation.txt"
    out.write_text("\n".join(lines) + "\n")
    digest = hashlib.sha256(out.read_bytes()).hexdigest()
    print(f"wrote {out} lines={len(lines)} sha256={digest}")


if __name__ == "__main__":
    main()
