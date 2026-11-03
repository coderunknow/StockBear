#!/usr/bin/env python3
"""exp-0032: draw-aware Bradley-Terry-Davidson rating fit + bootstrap.

Reads the raw game records of the 40 decisive ladder cells and fits a
multi-opponent BTD model (explicit draw parameter) by maximum likelihood.
Reports pool-specific INTERNAL ratings with opening-cluster bootstrap CIs,
per-pairing residuals, games per pairing, leave-one-anchor-out sensitivity, and
an explicitly QUALIFIED contextual calibration to Stockfish 11's own UCI_Elo
self-rating. NO absolute/CCRL/FIDE-comparable Elo is claimed.
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import minimize

ROOT = Path(__file__).resolve().parents[1]
CELLS = ROOT / "benchmarks" / "dev6-baseline" / "ladder_cells.json"
OUT = ROOT / "benchmarks" / "dev6-baseline" / "ladder_results.json"
MD = ROOT / "docs" / "DEV6_EXTERNAL_LADDER_REPORT.md"
ELO_K = 400.0 / math.log(10.0)   # 173.7178: Elo = ELO_K * (r_i - r_j)


def load_games():
    meta = json.loads(CELLS.read_text())
    games, cells = [], []
    for c in meta["cells"]:
        if "error" in c:
            continue
        d = ROOT / "benchmarks" / "exp-runs" / f"exp0032-ladder-{c['anchor']}-{c['subject']}"
        recs = []
        for line in (d / "match.jsonl").read_text().splitlines():
            o = json.loads(line)
            if "game" in o and o.get("score_a") is not None:
                recs.append(o)
        recs.sort(key=lambda r: r["game"])
        for k in range(0, len(recs) - 1, 2):
            if k + 1 >= len(recs):
                continue
            a, b = recs[k], recs[k + 1]
            for x in (a, b):
                games.append({"i": c["subject"], "j": c["anchor"],
                              "score": x["score_a"], "cluster": x["opening"],
                              "cell": d.name})
        cells.append({"subject": c["subject"], "anchor": c["anchor"],
                      "games": c["games_completed"], "score": c["score"],
                      "ci95": c["ci95"]})
    return games, cells


def fit(games, engines):
    idx = {e: k for k, e in enumerate(engines)}
    n = len(engines)
    I = np.array([idx[g["i"]] for g in games], dtype=int)
    J = np.array([idx[g["j"]] for g in games], dtype=int)
    S = np.array([g["score"] for g in games], dtype=float)
    W = (S == 1.0).astype(float)
    D = (S == 0.5).astype(float)
    L = (S == 0.0).astype(float)

    def nll(p):
        r = p[:n]
        r = r - r.mean()
        nu = math.exp(min(20.0, max(-20.0, p[n])))
        d = r[I] - r[J]
        # log-sum-exp stabilised denominator log Z, Z = e^{d/2}+e^{-d/2}+2nu
        h = 0.5 * d
        m = np.maximum(np.abs(h), np.log(2 * nu) - math.log(2))
        # log Z = log(2cosh(h) + 2nu)
        lz = np.log(2 * np.cosh(h) + 2 * nu)
        ll = W * (h - lz) + D * (math.log(2 * nu) - lz) + L * (-h - lz)
        return -float(ll.sum())

    p0 = np.zeros(n + 1)
    p0[n] = math.log(0.5)
    res = minimize(nll, p0, method="L-BFGS-B",
                   bounds=[(-20, 20)] * n + [(-6, 6)],
                   options={"maxiter": 2000, "ftol": 1e-11})
    r = res.x[:n]
    r = r - r.mean()
    nu = math.exp(res.x[n])
    # predicted probabilities (for residuals / fit)
    return {"r": r, "nu": nu, "nll": float(res.fun), "success": bool(res.success),
            "elo": r * ELO_K, "_fun": nll}


def main():
    if not CELLS.exists():
        print("no ladder_cells.json yet (run scripts/dev6_ladder.py first)")
        return
    games, cells = load_games()
    if not games:
        print("no ladder games found (run scripts/dev6_ladder.py first)")
        return
    engines = sorted({g["i"] for g in games} | {g["j"] for g in games})
    base = fit(games, engines)
    n = len(engines)
    idx = {e: k for k, e in enumerate(engines)}

    # opening-cluster bootstrap: resample distinct openings (each = one pair)
    clusters = sorted({g["cluster"] for g in games})
    by_cluster = {}
    for g in games:
        by_cluster.setdefault(g["cluster"], []).append(g)
    rng = np.random.default_rng(20261110)
    reps, boot = 1000, []
    keys = np.array(clusters)
    for _ in range(reps):
        sample = rng.choice(len(keys), size=len(keys), replace=True)
        gs = []
        for s in sample:
            gs.extend(by_cluster[keys[s]])
        try:
            f = fit(gs, engines)
            boot.append(f["elo"])
        except Exception:
            continue
    B = np.asarray(boot)
    lo, hi = np.percentile(B, [2.5, 97.5], axis=0)
    ratings = [{"engine": e, "internal_elo": float(base["elo"][idx[e]]),
                "ci95": [float(lo[idx[e]]), float(hi[idx[e]])],
                "games": sum(1 for g in games if g["i"] == e or g["j"] == e)}
               for e in engines]

    # residuals: observed vs predicted score per cell
    nu = base["nu"]
    residuals = []
    for c in cells:
        r_i = base["r"][idx[c["subject"]]]
        r_j = base["r"][idx[c["anchor"]]]
        h = 0.5 * (r_i - r_j)
        lz = math.log(2 * math.cosh(h) + 2 * nu)
        pw = math.exp(h - lz)
        pd = math.exp(math.log(2 * nu) - lz)
        pred = pw + 0.5 * pd
        residuals.append({"subject": c["subject"], "anchor": c["anchor"],
                          "games": c["games"], "observed": c["score"],
                          "predicted": round(pred, 4),
                          "residual": round(c["score"] - pred, 4),
                          "elo_ci95": c["ci95"]})
    rmse = math.sqrt(np.mean([x["residual"] ** 2 for x in residuals]))

    # leave-one-anchor-out sensitivity: does the subject ORDER change?
    anchors = sorted({g["j"] for g in games})
    loo = []
    for a in anchors:
        gs = [g for g in games if g["j"] != a]
        en2 = sorted({g["i"] for g in gs} | {g["j"] for g in gs})
        try:
            f = fit(gs, en2)
            order = sorted([e for e in en2 if e.startswith("dev")],
                           key=lambda e: -f["elo"][{x: k for k, x in enumerate(en2)}[e]])
            loo.append({"dropped_anchor": a, "subject_order": order,
                        "fitted": True})
        except Exception as ex:
            loo.append({"dropped_anchor": a, "fitted": False, "note": str(ex)})

    # QUALIFIED contextual calibration: SF11's own UCI_Elo self-rating anchor.
    # E = 1346.6 + 143.4 * level^0.806 (SF11 src/search.cpp). This is an
    # approximate, DIFFERENT time control / self-reported scale: used ONLY to
    # give an order-of-magnitude context, NEVER a certified absolute rating.
    mapping = {"sf11-L4": 4, "sf11-L8": 8, "sf11-L12": 12,
               "sf11-L16": 16, "sf11-L20": 20}
    xs, ys = [], []
    for a, lvl in mapping.items():
        if a in idx:
            xs.append(base["elo"][idx[a]])
            ys.append(1346.6 + 143.4 * lvl ** 0.806)
    calib = {"status": "NOT DEFENSIBLY CALIBRATED",
             "note": ("SF11 UCI_Elo is an approximate self-rating for a different "
                      "time control (60+0.6) and full-strength SF; mapping a "
                      "fixed-node pool onto it is a rough context only. The gap "
                      "to 3000 Elo is NOT asserted.")}
    if len(xs) >= 3:
        A = np.vstack([np.asarray(xs), np.ones(len(xs))]).T
        slope, intercept = np.linalg.lstsq(A, np.asarray(ys), rcond=None)[0]
        pred = slope * np.asarray(xs) + intercept
        resid_sd = float(np.std(ys - pred, ddof=2))
        dev5 = next((r for r in ratings if r["engine"] == "dev5_official"), None)
        calib.update({
            "slope": float(slope), "intercept": float(intercept),
            "anchor_residual_sd_elo": resid_sd,
            "sf11_anchor_points": [{"anchor": a, "internal_elo": float(x),
                                    "sf11_UCI_Elo_context": float(y)}
                                   for a, x, y in zip(mapping, xs, ys)],
            "dev5_official_approximate_context_elo":
                (float(slope * dev5["internal_elo"] + intercept) if dev5 else None),
            "caveat": ("Systematic error is unknown and likely large; this number "
                       "is CONTEXT, not a measured absolute rating, and must not "
                       "be used to claim a gap to 3000 or any CCRL equivalence.")})

    obs_draw = float(np.mean([g["score"] == 0.5 for g in games]))
    result = {
        "experiment": "exp-0032", "prereg": "docs/DEV6_PREREG_EXP0031.md",
        "model": "Bradley-Terry-Davidson (draw-aware), MLE, sum(r)=0",
        "scale": "pool-specific INTERNAL rating; Elo units = (400/ln10)*r; NOT CCRL/FIDE comparable",
        "engines": engines, "games": len(games), "clusters": len(clusters),
        "draw_parameter_nu": base["nu"], "observed_draw_rate": obs_draw,
        "nll": base["nll"], "fit_success": base["success"],
        "bootstrap_replicates": len(B), "residual_rmse": rmse,
        "ratings": ratings, "games_per_pairing": cells,
        "residuals": residuals, "leave_one_anchor_out": loo,
        "contextual_calibration": calib,
        "saturated_cells": [c["anchor"] for c in cells if c["score"] <= 0.05 or c["score"] >= 0.95],
    }
    OUT.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")

    L = ["# exp-0032 — external rating ladder results (pool-specific INTERNAL rating)", "",
         f"Model: **Bradley-Terry-Davidson** (draw-aware, nu = {base['nu']:.3f}) fitted by MLE "
         f"on **{len(games)} games** across **{len(clusters)} distinct openings** and "
         f"{len(engines)} engines. Opening-cluster bootstrap: {len(B)} replicates, two-sided "
         "95% percentile CIs. This is an INTERNAL ladder on a FIXED-NODE control "
         "(`--nodes 6000`, 40+4 clock not used), this hardware, these exact pinned binaries. "
         "It is NOT a 40+4 fixed-time Elo, NOT CCRL/CEGT/FIDE-comparable.", "",
         "## Estimated internal ratings (mean 0 by construction)", "",
         "| engine | internal Elo | 95% CI | games |", "|---|---|---|---|"]
    for r in sorted(ratings, key=lambda x: -x["internal_elo"]):
        L.append(f"| {r['engine']} | {r['internal_elo']:+.1f} | "
                 f"[{r['ci95'][0]:+.1f}, {r['ci95'][1]:+.1f}] | {r['games']} |")
    L += ["", f"Observed draw rate {obs_draw:.3f}; fit NLL {base['nll']:.1f}; "
          f"per-cell residual RMSE {rmse:.3f}; converged {base['success']}.", "",
          "## Games per pairing / residuals (full table)", "",
          "| subject | anchor | games | observed score | predicted | residual | Elo CI |",
          "|---|---|---|---|---|---|---|"]
    for x in residuals:
        L.append(f"| {x['subject']} | {x['anchor']} | {x['games']} | "
                 f"{x['observed']:.3f} | {x['predicted']:.3f} | {x['residual']:+.3f} | "
                 f"{x['elo_ci95']} |")
    L += ["", "## Rating-pool coverage, model fit, sensitivity", "",
          f"- Rating range: {min(r['internal_elo'] for r in ratings):+.1f} .. "
          f"{max(r['internal_elo'] for r in ratings):+.1f} internal Elo.",
          f"- Saturated cells (score <=0.05 or >=0.95): "
          f"{sorted(set(result['saturated_cells']))} — retained, never hidden.",
          "- Leave-one-anchor-out subject order:"]
    for x in loo:
        L.append(f"  - drop {x['dropped_anchor']}: "
                 f"{' > '.join(x.get('subject_order', [])) if x['fitted'] else 'fit failed'}")
    L += ["", "## Contextual calibration (QUALIFIED, not a claim)", "",
          f"- Status: **{calib['status']}**. {calib['note']}"]
    if "slope" in calib:
        L += [f"- Rough affine context from SF11's own `UCI_Elo` anchors "
              f"(slope {calib['slope']:.3f}, intercept {calib['intercept']:.1f}, "
              f"anchor residual SD {calib['anchor_residual_sd_elo']:.0f} Elo): "
              f"dev5-official ≈ **{calib['dev5_official_approximate_context_elo']:.0f} Elo "
              "context**. This is an approximate SELF-anchored number with unknown, "
              "likely large systematic error.", ""]
        for p in calib["sf11_anchor_points"]:
            L.append(f"- {p['anchor']}: internal {p['internal_elo']:+.1f} vs "
                     f"SF11 UCI_Elo context {p['sf11_UCI_Elo_context']:.0f}")
    L += ["", "**The numeric gap to 3,000 Elo is NOT defensible from this pool and is NOT "
          "asserted.** 3,000 Elo remains a long-term strategic target. Published CCRL "
          "ratings and SF11 UCI_Elo are contextual anchors only.", "",
          "Raw: `benchmarks/exp-runs/exp0032-ladder-*/` (PGN/JSONL/CSV/cell.json), "
          "`benchmarks/dev6-baseline/ladder_cells.json`, machine-readable "
          "`benchmarks/dev6-baseline/ladder_results.json`. Opponent identities: "
          "`docs/DEV6_EXTERNAL_OPPONENTS.md`."]
    MD.write_text("\n".join(L) + "\n")
    print(json.dumps({"games": len(games), "engines": len(engines),
                      "nu": round(base["nu"], 3), "rmse": round(rmse, 4),
                      "ratings": {r["engine"]: round(r["internal_elo"], 1) for r in ratings},
                      "calib": calib["status"]}, indent=2))
    print("wrote", OUT, MD)


if __name__ == "__main__":
    main()
