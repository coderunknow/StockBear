#!/usr/bin/env python3
"""Noise-resistant A/B cost probe for an evaluation change.

The shared sandbox produced 170-310 ns for the SAME binary in consecutive runs,
so a naive "run A, run B, compare means" comparison is unusable (this is the
defect that invalidated the earlier frozen NPS gate: 7/12 A/A false rejects).

Design used here instead:
  * ONE process links the engine core once and alternates A/B inside the same
    timing loop, many short blocks, so drift and scheduler noise hit both arms.
  * Reports the PAIRED per-block ratio distribution and its median, plus an A/A
    control (identical config both arms) which MUST centre on 1.0. If the A/A
    control is wide, the measurement is declared UNUSABLE rather than quoted.

Diagnostic only. Makes no strength claim.
Usage: recovery_eval_cost.py --probe BIN --a PARAMS --b PARAMS [--blocks 40]
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import platform
import sys
import statistics
import subprocess
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe", required=True)
    ap.add_argument("--a", required=True)
    ap.add_argument("--b", required=True)
    ap.add_argument("--blocks", type=int, default=40)
    ap.add_argument("--epd", help="explicit diagnostic corpus (recommended)")
    ap.add_argument("--json")
    ap.add_argument("--raw-json", help="preserve every block plus input identities")
    args = ap.parse_args()
    if args.blocks < 1:
        ap.error("--blocks must be positive")

    ratios = []
    aa = []
    raw = []
    for i in range(args.blocks):
        # alternate order to cancel any systematic warm-up advantage
        first, second = (args.a, args.b) if i % 2 == 0 else (args.b, args.a)
        vals = {}
        for tag, path in (("first", first), ("second", second)):
            cmd = [args.probe, path]
            if args.epd:
                cmd.append(args.epd)
            r = subprocess.run(cmd, capture_output=True, text=True)
            if r.returncode != 0:
                print("probe failed:", r.stderr[-500:])
                return 2
            vals[tag] = float(r.stdout.split()[1])
        a_ns = vals["first"] if i % 2 == 0 else vals["second"]
        b_ns = vals["second"] if i % 2 == 0 else vals["first"]
        ratios.append(b_ns / a_ns)
        raw.append({"block": i, "a_first": i % 2 == 0,
                    "a_ns": a_ns, "b_ns": b_ns, "ratio": b_ns / a_ns})
        # A/A control from the same pair of measurements when both arms are the
        # same file (caller can pass --a == --b to calibrate).
        if args.a == args.b:
            aa.append(b_ns / a_ns)

    ratios.sort()
    med = statistics.median(ratios)
    lo = ratios[int(0.10 * len(ratios))]
    hi = ratios[int(0.90 * len(ratios)) - 1]
    out = {"blocks": args.blocks, "median_b_over_a": med,
           "p10": lo, "p90": hi, "min": ratios[0], "max": ratios[-1],
           "a_params": args.a, "b_params": args.b}
    print(f"paired B/A cost ratio: median {med:.4f}  p10 {lo:.4f}  p90 {hi:.4f}  "
          f"range [{ratios[0]:.4f}, {ratios[-1]:.4f}]  ({args.blocks} blocks)")
    if args.a == args.b:
        spread = hi - lo
        print(f"A/A CONTROL: spread(p90-p10) = {spread:.4f}")
        usable = spread < 0.10
        print("A/A control", "TIGHT enough to interpret" if usable else
              "TOO WIDE — this environment cannot resolve the cost; do NOT quote a ratio")
        out["aa_spread"] = spread
        out["usable"] = usable
    if args.json:
        Path(args.json).write_text(json.dumps(out, indent=2) + "\n")
    if args.raw_json:
        paths = {str(Path(args.probe).resolve()), str(Path(args.a).resolve()),
                 str(Path(args.b).resolve()), str(Path(__file__).resolve()),
                 str((Path(__file__).parent / "probes/evalprof.cpp").resolve())}
        if args.epd:
            paths.add(str(Path(args.epd).resolve()))
        raw_out = {"argv": sys.argv, "blocks_raw": raw, "summary": out,
                   "runtime": {"python": platform.python_version(),
                               "platform": platform.platform(),
                               "cpu_affinity": sorted(os.sched_getaffinity(0))},
                   "sha256": {p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
                              for p in sorted(paths)}}
        Path(args.raw_json).write_text(json.dumps(raw_out, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
