#!/usr/bin/env python3
"""Generate exp-0044's FRESH, DISJOINT Tier-1 opening suites.

Committed and run BEFORE any exp-0044 evaluation game. Draws 1,400 8-ply
openings from a fixed seed, rejecting every final position already present in
any earlier committed suite (including exp-0043) and every position drawn
earlier in this run. Splits into stage0=200, null=200, batchA=500,
batchB=500; each slice has enough distinct openings for its colour-reversed
pair count and all four slices are mutually disjoint. Regenerate
byte-identically with:
    .venv/bin/python scripts/dev6_exp0044_openings.py
"""
from __future__ import annotations
import hashlib
import json
import random
from pathlib import Path
import chess
from make_openings import draw

ROOT = Path(__file__).resolve().parents[1]
POS = ROOT / "benchmarks" / "positions"
BASE = ROOT / "benchmarks" / "dev6-baseline"
SEED = 2026120301
COUNT = 1400
PLIES = 8
SLICES = [("stage0", 200), ("null", 200), ("batchA", 500), ("batchB", 500)]


def key(moves: list[str]) -> str:
    board = chess.Board()
    for m in moves:
        board.push_uci(m)
    return " ".join(board.fen().split()[:4])


def main() -> None:
    excluded: set[str] = set()
    excluded_files: list[str] = []
    for path in sorted(POS.glob("openings*.txt")):
        if path.name.startswith("openings_exp0044"):
            continue  # own outputs, so re-running is byte-identical
        excluded_files.append(path.name)
        for line in path.read_text().splitlines():
            if line and not line.startswith("#") and "|" in line:
                excluded.add(key(line.split("|", 1)[1].split()))
    seen = set(excluded)
    rng = random.Random(SEED)
    lines: list[str] = []
    for i in range(COUNT):
        while True:
            moves = draw(rng, PLIES)
            k = key(moves)
            if k not in seen:
                break
        seen.add(k)
        fam = " ".join(moves[:4])
        lines.append(f"EXP0044 {i + 1:04d} ({fam})|{' '.join(moves)}")
    assert len({key(l.split("|", 1)[1].split()) for l in lines}) == COUNT
    header = [
        f"# exp-0044 Tier-1: seed {SEED}, {COUNT} paired openings, {PLIES} plies",
        "# ZERO exact final-position overlap with all earlier committed suites;",
        "# stage0 / null / batchA / batchB slices are mutually disjoint.",
    ]
    master = POS / "openings_exp0044.txt"
    master.write_text("\n".join(header + lines) + "\n")
    slices: dict[str, str] = {}
    off = 0
    for name, n in SLICES:
        chunk = lines[off:off + n]
        off += n
        assert len(chunk) == n
        p = POS / f"openings_exp0044_{name}.txt"
        p.write_text("\n".join(header + chunk) + "\n")
        slices[name] = hashlib.sha256(p.read_bytes()).hexdigest()
    assert off == COUNT
    meta = {
        "seed": SEED, "count": COUNT, "disjoint_overlap": 0,
        "excluded_file_count": len(excluded_files),
        "excluded_positions": len(excluded),
        "master_sha256": hashlib.sha256(master.read_bytes()).hexdigest(),
        "slices": slices,
    }
    (BASE / "exp0044_suites.json").write_text(json.dumps(meta, indent=2) + "\n")
    print(f"seed={SEED} count={COUNT} excluded_files={len(excluded_files)} "
          f"excluded_positions={len(excluded)} overlap=0")
    for k, v in slices.items():
        print(f"  {k}: {v[:16]}")


if __name__ == "__main__":
    main()
