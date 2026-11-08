#!/usr/bin/env python3
"""Condition-by-condition validity/screen decision check for exp-0066.

Does not trust the audit banner. Reads the independent raw audit JSON, exported
fingerprints and raw per-job configurations, the frozen prospective search-cost
guard and the independently re-derived suite verification. Fails closed if an
expected identity field is missing. Primary = batchA+batchB only (6,000 games);
nulls are never pooled. This is a SCREEN, not Gate 1.

The candidate is a SEARCH switch, so the frozen prospective cost evidence is
benchmarks/recovery/exp0066_node_cost_guard.json (fixed-NODE wall-time A/B),
not the evaluate()-cost instrument; see prereg section 5.7.
"""
from __future__ import annotations
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUN_ID = 42434718590
EXPORT_RUN_ID = 0  # set from the export run before closure
D = ROOT / f"benchmarks/exp-runs/tier1-export/run-{RUN_ID}"
SOURCE = "a17e304e297f2edb89e526bf1b5fd891d81e60bc"
PREREG = "96c20de126b9ce8f5ca2031c5a90dfb72e24794462c077651939d1084c215fa3"
PREREG_PATH = "docs/DEV6_PREREG_EXP0066.md"
RACE = "research-data/params_exp0055_race.txt"
GAMES = {"batchA": 3000, "batchB": 3000, "null": 1200, "stage0": 600}
SWITCH = "persistentcontinuation"
# arm -> (A switch value, B switch value); EvalParams is RACE on every arm.
WANT_SWITCH = {"batchA": ("true", "false"), "batchB": ("true", "false"),
               "null": ("true", "true"), "stage0": ("false", "false")}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    assert EXPORT_RUN_ID, "EXPORT_RUN_ID must be set before closure"
    a = json.loads((ROOT / "benchmarks/recovery/exp0066_independent_raw_audit.json").read_text())
    jobs = a["jobs"]
    checks = {}

    def add(name, ok, detail):
        checks[name] = {"pass": bool(ok), "detail": detail}
        if not ok:
            print("FAIL", name, detail)

    # --- frozen prospective gates: per-node cost + sequential efficacy -----
    guard_path = ROOT / "benchmarks/recovery/exp0066_node_cost_guard.json"
    guard = json.loads(guard_path.read_text())
    ratio = guard["time_ratio_on_over_off"]
    spread = guard["aa_spread"]
    add("per_node_cost_guard_pass",
        guard["verdict"] == "PASS" and ratio <= guard["limit"]
        and spread < guard["spread_limit"],
        {"ratio": ratio, "limit": guard["limit"], "aa_spread": spread})
    eff_path = ROOT / "benchmarks/recovery/exp0066_continuation_lifetime_diagnostic.json"
    eff = json.loads(eff_path.read_text())
    add("sequential_efficacy_gate_pass",
        eff["gate_pass"] and eff["overall_ratio"] <= eff["gate_overall_max"]
        and eff["majority_condition"],
        {"overall_ratio": eff["overall_ratio"], "games_improving": eff["games_at_or_below_1"],
         "games": eff["games"]})
    plan = json.loads((ROOT / "benchmarks/exp-runs/tier1-plan-exp0066.json").read_text())
    add("gate_digests_pinned_in_plan",
        plan["pregame_gates"]["per_node_cost"]["evidence_sha256"] == sha(guard_path)
        and plan["pregame_gates"]["efficacy"]["evidence_sha256"] == sha(eff_path),
        "plan pins both gate digests")
    mut = json.loads((ROOT / "benchmarks/recovery/exp0066_mutation_matrix.json").read_text())
    add("mutation_matrix_pass", mut["verdict"] == "PASS" and mut["killed"] == mut["killable"]
        and mut["killable"] >= 8 and mut["controls_survived"] == 2,
        {"killed": mut["killed"], "killable": mut["killable"]})
    uci = json.loads((ROOT / "benchmarks/recovery/exp0066_uci_lifetime.json").read_text())
    uchecks = {c["name"]: c["pass"] for c in uci["checks"]}
    add("uci_lifetime_oracle_pass",
        uci["verdict"] == "PASS" and len(uchecks) == 6 and all(uchecks.values())
        and uchecks.get("cross_game_isolation_on") is True
        and uchecks.get("cross_configuration_isolation_on") is True, uchecks)
    frozen = subprocess.run(
        ["git", "log", "--format=%H", "--", PREREG_PATH],
        cwd=ROOT, capture_output=True, text=True, check=True).stdout.split()
    add("prereg_single_commit_never_edited", len(frozen) == 1, frozen)
    add("prereg_digest_matches_plan", sha(ROOT / PREREG_PATH) == PREREG, PREREG)
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", SOURCE, "HEAD"],
        cwd=ROOT, capture_output=True, text=True)
    add("freeze_is_ancestor_of_head", ancestor.returncode == 0, SOURCE)

    fps, cfgs, dirs = {}, {}, {}
    for short in GAMES:
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
    opt_ok = all(opts[k]["a"].get("evalparams") == RACE
                 and opts[k]["b"].get("evalparams") == RACE
                 and opts[k]["a"].get("tteval") == "true"
                 and opts[k]["b"].get("tteval") == "true" for k in GAMES)
    add("explicit_eval_options", opt_ok, opts)
    sw = {k: {"a": opts[k]["a"].get(SWITCH), "b": opts[k]["b"].get(SWITCH)} for k in GAMES}
    add("explicit_switch_values",
        all((sw[k]["a"], sw[k]["b"]) == WANT_SWITCH[k] for k in GAMES), sw)
    add("primary_arms_differ_only_by_switch",
        all(opts[k]["a"] != opts[k]["b"]
            and {x: v for x, v in opts[k]["a"].items() if x != SWITCH}
            == {x: v for x, v in opts[k]["b"].items() if x != SWITCH}
            for k in ("batchA", "batchB")), "primary arms identical except the switch")
    add("shipped_default_is_off",
        all(str(c["engine_a_defaults"].get(SWITCH, "")).lower() == "false"
            for c in cfgs.values()),
        {k: c["engine_a_defaults"].get(SWITCH) for k, c in cfgs.items()})
    add("identical_recorded_defaults",
        all(c["engine_a_defaults"] == c["engine_b_defaults"] for c in cfgs.values()),
        "engine_a_defaults == engine_b_defaults in every job")

    for k in ("stage0", "null"):
        ci = jobs[k]["stats"]["elo_ci95"]
        add(f"{k}_null_includes_zero", ci[0] < 0 < ci[1], ci)
    add("auditor_issues_zero", a["issues"] == [], a["issues"])
    blobs_ok, blobs_total = a["committed_blobs"].split("/")
    add("committed_blobs", blobs_ok == blobs_total and int(blobs_total) > 0, a["committed_blobs"])
    sums_ok, sums_total = a["checksums"].split("/")
    add("per_job_checksums", sums_ok == sums_total and int(sums_total) > 0, a["checksums"])
    add("option_load_proof", all(len(v) >= 2 for v in a["option_load_proof"].values()),
        a["option_load_proof"])
    replay = {k: jobs[k]["pgn_replay"] for k in GAMES}
    add("pgn_replay_7800",
        sum(replay[k]["games_replayed"] for k in GAMES) == sum(GAMES.values())
        and all(replay[k]["games_replayed"] == GAMES[k] and replay[k]["inconsistent"] == 0
                for k in GAMES), replay)
    add("zero_failures", all(jobs[k]["time_forfeits"] == 0 and jobs[k]["illegal"] == 0
                             and jobs[k]["engine_failures"] == 0 for k in GAMES), True)
    suite = json.loads((ROOT / "benchmarks/recovery/exp0066_suite_verification.json").read_text())
    add("openings_disjoint", suite["verdict"] == "PASS", suite.get("issues"))
    log = (dirs["stage0"] / "run.log").read_text()
    add("stage0_ctest_21", "100% tests passed out of 21" in log and "ctest PASS" in log,
        "stage0 run.log")
    add("feature_enabled_in_both_arms",
        all(opts[k]["a"].get("continuationhistory") == "true"
            and opts[k]["b"].get("continuationhistory") == "true" for k in GAMES),
        {k: (opts[k]["a"].get("continuationhistory"), opts[k]["b"].get("continuationhistory"))
         for k in GAMES})

    comb = jobs["_combined"]["stats"]
    ba, bb = jobs["batchA"]["stats"]["elo"], jobs["batchB"]["stats"]["elo"]
    valid = all(c["pass"] for c in checks.values())
    advance = valid and comb["elo"] >= 15 and comb["elo_ci95"][0] > 0 and ba >= -5 and bb >= -5
    close = valid and (comb["elo_ci95"][1] < 5 or comb["elo"] <= 0)
    verdict = "INVALID" if not valid else ("SCREEN_ADVANCE" if advance else ("CLOSED" if close else "INCONCLUSIVE"))
    out = {"experiment": "exp0066", "decision_rule": {"advance_point_min": 15, "advance_lcb_min_exclusive": 0, "advance_each_batch_min": -5, "close_ucb_max_exclusive": 5, "close_point_max": 0}, "run_id": RUN_ID, "export_run_id": EXPORT_RUN_ID,
           "source_sha": SOURCE, "valid": valid, "checks": checks, "combined": comb,
           "batchA_elo": ba, "batchB_elo": bb, "verdict": verdict, "gate1_met": False,
           "per_node_cost_guard": {"time_ratio": ratio, "aa_spread": spread,
                                   "limit": guard["limit"]},
           "sequential_efficacy": {"overall_ratio": eff["overall_ratio"],
                                   "games_improving": eff["games_at_or_below_1"]},
           "note": "Persistent continuation-history increment screen on threats+race; ContinuationHistory=true in BOTH arms; "
                   "same-binary ablation, not integral vs dev5 and not Gate 1."}
    dest = ROOT / "benchmarks/recovery/exp0066_validity.json"
    dest.write_text(json.dumps(out, indent=2) + "\n")
    print(verdict, "valid=", valid, "elo=", comb["elo"], "ci=", comb["elo_ci95"])
    return 0 if valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
