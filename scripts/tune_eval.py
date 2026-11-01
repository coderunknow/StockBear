#!/usr/bin/env python3
"""Offline Texel-style tuning of StockBear's handcrafted evaluation.

Why Texel and not SPSA: the evaluation is linear in its parameters and the
engine can emit the exact per-parameter counts for a position (`stockbear
evaldata`), so a position's score is a dot product we can evaluate for any
candidate parameter set without a search. That makes logistic regression on
recorded game results cheap, exact and fully reproducible, while SPSA would need
a playable engine inside the loop for every parameter vector.

Method
------
For a position with count vector c and parameters w the evaluation is
    s(w) = (sum_i w_mg[i] * c_mg[i] * phase + sum_i w_eg[i] * c_eg[i] * (24 - phase)) / 24
(the engine's own tapering, recomputed here). The tuning target for a game
result R from the side to move's point of view is
    t = 1 for a win, 0.5 for a draw, 0 for a loss,
and the model is the usual logistic link  p = 1 / (1 + 10^(-s/K)).
We minimise the mean logistic loss over the training positions by coordinate
descent over integer parameter values, then report the loss and mean squared
error on both the training and the held-out games. Holdout positions come from
games the optimiser never saw, because positions inside one game share a label.

Usage:
  python3 scripts/tune_eval.py --features features.csv --meta positions.meta.json \
      --engine ./build/stockbear --out tuned-params.txt --report tuning.json
"""
import argparse
import json
import math
import subprocess
from pathlib import Path

import numpy as np


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--features", required=True, help="output of `stockbear evaldata`")
    parser.add_argument("--meta", required=True, help="output of build_tuning_data.py")
    parser.add_argument("--engine", required=True, help="engine used to read the parameter table")
    parser.add_argument("--out", required=True, help="tuned parameter file for `--params`")
    parser.add_argument("--report", required=True, help="JSON report")
    parser.add_argument("--holdout-fraction", type=float, default=0.2)
    parser.add_argument("--k", type=float, default=400.0, help="Texel scale (centipawns per logit)")
    parser.add_argument("--tune-k", action="store_true", help="also choose K on the holdout set")
    parser.add_argument("--sweeps", type=int, default=8)
    parser.add_argument("--max-step", type=int, default=64)
    parser.add_argument("--seed", type=int, default=20261101)
    parser.add_argument("--ridge", type=float, default=0.02,
                        help="L2 pull towards the shipped set, in units of each parameter's range")
    parser.add_argument("--max-delta-fraction", type=float, default=0.35,
                        help="largest allowed move away from the shipped value, as a fraction of the range")
    parser.add_argument("--no-preserve-sign", action="store_true",
                        help="allow parameters whose shipped value has a known sign to change sign")
    parser.add_argument("--anchor", action="append", default=[],
                        help="parameter to keep at its shipped value (repeatable); MaterialPawn is the scale anchor")
    return parser.parse_args()


def read_table(engine):
    """Parameter names, shipped values and legal ranges, straight from the binary."""
    text = subprocess.run([engine, "eval", "--dump-params"], capture_output=True,
                          text=True, check=True).stdout
    names, values, ranges = [], [], []
    for line in text.strip().splitlines():
        name, mg, eg, lo, hi = line.split()
        names.append(name)
        values.append((int(mg), int(eg)))
        ranges.append((int(lo), int(hi)))
    return names, values, ranges


def load_features(path, param_count):
    """Design matrix Z with score(w) = Z @ w, plus side-to-move flags."""
    with open(path, encoding="utf-8") as handle:
        handle.readline()          # "# stockbear evaldata; ..." comment
        header = handle.readline().strip().split(",")
    expected = 2 + 2 * param_count + 1
    if len(header) != expected:
        raise SystemExit(f"feature header has {len(header)} columns, expected {expected}")
    data = np.loadtxt(path, delimiter=",", skiprows=2, usecols=range(1, len(header)),
                      dtype=np.float64)
    fens = [line.split(",", 1)[0] for line in
            Path(path).read_text(encoding="utf-8").splitlines()[2:]]
    if len(fens) != data.shape[0]:
        raise SystemExit("feature file rows disagree with its FEN column")
    phase = data[:, 0]
    mg = data[:, 1:1 + param_count]
    eg = data[:, 1 + param_count:1 + 2 * param_count]
    # The counts are White minus Black, so score(w) is a White-relative score.
    # Tapering is linear in the parameters, which is what makes the tuner a
    # regression instead of a search: z_row @ w reproduces the engine exactly
    # (up to its final clamp) for any parameter set.
    z = np.empty((data.shape[0], 2 * param_count), dtype=np.float64)
    z[:, :param_count] = mg * (phase / 24.0)[:, None]
    z[:, param_count:] = eg * ((24.0 - phase) / 24.0)[:, None]
    return z, fens


def logistic(s, k):
    """p = 1 / (1 + 10^(-s/K)), computed without overflow."""
    return 1.0 / (1.0 + np.exp(-(s / k) * math.log(10.0)))


def loss_of(s, target, k):
    p = np.clip(logistic(s, k), 1e-12, 1.0 - 1e-12)
    return float(-np.mean(target * np.log(p) + (1.0 - target) * np.log(1.0 - p)))


def loss_and_error(z, w, target, k):
    return loss_of(z @ w, target, k), None


def score_rmse(z, w, target):
    """RMSE between the model score and the score its label implies.

    Decisive games are compared against +/-800 cp and draws against 0; it is a
    calibration figure, not a strength measurement.
    """
    s = z @ w
    implied = np.where(target > 0.75, 800.0, np.where(target < 0.25, -800.0, 0.0))
    return float(np.sqrt(np.mean((s - implied) ** 2)))


def main():
    args = parse_args()
    names, values, ranges = read_table(args.engine)
    param_count = len(names)
    z, fens = load_features(args.features, param_count)
    meta = json.load(open(args.meta, encoding="utf-8"))
    records = meta["records"]
    if len(records) != z.shape[0]:
        raise SystemExit(f"feature rows {z.shape[0]} != metadata rows {len(records)}")
    # build_tuning_data stores side-to-move-relative targets; the design matrix
    # is White-relative, so convert once here.
    stm_white = np.array([f.split()[1] == "w" for f in fens])
    target = np.array([r["target"] for r in records], dtype=np.float64)
    target = np.where(stm_white, target, 1.0 - target)
    games = np.array([r["game"] for r in records], dtype=np.int64)

    # Split by game, deterministically, so no opening pair straddles the split.
    rng = np.random.default_rng(args.seed)
    unique_games = np.unique(games)
    rng.shuffle(unique_games)
    holdout_games = set(unique_games[:max(1, int(len(unique_games) * args.holdout_fraction))])
    is_holdout = np.array([g in holdout_games for g in games])
    train, test = ~is_holdout, is_holdout
    if train.sum() < 1000 or test.sum() < 200:
        raise SystemExit("not enough positions after the split")

    w0 = np.array([values[i][0] for i in range(param_count)] +
                  [values[i][1] for i in range(param_count)], dtype=np.float64)
    w = w0.copy()
    pairs = np.array([ranges[i] for i in range(param_count)], dtype=np.float64)
    lo_bounds, hi_bounds = pairs[:, 0].copy(), pairs[:, 1].copy()
    if not args.no_preserve_sign:
        # A penalty stays a penalty and a bonus stays a bonus. Without this the
        # fit happily flips isolated-pawn and king-rank terms, which is a
        # textbook symptom of fitting correlated noise on a small dataset.
        for index in range(param_count):
            for value in values[index]:
                if value > 0:
                    lo_bounds[index] = max(lo_bounds[index], 0.0)
                elif value < 0:
                    hi_bounds[index] = min(hi_bounds[index], 0.0)
    bounds = np.concatenate([pairs] * 2)
    span = np.tile(np.maximum(1.0, hi_bounds - lo_bounds), 2)
    # Regularisation and a movement cap keep a small, correlated dataset from
    # driving single parameters to their box limits: the loss is flat along
    # "pawn value vs everything else" and along "doubled pawn penalty vs
    # passed pawn bonus", so an unregularised fit trades one for the other.
    limit = args.max_delta_fraction * span
    fixed = set()
    for name in args.anchor:
        lowered = name.lower()
        for index, param in enumerate(names):
            if param.lower() == lowered:
                fixed.update({index, param_count + index})
    if not fixed:
        for index, param in enumerate(names):
            if param.lower() == "materialpawn":
                fixed.update({index, param_count + index})
    k = args.k

    def penalty(candidate):
        delta = (candidate - w0) / span
        return args.ridge * float(delta @ delta)

    zt, tt = z[train], target[train]
    loss0 = loss_of(z[train] @ w, tt, k) + penalty(w)
    loss0_hold, _ = loss_and_error(z[test], w, target[test], k)
    print(f"start: train loss {loss0:.6f} holdout loss {loss0_hold:.6f} (K={k})")

    # Coordinate descent with an exponentially shrinking step size. Only the
    # column of the parameter being changed is touched, so a trial costs O(n).
    current = zt @ w
    history = []
    for sweep in range(args.sweeps):
        improved = 0
        step = max(1, args.max_step >> min(sweep, 5))
        for i in range(2 * param_count):
            column = zt[:, i]
            if not np.any(column) or i in fixed:
                continue  # parameter unused by this dataset, or anchored
            for direction in (step, -step):
                candidate = w[i] + direction
                lo, hi = bounds[i]
                if candidate < lo or candidate > hi:
                    continue
                if abs(candidate - w0[i]) > limit[i]:
                    continue
                trial = current + direction * column
                candidate_w = w.copy()
                candidate_w[i] = candidate
                loss = loss_of(trial, tt, k) + penalty(candidate_w)
                if loss < loss0 - 1e-12:
                    w[i] = candidate
                    current = trial
                    loss0 = loss
                    improved += 1
                    break
        history.append({"sweep": sweep, "step": step, "changes": improved,
                        "train_objective": float(loss0),
                        "train_loss": float(loss_of(current, tt, k))})
        print(f"sweep {sweep}: step {step} changes {improved} objective {loss0:.6f}"
              f" loss {loss_of(current, tt, k):.6f}")
        if improved == 0:
            break

    best_k = k
    if args.tune_k:
        candidates = [200.0, 250.0, 300.0, 350.0, 400.0, 450.0, 500.0, 600.0, 700.0]
        losses = {cand: loss_of(z[train] @ w, tt, cand) for cand in candidates}
        best_k = min(losses, key=losses.get)
        print("K candidates:", {c: round(v, 6) for c, v in losses.items()}, "->", best_k)

    train_loss, _ = loss_and_error(z[train], w, tt, best_k)
    hold_loss, _ = loss_and_error(z[test], w, target[test], best_k)
    baseline_train, _ = loss_and_error(z[train], w0, tt, best_k)
    baseline_hold, _ = loss_and_error(z[test], w0, target[test], best_k)
    report = {
        "method": "Texel-style logistic loss, coordinate descent on integer parameters",
        "k": best_k,
        "positions": {"train": int(train.sum()), "holdout": int(test.sum()),
                      "games_train": len(unique_games) - len(holdout_games),
                      "games_holdout": len(holdout_games)},
        "seed": args.seed,
        "ridge": args.ridge,
        "max_delta_fraction": args.max_delta_fraction,
        "preserve_sign": not args.no_preserve_sign,
        "anchored": sorted(names[i] for i in range(param_count)
                           if i in fixed or param_count + i in fixed),
        "holdout_fraction": args.holdout_fraction,
        "loss": {"baseline_train": float(baseline_train), "tuned_train": float(train_loss),
                 "baseline_holdout": float(baseline_hold), "tuned_holdout": float(hold_loss)},
        "score_rmse_cp": {"baseline_train": score_rmse(z[train], w0, tt),
                          "tuned_train": score_rmse(z[train], w, tt),
                          "baseline_holdout": score_rmse(z[test], w0, target[test]),
                          "tuned_holdout": score_rmse(z[test], w, target[test])},
        "sweeps": history,
        "baseline": {names[i]: list(values[i]) for i in range(param_count)},
        "tuned": {names[i]: [int(w[i]), int(w[param_count + i])] for i in range(param_count)},
        "changed": {names[i]: {"from": list(values[i]), "to": [int(w[i]), int(w[param_count + i])]}
                    for i in range(param_count)
                    if (int(w[i]), int(w[param_count + i])) != tuple(values[i])},
    }
    with open(args.report, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=1)
        handle.write("\n")
    with open(args.out, "w", encoding="utf-8") as handle:
        for i in range(param_count):
            handle.write(f"{names[i]} {int(w[i])} {int(w[param_count + i])}\n")
    print(json.dumps({k: v for k, v in report.items()
                      if k in ("positions", "loss", "score_rmse_cp", "k")}, indent=1))
    print(f"changed parameters: {len(report['changed'])}")


if __name__ == "__main__":
    main()
