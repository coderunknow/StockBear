#!/usr/bin/env python3
"""Exercise the Tier-1 file-option load assertion on the REAL runner, zero games.

exp-0051 established that a file-valued UCI option which fails to load is NOT
fatal to the engine: it prints `could not load` and plays on with fallback
tables, manufacturing a convincing fake result. The runner must abort instead.
exp-0052 extends that guard from PstFile to EvalParams.

This drives `scripts/dev6_tier1_job.py` itself (no refactor, no mock) with
`games: 0`. The runner asserts `games > 0` AFTER the option probe, so a scenario
that reaches the games assertion has already passed the probe, and a scenario
that fails earlier proves the guard fired. ZERO games are played in every case.

Scenarios:
  valid                 -> probe passes, aborts at the games assertion
  undeclared_evalparams -> aborts: asset not declared
  corrupt_evalparams    -> packaged, then aborts: could not load
  undeclared_pst        -> aborts: asset not declared (regression guard)
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "benchmarks/exp-runs/tier1-plan-exp0052.json"
CAND = "research-data/params_exp0052_ks.txt"


def run_scenario(name: str, mutate, expect: str) -> dict:
    plan = json.loads(PLAN.read_text())
    job = dict(plan["jobs"][1])          # batchA: candidate vs exact dev5
    job["id"] = f"guardcheck-{name}"
    job["games"] = 0                     # ZERO games; probe still runs
    job["ctest"] = False
    mutate(job)
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    env = dict(os.environ)
    # This is a local instrument check, never a benchmark run.
    env.pop("GITHUB_ACTIONS", None)
    env.pop("RUNNER_NAME", None)
    p = subprocess.run(
        [sys.executable, "scripts/dev6_tier1_job.py", "--job", json.dumps(job),
         "--source-sha", head, "--experiment-id", "exp0052guard",
         "--run-id", "local-guard", "--run-attempt", "1"],
        cwd=ROOT, capture_output=True, text=True, timeout=1800, env=env)
    blob = p.stdout + p.stderr
    (ROOT / f"/tmp/guard_{name}.txt").write_text(blob)
    hit = expect in blob
    # A guard scenario must NOT reach the games assertion.
    reached_games = "games must be a positive even number" in blob
    ok = hit and (reached_games if name == "valid" else not reached_games)
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: expected {expect!r} "
          f"(found={hit}, reached_games_assertion={reached_games})")
    if not ok:
        print(blob[-2500:])
    return {"scenario": name, "expected_substring": expect, "found": hit,
            "reached_games_assertion": reached_games, "pass": ok,
            "exit_code": p.returncode}


def main() -> int:
    corrupt = ROOT / "research-data/params_exp0052_corrupt_guard.txt"
    corrupt.write_text("KingSafetyQuadratic not_a_number 0\n")
    results = []
    try:
        results.append(run_scenario("valid", lambda j: None,
                                    "games must be a positive even number"))
        results.append(run_scenario(
            "undeclared_evalparams",
            lambda j: j.update(assets=[]),
            "is not declared in job['assets']"))
        def swap(j):
            j["a_options"] = [f"EvalParams={corrupt.relative_to(ROOT)}", "TTEval=true"]
            j["assets"] = [str(corrupt.relative_to(ROOT))]
        results.append(run_scenario("corrupt_evalparams", swap, "could not load"))
        results.append(run_scenario(
            "undeclared_pst",
            lambda j: (j["a_options"].append(
                "PstFile=benchmarks/dev6-baseline/exp0049_results/exp0049.sbpst"),
                j.update(assets=[CAND])),
            "is not declared in job['assets']"))
    finally:
        corrupt.unlink(missing_ok=True)
    ok = all(r["pass"] for r in results)
    out = {"purpose": "file-option load guard, real runner, ZERO games",
           "games_played": 0, "scenarios": results,
           "verdict": "PASS" if ok else "FAIL"}
    (ROOT / "benchmarks/recovery/exp0052_option_guard_check.json").write_text(
        json.dumps(out, indent=2) + "\n")
    print("\nverdict:", out["verdict"], "| games played: 0")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
