#!/usr/bin/env python3
"""Generate the two v0.1.0-dev6 decisive-confirmation opening suites.

Produces two FRESH, DISJOINT suites of 3300 paired openings each (batch A =
exp-0028, batch B = exp-0029), every final position excluded from ALL existing
suites in benchmarks/positions/ AND from the other decisive suite. Each master
suite is split into 6 immutable slice files of 550 openings, one per shard;
because tournament.py plays 2 colour-reversed games per opening and uses
`openings[(pair) % len(openings)]`, a 1100-game shard on its 550-opening slice
uses every opening exactly once -> no repeated opening positions within a batch.
6 shards x 1100 games = 6600 games per batch -> 3300 distinct opening clusters.

Seeds are fixed and this script + the generated suites are committed BEFORE any
decisive result is collected. Regenerate (should be byte-identical) with:
  .venv/bin/python scripts/dev6_decisive_openings.py
"""
import hashlib
from pathlib import Path
import random

import chess
from make_openings import draw

ROOT = Path(__file__).resolve().parents[1]
POSDIR = ROOT / "benchmarks" / "positions"
PLIES = 8
PAIRS = 3300
SHARDS = 6
PER_SHARD = PAIRS // SHARDS  # 550
BATCHES = [("exp0028", 2026110503), ("exp0029", 2026110504)]


def key(moves):
    board = chess.Board()
    for m in moves:
        board.push_uci(m)
    return " ".join(board.fen().split()[:4])


def main():
    # Exclude every position used by any pre-existing suite, but NOT the suites
    # this script itself generates (exp0028/exp0029) so re-running it is
    # byte-identical regardless of a previous run's output files.
    excluded = set()
    excluded_files = []
    for path in sorted(POSDIR.glob("openings*.txt")):
        if path.name.startswith(("openings_exp0028", "openings_exp0029")):
            continue
        excluded_files.append(path.name)
        for line in path.read_text().splitlines():
            if not line.startswith("#") and "|" in line:
                excluded.add(key(line.split("|", 1)[1].split()))
    seen = set(excluded)
    manifest = {"plies": PLIES, "pairs_per_batch": PAIRS, "shards_per_batch": SHARDS,
                "openings_per_shard": PER_SHARD, "excluded_from": excluded_files,
                "batches": []}
    for name, seed in BATCHES:
        rng = random.Random(seed)
        lines = [f"# {name} decisive confirmation: seed {seed}, {PAIRS} paired openings, {PLIES} plies",
                 "# Names cluster distinct openings; final positions deduplicated.",
                 "# Excludes ALL earlier suites and the other decisive suite."]
        local = []
        for i in range(PAIRS):
            while True:
                moves = draw(rng, PLIES)
                final = key(moves)
                if final not in seen:
                    break
            seen.add(final)  # disjoint across the two batches too
            fam = " ".join(moves[:4])
            local.append(f"{name.upper()} {i + 1:04d} ({fam})|{' '.join(moves)}")
        lines += local
        master = POSDIR / f"openings_{name}_confirmation.txt"
        master.write_text("\n".join(lines) + "\n")
        master_sha = hashlib.sha256(master.read_bytes()).hexdigest()
        slices = []
        for s in range(SHARDS):
            chunk = local[s * PER_SHARD:(s + 1) * PER_SHARD]
            assert len(chunk) == PER_SHARD
            sp = POSDIR / f"openings_{name}_shard{s + 1:02d}.txt"
            sp.write_text("\n".join(chunk) + "\n")
            slices.append({"file": sp.name,
                           "sha256": hashlib.sha256(sp.read_bytes()).hexdigest(),
                           "openings": len(chunk)})
        rec = {"batch": name, "seed": seed, "master": master.name,
               "master_sha256": master_sha, "pairs": PAIRS, "slices": slices}
        manifest["batches"].append(rec)
        print(f"{name}: master sha256={master_sha} slices={len(slices)}")
    import json
    (ROOT / "benchmarks" / "dev6-baseline" / "decisive_suites.json").write_text(
        json.dumps(manifest, indent=2) + "\n")
    print("wrote benchmarks/dev6-baseline/decisive_suites.json")


if __name__ == "__main__":
    main()
