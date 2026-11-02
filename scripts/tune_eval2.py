#!/usr/bin/env python3
"""dev5 Texel-style tuner for StockBear's classical evaluation (v2).

Differences from ``scripts/tune_eval.py`` (dev3, kept unchanged for provenance):

* Labels may come from a teacher search (``<cp> <game> <fen>`` files produced by
  ``scripts/label_search.py``) in addition to game outcomes, or a blend of both.
  The model is still exactly linear in the parameters, so every candidate is a
  plain regression on the engine's own ``evaldata`` counts.
* ``--target cp`` distills teacher centipawns by (clipped) least squares and
  then refines with a few logistic epochs; ``--target outcome``/``search``/
  ``blend`` use the Texel logistic objective. Optimisation is minibatch Adam
  with projection onto the legal parameter ranges, several random restarts,
  and a game-level train/val/test split (the same game-hash split the NNUE
  trainer uses).
* After fitting, the whole parameter vector is rescaled so MaterialPawn mg
  stays at its shipped 100 cp: the engine's search margins are calibrated in
  that scale, and the evaluation is linear in the parameters, so rescaling
  changes nothing about the fit.

Model (identical arithmetic to the engine): for counts c (White minus Black) and
phase p, the White-relative score is
    s(w) = (sum_i w_mg[i] c_mg[i] * p + sum_i w_eg[i] c_eg[i] * (24 - p)) / 24
and the side-to-move score is +/- s.

Usage:
  python3 scripts/tune_eval2.py --features features.csv \
      --labels labels.txt [--corpus corpus.txt] \
      --engine ./build-dev4/build/stockbear \
      --target cp --out params.txt --report report.json
"""
from __future__ import annotations

import argparse
import json
import math
import subprocess
from pathlib import Path

import numpy as np

LN10 = math.log(10.0)


def read_table(engine):
    text = subprocess.run([engine, "eval", "--dump-params"], capture_output=True,
                          text=True, check=True).stdout
    names, values, mins, maxs = [], [], [], []
    for line in text.strip().splitlines():
        name, mg, eg, l, h = line.split()
        names.append(name)
        values.append([int(mg), int(eg)])
        mins.append([int(l), int(l)])
        maxs.append([int(h), int(h)])
    return (names, np.array(values, dtype=np.float64),
            np.array(mins, dtype=np.float64), np.array(maxs, dtype=np.float64))


def load_features(path, nparam):
    with open(path, encoding="utf-8") as handle:
        handle.readline()
        header = handle.readline().strip().split(",")
    assert len(header) == 2 + 2 * nparam + 1, header[:3]
    data = np.loadtxt(path, delimiter=",", skiprows=2, usecols=range(1, len(header)),
                      dtype=np.float64)
    fens = [line.split(",", 1)[0] for line in
            Path(path).read_text(encoding="utf-8").splitlines()[2:]]
    phase = data[:, 0]
    mg = data[:, 1:1 + nparam]
    eg = data[:, 1 + nparam:1 + 2 * nparam]
    z = np.empty((data.shape[0], 2 * nparam), dtype=np.float64)
    z[:, :nparam] = mg * (phase / 24.0)[:, None]
    z[:, nparam:] = eg * ((24.0 - phase) / 24.0)[:, None]
    return z, fens


def load_labels(path):
    out = {}
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            value, game, fen = line.split(" ", 2)
            out[fen] = (float(value), int(game))
    return out


def sigmoid_log10(s, k):
    return 1.0 / (1.0 + np.exp(-np.clip(s / k, -6.0, 6.0) * LN10))


def bce(p, t):
    p = np.clip(p, 1e-9, 1 - 1e-9)
    return float(-np.mean(t * np.log(p) + (1 - t) * np.log(1 - p)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--features", required=True)
    ap.add_argument("--labels", action="append", default=[])
    ap.add_argument("--corpus", action="append", default=[])
    ap.add_argument("--engine", required=True)
    ap.add_argument("--target", choices=["cp", "search", "outcome", "blend"], default="cp")
    ap.add_argument("--out", required=True)
    ap.add_argument("--report", required=True)
    ap.add_argument("--restarts", type=int, default=4)
    ap.add_argument("--epochs", type=int, default=40)
    ap.add_argument("--batch", type=int, default=8192)
    ap.add_argument("--lr", type=float, default=0.03)
    ap.add_argument("--k-grid", default="250,400,600,800")
    ap.add_argument("--cp-clip", type=float, default=900.0,
                    help="teacher cp are clipped to +/- this before use")
    ap.add_argument("--seed", type=int, default=20261102)
    ap.add_argument("--blend", type=float, default=0.5)
    ap.add_argument("--ridge", type=float, default=1e-4,
                    help="L2 pull towards the shipped set, relative to param range")
    args = ap.parse_args()

    names, shipped, mins, maxs = read_table(args.engine)
    nparam = len(names)
    z, fens = load_features(args.features, nparam)
    stm = np.array([1.0 if f.split()[1] == "w" else -1.0 for f in fens])

    search = {}
    for path in args.labels:
        search.update(load_labels(path))
    outcome = {}
    for path in args.corpus:
        outcome.update(load_labels(path))

    n = len(fens)
    game = np.full(n, -1, dtype=np.int64)
    cp = np.zeros(n)
    res = np.full(n, np.nan)
    has_search = np.zeros(n, dtype=bool)
    has_outcome = np.zeros(n, dtype=bool)
    for i, f in enumerate(fens):
        if f in search:
            cp[i], game[i] = search[f]
            has_search[i] = True
        if f in outcome:
            res[i], game[i] = outcome[f]
            has_outcome[i] = True
    keep = (has_search | has_outcome)
    z, stm, game, cp, res, has_search, has_outcome = (
        z[keep], stm[keep], game[keep], cp[keep], res[keep], has_search[keep], has_outcome[keep])
    n = len(game)
    print(f"{n} positions: {int(has_search.sum())} search-labelled, {int(has_outcome.sum())} outcome-labelled")

    bucket = (game * 2654435761) % 100
    split = np.where(bucket < 5, 2, np.where(bucket < 12, 1, 0))
    tr = np.nonzero(split == 0)[0]
    va = np.nonzero(split == 1)[0]
    te = np.nonzero(split == 2)[0]

    # which rows each objective may use
    if args.target in ("cp", "search"):
        usable = has_search
    elif args.target == "outcome":
        usable = has_outcome
    else:
        usable = has_search & has_outcome
    tr = tr[usable[tr]]
    va = va[usable[va]]
    te = te[usable[te]]
    print(f"usable rows: train {tr.size} val {va.size} test {te.size}")

    cp_clip = np.clip(cp, -args.cp_clip, args.cp_clip)
    # parameter vector layout: [mg block (nparam), eg block (nparam)]
    lo = np.concatenate([mins[:, 0], mins[:, 1]])
    hi = np.concatenate([maxs[:, 0], maxs[:, 1]])
    span = np.maximum(hi - lo, 1.0)
    w0_ship = np.concatenate([shipped[:, 0], shipped[:, 1]])

    def targets_logistic(rows, k):
        if args.target == "search":
            t = sigmoid_log10(cp_clip[rows], k)
        elif args.target == "outcome":
            t = np.where(np.isnan(res[rows]), 0.5, res[rows])
        else:  # blend
            t = args.blend * sigmoid_log10(cp_clip[rows], k) + \
                (1 - args.blend) * np.where(np.isnan(res[rows]), 0.5, res[rows])
        return t

    def loss_grad(w, rows, k, want_grad):
        s = stm[rows] * (z[rows] @ w)
        if args.target == "cp":
            t = cp_clip[rows]
            diff = s - t
            loss = float(np.mean(diff * diff)) / 2.0
            if not want_grad:
                return loss, None
            g = z[rows].T @ (stm[rows] * diff) / len(rows)
        else:
            t = targets_logistic(rows, k)
            p = sigmoid_log10(s, k)
            loss = bce(p, t)
            if not want_grad:
                return loss, None
            pc = np.clip(p, 1e-9, 1 - 1e-9)
            d = (pc - t) * pc * (1 - pc) * LN10 / k
            g = z[rows].T @ (stm[rows] * d) / len(rows)
        # ridge towards shipped, scaled by parameter range
        g = g + args.ridge * (w - w0_ship) / span
        loss = loss + args.ridge * float(np.mean(((w - w0_ship) / span) ** 2))
        return loss, g

    def evaluate(w, rows, k):
        s = stm[rows] * (z[rows] @ w)
        if args.target == "cp":
            t = cp_clip[rows]
            mse = float(np.mean((s - t) ** 2))
            corr = float(np.corrcoef(s, t)[0, 1]) if len(rows) > 10 else float("nan")
            return mse, corr
        t = targets_logistic(rows, k)
        return bce(sigmoid_log10(s, k), t), float(np.corrcoef(s, cp_clip[rows])[0, 1])

    k_grid = [float(x) for x in args.k_grid.split(",")]
    rng = np.random.default_rng(args.seed)
    results = []
    for restart in range(args.restarts):
        # init: shipped + perturbation, or closed-form ridge for cp mode
        w = w0_ship.copy()
        if args.target == "cp" and restart == 0:
            zt = z[tr] * stm[tr, None]
            a = zt.T @ zt + args.ridge * np.diag(span) / len(tr) * len(tr) * 0.01 + 1e-6 * np.eye(2 * nparam)
            b = zt.T @ cp_clip[tr]
            try:
                w = np.linalg.solve(a, b)
                w = np.clip(w, lo, hi)
            except np.linalg.LinAlgError:
                pass
        elif restart > 0:
            w = w + rng.normal(0, 0.05, size=w.size) * span
            w = np.clip(w, lo, hi)
        m = np.zeros_like(w)
        v = np.zeros_like(w)
        best = (float("inf"), None, None, None)
        step = 0
        for epoch in range(args.epochs):
            order = rng.permutation(tr)
            for begin in range(0, max(1, len(order) - args.batch + 1), args.batch):
                rows = order[begin:begin + args.batch]
                k = k_grid[restart % len(k_grid)]
                _, g = loss_grad(w, rows, k, True)
                step += 1
                m = 0.9 * m + 0.1 * g
                v = 0.999 * v + 0.001 * g * g
                mh = m / (1 - 0.9 ** step)
                vh = v / (1 - 0.999 ** step)
                w = w - args.lr * mh / (np.sqrt(vh) + 1e-8)
                w = np.clip(w, lo, hi)
            if epoch % 4 == 3 or epoch == args.epochs - 1:
                for k in (k_grid if args.target != "cp" else [k_grid[0]]):
                    vl, corr = evaluate(w, va, k)
                    if vl < best[0]:
                        best = (vl, k, w.copy(), corr)
                print(f"restart {restart} epoch {epoch}: best val {best[0]:.5f} "
                      f"corr {best[3]:.4f}", flush=True)
        # rescale so MaterialPawn mg == shipped (index 0 is mg of param 0)
        scale = w0_ship[0] / w[0]
        w_rescaled = w * scale
        # clip again after rescale (scale ~1 if anchored well)
        w_rescaled = np.clip(w_rescaled, lo, hi)
        vl, corr = evaluate(w_rescaled, va, best[1] if best[1] else k_grid[0])
        tl, tcorr = evaluate(w_rescaled, te, best[1] if best[1] else k_grid[0])
        results.append({"restart": restart, "k": best[1], "val": vl, "val_corr": corr,
                        "test": tl, "test_corr": tcorr, "w": w_rescaled, "scale": float(scale)})
        print(f"restart {restart}: val {vl:.5f} corr {corr:.4f} | test {tl:.5f} corr {tcorr:.4f} "
              f"(rescale {scale:.3f})", flush=True)

    best = min(results, key=lambda r: r["val"])
    w = best["w"]
    mg = w[:nparam]
    eg = w[nparam:]
    Path(args.out).write_text("\n".join(
        f"{names[i]} {int(round(mg[i]))} {int(round(eg[i]))}" for i in range(nparam)) + "\n")
    report = {
        "target": args.target, "blend": args.blend, "restarts": args.restarts,
        "epochs": args.epochs, "batch": args.batch, "lr": args.lr, "seed": args.seed,
        "cp_clip": args.cp_clip,
        "positions": int(n), "search_labelled": int(has_search.sum()),
        "outcome_labelled": int(has_outcome.sum()),
        "split": {"train": int(tr.size), "val": int(va.size), "test": int(te.size)},
        "best": {k: v for k, v in best.items() if k != "w"},
        "params": {names[i]: [int(round(mg[i])), int(round(eg[i]))] for i in range(nparam)},
        "all_restarts": [{k: v for k, v in r.items() if k != "w"} for r in results],
    }
    Path(args.report).write_text(json.dumps(report, indent=2))
    print("wrote", args.out)
    print("best:", {k: v for k, v in best.items() if k != "w"})


if __name__ == "__main__":
    main()
