#!/usr/bin/env python3
"""Scale-invariance audit of an accuracy gate (no games, no engine changes).

WHY THIS EXISTS
---------------
The frozen exp-0048/exp-0049 accuracy gate was `L_cand <= 0.97 * L_champ` AND
`B_cand <= B_champ`, using a FIXED logistic link p = 1/(1+10^(-s/400)).

A fixed link makes that gate sensitive to the MAGNITUDE of the evaluation, not
only to its ordering. Multiplying every parameter by a constant < 1 shrinks all
scores toward "drawish", which improves log-loss against a corpus whose outcomes
are mostly draws -- without any better position judgement. This script measures
that effect so a gate can be checked for scale-invariance BEFORE it is used.

It reports, for each rescale factor:
  * the frozen gate's own verdict (so a false pass is visible);
  * pairwise ordering sign flips and Spearman rank correlation vs the champion
    (so "no better judgement" is quantified rather than asserted);
  * a SCALE-INVARIANT comparison, where the champion is first optimally rescaled
    by a scalar fitted on the same data. If a pure rescale's apparent gain
    collapses to ~0 under that comparison, the gain was calibration only.

SCOPE: audit only. No strength games, no candidate, nothing activated. A rescale
is NOT a strength no-op (search margins are cp-calibrated), so this never claims
a rescaled arm is strength-identical -- only that a large "accuracy gain" can be
manufactured without better ordering.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import json
import math
import subprocess
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def sha(p: Path) -> str:
    import hashlib
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def read_params(p: Path) -> list[tuple[str, list[int]]]:
    out = []
    for line in p.read_text().splitlines():
        if line.strip() and not line.startswith("#"):
            t = line.split()
            out.append((t[0], [int(v) for v in t[1:]]))
    return out


def extract(engine: Path, epd: Path, params: Path, out: Path) -> np.ndarray:
    r = subprocess.run([str(engine), "evaldata", "--input", str(epd),
                        "--params", str(params), "--output", str(out)],
                       cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, f"evaldata rejected {params.name}: {r.stdout[-300:]}{r.stderr[-300:]}"
    lines = out.read_text().splitlines()
    hdr = next(l for l in lines if l.startswith("fen,"))
    body = [l for l in lines if not l.startswith("#") and not l.startswith("fen,")]
    return np.array([int(x["score"]) for x in csv.DictReader([hdr] + body)], dtype=np.float64)


def metrics(s: np.ndarray, y: np.ndarray, k: float = 400.0) -> tuple[float, float]:
    p = np.clip(1.0 / (1.0 + np.power(10.0, -s / k)), 1e-12, 1 - 1e-12)
    ll = float(-np.mean(y * np.log10(p) + (1 - y) * np.log10(1 - p)))
    return ll, float(np.mean((p - y) ** 2))


def best_scalar(s: np.ndarray, y: np.ndarray) -> float:
    """Golden-section search for the loss-minimising positive scale on s."""
    def f(c: float) -> float:
        return metrics(s * c, y)[0]
    lo, hi = 0.2, 2.0
    gr = (math.sqrt(5.0) - 1.0) / 2.0
    a, b = hi - gr * (hi - lo), lo + gr * (hi - lo)
    fa, fb = f(a), f(b)
    for _ in range(200):
        if fa < fb:
            hi, b, fb = b, a, fa
            a = hi - gr * (hi - lo); fa = f(a)
        else:
            lo, a, fa = a, b, fb
            b = lo + gr * (hi - lo); fb = f(b)
    return (lo + hi) / 2.0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", required=True)
    ap.add_argument("--engine", required=True)
    ap.add_argument("--params", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--stride", type=int, default=40)
    ap.add_argument("--max-positions", type=int, default=6000)
    ap.add_argument("--factors", default="0.80,0.85,0.90,0.95,1.05,1.10")
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    corpus = Path(a.corpus); engine = Path(a.engine).resolve()
    base_params = Path(a.params)

    with gzip.open(corpus / "corpus.epd.gz", "rt") as g:
        fens = g.read().splitlines()
    with gzip.open(corpus / "corpus.records.json.gz", "rt") as g:
        recs = json.load(g)
    idx = list(range(0, len(fens), a.stride))[:a.max_positions]
    epd = out / "positions.epd"
    epd.write_text("\n".join(fens[i] for i in idx) + "\n")
    y = np.array([recs[i]["target"] for i in idx], dtype=np.float64)

    entries = read_params(base_params)
    s0 = extract(engine, epd, base_params, out / "arm_champion.csv")
    L0, B0 = metrics(s0, y)
    # Scale-invariant reference: champion rescaled optimally on the SAME data.
    c_opt = best_scalar(s0, y)
    L_inv, B_inv = metrics(s0 * c_opt, y)

    arms = []
    for fac in [float(x) for x in a.factors.split(",")]:
        pf = out / f"params_u{int(round(fac*100))}.txt"
        pf.write_text("\n".join(k + " " + " ".join(str(int(round(v * fac))) for v in vals)
                                for k, vals in entries) + "\n")
        try:
            s = extract(engine, epd, pf, out / f"arm_u{int(round(fac*100))}.csv")
        except AssertionError as e:
            arms.append({"factor": fac, "rejected_by_loader": str(e)})
            continue
        L, B = metrics(s, y)
        d0 = np.sign(s0[:, None] - s0[None, :])
        d1 = np.sign(s[:, None] - s[None, :])
        arms.append({
            "factor": fac, "L": L, "B": B,
            "logloss_reduction_pct": 100.0 * (L0 - L) / L0,
            "frozen_gate_passed": bool(L <= 0.97 * L0 and B <= B0),
            "pairwise_ordering_sign_flips_pct": float(100.0 * (d0 != d1).mean()),
            "spearman_rank_corr": float(np.corrcoef(np.argsort(np.argsort(s)),
                                                   np.argsort(np.argsort(s0)))[0, 1]),
            "gain_vs_scale_invariant_reference_pct": 100.0 * (L_inv - L) / L_inv,
        })
    passing = [r["factor"] for r in arms if r.get("frozen_gate_passed")]
    report = {
        "purpose": "Scale-invariance audit of the frozen fixed-K accuracy gate",
        "scope": "AUDIT only. Zero strength games. Nothing activated or re-tuned.",
        "corpus": str(corpus), "n_positions": len(idx),
        "engine_sha256": sha(engine), "params_sha256": sha(base_params),
        "gate": "L_cand <= 0.97*L_champ AND B_cand <= B_champ, fixed K=400",
        "champion": {"L": L0, "B": B0},
        "scale_invariant_reference": {
            "optimal_champion_scale": c_opt, "L": L_inv, "B": B_inv,
            "note": ("Champion rescaled optimally on the same rows. Comparing against "
                     "THIS removes pure calibration from the measured gain.")},
        "arms": arms,
        "factors_passing_frozen_gate": passing,
        "gate_is_scale_invariant": not passing,
        "interpretation": (
            "Any factor listed in factors_passing_frozen_gate clears the frozen gate "
            "by rescaling alone. Ordering is essentially unchanged (see sign flips / "
            "Spearman), so the gain is calibration, not better judgement. A valid "
            "gate must be scale-invariant or calibrate K for both arms."),
        "caveat": ("A rescale is NOT a strength no-op: search margins are cp-calibrated. "
                   "No strength claim is made for any arm; none were played."),
    }
    (out / "SCALE_INVARIANCE.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: report[k] for k in ("champion", "scale_invariant_reference",
                                            "factors_passing_frozen_gate",
                                            "gate_is_scale_invariant")}, indent=2))
    for r in arms:
        if "logloss_reduction_pct" in r:
            print(f"  u{int(r['factor']*100)}: gain {r['logloss_reduction_pct']:+.3f}%  "
                  f"gate={'PASS' if r['frozen_gate_passed'] else 'fail'}  "
                  f"vs-scale-invariant {r['gain_vs_scale_invariant_reference_pct']:+.3f}%  "
                  f"order flips {r['pairwise_ordering_sign_flips_pct']:.3f}%")


if __name__ == "__main__":
    main()
