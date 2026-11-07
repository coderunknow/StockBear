#!/usr/bin/env python3
"""Generate exp-0055's FRESH, DISJOINT Tier-1 opening suites.

Committed and run BEFORE ANY exp-0055 game. Seed 2026110655, 1,900 8-ply
openings, rejecting every final position in ANY earlier committed suite and
every earlier draw. All earlier experiments are NEVER pooled or reused; this
includes exp-0051's suites, which are excluded by the glob below. exp-0055 SCREENS the
passed-pawn promotion-race INCREMENT on top of the CONFIRMED exp-0053/0054
threat term, by same-binary ablation. No earlier games are pooled.
Regenerate byte-identically with:
    python3 scripts/dev6_exp0055_openings.py
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
SEED = 2026110655
COUNT = 1900
PLIES = 8
SLICES = [("stage0", 200), ("null", 200), ("batchA", 750), ("batchB", 750)]
PREFIX = "openings_exp0055"


def key(moves: list[str]) -> str:
    board = chess.Board()
    for m in moves:
        board.push_uci(m)
    return " ".join(board.fen().split()[:4])


def main() -> None:
    excluded: set[str] = set()
    excluded_files: list[str] = []
    for path in sorted(POS.glob("openings*.txt")):
        if path.name.startswith(PREFIX):
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
        lines.append(f"EXP0055 {i + 1:04d} ({fam})|{' '.join(moves)}")
    assert len({key(l.split("|", 1)[1].split()) for l in lines}) == COUNT
    header = [
        f"# exp-0055: seed {SEED}, {COUNT} paired openings, {PLIES} plies",
        "# ZERO exact final-position overlap with ALL earlier committed suites;",
        "# four mutually disjoint slices. Earlier experiments NEVER pooled.",
    ]
    master = POS / f"{PREFIX}.txt"
    master.write_text("\n".join(header + lines) + "\n")
    slices: dict[str, str] = {}
    off = 0
    for name, n in SLICES:
        chunk = lines[off:off + n]
        off += n
        assert len(chunk) == n
        p = POS / f"{PREFIX}_{name}.txt"
        p.write_text("\n".join(header + chunk) + "\n")
        slices[name] = hashlib.sha256(p.read_bytes()).hexdigest()
    assert off == COUNT
    meta = {"seed": SEED, "count": COUNT, "disjoint_overlap": 0,
            "no_pooling_with_earlier_experiments": True,
            "excluded_file_count": len(excluded_files),
            "excluded_positions": len(excluded),
            "master_sha256": hashlib.sha256(master.read_bytes()).hexdigest(),
            "slices": slices}
    (BASE / "exp0055_suites.json").write_text(json.dumps(meta, indent=2) + "\n")
    print(f"seed={SEED} count={COUNT} excluded_files={len(excluded_files)} "
          f"excluded_positions={len(excluded)} overlap=0")
    for k, v in slices.items():
        print(f"  {k}: {v[:16]}")


if __name__ == "__main__":
    main()
