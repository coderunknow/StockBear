#!/usr/bin/env python3
"""exp-0067 frozen per-node cost guard. ContinuationHistory=true in BOTH arms;
the JOINT aging of both graded tables varies. Fixed NODE budget isolates per-node overhead
(the real fixed-time risk); fixed-depth timing would confound it with tree size.
Requirement: ON/OFF <= 1.10 and A/A spread < 0.10. Regression gate, not Elo."""
from __future__ import annotations
import hashlib, json, statistics, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / "build-rel/nodecost"
PARAMS = ROOT / "research-data/params_exp0055_race.txt"
EPD = ROOT / "benchmarks/positions/diagnostic_exp0064_ttid.epd"
NODES, PASSES, LIMIT, SPREAD_LIMIT = 20000, 3, 1.10, 0.10


def measure(arm):
    r = subprocess.run([str(PROBE), str(PARAMS), str(EPD), str(NODES), arm,
                        "jointpersistence", "16"], capture_output=True, text=True, check=True)
    t = r.stdout.split()
    return float(t[t.index("ms") + 1]), int(t[t.index("nodes") + 1])


def main():
    sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
    off, on, spreads, noff, non = [], [], [], [], []
    for _ in range(PASSES):
        a, na = measure("off"); b, nb = measure("off")
        c, nc = measure("on");  d, nd = measure("on")
        off += [a, b]; on += [c, d]; noff += [na, nb]; non += [nc, nd]
        spreads.append(abs(a - b) / ((a + b) / 2.0))
    ratio = statistics.median(on) / statistics.median(off)
    spread = statistics.median(spreads)
    node_dev = max(abs(x - y) / ((x + y) / 2.0) for x, y in zip(noff, non))
    ok = ratio <= LIMIT and spread < SPREAD_LIMIT
    out = {"guard": "fixed_node_wall_time_ab", "switch": "PersistentHistory + PersistentContinuation (joint)",
           "feature_on_in_both_arms": "ContinuationHistory=true",
           "nodes_per_position": NODES, "positions": 250, "hash_mb": 16,
           "passes": PASSES, "limit": LIMIT, "spread_limit": SPREAD_LIMIT,
           "off_ms": off, "on_ms": on, "median_off_ms": statistics.median(off),
           "median_on_ms": statistics.median(on), "time_ratio_on_over_off": ratio,
           "aa_spread": spread, "nodes_off": noff, "nodes_on": non,
           "max_node_count_deviation": node_dev,
           "params_sha256": sha(PARAMS), "corpus_sha256": sha(EPD), "probe_sha256": sha(PROBE),
           "verdict": "PASS" if ok else "FAIL", "strength_claim": False}
    (ROOT / "benchmarks/recovery/exp0067_node_cost_guard.json").write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    print(f"time ratio {ratio:.6f} (limit {LIMIT}), A/A spread {spread:.6f}, "
          f"node-count deviation {node_dev:.6f} -> {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
