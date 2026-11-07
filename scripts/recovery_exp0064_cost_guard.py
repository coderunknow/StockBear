#!/usr/bin/env python3
"""exp-0064 frozen search-cost regression guard.

The policy's evaluate()-cost instrument cannot exercise a search switch (this
candidate adds no evaluation work), so the preregistered substitute is a
fixed-depth same-binary wall-time A/B on the 250-position diagnostic corpus.

Requirement (frozen, never relaxed): median(ON)/median(OFF) <= 1.10 at BOTH
depth 5 and depth 7, with A/A machine-noise spread < 0.10. This is a REGRESSION
GUARD, not a benefit claim; only fixed-time games measure strength.

Block order per pass: OFF, OFF, ON, ON  (3 passes => 12 runs per depth).
"""
from __future__ import annotations
import hashlib
import json
import statistics
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / "build-rel/searchcost"
PARAMS = ROOT / "research-data/params_exp0055_race.txt"
EPD = ROOT / "benchmarks/positions/diagnostic_exp0064_ttid.epd"
PASSES = 3
DEPTHS = (5, 7)
LIMIT = 1.10
SPREAD_LIMIT = 0.10


def measure(depth: int, arm: str) -> tuple[float, int]:
    r = subprocess.run([str(PROBE), str(PARAMS), str(EPD), str(depth), arm, "16"],
                       capture_output=True, text=True, check=True)
    toks = r.stdout.split()
    return float(toks[toks.index("ms") + 1]), int(toks[toks.index("nodes") + 1])


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    out = {"guard": "fixed_depth_wall_time_ab", "limit": LIMIT,
           "spread_limit": SPREAD_LIMIT, "passes": PASSES, "depths": list(DEPTHS),
           "positions": 250, "hash_mb": 16,
           "params_sha256": sha(PARAMS), "corpus_sha256": sha(EPD),
           "probe_sha256": sha(PROBE), "results": {}}
    ok = True
    for depth in DEPTHS:
        off, on, spreads = [], [], []
        nodes_off, nodes_on = [], []
        for _ in range(PASSES):
            a, na = measure(depth, "off")
            b, nb = measure(depth, "off")
            c, nc = measure(depth, "on")
            d, nd = measure(depth, "on")
            off += [a, b]
            on += [c, d]
            nodes_off += [na, nb]
            nodes_on += [nc, nd]
            spreads.append(abs(a - b) / ((a + b) / 2.0))
        ratio = statistics.median(on) / statistics.median(off)
        spread = statistics.median(spreads)
        node_ratio = statistics.median(nodes_on) / statistics.median(nodes_off)
        passed = ratio <= LIMIT and spread < SPREAD_LIMIT
        ok = ok and passed
        out["results"][str(depth)] = {
            "off_ms": off, "on_ms": on, "median_off_ms": statistics.median(off),
            "median_on_ms": statistics.median(on), "aa_spread": spread,
            "time_ratio_on_over_off": ratio, "node_ratio_on_over_off": node_ratio,
            "nodes_off": nodes_off, "nodes_on": nodes_on, "pass": passed}
        print(f"depth {depth}: time ratio {ratio:.6f} (limit {LIMIT}), "
              f"A/A spread {spread:.6f}, node ratio {node_ratio:.6f} -> "
              f"{'PASS' if passed else 'FAIL'}", flush=True)
    out["verdict"] = "PASS" if ok else "FAIL"
    out["strength_claim"] = False
    dest = ROOT / "benchmarks/recovery/exp0064_search_cost_guard.json"
    dest.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    print("verdict", out["verdict"])
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
