#!/usr/bin/env python3
"""Known-value tests for scripts/match_stats.py (standard library only).

These pin down the statistics the tournament report quotes, so a regression in
the interval arithmetic cannot silently produce a nicer-looking Elo claim.
"""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "scripts"))

import match_stats  # noqa: E402


def close(a, b, tol=1e-6):
    return abs(a - b) <= tol


def test_wilson_known_value():
    # Wilson 95% interval for 5 successes out of 10 is [0.2366, 0.7634].
    result = match_stats.wilson([1.0] * 5 + [0.0] * 5)
    assert result["games"] == 10
    assert close(result["score"], 0.5)
    lo, hi = result["ci95"]
    assert close(lo, 0.23659, 1e-4), lo
    assert close(hi, 0.76341, 1e-4), hi
    # The interval must stay inside [0, 1] for degenerate samples.
    all_wins = match_stats.wilson([1.0] * 20)
    assert all_wins["ci95"][0] > 0.0 and all_wins["ci95"][1] <= 1.0


def test_interval_shrinks_with_more_games():
    small = match_stats.wilson([1.0, 0.0] * 5)
    large = match_stats.wilson([1.0, 0.0] * 50)
    small_width = small["ci95"][1] - small["ci95"][0]
    large_width = large["ci95"][1] - large["ci95"][0]
    assert large_width < small_width, (small_width, large_width)


def test_elo_transform():
    assert close(match_stats.score_to_elo(0.5), 0.0)
    assert close(match_stats.score_to_elo(0.75), 400.0 * math.log10(3.0))
    assert match_stats.score_to_elo(1.0) == float("inf")
    assert match_stats.score_to_elo(0.0) == float("-inf")


def test_pentanomial_matches_hand_computation():
    # Four opening pairs worth 2, 2, 1.5 and 0.5 points: mean 1.5, i.e. a 75%
    # score. The variance is taken over pair scores, which is what makes the
    # interval honour the dependence between the two games of an opening.
    pairs = [2.0, 2.0, 1.5, 0.5]
    result = match_stats.pentanomial(pairs)
    mean = sum(pairs) / len(pairs)
    variance = sum((p - mean) ** 2 for p in pairs) / (len(pairs) - 1)
    stderr = math.sqrt(variance / len(pairs))
    assert close(result["pair_score_mean"], mean)
    assert close(result["pair_score_stderr"], stderr)
    assert close(result["score"], mean / 2.0)
    assert close(result["elo_difference"], 400.0 * math.log10(0.75 / 0.25))
    lo, hi = result["elo_ci95"]
    assert lo < result["elo_difference"]
    # A 75 % score with only four pairs has no finite upper bound once the
    # interval is clamped at 100 %, so the upper end is serialised as null
    # rather than as the invalid JSON token "Infinity".
    assert hi is None or hi > result["elo_difference"]
    assert result["pentanomial_counts_2_1.5_1_0.5_0"] == [2, 1, 0, 1, 0]


def test_pentanomial_needs_pairs():
    assert "note" in match_stats.pentanomial([2.0])


def test_sprt_decisions():
    strong = match_stats.lmr_step([2.0] * 170 + [1.5] * 30, 0.0, 5.0)
    assert strong["decision"] == "accept H1", strong
    weak = match_stats.lmr_step([0.6] * 170 + [0.5] * 30, 0.0, 5.0)
    assert weak["decision"] == "accept H0", weak
    neutral = match_stats.lmr_step([1.5, 0.5] * 10, 0.0, 5.0)
    assert neutral["decision"] == "continue", neutral
    assert neutral["lower_bound"] < neutral["llr"] < neutral["upper_bound"]
    # A degenerate sample (every pair identical) has no variance information,
    # so the step must say so rather than report a decision.
    degenerate = match_stats.lmr_step([2.0] * 5, 0.0, 5.0)
    assert degenerate["decision"] == "continue"
    assert "degenerate" in degenerate["note"]


def test_summary_is_valid_strict_json():
    # Every match summary must survive a strict JSON round trip, including
    # all-wins and all-losses samples where Elo is unbounded.
    import json
    for scores, pairs in (([1.0] * 20, [2.0] * 10),
                          ([0.0] * 20, [0.0] * 10),
                          ([1.0, 0.5, 0.0, 1.0], [1.5, 1.0])):
        summary = match_stats.summarise(scores, pairs,
                                        match_stats.lmr_step(pairs, 0.0, 5.0))
        text = json.dumps({"summary": summary}, allow_nan=False)
        assert "Infinity" not in text and "NaN" not in text
        assert json.loads(text)["summary"]["paired"] is not None
    all_wins = match_stats.summarise([1.0] * 20, [2.0] * 10,
                                     match_stats.lmr_step([2.0] * 10, 0.0, 5.0))
    assert all_wins["paired"]["elo_difference"] is None
    assert "elo_ci95" in all_wins["paired"]
    # The human-readable report still shows the unbounded direction.
    assert "-inf" in match_stats.format_report(all_wins) or "+inf" in match_stats.format_report(all_wins)


def test_zero_variance_reports_no_interval():
    # Ten identical pair scores give zero variance; a zero-width interval would
    # present a point estimate as certainty, so no interval is reported and the
    # text report says so.
    identical = match_stats.pentanomial([1.0] * 10)
    assert identical["elo_ci95"] == [None, None]
    assert "no variance" in identical["elo_ci95_note"]
    summary = match_stats.summarise([0.5] * 20, [1.0] * 10,
                                    pair_openings=["A", "B"] * 5)
    text = match_stats.format_report(summary)
    assert "interval not estimable" in text, text


def test_unbounded_elo_keeps_its_direction():
    # An all-wins sample is unbounded upwards, an all-losses sample downwards.
    won = match_stats.summarise([1.0] * 4, [2.0, 2.0], pair_openings=["A", "B"])
    lost = match_stats.summarise([0.0] * 4, [0.0, 0.0], pair_openings=["A", "B"])
    won_text = match_stats.format_report(won)
    lost_text = match_stats.format_report(lost)
    # The point estimate and the naive lower bound are the unbounded direction
    # of the result; the earlier code always printed "-inf" for both ends.
    assert "+inf" in won_text, won_text
    assert "[-inf," not in won_text, won_text
    assert "-inf" in lost_text, lost_text
    assert "+inf" not in lost_text, lost_text


def test_opening_clustered_interval_accounts_for_repeats():
    # Two openings replayed five times each: the clustered interval must be
    # wider than the pentanomial one, which assumes 10 independent pairs.
    pair_scores = [2.0, 2.0, 2.0, 2.0, 2.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    openings = ["A"] * 5 + ["B"] * 5
    plain = match_stats.pentanomial(pair_scores)
    clustered = match_stats.opening_clustered(pair_scores, openings)
    assert clustered["clusters"] == 2
    # df = G-1 = 1. The value is the true t_{0.975,1} = 12.70620473... rounded
    # UP at 1e-6, so the interval is never narrower than nominal 95 %.
    assert clustered["critical_value"] == 12.706205
    # stderr = 1.0 pair points here, so the t interval covers the whole range
    # and both ends are unbounded, while the plain pentanomial interval is not.
    assert clustered["elo_ci95"] == [None, None], clustered
    assert plain["elo_ci95"] != [None, None], plain
    # One opening only: no between-opening information, so no interval.
    assert "note" in match_stats.opening_clustered([2.0, 1.0], ["A", "A"])


def test_report_contains_uncertainty_and_sample_size():
    summary = match_stats.summarise([1.0, 0.5, 0.0, 1.0], [1.5, 1.0],
                                    match_stats.lmr_step([1.5, 1.0], 0.0, 5.0))
    text = match_stats.format_report(summary)
    assert "games 4:" in text
    assert "opening pairs" in text
    assert "Elo" in text and "[" in text and "]" in text
    assert "sprt" in text


# --- Independent reference for the Student-t critical values -----------------
# The gate decision is "opening-clustered 95 % CI lower bound strictly > +50".
# If the critical value is too SMALL the interval is too narrow and the lower
# bound is biased UPWARD, i.e. toward passing. The shipped table used to be
# rounded to nearest, which made 14 of 128 checked df anti-conservative. These
# tests recompute t_{0.975,df} from scratch via the regularised incomplete beta
# function (continued fraction + bisection), with no dependency on the table.

def _betacf(a, b, x):
    MAXIT, EPS, FPMIN = 500, 3e-16, 1e-300
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < FPMIN:
        d = FPMIN
    d = 1.0 / d
    h = d
    for m in range(1, MAXIT + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < FPMIN:
            d = FPMIN
        c = 1.0 + aa / c
        if abs(c) < FPMIN:
            c = FPMIN
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < FPMIN:
            d = FPMIN
        c = 1.0 + aa / c
        if abs(c) < FPMIN:
            c = FPMIN
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < EPS:
            break
    return h


def _betai(a, b, x):
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    lbeta = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
    front = math.exp(lbeta + a * math.log(x) + b * math.log(1.0 - x))
    if x < (a + 1.0) / (a + b + 2.0):
        return front * _betacf(a, b, x) / a
    return 1.0 - front * _betacf(b, a, 1.0 - x) / b


def _t975_reference(df):
    """Smallest t with P(|T_df| > t) <= 0.05, by bisection on the exact CDF."""
    lo, hi = 1.0, 200.0
    for _ in range(200):
        mid = (lo + hi) / 2.0
        if _betai(df / 2.0, 0.5, df / (df + mid * mid)) > 0.05:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


def test_t_critical_values_are_never_anti_conservative():
    dfs = list(range(1, 121)) + [150, 200, 300, 500, 1000, 2000, 5000, 10000]
    for df in dfs:
        reference = _t975_reference(df)
        got = match_stats._t95(df)
        # The safety property: never narrower than nominal 95 %.
        assert got >= reference - 1e-9, (
            f"anti-conservative t critical value at df={df}: "
            f"table {got!r} < true {reference!r}")
        # Upper bounds are MEASURED, not guessed, and differ by construction:
        #   exact table df : ceiled at 1e-6      -> excess < 1e-6
        #   interpolated   : chord above convex  -> excess < 4e-3 (max 3.54e-3)
        #   df > 120       : clamped at t(120)   -> excess < 2.1e-2
        # All three err conservative; a gross typo would exceed these.
        if df in match_stats._T975:
            limit = 1e-6
        elif df <= 120:
            limit = 4e-3
        else:
            limit = 2.1e-2
        assert got <= reference + limit, (df, got, reference, limit)


def test_t_critical_values_are_monotone_and_bounded_below_by_normal():
    previous = None
    for df in range(1, 10001):
        value = match_stats._t95(df)
        if previous is not None:
            assert value <= previous + 1e-12, (df, value, previous)
        # t converges to the normal quantile from above; never below it.
        assert value >= match_stats.Z95 - 1e-12, (df, value)
        previous = value


def test_clustered_variance_matches_independent_derivation():
    # CR1 variance of the pair mean, accumulated per cluster in a different
    # algebraic form from the implementation, on pseudo-random cluster sizes.
    state = 12345
    def rnd(n):
        nonlocal state
        state = (1103515245 * state + 12345) % (2 ** 31)
        return state % n
    for _ in range(50):
        groups = 2 + rnd(10)
        scores, openings = [], []
        for g in range(groups):
            for _ in range(1 + rnd(6)):
                scores.append(rnd(5) / 2.0)
                openings.append(f"op{g}")
        n = len(scores)
        mean = sum(scores) / n
        per = {}
        for value, opening in zip(scores, openings):
            per.setdefault(opening, []).append(value)
        total = 0.0
        for values in per.values():
            deviation = sum(v - mean for v in values)
            total += deviation * deviation
        reference = math.sqrt((groups / (groups - 1.0)) * total / (n * n))
        got = match_stats.opening_clustered(scores, openings)
        assert got["clusters"] == groups
        assert abs(got["pair_score_stderr"] - reference) < 1e-12
        assert abs(got["elo_difference"]
                   - match_stats.score_to_elo(mean / 2.0)) < 1e-9


def test_clustering_widens_interval_under_within_opening_correlation():
    scores, openings = [], []
    for g in range(20):
        value = 2.0 if g % 2 else 0.0   # perfectly correlated inside an opening
        for _ in range(5):
            scores.append(value)
            openings.append(f"op{g}")
    clustered = match_stats.opening_clustered(scores, openings)
    unclustered = match_stats.opening_clustered(
        scores, [f"u{i}" for i in range(len(scores))])
    assert clustered["pair_score_stderr"] > unclustered["pair_score_stderr"]


def main():
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
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
