#!/usr/bin/env python3
"""Condition-by-condition validity/decision check for exp-0060.

Does not trust the audit banner. Reads the independent raw audit JSON, the
exported fingerprints/raw configs, cost-gate verdict and suite verification.
Fails closed if an expected identity field is missing.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
D = ROOT / "benchmarks/exp-runs/tier1-export/run-42352690063"
SOURCE = "8e77e0fec3ee4d919b6aedfc02f89cb9d5c19950"
PREREG = "24f143ccb4e524469e322626e14f8690e226ab29ee9d537f15ddf345353e2a18"

def main():
    a = json.loads((ROOT / "benchmarks/recovery/exp0060_independent_raw_audit.json").read_text())
    jobs = a["jobs"]
    checks = {}
    def add(name, ok, detail):
        checks[name] = {"pass": bool(ok), "detail": detail}
        if not ok:
            print("FAIL", name, detail)

    cost_dir = D / "cost-gate-exp0060-run42352690063"
    cost = json.loads((cost_dir / "verdict.json").read_text())
    add("cost_gate_before_games", cost["pass"] and cost["games_dispatched"] == 0, cost["checks"])
    cost_sums = (cost_dir / "SHA256SUMS.txt").read_text().splitlines()
    cost_ok = 0
    for line in cost_sums:
        h, _, fn = line.partition("  ")
        if hashlib.sha256((cost_dir / fn.strip()).read_bytes()).hexdigest() == h:
            cost_ok += 1
    add("cost_gate_checksums", cost_ok == len(cost_sums), f"{cost_ok}/{len(cost_sums)}")

    fps, cfgs = {}, {}
    for short in ("batchA", "batchB", "null", "stage0"):
        j = next(D.glob(f"tier1-*{short}-run*"))
        fps[short] = json.loads((j / "fingerprint.json").read_text())
        cfgs[short] = json.loads((j / "match.jsonl").read_text().splitlines()[0])["configuration"]
    proto = all(f["source_sha"] == SOURCE and f["prereg_sha256"] == PREREG
                and f["plan_job"]["control"] == {"base_ms": 40, "inc_ms": 4}
                and f["plan_job"]["hash"] == 16 and f["plan_job"]["threads"] == 1
                and f["plan_job"]["max_plies"] == 240 for f in fps.values())
    add("source_prereg_protocol", proto, {k: f["source_sha"] for k, f in fps.items()})

    binids = {k: {"a": c["engine_a_sha256"], "b": c["engine_b_sha256"],
                  "built": fps[k]["built_binary_sha256"],
                  "packaged": fps[k]["packaged_binary_sha256"]} for k, c in cfgs.items()}
    same = all(v["a"] == v["b"] == v["built"] == v["packaged"] for v in binids.values())
    same &= len({v["a"] for v in binids.values()}) == 1
    add("same_binary_arms", same, binids)

    opts = {k: {"a": c["engine_a_options"], "b": c["engine_b_options"]} for k, c in cfgs.items()}
    want = {"batchA": ("research-data/params_exp0055_race.txt", "research-data/params_exp0053_threats.txt"),
            "batchB": ("research-data/params_exp0055_race.txt", "research-data/params_exp0053_threats.txt"),
            "null": ("research-data/params_exp0055_race.txt", "research-data/params_exp0055_race.txt"),
            "stage0": ("research-data/params_abc.txt", "research-data/params_abc.txt")}
    opt_ok = all(opts[k]["a"].get("evalparams") == pa and opts[k]["b"].get("evalparams") == pb
                 and opts[k]["a"].get("tteval") == "true" and opts[k]["b"].get("tteval") == "true"
                 for k, (pa, pb) in want.items())
    add("explicit_options", opt_ok, opts)
    defaults_ok = all(c["engine_a_defaults"] == c["engine_b_defaults"] for c in cfgs.values())
    add("identical_recorded_defaults", defaults_ok, "engine_a_defaults == engine_b_defaults in every job")

    for k in ("stage0", "null"):
        ci = jobs[k]["stats"]["elo_ci95"]
        add(f"{k}_null_includes_zero", ci[0] < 0 < ci[1], ci)
    add("auditor_issues_zero", a["issues"] == [], a["issues"])
    add("committed_blobs", a["committed_blobs"] == "68/68", a["committed_blobs"])
    add("per_job_checksums", a["checksums"] == "44/44", a["checksums"])
    add("option_load_proof", all(len(v) >= 2 for v in a["option_load_proof"].values()), a["option_load_proof"])
    replay = {k: jobs[k]["pgn_replay"] for k in ("batchA", "batchB", "null", "stage0")}
    add("pgn_replay_7800", all(replay[k]["games_replayed"] == n and replay[k]["inconsistent"] == 0
                               for k, n in [("batchA", 3000), ("batchB", 3000), ("null", 1200), ("stage0", 600)]), replay)
    add("zero_failures", all(jobs[k]["time_forfeits"] == 0 and jobs[k]["illegal"] == 0 and jobs[k]["engine_failures"] == 0
                             for k in ("batchA", "batchB", "null", "stage0")), True)
    suite = json.loads((ROOT / "benchmarks/recovery/exp0060_suite_verification.json").read_text())
    add("openings_disjoint", suite["verdict"] == "PASS", suite.get("issues"))
    log = (next(D.glob("tier1-*stage0-run*")) / "run.log").read_text()
    add("stage0_ctest_17", "100% tests passed out of 17" in log and "ctest PASS" in log, "stage0 run.log")

    comb = jobs["_combined"]["stats"]
    ba, bb = jobs["batchA"]["stats"]["elo"], jobs["batchB"]["stats"]["elo"]
    valid = all(c["pass"] for c in checks.values())
    confirmed = valid and comb["elo"] >= 20 and comb["elo_ci95"][0] > 0 and ba >= -5 and bb >= -5
    rejected = valid and (comb["elo_ci95"][1] < 10 or comb["elo"] <= 0)
    verdict = "CONFIRMED_INCREMENT" if confirmed else ("REJECTED" if rejected else ("INVALID" if not valid else "INCONCLUSIVE"))
    out = {"experiment": "exp0060", "run_id": 42352690063, "export_run_id": 42354629242,
           "source_sha": SOURCE, "valid": valid, "checks": checks, "combined": comb,
           "batchA_elo": ba, "batchB_elo": bb, "verdict": verdict, "gate1_met": False,
           "note": "Confirms race increment only; not integral vs dev5 and not Gate 1."}
    dest = ROOT / "benchmarks/recovery/exp0060_validity.json"
    dest.write_text(json.dumps(out, indent=2) + "\n")
    print(verdict, "valid=", valid, "elo=", comb["elo"], "ci=", comb["elo_ci95"])
    return 0 if valid else 1

if __name__ == "__main__":
    raise SystemExit(main())
