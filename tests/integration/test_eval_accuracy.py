#!/usr/bin/env python3
"""Property tests for the scale-invariant accuracy comparison.

The point of these tests is the NEGATIVE CONTROL that the old fixed-K gate
failed: a pure positive rescale of an evaluation must score ZERO gain. Without
that property a gate can be cleared by shrinking every score toward a draw
(verified in docs/DEV6_ACCURACY_GATE_VALIDITY.md: a 0.80 rescale of every champion
parameter passed the frozen 3% gate on two independent corpora).

Standard library + numpy only; no engine required.
"""
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "scripts"))

import eval_accuracy as ea  # noqa: E402


def _fixture(n=4000, seed=17):
    """Scores with genuine signal plus a draw-heavy outcome distribution."""
    rng = np.random.default_rng(seed)
    latent = rng.normal(0.0, 220.0, n)
    p = 1.0 / (1.0 + np.power(10.0, -latent / 400.0))
    u = rng.random(n)
    # 45% draws, mimicking a real self-play corpus.
    target = np.where(u < 0.45, 0.5, np.where(u < 0.45 + 0.55 * p, 1.0, 0.0))
    return latent + rng.normal(0.0, 90.0, n), target


def test_pure_rescale_scores_zero_gain():
    s, t = _fixture()
    for factor in (0.5, 0.8, 0.95, 1.0, 1.25, 2.0, 10.0):
        cmp = ea.compare(s, s * factor, t)
        assert abs(cmp.relative_logloss_reduction) < 1e-6, (factor, cmp)
        assert cmp.auc_gain is None or abs(cmp.auc_gain) < 1e-12, (factor, cmp)


def test_old_fixed_link_metric_is_fooled_by_the_same_rescale():
    # Demonstrates the defect this module exists to fix: at a FIXED link the
    # uncalibrated loss improves materially under a pure rescale.
    s, t = _fixture()
    base = ea.logloss(s, t)
    gains = [(f, (base - ea.logloss(s * f, t)) / base) for f in (0.5, 0.6, 0.8)]
    assert any(g > 0.01 for _, g in gains), gains
    # ...while the calibrated comparison correctly reports ~0 for every one.
    for f, _ in gains:
        assert abs(ea.compare(s, s * f, t).relative_logloss_reduction) < 1e-6


def test_genuine_improvement_is_still_detected():
    s, t = _fixture()
    rng = np.random.default_rng(99)
    worse = s + rng.normal(0.0, 260.0, s.size)      # same scale, more noise
    cmp = ea.compare(worse, s, t)
    assert cmp.relative_logloss_reduction > 0.01, cmp
    assert cmp.auc_gain > 0.01, cmp


def test_sign_flip_is_a_regression_and_auc_shows_its_severity():
    s, t = _fixture()
    cmp = ea.compare(s, -s, t)
    assert cmp.relative_logloss_reduction < 0.0, cmp
    # Calibrated log-loss is FLOORED at the constant predictor log10(2), because
    # a bad arm can shrink its scale to zero. So it cannot express the true
    # severity of a sign flip; assert it reaches that floor instead of an
    # arbitrary threshold (an earlier -0.05 assertion was simply unachievable).
    floor = math.log10(2.0)
    assert cmp.logloss_candidate <= floor + 1e-4, cmp
    worst_possible = (cmp.logloss_champion - floor) / cmp.logloss_champion
    assert cmp.relative_logloss_reduction >= worst_possible - 1e-4, cmp
    # AUC has no such floor and does show the severity.
    assert cmp.auc_gain < -0.3, cmp


def test_auc_invariant_to_any_increasing_transform():
    s, t = _fixture()
    a = ea.pairwise_auc(s, t)
    for f in (lambda x: x * 0.01, lambda x: x * 7.0,
              lambda x: np.sign(x) * np.log1p(np.abs(x)), lambda x: x + 1000.0):
        assert abs(ea.pairwise_auc(f(s), t) - a) < 1e-12


def test_auc_matches_direct_pair_count():
    # Small case checked against the O(n^2) definition, ties counted as one half.
    s = np.array([10.0, 20.0, 20.0, 5.0, 30.0, 1.0])
    t = np.array([1.0, 1.0, 0.0, 0.0, 0.5, 1.0])
    pos, neg = s[t >= 1.0], s[t <= 0.0]
    total = 0.0
    for a in pos:
        for b in neg:
            total += 1.0 if a > b else (0.5 if a == b else 0.0)
    assert abs(ea.pairwise_auc(s, t) - total / (pos.size * neg.size)) < 1e-12


def test_auc_none_when_one_class_absent():
    assert ea.pairwise_auc(np.array([1.0, 2.0]), np.array([1.0, 1.0])) is None
    assert ea.pairwise_auc(np.array([1.0, 2.0]), np.array([0.5, 0.5])) is None


def test_all_zero_scores_are_handled():
    t = np.array([1.0, 0.0, 0.5, 1.0])
    z = np.zeros(4)
    loss, scale = ea.calibrated_logloss(z, t)
    assert scale == 1.0 and math.isfinite(loss)
    assert abs(loss - math.log10(2.0)) < 1e-12


def test_train_fitted_scale_applies_to_holdout():
    s, t = _fixture()
    half = s.size // 2
    _, c = ea.calibrated_logloss(s[:half], t[:half])
    held, used = ea.calibrated_logloss(s[half:], t[half:], scale=c)
    assert used == c and math.isfinite(held)
    # Applying the training scale must be no better than refitting on holdout.
    refit, _ = ea.calibrated_logloss(s[half:], t[half:])
    assert held >= refit - 1e-12


def test_fit_scale_recovers_a_known_shrink():
    s, t = _fixture()
    _, c_true = ea.calibrated_logloss(s, t)
    _, c_half = ea.calibrated_logloss(s * 0.5, t)
    # Halving the scores must double the fitted scale.
    assert abs(c_half / c_true - 2.0) < 1e-3, (c_true, c_half)


def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failures = 0
    for test in tests:
        try:
            test()
            print("PASS", test.__name__)
        except Exception as error:  # noqa: BLE001 - report every failure
            failures += 1
            print("FAIL", test.__name__, error)
    print(f"tests {len(tests)}, failures {failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
