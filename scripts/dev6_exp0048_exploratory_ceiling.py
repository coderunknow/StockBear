#!/usr/bin/env python3
"""EXPLORATORY hypothesis-generation ONLY. NOT a preregistered test.

STATUS AND PERMITTED USE
-----------------------
exp-0048 is CLOSED as a NEGATIVE result (docs/DEV6_EXP0048_REPORT.md). Its frozen
protocol turned out to have a degenerate objective: the L2 penalty was the same
order of magnitude as the mean-normalised data gradient at ~1 cp, so the optimum
was the initialisation and the fitted table moved by at most 1.22 cp.

This script asks ONE engineering question before any further compute is spent:
*can* an expressive per-square table reduce held-out outcome loss at all, and by
roughly how much? That determines whether a successor hypothesis has any
credible path to the mission's +75 Elo gate, or whether the mechanism should be
abandoned outright.

 HARD RULES, stated here so the output cannot be misread:
  * These numbers are EXPLORATORY. They may NOT be used to activate exp-0047,
    to fill any Activation Record, or to claim a strength improvement.
  * This reuses the CLOSED exp-0048 corpus. That corpus and its holdout are
    therefore BURNED for confirmatory purposes. Any successor hypothesis MUST
    use a FRESH corpus, disjoint from this one and from every prior suite.
  * The regulariser sweep below is hypothesis generation, not model selection
    for a reported result. No value chosen here becomes a result; it can only
    inform a NEW preregistration that is frozen before its own fresh data.
  * Nothing here changes the exp-0048 verdict, its ledger entry, or its report.

Usage:
  python3 scripts/dev6_exp0048_exploratory_ceiling.py \
      --corpus benchmarks/exp-runs/corpus-export/run-42169244756 \
      --engine ./build-rel/stockbear --out /tmp/ceiling
"""
from __future__ import annotations

import argparse
import gzip
import json
import math
import random
from pathlib import Path

import chess
import numpy as np

import dev6_exp0048_fit as frozen

ROOT = Path(__file__).resolve().parents[1]
K = math.log(10.0) / 400.0
# Exploratory grid. The frozen exp-0048 value (1e-5) is included as the control
# so the degeneracy diagnosis can be reproduced side by side.
L2_GRID = [0.0, 1e-8, 1e-7, 1e-6, 1e-5]
ITERATIONS = 600
LEARNING_RATE = 5.0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", required=True)
    ap.add_argument("--engine", required=True)
    ap.add_argument("--params", default="research-data/params_abc.txt")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    corpus, out = Path(a.corpus), Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    work = out / "work"
    work.mkdir(exist_ok=True)

    manifest = json.loads((corpus / "MANIFEST.json").read_text())
    with gzip.open(corpus / "corpus.epd.gz", "rt") as g:
        fens = g.read().splitlines()
    with gzip.open(corpus / "corpus.records.json.gz", "rt") as g:
        records = json.load(g)
    params_path = ROOT / a.params
    params = frozen.read_params(params_path)

    games = sorted({r["game"] for r in records})
    shuffled = list(games)
    random.Random(frozen.HOLDOUT_SEED).shuffle(shuffled)
    n_ho = math.ceil(frozen.HOLDOUT_FRACTION * len(games))
    ho_games = set(shuffled[:n_ho])
    is_ho = np.array([r["game"] in ho_games for r in records])
    target = np.array([r["target"] for r in records], dtype=np.float64)

    all_epd = work / "all.epd"
    all_epd.write_text("\n".join(fens) + "\n")
    design = work / "design.csv"
    import subprocess
    r = subprocess.run([str(Path(a.engine).resolve()), "evaldata", "--input", str(all_epd),
                        "--params", str(params_path), "--output", str(design)],
                       cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-2000:]
    lines = design.read_text().splitlines()
    header = lines[1].split(",")
    rows = [l.split(",") for l in lines[2:] if l]
    n_par = (len(header) - 3) // 2
    names = [h[3:] for h in header[2:2 + n_par]]
    cm = np.array([[int(v) for v in row[2:2 + n_par]] for row in rows], dtype=np.int64)
    ce = np.array([[int(v) for v in row[2 + n_par:-1]] for row in rows], dtype=np.int64)
    phase = np.array([int(row[1]) for row in rows], dtype=np.int64)
    engine_score = np.array([int(row[-1]) for row in rows], dtype=np.int64)
    pmg = np.array([params.get(n, (0, 0))[0] for n in names], dtype=np.int64)
    peg = np.array([params.get(n, (0, 0))[1] for n in names], dtype=np.int64)
    pst_mask = np.array([n in frozen.PST_NAMES for n in names])
    sign = np.array([1 if f.split()[1] == "w" else -1 for f in fens], dtype=np.int64)
    nonpst_mg = cm @ np.where(pst_mask, 0, pmg)
    nonpst_eg = ce @ np.where(pst_mask, 0, peg)
    assert np.array_equal(sign * frozen.taper(cm @ pmg, ce @ peg, phase), engine_score)

    init_mg, init_eg = frozen.formulaic_tables(params)
    ri, ci, vv = [], [], []
    for i, fen in enumerate(fens):
        for sq, piece in chess.Board(fen).piece_map().items():
            ri.append(i)
            ci.append(frozen.PIECES.index(piece.piece_type) * 64 +
                      ((sq ^ 56) if piece.color == chess.WHITE else sq))
            vv.append(1 if piece.color == chess.WHITE else -1)
    ri = np.array(ri, dtype=np.int64)
    ci = np.array(ci, dtype=np.int64)
    vv = np.array(vv, dtype=np.float64)
    n_rows, n_feat = len(fens), 384

    tr = np.flatnonzero(~is_ho)
    mask = (~is_ho)[ri]
    tr_cols, tr_vals = ci[mask], vv[mask]
    local = np.full(n_rows, -1, dtype=np.int64)
    local[tr] = np.arange(len(tr))
    tr_local = local[ri[mask]]
    n_tr = len(tr)
    ph = phase[tr].astype(np.float64)
    w_mg, w_eg = ph / 24.0, (24.0 - ph) / 24.0
    sg = sign[tr].astype(np.float64)
    b_mg = nonpst_mg[tr].astype(np.float64)
    b_eg = nonpst_eg[tr].astype(np.float64)
    y = target[tr]
    theta0 = np.concatenate([init_mg.reshape(-1), init_eg.reshape(-1)]).astype(np.float64)

    print(f"EXPLORATORY ONLY - not a preregistered result. {n_rows} rows, "
          f"{n_tr} train / {int(is_ho.sum())} holdout", flush=True)
    print(f"{'L2':>10} {'train_L':>10} {'holdout_L':>10} {'reduction%':>11} "
          f"{'holdout_B':>10} {'rms_delta':>10} {'max_delta':>10}", flush=True)

    champ_L = frozen.logloss10(engine_score[is_ho], target[is_ho])
    champ_B = frozen.brier(engine_score[is_ho], target[is_ho])
    results = []
    for l2 in L2_GRID:
        theta = theta0.copy()
        m = np.zeros_like(theta)
        v = np.zeros_like(theta)
        for it in range(1, ITERATIONS + 1):
            pm = np.bincount(tr_local, weights=tr_vals * theta[:n_feat][tr_cols], minlength=n_tr)
            pe = np.bincount(tr_local, weights=tr_vals * theta[n_feat:][tr_cols], minlength=n_tr)
            raw = sg * ((b_mg + pm) * w_mg + (b_eg + pe) * w_eg)
            cl = np.abs(raw) > frozen.KNOWN_WIN
            s = np.clip(raw, -frozen.KNOWN_WIN, frozen.KNOWN_WIN)
            p = 1.0 / (1.0 + np.exp(-np.clip(K * s, -700, 700)))
            g_s = K * (p - y) / n_tr * (~cl)
            grad = np.empty_like(theta)
            grad[:n_feat] = np.bincount(tr_cols, weights=tr_vals * (g_s * sg * w_mg)[tr_local], minlength=n_feat)
            grad[n_feat:] = np.bincount(tr_cols, weights=tr_vals * (g_s * sg * w_eg)[tr_local], minlength=n_feat)
            delta = theta - theta0
            grad += 2.0 * l2 * delta
            m = 0.9 * m + 0.1 * grad
            v = 0.999 * v + 0.001 * grad * grad
            theta -= LEARNING_RATE * (m / (1 - 0.9 ** it)) / (np.sqrt(v / (1 - 0.999 ** it)) + 1e-8)
        rounded = np.sign(theta) * np.floor(np.abs(theta) + 0.5)
        final = np.clip(rounded, -2000, 2000).astype(np.int64)

        def score_of(tab_mg, tab_eg):
            fm = np.bincount(ri, weights=vv * tab_mg.reshape(-1)[ci], minlength=n_rows)
            fe = np.bincount(ri, weights=vv * tab_eg.reshape(-1)[ci], minlength=n_rows)
            return sign * frozen.taper(nonpst_mg + np.rint(fm).astype(np.int64),
                                       nonpst_eg + np.rint(fe).astype(np.int64), phase)

        cand = score_of(final[:n_feat].reshape(6, 64), final[n_feat:].reshape(6, 64))
        tr_L = frozen.logloss10(cand[~is_ho], target[~is_ho])
        ho_L = frozen.logloss10(cand[is_ho], target[is_ho])
        ho_B = frozen.brier(cand[is_ho], target[is_ho])
        d = theta - theta0
        row = {"l2": l2, "train_logloss": tr_L, "holdout_logloss": ho_L,
               "holdout_reduction_pct": 100.0 * (1.0 - ho_L / champ_L),
               "holdout_brier": ho_B, "rms_delta_cp": float(np.sqrt(np.mean(d * d))),
               "max_abs_delta_cp": float(np.max(np.abs(d))),
               "is_frozen_exp0048_control": l2 == 1e-5}
        results.append(row)
        print(f"{l2:>10.0e} {tr_L:>10.6f} {ho_L:>10.6f} {row['holdout_reduction_pct']:>11.4f} "
              f"{ho_B:>10.6f} {row['rms_delta_cp']:>10.3f} {row['max_abs_delta_cp']:>10.3f}", flush=True)

    best = max(results, key=lambda x: x["holdout_reduction_pct"])
    report = {
        "STATUS": "EXPLORATORY HYPOTHESIS GENERATION - NOT A PREREGISTERED RESULT",
        "permitted_use": "Inform a NEW preregistration only. May NOT activate exp-0047, "
                         "fill an Activation Record, or support any strength claim.",
        "corpus": str(corpus), "corpus_manifest_games": manifest["games"],
        "corpus_status": "CLOSED exp-0048 corpus; BURNED for confirmatory use. Any "
                         "successor hypothesis requires a FRESH disjoint corpus.",
        "exp0048_verdict_unchanged": "NEGATIVE / CLOSED",
        "iterations": ITERATIONS, "learning_rate": LEARNING_RATE,
        "champion_holdout_logloss": champ_L, "champion_holdout_brier": champ_B,
        "grid": results,
        "observed_ceiling_reduction_pct": best["holdout_reduction_pct"],
        "frozen_threshold_pct_for_reference": 3.0,
    }
    (out / "EXPLORATORY_CEILING.json").write_text(json.dumps(report, indent=2) + "\n")
    print(f"\nchampion holdout L={champ_L:.6f} B={champ_B:.6f}")
    print(f"best exploratory reduction: {best['holdout_reduction_pct']:.4f}% at L2={best['l2']:.0e}")
    print("REMINDER: exploratory only; a successor needs a fresh corpus and its own frozen prereg.")


if __name__ == "__main__":
    main()
