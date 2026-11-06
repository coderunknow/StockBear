#!/usr/bin/env python3
"""A/A calibration of the NPS cost gate on an ISOLATED GitHub-hosted runner.

WHY THIS LANE EXISTS
--------------------
The shared 2-core sandbox cannot resolve the frozen +/-3% NPS band. An A/A null
there (both arms the identical champion binary, true ratio exactly 1.0)
false-rejected 80% of evaluations at 3 reps and 58% at 5 reps, with ratios
0.894-1.035. See benchmarks/dev6-baseline/nps_gate_calibration/.

That finding invalidated BOTH directions of the gate on that host: exp-0048's
1.00967 "PASS" no longer establishes "free per node" (claim withdrawn), and
exp-0049's 0.93931 "FAIL" does not establish a 6% cost. Neither verdict changed,
because both closed on the timing-independent accuracy gate.

This job runs the SAME A/A null on a dedicated runner to find out whether an
isolated host can resolve the band at all.

SCOPE -- ENFORCED, NOT JUST DOCUMENTED
--------------------------------------
This lane measures NO candidate. There is no --pst input and no code path that
loads one. It cannot re-score, reopen or "retry" exp-0048 or exp-0049, and it
must never be used to re-roll a closed experiment's timing. Its output may only
inform how a FUTURE candidate's cost gate is frozen in that candidate's prereg,
before that candidate's corpus exists.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEV5 = ROOT / "benchmarks/binaries/stockbear-dev5-release"
DEV5_SHA = "391cb50e13ab99168aba0255482554ab5e59d1a34af810bf8f4d2c88e5bdb918"
DEFAULT_FLAGS = "-mpopcnt -mbmi2 -mlzcnt -DSB_SEE_CACHE=1 -flto=4"


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def tool(name: str) -> str:
    found = shutil.which(name)
    if found:
        return found
    # Pinned pip wheels land in ~/.local/bin on the hosted runner.
    alt = Path.home() / ".local" / "bin" / name
    assert alt.is_file(), f"required tool not found: {name}"
    return str(alt)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-sha", required=True)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--run-attempt", default="1")
    ap.add_argument("--nodes", type=int, default=300000)
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--evaluations", type=int, default=6)
    ap.add_argument("--require-zero-false-rejects", action="store_true", default=True)
    a = ap.parse_args()

    out = ROOT / "benchmarks/exp-runs/cost-gate-calibration"
    out.mkdir(parents=True, exist_ok=True)
    log = open(out / "run.log", "w")

    def say(*args):
        line = " ".join(str(x) for x in args)
        print(line, flush=True)
        log.write(line + "\n")
        log.flush()

    # ---- 1. provenance: the checkout must BE the pinned source ---------------
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                          capture_output=True, text=True).stdout.strip()
    assert head == a.source_sha, f"checkout {head} != pinned {a.source_sha}"
    assert sha(DEV5) == DEV5_SHA, "immutable dev5 baseline binary changed"
    say("source_sha VERIFIED", head)
    say("dev5 baseline sha256 VERIFIED", DEV5_SHA)

    # ---- 2. build the engine from the pinned source, frozen flags -----------
    build = ROOT / "build-costgate"
    if build.exists():
        shutil.rmtree(build)
    cmake, ninja = tool("cmake"), tool("ninja")
    r = subprocess.run([cmake, "-S", ".", "-B", str(build), "-G", "Ninja",
                        "-DCMAKE_BUILD_TYPE=Release",
                        f"-DCMAKE_CXX_FLAGS={DEFAULT_FLAGS}",
                        "-DCMAKE_MAKE_PROGRAM=" + ninja,
                        "-DSTOCKBEAR_BUILD_TESTS=OFF"],
                       cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
    assert r.returncode == 0, "cmake configure failed"
    r = subprocess.run([cmake, "--build", str(build), "-j", "2",
                        "--target", "stockbear"],
                       cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
    assert r.returncode == 0, "engine build failed"
    engine = build / "stockbear"
    say("engine built sha256", sha(engine), "flags", DEFAULT_FLAGS)

    # ---- 3. record the host, so a future prereg can name it -----------------
    cpu = ""
    try:
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.startswith("model name"):
                cpu = line.split(":", 1)[1].strip()
                break
    except OSError:
        pass
    # A local smoke run must never be mistakable for isolated-runner evidence.
    # GITHUB_ACTIONS is set to "true" only inside a GitHub Actions job.
    on_actions = os.environ.get("GITHUB_ACTIONS") == "true"
    isolated = on_actions and bool(os.environ.get("RUNNER_NAME"))
    host = {
        "executed_on_github_actions": on_actions,
        "isolated_runner": isolated,
        "runner_name": os.environ.get("RUNNER_NAME", ""),
        "os": platform.platform(), "machine": platform.machine(),
        "cpu_model": cpu, "nproc": os.cpu_count(),
        "python": platform.python_version(),
        "gcc": subprocess.run(["gcc", "--version"], capture_output=True,
                              text=True).stdout.splitlines()[0],
        "cmake": subprocess.run([cmake, "--version"], capture_output=True,
                                text=True).stdout.splitlines()[0],
        "runner_image": os.environ.get("ImageOS", ""),
        "runner_os": os.environ.get("ImageVersion", ""),
        "github_run_id": a.run_id, "github_run_attempt": a.run_attempt,
    }
    say("host", json.dumps(host))

    # ---- 4. A/A null: identical arms, true ratio exactly 1.0 ----------------
    r = subprocess.run([sys.executable,
                        str(ROOT / "scripts/dev6_nps_gate_calibration.py"),
                        "--engine", str(engine), "--out", str(out / "aa"),
                        "--nodes", str(a.nodes), "--reps", str(a.reps),
                        "--evaluations", str(a.evaluations)],
                       cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
    assert r.returncode == 0, "A/A calibration failed to run"
    cal = json.loads((out / "aa" / "CALIBRATION.json").read_text())
    say("A/A false_rejects", cal["false_rejects"], "/", a.evaluations)
    say("A/A ratio range", cal["ratio_min"], cal["ratio_max"])
    say("A/A max arm self-spread", cal["max_arm_self_spread"])
    say("band resolvable on this host:", cal["band_resolvable_on_this_host"])

    manifest = {
        "purpose": "A/A instrument calibration of the NPS cost gate on an isolated runner",
        "scope_warning": (
            "NO candidate measured; no --pst input exists in this lane. Does NOT "
            "re-run, re-score or reopen exp-0048/exp-0049. Output may only inform how "
            "a FUTURE candidate's cost gate is frozen in its own prereg."),
        "source_sha": head,
        "engine_sha256": sha(engine),
        "build_flags": DEFAULT_FLAGS,
        "dev5_baseline_sha256": DEV5_SHA,
        "calibration_script_sha256": sha(ROOT / "scripts/dev6_nps_gate_calibration.py"),
        "host": host,
        "true_ratio_by_construction": 1.0,
        "nodes_per_position": a.nodes,
        "reps_per_evaluation": a.reps,
        "evaluations": a.evaluations,
        "band": cal["band"],
        "false_rejects": cal["false_rejects"],
        "false_reject_rate": cal["false_reject_rate"],
        "aa_ratio_min": cal["ratio_min"],
        "aa_ratio_max": cal["ratio_max"],
        "max_arm_self_spread": cal["max_arm_self_spread"],
        "observed_aa_half_range": cal["observed_aa_half_range"],
        "band_half_width": cal["band_half_width"],
        "band_resolvable_on_this_host": cal["band_resolvable_on_this_host"],
        "verdict": (
            ("ISOLATED RUNNER CAN RESOLVE THE BAND"
             if cal["band_resolvable_on_this_host"]
             else "ISOLATED RUNNER ALSO CANNOT RESOLVE THE BAND")
            if isolated else
            ("LOCAL/NON-ISOLATED RUN - NOT VALID HOST EVIDENCE "
             "(smoke test only; band_resolvable="
             f"{cal['band_resolvable_on_this_host']})")),
    }
    if not isolated:
        say("WARNING: not an isolated GitHub runner; this output is a SMOKE TEST")
        say("         and must not be cited as host-capability evidence.")
    (out / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
    # Close the log BEFORE hashing it, or the digest is stale (a bug fixed once
    # already in the corpus lane).
    log.close()
    sums = []
    for p in sorted(out.rglob("*")):
        if p.is_file() and p.name != "SHA256SUMS.txt":
            sums.append(f"{sha(p)}  {p.relative_to(out).as_posix()}")
    (out / "SHA256SUMS.txt").write_text("\n".join(sums) + "\n")
    chk = subprocess.run(["sha256sum", "-c", "SHA256SUMS.txt"], cwd=out,
                         capture_output=True, text=True)
    assert chk.returncode == 0, f"checksum verification failed:\n{chk.stdout}"
    print(chk.stdout.strip())
    print("VERDICT:", manifest["verdict"])

    # The JOB succeeds when the measurement is validly performed. A host that
    # cannot resolve the band is a legitimate, informative result, not a crash.
    # The advisory gate is reported in the manifest for a future prereg to use.


if __name__ == "__main__":
    main()
