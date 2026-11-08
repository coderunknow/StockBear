#!/usr/bin/env python3
"""Pre-dispatch plan validator: catch arm-configuration defects BEFORE games.

Written after exp-0067 was invalidated by a plan-generation bug: a single
`persist` flag was passed to BOTH a_options and b_options, so the primary batches
ran treatment-vs-treatment (an accidental A/A null) instead of the ablation.
7,800 games were spent before the post-hoc validity script caught it.

This validator is deliberately cheap and runs BEFORE any dispatch. It asserts the
causal contrast actually exists in the plan:

  * primary (non-null) jobs: arm A and arm B must DIFFER, and must differ ONLY by
    the declared intervention options;
  * the declared intervention options must take the documented treatment value in
    A and control value in B;
  * null jobs: arms must be IDENTICAL (that is what makes them nulls);
  * every feature-enable option required by the design must be present in BOTH
    arms of every job (otherwise part of the intervention is a no-op);
  * EvalParams must be explicit and identical in both arms;
  * protocol, game counts and slice sizes must match the declared budget.

Usage: recovery_validate_plan.py PLAN.json --switches A=B [--switches ...]
       --feature KEY=VALUE [--feature ...] --primary batchA,batchB
Exit 0 = plan is safe to dispatch; exit 1 = defect, DO NOT DISPATCH.
"""
from __future__ import annotations
import argparse, hashlib, json, sys
from pathlib import Path


def parse_options(lst):
    out = {}
    for item in lst:
        if "=" not in item:
            raise ValueError(f"malformed option (expected KEY=VALUE): {item!r}")
        k, v = item.split("=", 1)
        out[k.strip().lower()] = v.strip()
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("--switches", action="append", required=True,
                    help="intervention option as NAME:TREATMENT:CONTROL, e.g. PersistentHistory:true:false")
    ap.add_argument("--feature", action="append", default=[],
                    help="option required in BOTH arms, e.g. ContinuationHistory=true")
    ap.add_argument("--primary", default="batchA,batchB")
    ap.add_argument("--nulls", default="null,stage0")
    ap.add_argument("--json")
    a = ap.parse_args()
    plan = json.loads(Path(a.plan).read_text())
    primary = {s.strip() for s in a.primary.split(",")}
    nulls = {s.strip() for s in a.nulls.split(",")}
    interventions = {}
    for spec in a.switches:
        name, treat, ctrl = spec.split(":")
        interventions[name.lower()] = (treat.lower(), ctrl.lower())
    features = {}
    for spec in a.feature:
        k, v = spec.split("=", 1)
        features[k.lower()] = v.lower()

    checks, problems = {}, []

    def add(name, ok, detail):
        checks[name] = {"pass": bool(ok), "detail": detail}
        if not ok:
            problems.append(name)

    jobs = plan["jobs"]
    seen = set()
    for j in jobs:
        jid = j["id"]
        short = next((s for s in list(primary) + list(nulls) if jid.endswith(s)), jid)
        seen.add(short)
        A, B = parse_options(j["a_options"]), parse_options(j["b_options"])
        is_null = bool(j.get("null")) or short in nulls
        # feature enables in BOTH arms
        add(f"{short}_features_in_both_arms",
            all(A.get(k) == v and B.get(k) == v for k, v in features.items()),
            {"required": features, "a": {k: A.get(k) for k in features},
             "b": {k: B.get(k) for k in features}})
        # explicit identical eval params
        add(f"{short}_evalparams_explicit_and_equal",
            A.get("evalparams") is not None and A.get("evalparams") == B.get("evalparams"),
            {"a": A.get("evalparams"), "b": B.get("evalparams")})
        if is_null:
            add(f"{short}_null_arms_identical", A == B,
                "null job: arms must be identical" if A == B else {"a": A, "b": B})
        else:
            add(f"{short}_arms_actually_differ", A != B,
                "PRIMARY ARMS ARE IDENTICAL - no causal contrast" if A == B else "arms differ")
            diff = {k for k in set(A) | set(B) if A.get(k) != B.get(k)}
            add(f"{short}_differ_only_by_intervention", diff == set(interventions),
                {"differing_keys": sorted(diff), "declared": sorted(interventions)})
            add(f"{short}_intervention_values_correct",
                all(A.get(k) == t and B.get(k) == c for k, (t, c) in interventions.items()),
                {k: {"a": A.get(k), "want_a": t, "b": B.get(k), "want_b": c}
                 for k, (t, c) in interventions.items()})
        add(f"{short}_protocol", j.get("control") == {"base_ms": 40, "inc_ms": 4}
            and j.get("hash") == 16 and j.get("threads") == 1 and j.get("max_plies") == 240,
            {k: j.get(k) for k in ("control", "hash", "threads", "max_plies")})
    add("all_expected_slices_present", primary | nulls <= seen, sorted(seen))
    add("primary_is_6000", sum(j["games"] for j in jobs
                               if any(j["id"].endswith(s) for s in primary)) == 6000,
        "primary game count")
    add("total_is_7800", sum(j["games"] for j in jobs) == 7800, "total game count")
    add("openings_slices_distinct", len({j["openings"] for j in jobs}) == len(jobs),
        "each job uses its own opening slice")
    out = {"plan": a.plan,
           "plan_sha256": hashlib.sha256(Path(a.plan).read_bytes()).hexdigest(),
           "checks": checks, "problems": problems,
           "verdict": "SAFE_TO_DISPATCH" if not problems else "DO_NOT_DISPATCH"}
    text = json.dumps(out, indent=2)
    if a.json:
        Path(a.json).write_text(text + "\n")
    for p in problems:
        print("DEFECT:", p, json.dumps(checks[p]["detail"])[:300])
    print(out["verdict"], f"({sum(c['pass'] for c in checks.values())}/{len(checks)} checks pass)")
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())