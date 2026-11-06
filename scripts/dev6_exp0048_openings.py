#!/usr/bin/env python3
"""Generate exp-0048's FRESH, DISJOINT bullet-corpus opening suite.

Commit and run BEFORE ANY exp-0048 corpus game. Seed 2026110601, 3,000 8-ply
openings (played twice with reversed colours = 6,000 self-play games), rejecting
every final position present in ANY earlier committed suite. This corpus is for
EVALUATOR FITTING / accuracy measurement only; it is never pooled with any
strength-match suite and never reused as a decisive batch suite. Regenerate
byte-identically with:
    python3 scripts/dev6_exp0048_openings.py
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
SEED = 2026110601
COUNT = 3000
PLIES = 8
PREFIX = "openings_exp0048_corpus"
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
        lines.append(f"EXP0048C {i + 1:04d} ({fam})|{' '.join(moves)}")
    assert len({key(l.split("|", 1)[1].split()) for l in lines}) == COUNT
    header = [
        f"# exp-0048 evaluator-fitting corpus: seed {SEED}, {COUNT} openings, {PLIES} plies",
        "# ZERO exact final-position overlap with ALL earlier committed suites.",
        "# For evaluator fitting/accuracy only; NEVER a decisive strength batch.",
    ]
    master = POS / f"{PREFIX}.txt"
    master.write_text("\n".join(header + lines) + "\n")
    # Shard slices for isolated-runner generation (disjoint, contiguous).
    slices: dict[str, str] = {}
    per = COUNT // SHARDS
    for s in range(SHARDS):
        chunk = lines[s * per:(s + 1) * per]
        p = POS / f"{PREFIX}_s{s:02d}.txt"
        p.write_text("\n".join(header + chunk) + "\n")
        slices[f"s{s:02d}"] = hashlib.sha256(p.read_bytes()).hexdigest()
    meta = {"seed": SEED, "count": COUNT, "plies": PLIES, "shards": SHARDS,
            "disjoint_overlap": 0, "purpose": "evaluator-fitting-only",
            "excluded_file_count": len(excluded_files),
            "excluded_positions": len(excluded),
            "master_sha256": hashlib.sha256(master.read_bytes()).hexdigest(),
            "slices": slices}
    (BASE / "exp0048_corpus_suites.json").write_text(json.dumps(meta, indent=2) + "\n")
    print(f"seed={SEED} count={COUNT} excluded_files={len(excluded_files)} "
          f"excluded_positions={len(excluded)} overlap=0 shards={SHARDS}")

    # Diagnostic-screen suites (prereg §6): drawn from the SAME RNG stream
    # immediately after the corpus openings, so they are disjoint from the
    # corpus, from every earlier suite, and from each other. The corpus files
    # and metadata above are final before this point and never change.
    screen_prefix = "openings_exp0048_screen"
    screen_lines: list[str] = []
    for i in range(1000):
        while True:
            moves = draw(rng, PLIES)
            k = key(moves)
            if k not in seen:
                break
        seen.add(k)
        fam = " ".join(moves[:4])
        screen_lines.append(f"EXP0048S {i + 1:04d} ({fam})|{' '.join(moves)}")
    screen_header = [
        f"# exp-0048 diagnostic screen: seed {SEED} (same stream, after corpus), {PLIES} plies",
        "# ZERO overlap with all earlier suites, the exp-0048 corpus, and each other.",
        "# Diagnostic ONLY (2 x 1000 games); never a decisive Gate-1 batch.",
    ]
    screen_slices: dict[str, str] = {}
    for name, chunk in (("batchA", screen_lines[:500]), ("batchB", screen_lines[500:])):
        assert len(chunk) == 500
        p = POS / f"{screen_prefix}_{name}.txt"
        p.write_text("\n".join(screen_header + chunk) + "\n")
        screen_slices[name] = hashlib.sha256(p.read_bytes()).hexdigest()
    screen_meta = {"seed": SEED, "count": 1000, "plies": PLIES,
                   "purpose": "diagnostic-screen-only", "disjoint_overlap": 0,
                   "slices": screen_slices}
    (BASE / "exp0048_screen_suites.json").write_text(json.dumps(screen_meta, indent=2) + "\n")
    print(f"screen: 2 x 500 openings, overlap=0 (corpus + {len(excluded_files)} earlier files)")


if __name__ == "__main__":
    main()
