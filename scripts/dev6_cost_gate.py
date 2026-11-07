#!/usr/bin/env python3
"""Prospective, fail-closed evaluation-cost gate for a frozen Tier-1 plan.

Runs in the isolated prepare job BEFORE any benchmark matrix job. It builds the
pinned source, links the diagnostic probe, measures a noise-resistant A/A
control and two A/B contrasts, then independently checks the frozen numeric
budget. A failed control stops before A/B; a failed limit exits nonzero so the
workflow cannot start games. Raw times, hashes, logs and a verdict are preserved.
"""
from __future__ import annotations
import argparse, hashlib, json, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

def run(cmd, log=None):
    print("+ " + " ".join(map(str, cmd)), flush=True)
    r = subprocess.run(list(map(str, cmd)), cwd=ROOT, text=True,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if log is not None:
        log.write_text(r.stdout)
    print(r.stdout, end="", flush=True)
    return r

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", required=True)
    ap.add_argument("--source-sha", required=True)
    ap.add_argument("--experiment-id", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    plan = json.loads(Path(a.plan).read_text())
    gate = plan.get("cost_gate")
    if not gate:
        print("no cost_gate in plan; nothing to enforce")
        return 0
    out = ROOT / a.out
    out.mkdir(parents=True, exist_ok=True)
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    assert head == a.source_sha, f"cost gate source mismatch {head} != {a.source_sha}"
    assert plan.get("experiment_id") == a.experiment_id
    prereg = ROOT / gate["prereg"]
    assert sha(prereg) == gate["prereg_sha256"], "frozen prereg changed"
    budget_path = ROOT / gate["budget"]
    budget = json.loads(budget_path.read_text())
    assert budget["prereg_sha256"] == gate["prereg_sha256"]
    assert sha(ROOT / gate["policy"]) == budget["policy_sha256"]
    corpus = ROOT / gate["corpus"]
    assert sha(corpus) == gate["corpus_sha256"] == budget["corpus_sha256"]
    assert len([x for x in corpus.read_text().splitlines() if x.strip()]) == gate["corpus_n"] == budget["corpus_n"]
    for k in ("aa_blocks", "ab_blocks", "repeats", "passes_per_block",
              "increment_median_max", "combined_median_max"):
        assert gate[k] == budget[k], f"budget/gate mismatch {k}"
    assert gate["max_attempts"] == 1, "this gate is a single prospective CI attempt"

    flags = gate["build_flags"]
    build = ROOT / "build-cost-gate"
    r = run(["cmake", "-S", ".", "-B", build, "-G", "Ninja",
             "-DCMAKE_BUILD_TYPE=Release", f"-DCMAKE_CXX_FLAGS={flags}",
             "-DSTOCKBEAR_BUILD_TESTS=OFF"], out / "cmake_configure.log")
    assert r.returncode == 0, "cmake configure failed"
    r = run(["cmake", "--build", build, "-j", "2", "--target", "stockbear_core"],
            out / "cmake_build.log")
    assert r.returncode == 0, "core build failed"
    probe = build / "evalprof"
    r = run(["c++", "-O3", "-std=c++17", *flags.split(), "-Isrc",
             "scripts/probes/evalprof.cpp", build / "libstockbear_core.a",
             "-pthread", "-o", probe], out / "probe_build.log")
    assert r.returncode == 0, "probe link failed"

    def measure(name, pa, pb, blocks):
        summary = out / f"{name}_summary.json"
        raw = out / f"{name}_raw.json"
        cmd = [sys.executable, "scripts/recovery_eval_cost.py", "--probe", probe,
               "--a", pa, "--b", pb, "--blocks", blocks, "--repeats", gate["repeats"],
               "--epd", corpus, "--json", summary, "--raw-json", raw]
        r = run(cmd, out / f"{name}.log")
        assert r.returncode == 0, f"{name} probe failed"
        s = json.loads(summary.read_text())
        assert s["blocks"] == blocks and s["repeats"] == gate["repeats"]
        return s, json.loads(raw.read_text())

    checks = {}
    aa, aa_raw = measure("aa", gate["ablation_params"], gate["ablation_params"], gate["aa_blocks"])
    checks["aa_spread"] = {"value": aa["aa_spread"], "limit_exclusive": gate["aa_spread_max_exclusive"],
                           "pass": aa["aa_spread"] < gate["aa_spread_max_exclusive"]}
    lo, hi = gate["aa_median_range"]
    checks["aa_median"] = {"value": aa["median_b_over_a"], "range": [lo, hi],
                           "pass": lo <= aa["median_b_over_a"] <= hi}
    if not all(c["pass"] for c in checks.values()):
        verdict = {"experiment_id": a.experiment_id, "source_sha": head,
                   "pass": False, "stage": "aa_control", "checks": checks,
                   "games_dispatched": 0}
        (out / "verdict.json").write_text(json.dumps(verdict, indent=2) + "\n")
        write_sums(out)
        print("COST GATE FAILED at A/A control; no A/B or games", flush=True)
        return 1

    inc, inc_raw = measure("increment", gate["ablation_params"], gate["candidate_params"], gate["ab_blocks"])
    comb, comb_raw = measure("combined", gate["champion_params"], gate["candidate_params"], gate["ab_blocks"])
    checks["increment_median"] = {"value": inc["median_b_over_a"], "limit": gate["increment_median_max"],
                                  "pass": inc["median_b_over_a"] <= gate["increment_median_max"]}
    checks["combined_median"] = {"value": comb["median_b_over_a"], "limit": gate["combined_median_max"],
                                  "pass": comb["median_b_over_a"] <= gate["combined_median_max"]}
    # Raw identity cross-checks, independent of the probe's own summary banner.
    for raw in (aa_raw, inc_raw, comb_raw):
        assert raw["sha256"][str(corpus.resolve())] == gate["corpus_sha256"]
        assert raw["sha256"][str(probe.resolve())] == sha(probe)
    ok = all(c["pass"] for c in checks.values())
    verdict = {"experiment_id": a.experiment_id, "source_sha": head,
               "prereg_sha256": gate["prereg_sha256"], "budget_sha256": sha(budget_path),
               "pass": ok, "stage": "complete", "checks": checks,
               "games_dispatched": 0, "instrument": "median of paired repeats per block",
               "repeats": gate["repeats"], "aa_blocks": gate["aa_blocks"], "ab_blocks": gate["ab_blocks"]}
    (out / "verdict.json").write_text(json.dumps(verdict, indent=2) + "\n")
    write_sums(out)
    print("COST GATE", "PASS" if ok else "FAIL", flush=True)
    return 0 if ok else 1

def write_sums(out: Path):
    lines = []
    for p in sorted(out.iterdir()):
        if p.is_file() and p.name != "SHA256SUMS.txt":
            lines.append(f"{sha(p)}  {p.name}")
    (out / "SHA256SUMS.txt").write_text("\n".join(lines) + "\n")

if __name__ == "__main__":
    raise SystemExit(main())
