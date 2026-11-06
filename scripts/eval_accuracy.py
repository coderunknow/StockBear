"""Scale-invariant evaluator-accuracy comparison.

WHY THIS MODULE EXISTS
----------------------
The exp-0048/exp-0049 gate compared log-loss at a FIXED logistic link
(p = 1/(1+10^(-s/400))) against an uncalibrated baseline. An audit
(`docs/DEV6_ACCURACY_GATE_VALIDITY.md`) showed that multiplying EVERY champion
parameter by 0.80 clears that gate on two independent corpora (+3.04%, +3.11%)
while leaving the ordering of positions essentially unchanged (Spearman 0.9998).
The "gain" was probability calibration toward a draw-heavy outcome distribution,
not better evaluation.

This module removes that failure mode. Both arms are given the SAME monotone
recalibration freedom before comparison, so a pure positive rescale of either arm
scores exactly zero gain. Two complementary views are provided:

  * `calibrated_logloss` - fit the loss-minimising positive scale for the arm on
    the evaluation rows, then report the loss. Retains a proper scoring rule
    (so genuine improvements still show) while quotienting out global confidence.
  * `pairwise_auc` - a ranking-only statistic, exactly invariant to ANY strictly
    increasing transform. Uses only decisive rows (target 0 or 1).

NEITHER IS AN ELO PREDICTOR. `docs/DEV6_ACCURACY_ELO_LINK_AUDIT.md` shows no
accuracy->Elo calibration exists in this project (the fitted slope's 95% CI spans
zero). These are candidate-development diagnostics, not activation evidence, and
they do not license any strength claim.

Honest limitations, both verified by property tests:

1. Fitting the scale on the SAME rows used for scoring is optimistic for both
   arms. Because BOTH get the same freedom the comparison is fair, but for a
   decisive measurement the scale should be fitted on the training split and
   applied to the holdout. `fit_scale`/`apply_scale` are exposed for that.

2. Calibrated log-loss is FLOORED at the constant-predictor loss log10(2): a
   catastrophically bad arm can shrink its scale toward zero and land there. So
   this metric COMPRESSES large regressions (a sign flip scores only ~-4%, not
   -100%). It is therefore a good detector of genuine IMPROVEMENT but a poor
   severity measure for regressions. `pairwise_auc` has no such floor (the same
   sign flip scores -0.49) and should be read alongside it. Never use the
   calibrated loss alone to decide that a candidate is "not much worse".
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

K_DEFAULT = 400.0
_EPS = 1e-12


def _prob(score: np.ndarray, k: float) -> np.ndarray:
    return np.clip(1.0 / (1.0 + np.power(10.0, -np.asarray(score, dtype=np.float64) / k)),
                   _EPS, 1.0 - _EPS)


def logloss(score: np.ndarray, target: np.ndarray, k: float = K_DEFAULT) -> float:
    """Texel log10 loss at a fixed link. NOT scale-invariant; kept for reference."""
    p = _prob(score, k)
    t = np.asarray(target, dtype=np.float64)
    return float(-np.mean(t * np.log10(p) + (1.0 - t) * np.log10(1.0 - p)))


def brier(score: np.ndarray, target: np.ndarray, k: float = K_DEFAULT) -> float:
    p = _prob(score, k)
    return float(np.mean((p - np.asarray(target, dtype=np.float64)) ** 2))


def fit_scale(score: np.ndarray, target: np.ndarray, k: float = K_DEFAULT,
              lo: float = 1e-3, hi: float = 1e3) -> float:
    """Loss-minimising positive scale, by golden-section on log(scale).

    The scores are first NORMALISED by their own RMS, and the search runs on the
    normalised scores. Without that step a fixed bracket silently clamps the
    calibration for extreme inputs: a property test at factor 10 pinned the
    fitted scale to the old lower bound (0.05) and reported a spurious -0.6%
    "regression" for what is exactly the same evaluation. Normalising makes the
    bracket meaningless in input units, so the result is invariant to the input
    scale by construction rather than by luck.

    Log-parameterised so the search is symmetric in shrink/grow and cannot
    propose a non-positive scale (which would flip the evaluation's sign).
    The loss is unimodal in the scale for a fixed score direction, so a
    bracketed search is appropriate and deterministic.
    """
    s = np.asarray(score, dtype=np.float64)
    t = np.asarray(target, dtype=np.float64)
    if not np.any(np.abs(s) > 0):
        return 1.0                      # all-zero scores: nothing to calibrate
    rms = float(np.sqrt(np.mean(s * s)))
    if not math.isfinite(rms) or rms <= 0.0:
        return 1.0
    s = s / rms                         # bracket now in RMS units, not cp

    def f(log_c: float) -> float:
        return logloss(s * math.exp(log_c), t, k)

    a, b = math.log(lo), math.log(hi)
    gr = (math.sqrt(5.0) - 1.0) / 2.0
    c1, c2 = b - gr * (b - a), a + gr * (b - a)
    f1, f2 = f(c1), f(c2)
    for _ in range(200):
        if f1 < f2:
            b, c2, f2 = c2, c1, f1
            c1 = b - gr * (b - a); f1 = f(c1)
        else:
            a, c1, f1 = c1, c2, f2
            c2 = a + gr * (b - a); f2 = f(c2)
    return math.exp((a + b) / 2.0) / rms   # undo the normalisation


def apply_scale(score: np.ndarray, scale: float) -> np.ndarray:
    return np.asarray(score, dtype=np.float64) * float(scale)


def calibrated_logloss(score: np.ndarray, target: np.ndarray,
                       k: float = K_DEFAULT, scale: float | None = None) -> tuple[float, float]:
    """(loss, scale). Pass `scale` from the training split to score a holdout."""
    c = fit_scale(score, target, k) if scale is None else float(scale)
    return logloss(apply_scale(score, c), target, k), c


def pairwise_auc(score: np.ndarray, target: np.ndarray) -> float | None:
    """Ranking-only accuracy on decisive rows; invariant to any increasing map.

    P(score_win > score_loss) with ties counted as one half. Returns None if
    either class is absent. O(n log n) via rank statistics, so it is usable on
    full corpora rather than a subsample.
    """
    s = np.asarray(score, dtype=np.float64)
    t = np.asarray(target, dtype=np.float64)
    pos, neg = s[t >= 1.0], s[t <= 0.0]
    if pos.size == 0 or neg.size == 0:
        return None
    combined = np.concatenate([pos, neg])
    order = np.argsort(combined, kind="mergesort")
    ranks = np.empty(combined.size, dtype=np.float64)
    sorted_vals = combined[order]
    i = 0
    while i < sorted_vals.size:                      # average ranks within ties
        j = i
        while j + 1 < sorted_vals.size and sorted_vals[j + 1] == sorted_vals[i]:
            j += 1
        ranks[order[i:j + 1]] = (i + j) / 2.0 + 1.0
        i = j + 1
    r_pos = ranks[:pos.size].sum()
    n_p, n_n = float(pos.size), float(neg.size)
    return float((r_pos - n_p * (n_p + 1.0) / 2.0) / (n_p * n_n))


@dataclass
class Comparison:
    logloss_champion: float
    logloss_candidate: float
    scale_champion: float
    scale_candidate: float
    relative_logloss_reduction: float
    auc_champion: float | None
    auc_candidate: float | None
    auc_gain: float | None

    def as_dict(self) -> dict:
        return {
            "metric": "scale-calibrated Texel log10 loss + ranking AUC",
            "scale_invariant": True,
            "logloss_champion": self.logloss_champion,
            "logloss_candidate": self.logloss_candidate,
            "scale_champion": self.scale_champion,
            "scale_candidate": self.scale_candidate,
            "relative_logloss_reduction": self.relative_logloss_reduction,
            "auc_champion": self.auc_champion,
            "auc_candidate": self.auc_candidate,
            "auc_gain": self.auc_gain,
            "not_an_elo_predictor": True,
        }


def compare(champion: np.ndarray, candidate: np.ndarray, target: np.ndarray,
            k: float = K_DEFAULT, scale_champion: float | None = None,
            scale_candidate: float | None = None) -> Comparison:
    """Compare two evaluators with the recalibration freedom given to BOTH."""
    lc, cc = calibrated_logloss(champion, target, k, scale_champion)
    lk, ck = calibrated_logloss(candidate, target, k, scale_candidate)
    ac, ak = pairwise_auc(champion, target), pairwise_auc(candidate, target)
    return Comparison(lc, lk, cc, ck, (lc - lk) / lc if lc else 0.0,
                      ac, ak, (ak - ac) if (ac is not None and ak is not None) else None)
