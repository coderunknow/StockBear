#!/usr/bin/env python3
"""Condition-by-condition validity/Gate-1 decision check for exp-0062.

Does not trust the audit banner. Reads the independent raw audit JSON, exported
fingerprints/raw configs, per-job checksums and suite verification. Fails closed
if an expected identity field is missing. The primary estimate is batchA+batchB
only; nulls are never pooled. Gate: point >= +75 AND 95% LCB strictly > +50.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUN_ID = 42356232866
EXPORT_RUN_ID = 42364780824
D = ROOT / f"benchmarks/exp-runs/tier1-export/run-{RUN_ID}"
SOURCE = "95606a513c4cc96231fbbba89e04165348c23fbb"
PREREG = "b7bab412fe0a2c6ca992e188c4d42b14cf9450e86dbdefb1e8004363c6a90365"
DEV5 = "391cb50e13ab99168aba0255482554ab5e59d1a34af810bf8f4d2c88e5bdb918"
RACE = "research-data/params_exp0055_race.txt"
CHAMP = "research-data/params_abc.txt"
RACE_SHA = "82f93ba7a7b7e8e757c245098f5e2c4f42c866aa25124c73d0ad67ad11f89f01"
CHAMP_SHA = "8a9dc81fa5921e5b642c790ffa3cf84c2ba68f2193023c19dc7f3f7cea86d0be"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    a = json.loads((ROOT / "benchmarks/recovery/exp0062_independent_raw_audit.json").read_text())
    jobs = a["jobs"]
    checks = {}

    def add(name, ok, detail):
        checks[name] = {"pass": bool(ok), "detail": detail}
        if not ok:
            print("FAIL", name, detail)

    fps, cfgs, dirs = {}, {}, {}
    for short in ("batchA", "batchB", "null", "stage0"):
        j = next(D.glob(f"tier1-*{short}-run*"))
        dirs[short] = j
        fps[short] = json.loads((j / "fingerprint.json").read_text())
        cfgs[short] = json.loads((j / "match.jsonl").read_text().splitlines()[0])["configuration"]

    proto = all(f["source_sha"] == SOURCE and f["prereg_sha256"] == PREREG
                and f["plan_job"]["control"] == {"base_ms": 40, "inc_ms": 4}
                and f["plan_job"]["hash"] == 16 and f["plan_job"]["threads"] == 1
                and f["plan_job"]["max_plies"] == 240 for f in fps.values())
    add("source_prereg_protocol", proto, {k: f["source_sha"] for k, f in fps.items()})

    bin_ok = True
    bin_detail = {}
    for k, c in cfgs.items():
        built, packaged = fps[k]["built_binary_sha256"], fps[k]["packaged_binary_sha256"]
        ea, eb = c["engine_a_sha256"], c["engine_b_sha256"]
        bin_detail[k] = {"a": ea, "b": eb, "built": built, "packaged": packaged}
        if built != packaged or ea != built:
            bin_ok = False
        if k in ("batchA", "batchB"):
            if eb != DEV5:
                bin_ok = False
        else:
            if eb != built:
                bin_ok = False
    bin_ok &= len({fps[k]["built_binary_sha256"] for k in fps}) == 1
    add("binary_identities", bin_ok, bin_detail)

    opts = {k: {"a": c["engine_a_options"], "b": c["engine_b_options"]} for k, c in cfgs.items()}
    want = {"batchA": (RACE, CHAMP), "batchB": (RACE, CHAMP),
            "null": (RACE, RACE), "stage0": (CHAMP, CHAMP)}
    opt_ok = all(opts[k]["a"].get("evalparams") == pa and opts[k]["b"].get("evalparams") == pb
                 and opts[k]["a"].get("tteval") == "true" and opts[k]["b"].get("tteval") == "true"
                 for k, (pa, pb) in want.items())
    add("explicit_options", opt_ok, opts)

    # Different binaries legitimately expose different default UCI option sets.
    # Null arms must be identical; primary arms must record defaults and the
    # candidate's new battery row (if present) must be default-off.
    defaults_ok = all(cfgs[k]["engine_a_defaults"] == cfgs[k]["engine_b_defaults"] for k in ("null", "stage0"))
    defaults_ok &= all(bool(cfgs[k]["engine_a_defaults"]) and bool(cfgs[k]["engine_b_defaults"]) for k in cfgs)
    batt = cfgs["batchA"]["engine_a_defaults"].get("kingsliderbattery")
    defaults_ok &= batt is None or str(batt).split()[0] in ("0", "default", "0/0") or "default 0" in str(batt)
    add("recorded_defaults", defaults_ok, {"null_stage0_identical": True, "candidate_battery_default": batt})

    sums_ok, sums_total = 0, 0
    for k, j in dirs.items():
        lines = (j / "SHA256SUMS.txt").read_text().splitlines()
        for line in lines:
            h, _, fn = line.partition("  ")
            sums_total += 1
            if sha(j / fn.strip()) == h:
                sums_ok += 1
    add("per_job_checksums_independent", sums_ok == sums_total and sums_total > 0, f"{sums_ok}/{sums_total}")

    asset_detail, asset_ok = {}, True
    for k, c in cfgs.items():
        pa, pb = want[k]
        ia = c["engine_a_input_files"].get("evalparams", {})
        ib = c["engine_b_input_files"].get("evalparams", {})
        asset_detail[k] = {"a": ia, "b": ib}
        if ia.get("path") != pa or ib.get("path") != pb:
            asset_ok = False
        if ia.get("sha256") != (RACE_SHA if pa == RACE else CHAMP_SHA):
            asset_ok = False
        if ib.get("sha256") != (RACE_SHA if pb == RACE else CHAMP_SHA):
            asset_ok = False
    add("frozen_config_assets", asset_ok, asset_detail)

    for k in ("stage0", "null"):
        ci = jobs[k]["stats"]["elo_ci95"]
        add(f"{k}_null_includes_zero", ci[0] < 0 < ci[1], ci)
    add("auditor_issues_zero", a["issues"] == [], a["issues"])
    add("committed_blobs", a["committed_blobs"] == "54/54", a["committed_blobs"])
    add("auditor_checksums", a["checksums"] == f"{sums_total}/{sums_total}", a["checksums"])
    add("option_load_proof", all(len(v) >= 2 for v in a["option_load_proof"].values()), a["option_load_proof"])

    replay = {k: jobs[k]["pgn_replay"] for k in ("batchA", "batchB", "null", "stage0")}
    add("pgn_replay_15000", all(replay[k]["games_replayed"] == n and replay[k]["inconsistent"] == 0
                               for k, n in [("batchA", 6600), ("batchB", 6600), ("null", 1200), ("stage0", 600)]), replay)
    add("zero_failures", all(jobs[k]["time_forfeits"] == 0 and jobs[k]["illegal"] == 0 and jobs[k]["engine_failures"] == 0
                             for k in ("batchA", "batchB", "null", "stage0")), True)
    suite = json.loads((ROOT / "benchmarks/recovery/exp0062_suite_verification.json").read_text())
    add("openings_disjoint", suite["verdict"] == "PASS", suite.get("issues"))
    log = (dirs["stage0"] / "run.log").read_text()
    add("stage0_ctest_18", "100% tests passed out of 18" in log and "ctest PASS" in log, "stage0 run.log")

    plan = json.loads((ROOT / "benchmarks/exp-runs/tier1-plan-exp0062.json").read_text())
    add("budget_games", sum(j["games"] for j in plan["jobs"]) == 15000
        and sum(j["games"] for j in plan["jobs"] if j["id"].endswith(("batchA", "batchB"))) == 13200,
        {j["id"]: j["games"] for j in plan["jobs"]})

    comb = jobs["_combined"]["stats"]
    ba, bb = jobs["batchA"]["stats"]["elo"], jobs["batchB"]["stats"]["elo"]
    valid = all(c["pass"] for c in checks.values())
    gate_met = valid and comb["elo"] >= 75 and comb["elo_ci95"][0] > 50
    verdict = "INVALID" if not valid else ("GATE_MET" if gate_met else "GATE_UNMET")
    out = {"experiment": "exp0062", "run_id": RUN_ID, "export_run_id": EXPORT_RUN_ID,
           "source_sha": SOURCE, "valid": valid, "checks": checks, "combined": comb,
           "batchA_elo": ba, "batchB_elo": bb, "verdict": verdict, "gate1_met": gate_met,
           "gate": {"point_min": 75, "lcb_strictly_greater": 50},
           "note": "Direct integrated threats+race vs exact published dev5; no component summation."}
    dest = ROOT / "benchmarks/recovery/exp0062_validity.json"
    dest.write_text(json.dumps(out, indent=2) + "\n")
    print(verdict, "valid=", valid, "elo=", comb["elo"], "ci=", comb["elo_ci95"])
    return 0 if valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
