#!/usr/bin/env python3
"""Generate exp-0045's FRESH, DISJOINT Tier-1 opening suites.

Committed and run BEFORE any exp-0045 evaluation game. Seed 2026120501,
1,400 8-ply openings, rejecting every final position in ANY earlier committed
suite (including exp-0044 screen + confirmation) and every earlier draw in
this run. Splits into stage0=200, null=200, batchA=500, batchB=500.
Regenerate byte-identically with:
    .venv/bin/python scripts/dev6_exp0045_openings.py
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
SEED = 2026120501
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
        if path.name.startswith("openings_exp0045"):
            continue
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
        lines.append(f"EXP0045 {i + 1:04d} ({fam})|{' '.join(moves)}")
    assert len({key(l.split("|", 1)[1].split()) for l in lines}) == COUNT
    header = [
        f"# exp-0045 Tier-1: seed {SEED}, {COUNT} paired openings, {PLIES} plies",
        "# ZERO exact final-position overlap with ALL earlier committed suites;",
        "# stage0 / null / batchA / batchB slices are mutually disjoint.",
    ]
    master = POS / "openings_exp0045.txt"
    master.write_text("\n".join(header + lines) + "\n")
    slices: dict[str, str] = {}
    off = 0
    for name, n in SLICES:
        chunk = lines[off:off + n]
        off += n
        assert len(chunk) == n
        p = POS / f"openings_exp0045_{name}.txt"
        p.write_text("\n".join(header + chunk) + "\n")
        slices[name] = hashlib.sha256(p.read_bytes()).hexdigest()
    assert off == COUNT
    meta = {"seed": SEED, "count": COUNT, "disjoint_overlap": 0,
            "excluded_file_count": len(excluded_files),
            "excluded_positions": len(excluded),
            "master_sha256": hashlib.sha256(master.read_bytes()).hexdigest(),
            "slices": slices}
    (BASE / "exp0045_suites.json").write_text(json.dumps(meta, indent=2) + "\n")
    print(f"seed={SEED} count={COUNT} excluded_files={len(excluded_files)} "
          f"excluded_positions={len(excluded)} overlap=0")
    for k, v in slices.items():
        print(f"  {k}: {v[:16]}")


if __name__ == "__main__":
    main()
