#!/usr/bin/env python3
"""Condition-by-condition validity/screen decision check for exp-0064.

Does not trust the audit banner. Reads the independent raw audit JSON, exported
fingerprints and raw per-job configurations, the frozen prospective search-cost
guard and the independently re-derived suite verification. Fails closed if an
expected identity field is missing. Primary = batchA+batchB only (6,000 games);
nulls are never pooled. This is a SCREEN, not Gate 1.

The candidate is a SEARCH switch, so the frozen prospective cost evidence is
benchmarks/recovery/exp0064_search_cost_guard.json (fixed-depth wall-time A/B),
not the evaluate()-cost instrument; see prereg section 5.7.
"""
from __future__ import annotations
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUN_ID = 42379450457
EXPORT_RUN_ID = 0  # set after the explicit export run; asserted before closure
D = ROOT / f"benchmarks/exp-runs/tier1-export/run-{RUN_ID}"
SOURCE = "48a6110104448b3e3197286c2216d21cf047aba0"
PREREG = "0f29d36bb5725df062f293cdfaa6237914ec8b44af7778c622931d26890d0cfc"
PREREG_PATH = "docs/DEV6_PREREG_EXP0064.md"
RACE = "research-data/params_exp0055_race.txt"
GAMES = {"batchA": 3000, "batchB": 3000, "null": 1200, "stage0": 600}
SWITCH = "ttextensionagnostic"
# arm -> (A switch value, B switch value); EvalParams is RACE on every arm.
WANT_SWITCH = {"batchA": ("true", "false"), "batchB": ("true", "false"),
               "null": ("true", "true"), "stage0": ("false", "false")}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    assert EXPORT_RUN_ID, "EXPORT_RUN_ID must be set before closure"
    a = json.loads((ROOT / "benchmarks/recovery/exp0064_independent_raw_audit.json").read_text())
    jobs = a["jobs"]
    checks = {}

    def add(name, ok, detail):
        checks[name] = {"pass": bool(ok), "detail": detail}
        if not ok:
            print("FAIL", name, detail)

    # --- prospective cost guard, frozen and committed BEFORE the dispatch ----
    guard_path = ROOT / "benchmarks/recovery/exp0064_search_cost_guard.json"
    guard = json.loads(guard_path.read_text())
    ratios = {d: r["time_ratio_on_over_off"] for d, r in guard["results"].items()}
    spreads = {d: r["aa_spread"] for d, r in guard["results"].items()}
    add("search_cost_guard_pass",
        guard["verdict"] == "PASS"
        and all(v <= guard["limit"] for v in ratios.values())
        and all(v < guard["spread_limit"] for v in spreads.values()),
        {"ratios": ratios, "limit": guard["limit"], "spreads": spreads})
    add("search_cost_guard_sha_pinned_in_plan",
        json.loads((ROOT / "benchmarks/exp-runs/tier1-plan-exp0064.json").read_text())
        ["search_cost_guard"]["evidence_sha256"] == sha(guard_path),
        "plan pins the guard digest")
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
    suite = json.loads((ROOT / "benchmarks/recovery/exp0064_suite_verification.json").read_text())
    add("openings_disjoint", suite["verdict"] == "PASS", suite.get("issues"))
    log = (dirs["stage0"] / "run.log").read_text()
    add("stage0_ctest_19", "100% tests passed out of 19" in log and "ctest PASS" in log,
        "stage0 run.log")

    comb = jobs["_combined"]["stats"]
    ba, bb = jobs["batchA"]["stats"]["elo"], jobs["batchB"]["stats"]["elo"]
    valid = all(c["pass"] for c in checks.values())
    advance = valid and comb["elo"] >= 10 and comb["elo_ci95"][0] > 0 and ba >= -5 and bb >= -5
    close = valid and (comb["elo_ci95"][1] < 3 or comb["elo"] <= 0)
    verdict = "INVALID" if not valid else ("SCREEN_ADVANCE" if advance else ("CLOSED" if close else "INCONCLUSIVE"))
    out = {"experiment": "exp0064", "run_id": RUN_ID, "export_run_id": EXPORT_RUN_ID,
           "source_sha": SOURCE, "valid": valid, "checks": checks, "combined": comb,
           "batchA_elo": ba, "batchB_elo": bb, "verdict": verdict, "gate1_met": False,
           "search_cost_guard": {"time_ratios": ratios, "aa_spreads": spreads,
                                 "limit": guard["limit"]},
           "note": "Extension-agnostic main-TT identity increment screen on threats+race; "
                   "same-binary ablation, not integral vs dev5 and not Gate 1."}
    dest = ROOT / "benchmarks/recovery/exp0064_validity.json"
    dest.write_text(json.dumps(out, indent=2) + "\n")
    print(verdict, "valid=", valid, "elo=", comb["elo"], "ci=", comb["elo_ci95"])
    return 0 if valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
