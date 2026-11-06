#!/usr/bin/env python3
"""Generate exp-0049's FRESH, DISJOINT bullet-corpus and screen opening suites.

Commit and run BEFORE ANY exp-0049 corpus game. Seed 2026110611, 3,000 8-ply
corpus openings (played twice with reversed colours = 6,000 self-play games)
plus 1,000 screen openings, rejecting every final position present in ANY
earlier committed suite -- INCLUDING the burned exp-0048 corpus and its unused
screen suites.

The exp-0048 corpus is BURNED: its holdout informed the exploratory L2 grid, so
it cannot serve as confirmatory data for this hypothesis. This suite exists
precisely so exp-0049 is tested on data its hyperparameters never saw.

Regenerate byte-identically with:
    python3 scripts/dev6_exp0049_openings.py
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
SEED = 2026110611
COUNT = 3000
SCREEN_COUNT = 1000
PLIES = 8
PREFIX = "openings_exp0049_corpus"
SCREEN_PREFIX = "openings_exp0049_screen"
SHARDS = 8


def key(moves: list[str]) -> str:
    board = chess.Board()
    for m in moves:
        board.push_uci(m)
    return " ".join(board.fen().split()[:4])


def main() -> None:
    excluded: set[str] = set()
    excluded_files: list[str] = []
    for path in sorted(POS.glob("openings*.txt")):
        if path.name.startswith(PREFIX) or path.name.startswith(SCREEN_PREFIX):
            continue
        excluded_files.append(path.name)
        for line in path.read_text().splitlines():
            if line and not line.startswith("#") and "|" in line:
                excluded.add(key(line.split("|", 1)[1].split()))
    # The burned exp-0048 suites must be in the exclusion set: this is the whole
    # point of a fresh corpus. Fail loudly if they somehow are not.
    assert any("exp0048_corpus" in f for f in excluded_files), \
        "exp-0048 corpus suites missing from the exclusion set"
    seen = set(excluded)
    rng = random.Random(SEED)

    def draw_unique(tag: str, i: int) -> str:
        while True:
            moves = draw(rng, PLIES)
            k = key(moves)
            if k not in seen:
                break
        seen.add(k)
        return f"{tag} {i + 1:04d} ({' '.join(moves[:4])})|{' '.join(moves)}"

    lines = [draw_unique("EXP0049C", i) for i in range(COUNT)]
    assert len({key(l.split("|", 1)[1].split()) for l in lines}) == COUNT
    header = [
        f"# exp-0049 evaluator-fitting corpus: seed {SEED}, {COUNT} openings, {PLIES} plies",
        "# ZERO exact final-position overlap with ALL earlier committed suites,",
        "# INCLUDING the burned exp-0048 corpus and its unused screen suites.",
        "# For evaluator fitting/accuracy only; NEVER a decisive strength batch.",
    ]
    master = POS / f"{PREFIX}.txt"
    master.write_text("\n".join(header + lines) + "\n")
    slices: dict[str, str] = {}
    per = COUNT // SHARDS
    for s in range(SHARDS):
        p = POS / f"{PREFIX}_s{s:02d}.txt"
        p.write_text("\n".join(header + lines[s * per:(s + 1) * per]) + "\n")
        slices[f"s{s:02d}"] = hashlib.sha256(p.read_bytes()).hexdigest()
    meta = {"seed": SEED, "count": COUNT, "plies": PLIES, "shards": SHARDS,
            "disjoint_overlap": 0, "purpose": "evaluator-fitting-only",
            "excludes_burned_exp0048_corpus": True,
            "excluded_file_count": len(excluded_files),
            "excluded_positions": len(excluded),
            "master_sha256": hashlib.sha256(master.read_bytes()).hexdigest(),
            "slices": slices}
    (BASE / "exp0049_corpus_suites.json").write_text(json.dumps(meta, indent=2) + "\n")
    print(f"seed={SEED} count={COUNT} excluded_files={len(excluded_files)} "
          f"excluded_positions={len(excluded)} overlap=0 shards={SHARDS}")

    screen_lines = [draw_unique("EXP0049S", i) for i in range(SCREEN_COUNT)]
    screen_header = [
        f"# exp-0049 diagnostic screen: seed {SEED} (same stream, after corpus), {PLIES} plies",
        "# ZERO overlap with all earlier suites, the exp-0049 corpus, and each other.",
        "# Diagnostic ONLY (2 x 1000 games); never a decisive Gate-1 batch.",
    ]
    screen_slices: dict[str, str] = {}
    for name, chunk in (("batchA", screen_lines[:500]), ("batchB", screen_lines[500:])):
        assert len(chunk) == 500
        p = POS / f"{SCREEN_PREFIX}_{name}.txt"
        p.write_text("\n".join(screen_header + chunk) + "\n")
        screen_slices[name] = hashlib.sha256(p.read_bytes()).hexdigest()
    (BASE / "exp0049_screen_suites.json").write_text(json.dumps(
        {"seed": SEED, "count": SCREEN_COUNT, "plies": PLIES,
         "purpose": "diagnostic-screen-only", "disjoint_overlap": 0,
         "slices": screen_slices}, indent=2) + "\n")
    print(f"screen: 2 x 500 openings, overlap=0 (corpus + {len(excluded_files)} earlier files)")


if __name__ == "__main__":
    main()
