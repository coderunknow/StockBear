#!/usr/bin/env python3
"""Independently verify an opening-suite family is fresh and internally disjoint.

This deliberately does NOT import or trust the generator. It re-derives every
final position from the raw move lists with python-chess and recomputes the
intersections and digests itself, so a bug in the generator's own bookkeeping
cannot produce a false PASS.

Usage:
    python3 scripts/recovery_verify_suites.py --prefix openings_exp0052 \
        --meta benchmarks/dev6-baseline/exp0052_suites.json \
        --json benchmarks/recovery/exp0052_suite_verification.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import chess

ROOT = Path(__file__).resolve().parents[1]
POS = ROOT / "benchmarks" / "positions"


def final_key(moves: list[str]) -> str:
    board = chess.Board()
    for m in moves:
        board.push_uci(m)
    # First four FEN fields: piece placement, side, castling, ep.
    return " ".join(board.fen().split()[:4])


def read_suite(path: Path) -> list[str]:
    keys = []
    for line in path.read_text().splitlines():
        if line and not line.startswith("#") and "|" in line:
            keys.append(final_key(line.split("|", 1)[1].split()))
    return keys


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prefix", required=True)
    ap.add_argument("--meta", required=True)
    ap.add_argument("--json")
    args = ap.parse_args()

    meta = json.loads((ROOT / args.meta).read_text())
    issues: list[str] = []

    # 1. Every earlier committed suite, re-derived from raw moves.
    earlier: dict[str, set[str]] = {}
    for path in sorted(POS.glob("openings*.txt")):
        if path.name.startswith(args.prefix):
            continue
        earlier[path.name] = set(read_suite(path))
    earlier_union = set().union(*earlier.values()) if earlier else set()

    # 2. The new master and slices, re-derived independently.
    master_path = POS / f"{args.prefix}.txt"
    master = read_suite(master_path)
    slices = {name: read_suite(POS / f"{args.prefix}_{name}.txt")
              for name in meta["slices"]}

    if len(master) != meta["count"]:
        issues.append(f"master count {len(master)} != declared {meta['count']}")
    if len(set(master)) != len(master):
        issues.append(f"master has {len(master) - len(set(master))} duplicate positions")

    # 3. Master vs every earlier suite (per-file and union).
    per_file = {n: len(set(master) & s) for n, s in earlier.items()}
    overlap = len(set(master) & earlier_union)
    if overlap:
        issues.append(f"{overlap} master positions overlap earlier committed suites")

    # 4. Slices must be mutually disjoint and exactly partition the master.
    names = list(slices)
    pair_overlap = {}
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            n = len(set(slices[a]) & set(slices[b]))
            pair_overlap[f"{a}/{b}"] = n
            if n:
                issues.append(f"slices {a} and {b} share {n} positions")
    concat = [k for name in names for k in slices[name]]
    if len(concat) != len(master) or set(concat) != set(master):
        issues.append("slices do not exactly partition the master suite")
    for name, keys in slices.items():
        if len(set(keys)) != len(keys):
            issues.append(f"slice {name} has internal duplicates")

    # 5. Digests recomputed from bytes, not copied from the generator.
    digest_ok = {}
    digest_ok["master"] = (
        hashlib.sha256(master_path.read_bytes()).hexdigest() == meta["master_sha256"])
    for name, want in meta["slices"].items():
        got = hashlib.sha256((POS / f"{args.prefix}_{name}.txt").read_bytes()).hexdigest()
        digest_ok[name] = got == want
    for name, ok in digest_ok.items():
        if not ok:
            issues.append(f"digest mismatch for {name}")

    result = {
        "prefix": args.prefix,
        "verifier": "independent; generator not imported",
        "master_positions": len(master),
        "earlier_files": len(earlier),
        "earlier_positions": len(earlier_union),
        "master_vs_earlier_overlap": overlap,
        "per_file_overlap_nonzero": {k: v for k, v in per_file.items() if v},
        "slice_pair_overlap": pair_overlap,
        "slices_partition_master": len(concat) == len(master) and set(concat) == set(master),
        "slice_sizes": {k: len(v) for k, v in slices.items()},
        "digests_verified": digest_ok,
        "issues": issues,
        "verdict": "PASS" if not issues else "FAIL",
    }
    text = json.dumps(result, indent=2) + "\n"
    if args.json:
        (ROOT / args.json).write_text(text)
    print(text)
    return 0 if not issues else 1


if __name__ == "__main__":
    raise SystemExit(main())
