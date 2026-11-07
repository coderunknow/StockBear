#!/usr/bin/env python3
"""Fixed-depth liveness probe for a gated evaluation term.

A term can be perfectly correct and still be DEAD: never applied, gated off, or
cancelled by the taper. Correctness tests cannot detect that. This probe searches
a fixed set of positions at a fixed depth with the parameter OFF and ON in the
SAME binary and checks that the search tree actually changes.

This is a TREE-CHANGE PROXY ONLY. It is not a strength measurement and not a
speed measurement: node counts at fixed depth move for many reasons, and a
bestmove change says nothing about whether the new move is better.

The engine's UCI does not emit per-search node counts, so this drives a compiled
probe (scripts/probes/liveness.cpp) against the real Search API. The probe loads
each parameter file through the real loader and treats a failed load as a hard
error, because EvalParams otherwise silently keeps the previous table and would
fake a result.

Usage: recovery_liveness.py --probe BIN --a OFF_PARAMS --b ON_PARAMS \
           --positions EPD --depth 10 --json out.json
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe", required=True)
    ap.add_argument("--a", required=True, help="parameter file with the term OFF")
    ap.add_argument("--b", required=True, help="parameter file with the term ON")
    ap.add_argument("--positions", required=True)
    ap.add_argument("--depth", type=int, default=10)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--json")
    args = ap.parse_args()

    fens = [l.strip() for l in Path(args.positions).read_text().splitlines() if l.strip()]
    if args.limit:
        fens = fens[: args.limit]
    r = subprocess.run([args.probe, args.a, args.b, args.positions, str(args.depth)],
                       capture_output=True, text=True, timeout=3600)
    if r.returncode != 0:
        raise SystemExit(f"probe failed ({r.returncode}):\n{r.stderr[-1500:]}")
    if r.stderr.count("EvalParams loaded:") != 2:
        raise SystemExit(f"expected 2 load proofs, got:\n{r.stderr[:800]}")
    lines = [l.split() for l in r.stdout.splitlines() if l.strip()]
    if len(lines) != len(fens):
        raise SystemExit(f"probe returned {len(lines)} rows for {len(fens)} positions")
    live = changed = 0
    n_off = n_on = 0
    rows = []
    for fen, parts in zip(fens, lines):
        off = {"nodes": int(parts[0]), "bestmove": parts[2]}
        on = {"nodes": int(parts[1]), "bestmove": parts[3]}
        is_live = off["nodes"] != on["nodes"]
        live += int(is_live)
        changed += int(off["bestmove"] != on["bestmove"])
        n_off += off["nodes"]
        n_on += on["nodes"]
        rows.append({"fen": fen, "off": off, "on": on, "tree_changed": is_live})
        print(f"{'LIVE' if is_live else 'dead'}  nodes {off['nodes']:>9} -> {on['nodes']:>9}"
              f"  {off['bestmove']} -> {on['bestmove']}")

    out = {
        "fixed_depth": args.depth,
        "positions": len(fens),
        "positions_live": live,
        "bestmoves_changed": changed,
        "nodes_off": n_off,
        "nodes_on": n_on,
        "total_node_delta_pct": round((n_on - n_off) / n_off * 100, 2) if n_off else None,
        "a_params": args.a,
        "b_params": args.b,
        "load_proof": "both parameter files confirmed loaded by the probe",
        "note": "tree-change proxy only; NOT a strength or speed measurement",
        "per_position": rows,
    }
    print(f"\nliveness: {live}/{len(fens)} positions changed the search tree; "
          f"{changed} bestmoves changed")
    if live == 0:
        print("VERDICT: DEAD MECHANISM -- do not proceed to games")
    else:
        print("VERDICT: LIVE")
    if args.json:
        Path(args.json).write_text(json.dumps(out, indent=2) + "\n")
    return 0 if live else 1


if __name__ == "__main__":
    raise SystemExit(main())
