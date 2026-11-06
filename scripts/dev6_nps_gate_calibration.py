#!/usr/bin/env python3
"""A/A calibration of the frozen NPS cost gate (instrument validation ONLY).

WHY THIS EXISTS
---------------
exp-0049's cost gate reported median ratio 0.93931 (a ~6% slowdown) while the
CHAMPION arm varied 19.2% across repetitions against ITSELF -- same binary, same
options. A gate whose subject noise exceeds its decision band cannot support the
verdict it prints. exp-0048 measured 1.00967 on the same mechanism.

This script measures the instrument's FALSE-REJECT RATE by running the frozen
protocol with BOTH ARMS IDENTICAL (champion vs champion, no PST anywhere). The
true ratio is exactly 1.0 by construction, so every FAIL is a false reject.

SCOPE -- READ BEFORE USING THE OUTPUT
-------------------------------------
* This does NOT re-run, re-score or reopen exp-0049. exp-0049 is CLOSED NEGATIVE
  on its ACCURACY gate, which fails independently of any timing measurement.
  Re-rolling a closed experiment's timing until it looked better is exactly the
  selective measurement the preregistrations forbid, and is not done here.
* Its only legitimate use is to decide WHERE and HOW a FUTURE candidate's cost
  gate must be measured, and that decision must be frozen in that candidate's
  prereg BEFORE its corpus exists.
* A/A passes do not license claiming any candidate is free per node.

Protocol under test is the frozen one, unchanged: `bench --nodes N --hash 16
--params <champion>`, one fresh process per arm per repetition, >=3 reps in the
order A,B / B,A / A,B, position included iff BOTH arms hit exactly N nodes, the
included set identical across reps and >= half the suite, statistic
median(candidate nps) / median(champion nps), band [0.97, 1.03].
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import statistics
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHAMPION_PARAMS = "research-data/params_abc.txt"
BAND = (0.97, 1.03)


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def run_arm(engine: str, nodes: int, hash_mb: int, tag: str, out: Path) -> list[dict]:
    """One fresh process, champion config, NO PST. Identical for both arms."""
    cmd = [engine, "bench", "--nodes", str(nodes), "--hash", str(hash_mb),
           "--params", str(ROOT / CHAMPION_PARAMS)]
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=1800)
    assert r.returncode == 0, f"bench failed: {r.stderr[-2000:]}"
    (out / f"bench_{tag}.csv").write_text(r.stdout)
    lines = r.stdout.splitlines()
    header = next(l for l in lines if l.startswith("name,"))
    body = [l for l in lines if l.startswith('"')]
    rows = list(csv.DictReader(io.StringIO(header + "\n" + "\n".join(body))))
    assert rows, "no bench rows parsed"
    return [{"position": x["name"], "nodes": int(x["nodes"]),
             "time_us": int(x["time_us"])} for x in rows]


def aggregate(rows_a: list[dict], rows_b: list[dict], nodes: int) -> dict:
    """Frozen structural inclusion rule and nps = sum(nodes) / sum(time_us)."""
    assert [r["position"] for r in rows_a] == [r["position"] for r in rows_b]
    included, excluded = [], []
    for a, b in zip(rows_a, rows_b):
        if a["nodes"] == nodes and b["nodes"] == nodes:
            included.append(a["position"])
        else:
            excluded.append({"position": a["position"],
                             "nodes_a": a["nodes"], "nodes_b": b["nodes"]})
    assert len(included) * 2 >= len(rows_a), "included set below half the suite"
    keep = set(included)
    sa = [r for r in rows_a if r["position"] in keep]
    sb = [r for r in rows_b if r["position"] in keep]
    nps_a = sum(r["nodes"] for r in sa) / (sum(r["time_us"] for r in sa) / 1e6)
    nps_b = sum(r["nodes"] for r in sb) / (sum(r["time_us"] for r in sb) / 1e6)
    return {"included": included, "excluded": excluded,
            "nps_a": nps_a, "nps_b": nps_b,
            "node_counts_bit_identical": all(
                a["nodes"] == b["nodes"] for a, b in zip(rows_a, rows_b))}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--nodes", type=int, default=300000)
    ap.add_argument("--hash", type=int, default=16)
    ap.add_argument("--reps", type=int, default=3,
                    help="repetitions per gate evaluation (frozen protocol: 3)")
    ap.add_argument("--evaluations", type=int, default=5,
                    help="independent repetitions of the WHOLE gate")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    engine = str(Path(a.engine).resolve())

    evaluations = []
    for e in range(1, a.evaluations + 1):
        reps, nps_a, nps_b = [], [], []
        reference_set = None
        for i in range(1, a.reps + 1):
            order = ["a", "b"] if i % 2 else ["b", "a"]
            got = {}
            for arm in order:
                got[arm] = run_arm(engine, a.nodes, a.hash, f"e{e}_r{i}_{arm}", out)
            agg = aggregate(got["a"], got["b"], a.nodes)
            if reference_set is None:
                reference_set = agg["included"]
            assert agg["included"] == reference_set, "included set drifted across reps"
            nps_a.append(agg["nps_a"])
            nps_b.append(agg["nps_b"])
            reps.append({"repetition": i, "order": order, **agg})
        ratio = statistics.median(nps_b) / statistics.median(nps_a)
        passed = BAND[0] <= ratio <= BAND[1]
        ev = {"evaluation": e, "ratio": ratio, "passed": passed,
              "median_of_per_rep_ratios": statistics.median(
                  [r["nps_b"] / r["nps_a"] for r in reps]),
              "arm_a_nps": nps_a, "arm_b_nps": nps_b,
              "arm_a_self_spread": max(nps_a) / min(nps_a) - 1.0,
              "arm_b_self_spread": max(nps_b) / min(nps_b) - 1.0,
              "included_positions": reference_set, "reps": reps}
        evaluations.append(ev)
        print(f"evaluation {e}: ratio {ratio:.5f} "
              f"{'PASS' if passed else 'FALSE REJECT'}  "
              f"(arm A self-spread {ev['arm_a_self_spread']:.1%})", flush=True)

    fails = [e for e in evaluations if not e["passed"]]
    ratios = [e["ratio"] for e in evaluations]
    spreads = [max(e["arm_a_self_spread"], e["arm_b_self_spread"]) for e in evaluations]
    report = {
        "purpose": "A/A instrument calibration of the frozen NPS cost gate",
        "scope_warning": (
            "Instrument validation ONLY. Does NOT re-run or reopen exp-0049, which is "
            "CLOSED NEGATIVE on its accuracy gate independently of timing. Output may "
            "only inform how a FUTURE candidate's cost gate is measured, frozen in that "
            "candidate's prereg before its corpus exists."),
        "true_ratio_by_construction": 1.0,
        "engine_sha256": sha(Path(engine)),
        "champion_params_sha256": sha(ROOT / CHAMPION_PARAMS),
        "nodes_per_position": a.nodes, "hash_mb": a.hash, "threads": 1,
        "reps_per_evaluation": a.reps, "evaluations": a.evaluations,
        "band": list(BAND),
        "false_rejects": len(fails),
        "false_reject_rate": len(fails) / len(evaluations),
        "ratio_min": min(ratios), "ratio_max": max(ratios),
        "ratio_median": statistics.median(ratios),
        "max_arm_self_spread": max(spreads),
        "median_arm_self_spread": statistics.median(spreads),
        "evaluations_detail": evaluations,
    }
    # Minimum detectable effect: an instrument cannot resolve a band narrower
    # than its own A/A scatter. Report the observed half-range as a floor.
    report["observed_aa_half_range"] = (max(ratios) - min(ratios)) / 2.0
    report["band_half_width"] = (BAND[1] - BAND[0]) / 2.0
    report["band_resolvable_on_this_host"] = (
        report["observed_aa_half_range"] <= report["band_half_width"] and not fails)
    (out / "CALIBRATION.json").write_text(json.dumps(report, indent=2) + "\n")
    (out / "SHA256SUMS.txt").write_text(
        f"{sha(out / 'CALIBRATION.json')}  CALIBRATION.json\n")
    print(json.dumps({k: report[k] for k in (
        "false_rejects", "false_reject_rate", "ratio_min", "ratio_max",
        "max_arm_self_spread", "observed_aa_half_range", "band_half_width",
        "band_resolvable_on_this_host")}, indent=2))
    return None


if __name__ == "__main__":
    sys.exit(main())
