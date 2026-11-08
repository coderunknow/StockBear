#!/usr/bin/env python3
"""exp-0068 plan generator. Arm values are EXPLICIT per arm, never a single flag.

exp-0067 was invalidated because one `persist` flag was emitted into both arms.
Here the treatment and control option sets are built by two separate calls with
literal booleans, and the contrast is asserted before the file is written. The
independent pre-dispatch validator is still mandatory and runs afterwards.
"""
from __future__ import annotations
import hashlib, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sha = lambda p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest()

PREREG = "docs/DEV6_PREREG_EXP0068.md"
PSHA = "7bc1bfc2a74fc97331db976e5a423a6dc6b3d527cdc6e558aa19e650c52be158"
RACE = "research-data/params_exp0055_race.txt"
assert sha(PREREG) == PSHA, "prereg digest changed - it must never be edited"

COMMON = {"prereg": PREREG, "prereg_sha256": PSHA,
          "build_flags": "-mpopcnt -mbmi2 -mlzcnt -DSB_SEE_CACHE=1 -flto=4",
          "hash": 16, "threads": 1, "max_plies": 240,
          "control": {"base_ms": 40, "inc_ms": 4},
          "assets": [RACE], "engine_a": "candidate", "engine_b": "candidate"}


def options(history: bool, continuation: bool):
    """Explicit, independent values. The two are passed separately by the caller."""
    return [f"EvalParams={RACE}", "TTEval=true", "ContinuationHistory=true",
            f"PersistentHistory={'true' if history else 'false'}",
            f"PersistentContinuation={'true' if continuation else 'false'}"]


TREATMENT = options(True, True)    # arm A of the primary batches
CONTROL = options(False, False)    # arm B of the primary batches
assert TREATMENT != CONTROL, "no causal contrast"


def job(jid, games, seed, sl, null, ctest, a_opts, b_opts, note):
    j = dict(COMMON)
    j.update({"id": jid, "games": games, "seed": seed,
              "openings": f"benchmarks/positions/openings_exp0068_{sl}.txt",
              "null": null, "ctest": ctest,
              "a_options": list(a_opts), "b_options": list(b_opts), "note": note})
    return j


gates = {
    "composition_audit": {"evidence": "benchmarks/recovery/exp0067_composition_audit.json",
                          "evidence_sha256": sha("benchmarks/recovery/exp0067_composition_audit.json"),
                          "verdict": "PASS", "reused_from": "exp-0067 mechanism work (not its invalid games)"},
    "efficacy": {"evidence": "benchmarks/recovery/exp0067_joint_lifetime_diagnostic.json",
                 "evidence_sha256": sha("benchmarks/recovery/exp0067_joint_lifetime_diagnostic.json"),
                 "gate_overall_ratio_max": 0.98, "observed_overall_ratio": 0.974289,
                 "games_improving": 18, "games_total": 20, "verdict": "PASS"},
    "per_node_cost": {"evidence": "benchmarks/recovery/exp0067_node_cost_guard.json",
                      "evidence_sha256": sha("benchmarks/recovery/exp0067_node_cost_guard.json"),
                      "limit": 1.10, "observed_ratio": 1.026725, "aa_spread": 0.032082,
                      "verdict": "PASS", "eval_cost_gate_applicable": False},
    "mutations": {"evidence": "benchmarks/recovery/exp0067_mutation_matrix.json",
                  "evidence_sha256": sha("benchmarks/recovery/exp0067_mutation_matrix.json"),
                  "killed": 14, "killable": 14, "controls_survived": 3, "verdict": "PASS"},
    "uci_lifetime": {"evidence": "benchmarks/recovery/exp0067_uci_joint_lifetime.json",
                     "evidence_sha256": sha("benchmarks/recovery/exp0067_uci_joint_lifetime.json"),
                     "checks": 8, "verdict": "PASS"},
    "suites": {"evidence": "benchmarks/recovery/exp0068_suite_verification.json", "verdict": "PASS"},
    "plan_validation": {"evidence": "benchmarks/recovery/exp0068_plan_validation.json",
                        "validator": "scripts/recovery_validate_plan.py",
                        "validator_sha256": sha("scripts/recovery_validate_plan.py"),
                        "required_verdict": "SAFE_TO_DISPATCH",
                        "binding": "the validation JSON records plan_sha256; it must equal the dispatched plan digest (avoids a circular digest pin)",
                        "reason": "exp-0067 was INVALID because both arms carried the intervention; this gate proves the contrast exists BEFORE games"},
    "bench_signatures": {"4": "243f9a1c1ba5b36f", "6": "e06c4352681ae8eb", "7": "5bceff035f2a4ae4"},
    "registered_test_groups": 22,
    "pregame_signal": "Joint node ratio 0.974289 is WORSE than either single table (0.965386 / 0.966264); per-node cost 1.026725 gives time-to-depth ~1.0003, essentially neutral and worse than exp-0066's ~0.938. Disclosed before the games; weakens the prior. Not an Elo estimate.",
}

plan = {
    "experiment_id": "exp0068", "frozen_before_evaluation_games": True,
    "prereg": PREREG, "prereg_sha256": PSHA, "prereg_freeze_commit": "8a5498d",
    "control": "FIXED TIME 40+4 ms; never --nodes",
    "tier": "SCREEN of JOINT persistence of graded ordering state (not Gate-1)",
    "design": "SAME-BINARY ablation; ContinuationHistory=true in BOTH arms; arm A ages BOTH graded tables, arm B erases BOTH; primary batches do not play dev5",
    "mechanism": "age-instead-of-erase applied to history_ AND continuation_ at the same reset site",
    "new_search_semantics": False,
    "why_new_id": "exp-0067 CLOSED INVALID (author plan defect set the intervention in both arms). Its prereg section 8 requires a new experiment id for any rerun after games. No valid measurement of this contrast has ever existed, so thresholds are not result-informed.",
    "attribution": "ONE intervention, ONE state class, ONE site; both options always move together. Claim is for the JOINT configuration only; never decomposed.",
    "counter_move_persistence": "excluded (categorical, saturates after one write)",
    "no_pooling_with_earlier_experiments": True,
    "pools_exp0065_games": False, "pools_exp0066_games": False, "pools_exp0067_games": False,
    "never_sum_individual_elo": True,
    "frozen_combined": "batchA + batchB ONLY (6000 games)",
    "candidate_config": RACE, "candidate_config_sha256": sha(RACE),
    "ablation_config": RACE, "ablation_config_sha256": sha(RACE),
    "frozen_switch": {"names": ["PersistentHistory", "PersistentContinuation"],
                      "a": [True, True], "b": [False, False],
                      "shipped_default": [False, False],
                      "feature_enabled_both_arms": "ContinuationHistory=true"},
    "baseline_binary": "benchmarks/binaries/stockbear-dev5-release",
    "baseline_binary_sha256": "391cb50e13ab99168aba0255482554ab5e59d1a34af810bf8f4d2c88e5bdb918",
    "baseline_note": "Provenance only; primary arms are the identical candidate binary.",
    "expected_binary_sha256": "36fe761f20f28a252a977e24bff9a0addf798088619cea97d047ebf202fd87c8",
    "openings_seed": 2026110668,
    "decision_rule": {"promote_point_min": 10, "promote_lcb_min_exclusive": 0,
                      "promote_each_batch_point_min": -5, "close_ucb_max_exclusive": 3,
                      "close_point_max": 0, "otherwise": "INCONCLUSIVE",
                      "provenance": "carried over UNCHANGED from exp-0067's frozen prereg; not result-informed",
                      "promote_authorises": "record joint config as champion candidate only; NO gate claim, merge, tag, release or deploy"},
    "pregame_gates": gates,
    "jobs": [
        job("tier1-exp0068-stage0", 600, 2026110792, "stage0", True, True,
            CONTROL, CONTROL, "Stage-0 null: erase vs erase on the packaged candidate; fresh ctest 22 groups"),
        job("tier1-exp0068-batchA", 3000, 2026110793, "batchA", False, False,
            TREATMENT, CONTROL, "SCREEN batchA: arm A ages BOTH graded tables, arm B erases BOTH"),
        job("tier1-exp0068-batchB", 3000, 2026110794, "batchB", False, False,
            TREATMENT, CONTROL, "SCREEN batchB: independent seed, disjoint openings"),
        job("tier1-exp0068-null", 1200, 2026110795, "null", True, False,
            TREATMENT, TREATMENT, "powered candidate null: treatment vs identical treatment; CI must include 0"),
    ],
}

# Self-check the contrast BEFORE writing (the exp-0067 lesson).
for j in plan["jobs"]:
    a = {k: v for k, v in (o.split("=", 1) for o in j["a_options"])}
    b = {k: v for k, v in (o.split("=", 1) for o in j["b_options"])}
    if j["null"]:
        assert a == b, f"{j['id']}: null arms must be identical"
    else:
        assert a != b, f"{j['id']}: PRIMARY ARMS IDENTICAL"
        diff = {k for k in set(a) | set(b) if a.get(k) != b.get(k)}
        assert diff == {"PersistentHistory", "PersistentContinuation"}, f"{j['id']}: {diff}"
        assert a["PersistentHistory"] == a["PersistentContinuation"] == "true"
        assert b["PersistentHistory"] == b["PersistentContinuation"] == "false"

dest = ROOT / "benchmarks/exp-runs/tier1-plan-exp0068.json"
dest.write_text(json.dumps(plan, indent=2) + "\n")
budget = {"experiment_id": "exp0068", "prereg": PREREG, "prereg_sha256": PSHA,
          "total_games": 7800, "primary_games": 6000, "null_games": 1200, "stage0_games": 600,
          "benchmark_jobs": 4, "benchmark_timeout_minutes": 420,
          "prepare_timeout_minutes": 10, "export_timeout_minutes": 10,
          "max_workflow_vm_minutes": 1700, "benchmark_dispatches": 1, "export_dispatches": 1,
          "paid_services": False, "adaptive_games": False, "result_driven_reruns": False,
          "infrastructure_retry": "only before any game, identical plan, documented; a failed null is INVALID",
          "openings_seed": 2026110668, "openings_count": 3900,
          "slices": {"stage0": 300, "null": 600, "batchA": 1500, "batchB": 1500}}
(ROOT / "benchmarks/recovery/exp0068_compute_budget.json").write_text(json.dumps(budget, indent=2) + "\n")
print("prereg", PSHA)
print("plan", sha("benchmarks/exp-runs/tier1-plan-exp0068.json"))
for j in plan["jobs"]:
    print(j["id"], "A:", [o for o in j["a_options"] if "Persistent" in o],
          "B:", [o for o in j["b_options"] if "Persistent" in o])