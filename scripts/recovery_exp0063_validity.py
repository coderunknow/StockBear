#!/usr/bin/env python3
"""Condition-by-condition validity/screen decision check for exp-0063.

Does not trust the audit banner. Reads the independent raw audit JSON, exported
fingerprints/raw configs, prospective cost-gate verdict and suite verification.
Fails closed if an expected identity field is missing. Primary = batchA+batchB
only; nulls never pooled. This is a SCREEN, not Gate 1.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUN_ID = 42365991406
EXPORT_RUN_ID = 42367464017
D = ROOT / f"benchmarks/exp-runs/tier1-export/run-{RUN_ID}"
SOURCE = "7d9aa8f03741c97bac8ee134f5cb913ceffbc216"
PREREG = "31c481f3cd14969671bb9cf529015b3fc9ef4d1a8d656b4e7eab02bb8dc5e0a0"
BATTERY = "research-data/params_exp0061_battery.txt"
RACE = "research-data/params_exp0055_race.txt"
CHAMP = "research-data/params_abc.txt"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    assert EXPORT_RUN_ID, "EXPORT_RUN_ID must be set before closure"
    a = json.loads((ROOT / "benchmarks/recovery/exp0063_independent_raw_audit.json").read_text())
    jobs = a["jobs"]
    checks = {}

    def add(name, ok, detail):
        checks[name] = {"pass": bool(ok), "detail": detail}
        if not ok:
            print("FAIL", name, detail)

    cost_dir = D / f"cost-gate-exp0063-run{RUN_ID}"
    cost = json.loads((cost_dir / "verdict.json").read_text())
    add("cost_gate_before_games", cost["pass"] and cost["games_dispatched"] == 0, cost["checks"])
    cost_sums = (cost_dir / "SHA256SUMS.txt").read_text().splitlines()
    cost_ok = sum(1 for line in cost_sums
                  if sha(cost_dir / line.partition("  ")[2].strip()) == line.partition("  ")[0])
    add("cost_gate_checksums", cost_ok == len(cost_sums), f"{cost_ok}/{len(cost_sums)}")

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

    binids = {k: {"a": c["engine_a_sha256"], "b": c["engine_b_sha256"],
                  "built": fps[k]["built_binary_sha256"],
                  "packaged": fps[k]["packaged_binary_sha256"]} for k, c in cfgs.items()}
    same = all(v["a"] == v["b"] == v["built"] == v["packaged"] for v in binids.values())
    same &= len({v["a"] for v in binids.values()}) == 1
    add("same_binary_arms", same, binids)

    opts = {k: {"a": c["engine_a_options"], "b": c["engine_b_options"]} for k, c in cfgs.items()}
    want = {"batchA": (BATTERY, RACE), "batchB": (BATTERY, RACE),
            "null": (BATTERY, BATTERY), "stage0": (CHAMP, CHAMP)}
    opt_ok = all(opts[k]["a"].get("evalparams") == pa and opts[k]["b"].get("evalparams") == pb
                 and opts[k]["a"].get("tteval") == "true" and opts[k]["b"].get("tteval") == "true"
                 for k, (pa, pb) in want.items())
    add("explicit_options", opt_ok, opts)
    add("identical_recorded_defaults", all(c["engine_a_defaults"] == c["engine_b_defaults"] for c in cfgs.values()),
        "engine_a_defaults == engine_b_defaults in every job")

    for k in ("stage0", "null"):
        ci = jobs[k]["stats"]["elo_ci95"]
        add(f"{k}_null_includes_zero", ci[0] < 0 < ci[1], ci)
    add("auditor_issues_zero", a["issues"] == [], a["issues"])
    blobs_ok, blobs_total = a["committed_blobs"].split("/")
    add("committed_blobs", blobs_ok == blobs_total and int(blobs_total) > 0, a["committed_blobs"])
    add("per_job_checksums", a["checksums"] == "44/44", a["checksums"])
    add("option_load_proof", all(len(v) >= 2 for v in a["option_load_proof"].values()), a["option_load_proof"])
    replay = {k: jobs[k]["pgn_replay"] for k in ("batchA", "batchB", "null", "stage0")}
    add("pgn_replay_5800", all(replay[k]["games_replayed"] == n and replay[k]["inconsistent"] == 0
                               for k, n in [("batchA", 2000), ("batchB", 2000), ("null", 1200), ("stage0", 600)]), replay)
    add("zero_failures", all(jobs[k]["time_forfeits"] == 0 and jobs[k]["illegal"] == 0 and jobs[k]["engine_failures"] == 0
                             for k in ("batchA", "batchB", "null", "stage0")), True)
    suite = json.loads((ROOT / "benchmarks/recovery/exp0063_suite_verification.json").read_text())
    add("openings_disjoint", suite["verdict"] == "PASS", suite.get("issues"))
    log = (dirs["stage0"] / "run.log").read_text()
    add("stage0_ctest_18", "100% tests passed out of 18" in log and "ctest PASS" in log, "stage0 run.log")

    comb = jobs["_combined"]["stats"]
    ba, bb = jobs["batchA"]["stats"]["elo"], jobs["batchB"]["stats"]["elo"]
    valid = all(c["pass"] for c in checks.values())
    advance = valid and comb["elo"] >= 15 and comb["elo_ci95"][0] > 0 and ba >= -5 and bb >= -5
    close = valid and (comb["elo_ci95"][1] < 5 or comb["elo"] <= 0)
    verdict = "INVALID" if not valid else ("SCREEN_ADVANCE" if advance else ("CLOSED" if close else "INCONCLUSIVE"))
    out = {"experiment": "exp0063", "run_id": RUN_ID, "export_run_id": EXPORT_RUN_ID,
           "source_sha": SOURCE, "valid": valid, "checks": checks, "combined": comb,
           "batchA_elo": ba, "batchB_elo": bb, "verdict": verdict, "gate1_met": False,
           "cost_gate": {"increment_median": cost["checks"].get("increment_median"),
                         "combined_median": cost["checks"].get("combined_median")},
           "note": "Battery increment screen after semantics-preserving cost optimization; not integral vs dev5 and not Gate 1."}
    dest = ROOT / "benchmarks/recovery/exp0063_validity.json"
    dest.write_text(json.dumps(out, indent=2) + "\n")
    print(verdict, "valid=", valid, "elo=", comb["elo"], "ci=", comb["elo_ci95"])
    return 0 if valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
