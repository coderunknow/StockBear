#!/usr/bin/env python3
"""Independent dev6 confirmation analysis from raw per-game records.

Reads the raw JSONL records committed by the free-runner lane under
benchmarks/exp-runs/<id>/match.jsonl, rebuilds the colour-reversed pairs,
recomputes the opening-clustered CR1 95% Student-t interval (the primary
estimator) with match_stats, and evaluates the pre-registered gates in
docs/DEV6_PREREG.md. Also reports paired pentanomial, W/D/L, score/Elo, SPRT
(clearly labelled a normal approximation), terminations, adversarial events, a
paired/cluster bootstrap CI and leave-one-shard-out sensitivity.

Outputs (regenerate after results arrive):
  benchmarks/dev6-baseline/confirmation_results.json
  docs/DEV6_CONFIRMATION_REPORT.md
"""
import glob
import json
import math
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import match_stats
from pool_matches import load_shard

ROOT = Path(__file__).resolve().parents[1]
EXP = ROOT / "benchmarks" / "exp-runs"
OUTJSON = ROOT / "benchmarks" / "dev6-baseline" / "confirmation_results.json"
OUTMD = ROOT / "docs" / "DEV6_CONFIRMATION_REPORT.md"

SCREENS = ["exp0027-screen", "exp0027-control", "exp0027-exp0020"]
BATCH_A = [f"exp0028-shard{i:02d}" for i in range(1, 7)]
BATCH_B = [f"exp0029-shard{i:02d}" for i in range(1, 7)]
NULLS = ["exp0028-null", "exp0029-null"]


def records_for(ids):
    """Return (ids_found, games, pair_scores, pair_openings, records, terminations).

    Null-only lane jobs write `null.jsonl`; match jobs write `match.jsonl`.
    """
    found, games, ps, po, recs, terms = [], [], [], [], [], {}
    for jid in ids:
        p = EXP / jid / "match.jsonl"
        if not p.exists() or "null" in jid:
            alt = EXP / jid / "null.jsonl"
            if alt.exists():
                p = alt
        if not p.exists():
            continue
        found.append(jid)
        g, s, o, u, r = load_shard(str(p))
        games += g
        ps += s
        po += o
        recs += r
        for x in r:
            t = x.get("termination", "?")
            terms[t] = terms.get(t, 0) + 1
    return found, games, ps, po, recs, terms


def elo(s):
    return match_stats.score_to_elo(s)


def adverse(recs):
    out = {"time_forfeit": 0, "illegal_move": 0, "crash_or_engine_failure": 0,
           "uci_failure": 0, "max_ply_unadjudicated": 0}
    for r in recs:
        t = str(r.get("termination", ""))
        tl = t.lower()
        if "forfeit" in tl or "time" in tl and "forfeit" in tl:
            out["time_forfeit"] += 1
        if "illegal" in tl:
            out["illegal_move"] += 1
        if "engine_failure" in tl or "crash" in tl:
            out["crash_or_engine_failure"] += 1
        if "uci" in tl:
            out["uci_failure"] += 1
        if "unadjudicated" in tl or "max_pl" in tl:
            out["max_ply_unadjudicated"] += 1
    return out


def analyse(ids):
    found, games, ps, po, recs, terms = records_for(ids)
    if not found:
        return None
    adjudicated = [g for g in games if g is not None]
    summ = match_stats.summarise(adjudicated, ps,
                                 match_stats.lmr_step(ps, 0.0, 5.0),
                                 pair_openings=po)
    cl = summ.get("opening_clustered", {})
    paired = summ.get("paired", {})
    # paired/cluster bootstrap (1 pair per opening in this design): resample pairs
    boot = None
    if len(ps) > 30:
        try:
            import numpy as np
            rng = np.random.default_rng(20261103)
            arr = np.asarray(ps, dtype=float)
            n = len(arr)
            idx = rng.integers(0, n, size=(2000, n))
            means = arr[idx].mean(axis=1) / 2.0
            mins = np.clip(means, 1e-9, 1 - 1e-9)
            elos = 400.0 * np.log10(mins / (1 - mins))
            lo, hi = np.percentile(elos, [2.5, 97.5])
            boot = {"replicates": 2000, "elo_ci95": [float(lo), float(hi)],
                    "note": "paired (cluster) bootstrap of colour-reversed pairs"}
        except Exception as e:  # numpy optional
            boot = {"note": f"bootstrap unavailable: {e}"}
    # leave-one-shard-out sensitivity on the shard point estimate
    loo = []
    if len(found) > 1:
        for drop in found:
            rest = [x for x in found if x != drop]
            _, g2, s2, o2, _, _ = records_for(rest)
            a2 = [g for g in g2 if g is not None]
            c2 = match_stats.opening_clustered(s2, o2)
            loo.append({"dropped": drop,
                        "elo": c2.get("elo_difference"),
                        "ci95": c2.get("elo_ci95")})
    return {
        "ids": found,
        "games_total": len(games),
        "games_adjudicated": len(adjudicated),
        "unadjudicated": len(games) - len(adjudicated),
        "wins": summ["wins"], "draws": summ["draws"], "losses": summ["losses"],
        "score_pct": round(100.0 * (summ["wins"] + 0.5 * summ["draws"]) / max(1, len(adjudicated)), 3),
        "pairs": len(ps),
        "clusters": cl.get("clusters"),
        "clustered_elo": cl.get("elo_difference"),
        "clustered_ci95": cl.get("elo_ci95"),
        "clustered_t": cl.get("critical_value"),
        "clustered_df": (cl.get("clusters") - 1) if cl.get("clusters") else None,
        "paired_elo": paired.get("elo_difference"),
        "paired_ci95": paired.get("elo_ci95"),
        "pentanomial": paired.get("pentanomial_counts_2_1.5_1_0.5_0"),
        "sprt": summ.get("sprt"),
        "terminations": terms,
        "adverse_events": adverse(recs),
        "cluster_bootstrap": boot,
        "leave_one_shard_out": loo,
    }


def fmt_e(v):
    return "n/a" if v is None else f"{v:+.1f}"


def fmt_ci(c):
    if not c or c[0] is None or c[1] is None:
        return "n/a"
    return f"[{c[0]:+.1f}, {c[1]:+.1f}]"


def main():
    data = {}
    analyses = {}
    for label, ids in ([("screen_primary", ["exp0027-screen"]),
                        ("screen_control", ["exp0027-control"]),
                        ("screen_exp0020", ["exp0027-exp0020"]),
                        ("batch_A", BATCH_A), ("batch_B", BATCH_B),
                        ("combined", BATCH_A + BATCH_B),
                        ("null_A", ["exp0028-null"]), ("null_B", ["exp0029-null"]),
                        ("null_combined", NULLS)]):
        analyses[label] = analyse(ids)

    # gate evaluation
    c = analyses["combined"]
    A, B = analyses["batch_A"], analyses["batch_B"]
    gates = {}
    if c and c["clustered_ci95"] and c["clustered_ci95"][0] is not None:
        point = c["clustered_elo"]
        lcb = c["clustered_ci95"][0]
        gates["gate1_point_ge_75"] = bool(point is not None and point >= 75.0)
        gates["gate1_lcb_gt_50"] = bool(lcb > 50.0)
        gates["gate2_both_batches_positive"] = bool(
            A and B and (A["clustered_elo"] or 0) > 0 and (B["clustered_elo"] or 0) > 0)
        # consistency: batch CIs overlap and |diff| < 2*sqrt(seA^2+seB^2)
        def hw(a):
            return (a["clustered_ci95"][1] - a["clustered_ci95"][0]) / 2 if a and a["clustered_ci95"] and a["clustered_ci95"][0] is not None else None
        hA, hB = hw(A), hw(B)
        gates["gate2_reasonably_consistent"] = bool(
            hA and hB and abs((A["clustered_elo"] or 0) - (B["clustered_elo"] or 0)) < 2 * math.hypot(hA / 1.96, hB / 1.96))
        na, nb = analyses["null_A"], analyses["null_B"]
        def null_ok(n):
            return bool(n and n["clustered_ci95"] and n["clustered_ci95"][0] is not None
                        and n["clustered_ci95"][0] <= 0 <= n["clustered_ci95"][1])
        gates["gate3_nulls_include_zero"] = bool(null_ok(na) and null_ok(nb))
        ev = c["adverse_events"]
        gates["gate4_no_unresolved_engine_failure"] = bool(
            ev["illegal_move"] == 0 and ev["crash_or_engine_failure"] == 0 and ev["uci_failure"] == 0)
        gates["all_pass"] = all(gates.values())
    verdict = "PASS" if gates.get("all_pass") else ("FAIL / GATE NOT MET" if c else "NO DATA YET")

    data = {"source": "raw benchmarks/exp-runs/<id>/match.jsonl committed by the free dev6 lane",
            "primary_estimator": "opening-clustered CR1 variance, two-sided 95% Student-t (G-1 df), logistic Elo",
            "prereg": "docs/DEV6_PREREG.md", "verdict": verdict,
            "gates": gates, "analyses": analyses}
    OUTJSON.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n")

    # ---- markdown report ----
    L = []
    L.append("# v0.1.0-dev6 — confirmation report (independently recomputed from raw records)")
    L.append("")
    L.append(f"**Verdict: {verdict}.** Recomputed by `scripts/dev6_confirmation_report.py` "
             "from the raw per-game JSONL committed by the free dev6 lane. Primary estimator: "
             "opening-clustered CR1 variance with a two-sided 95% Student-t interval (G-1 df) "
             "on the logistic Elo scale. Pre-registered in `docs/DEV6_PREREG.md` before any result.")
    L.append("")
    L.append("Baseline for every strength claim: the **exact released v0.1.0-dev5** portable "
             "binary `391cb50e…` at champion options (`params_abc.txt` + `TTEval=true`). "
             "Conditions: 40+4 ms, hash 16 MB, 1 thread, paired colour-reversed openings, "
             "dedicated isolated GitHub-hosted runners. dev6 candidate built with the exact "
             "portable release flags `-mpopcnt -mbmi2 -mlzcnt -DSB_SEE_CACHE=1 -flto=4`.")
    L.append("")
    L.append("## Results")
    L.append("")
    L.append("| scope | games | W/D/L | score % | clustered Elo | 95% CI | clusters (df) | paired Elo [CI] |")
    L.append("|---|---|---|---|---|---|---|---|")
    order = [("Screen: primary (params_dev6_a)", "screen_primary"),
             ("Screen: integrity control (params_abc)", "screen_control"),
             ("Screen: historical params_exp0020", "screen_exp0020"),
             ("Decisive batch A (exp-0028)", "batch_A"),
             ("Decisive batch B (exp-0029)", "batch_B"),
             ("**COMBINED decisive (Gate 1)**", "combined"),
             ("Null A (candidate vs identical)", "null_A"),
             ("Null B (candidate vs identical)", "null_B"),
             ("Null combined", "null_combined")]
    for name, key in order:
        a = analyses[key]
        if not a:
            L.append(f"| {name} | — | no data | | | | | |")
            continue
        L.append(f"| {name} | {a['games_total']} | +{a['wins']} ={a['draws']} -{a['losses']} | "
                 f"{a['score_pct']:.2f} | {fmt_e(a['clustered_elo'])} | {fmt_ci(a['clustered_ci95'])} | "
                 f"{a['clusters']} ({a['clustered_df']}) | {fmt_e(a['paired_elo'])} {fmt_ci(a['paired_ci95'])} |")
    L.append("")
    if c:
        L.append(f"Combined decisive point estimate **{fmt_e(c['clustered_elo'])} Elo**, "
                 f"95% CI **{fmt_ci(c['clustered_ci95'])}**, t={c['clustered_t']:.3f} on "
                 f"{c['clustered_df']} df, {c['games_total']} games over {c['clusters']} distinct "
                 "opening clusters. Naive Wilson is NOT used as the primary estimator; the two "
                 "games of an opening are never treated as independent.")
    L.append("")
    L.append("## Pentanomial, SPRT, terminations, adversarial events")
    L.append("")
    for name, key in order:
        a = analyses[key]
        if not a:
            continue
        sp = a["sprt"] or {}
        llr = sp.get("llr")
        L.append(f"- **{name}**: pair-score counts (2/1.5/1/0.5/0) = {a['pentanomial']}; "
                 f"SPRT (normal approximation) LLR = {llr if llr is not None else 'n/a'}; "
                 f"term-inations {a['terminations']}; unadjudicated {a['unadjudicated']}; "
                 f"adversarial events {a['adverse_events']}.")
    L.append("")
    L.append("Pre-declared handling (`docs/DEV6_PREREG.md` §4): TIME_FORFEIT, ILLEGAL_MOVE, "
             "CRASH/ENGINE_FAILURE, UCI failure, MAX_PLY/unadjudicated are recorded individually, "
             "never hidden; engine-caused illegal moves/crashes/protocol failures are losses for "
             "the offending engine; unadjudicated games are excluded from the score and counted. "
             "No outcome was silently changed or removed; the counts above are the sensitivity check.")
    L.append("")
    L.append("## Sensitivity")
    L.append("")
    if c and c["cluster_bootstrap"]:
        L.append(f"- Combined paired/cluster bootstrap (2000 replicates): "
                 f"{fmt_ci(c['cluster_bootstrap'].get('elo_ci95'))} Elo "
                 f"({c['cluster_bootstrap'].get('note','')}).")
    for key in ("batch_A", "batch_B"):
        a = analyses[key]
        if a and a["leave_one_shard_out"]:
            los = ", ".join(f"−{x['dropped'].split('-')[-1]}: {fmt_e(x['elo'])}" for x in a["leave_one_shard_out"])
            L.append(f"- {key} leave-one-shard-out point estimates: {los}.")
    L.append("")
    L.append("## Gate evaluation (thresholds frozen in the pre-registration)")
    L.append("")
    if gates:
        L.append("| gate | requirement | result |")
        L.append("|---|---|---|")
        desc = {
            "gate1_point_ge_75": "combined point estimate >= +75 Elo",
            "gate1_lcb_gt_50": "combined 95% CI lower bound strictly > +50 Elo",
            "gate2_both_batches_positive": "both decisive batches show a positive point estimate",
            "gate2_reasonably_consistent": "the two batches are reasonably consistent",
            "gate3_nulls_include_zero": "both nulls' 95% intervals include zero",
            "gate4_no_unresolved_engine_failure": "no unresolved illegal-move/crash/UCI-failure regression",
            "all_pass": "ALL gates pass",
        }
        for k, v in gates.items():
            L.append(f"| {k} | {desc.get(k,'')} | {'PASS' if v else 'FAIL'} |")
    L.append("")
    L.append("## Verdict and consequences")
    L.append("")
    if verdict == "PASS":
        L.append("All mandatory strength gates pass; proceed only after the remaining mandatory "
                 "audits (external ladder, exact-SHA CI/CodeRabbit, exact-head testing) and with "
                 "explicit user authorization for merge/tag/release.")
    else:
        L.append("**The mandatory strength gate is NOT met.** Per the mission: no strength claim, "
                 "no release PR, no merge, no tag, no release, no `0.1.0-dev7` auto-increment. "
                 "All raw results are preserved; the direction is diagnosed and logged in the "
                 "Failure Ledger; research continues on materially different hypotheses. The "
                 "external rating ladder status is documented separately "
                 "(`docs/DEV6_EXTERNAL_LADDER.md`).")
    L.append("")
    L.append("Raw data: `benchmarks/exp-runs/exp0027-*`, `exp0028-*`, `exp0029-*` "
             "(PGN + JSONL + CSV + manifest + logs). Machine-readable recomputation: "
             "`benchmarks/dev6-baseline/confirmation_results.json`.")
    OUTMD.write_text("\n".join(L) + "\n")
    print("verdict:", verdict)
    print("gates:", gates)
    print("wrote", OUTMD, "and", OUTJSON)


if __name__ == "__main__":
    main()
