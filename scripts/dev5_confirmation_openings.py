#!/usr/bin/env python3
"""Generate the pre-registered dev5 confirmation suite without engine scores.

Deduplicate final chess positions and exclude positions in the exploratory suite.
Names identify canonical four-ply opening families for clustered analysis.
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
    old = ROOT / "benchmarks/positions/openings_dev4.txt"
    excluded = set()
    for line in old.read_text().splitlines():
        if not line.startswith("#") and "|" in line:
            excluded.add(key(line.split("|", 1)[1].split()))
    rng = random.Random(2026110205)
    lines = ["# dev5 confirmation: seed 2026110205, 550 paired openings, 8 plies",
             "# Names cluster canonical four-ply families; final positions deduplicated."]
    seen = set(excluded)
    for _ in range(550):
        while True:
            moves = draw(rng, 8)
            final = key(moves)
            if final not in seen:
                break
        seen.add(final)
        family = hashlib.sha256(key(moves[:4]).encode()).hexdigest()
        lines.append(f"Family {family} | {' '.join(moves)}")
    out = ROOT / "benchmarks/positions/openings_dev5_confirmation.txt"
    out.write_text("\n".join(lines) + "\n")
    print(out)
    print("sha256", hashlib.sha256(out.read_bytes()).hexdigest())
    print("unique final positions", len(seen) - len(excluded))
    print("families", len({line.split("|")[0].strip() for line in lines[2:]}))


if __name__ == "__main__":
    main()
