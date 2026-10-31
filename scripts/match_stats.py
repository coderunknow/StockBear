#!/usr/bin/env python3
"""Match statistics helpers for StockBear's tournament harness (standard library only).

Two estimators are produced for a paired-opening match:

* the naive binomial/Wilson estimate over all games, which ignores the fact that
  games sharing an opening are correlated, and
* a *pentanomial* estimate that treats the two games of an opening pair as one
  observation with score in {0, 0.5, 1, 1.5, 2}. The pentanomial variance
  captures the within-pair dependence, and
* an *opening-clustered* variant of the pentanomial interval that also accounts
  for the same opening being replayed several times: the variance is computed
  from per-opening cluster totals (CR1) with a t critical value on G-1 degrees of
  freedom. When the number of distinct openings is small relative to the number of
  pairs this interval is wider than the plain pentanomial one, and it is the one
  quoted in the release notes.

Elo is reported only with an explicit interval and sample size. A point estimate
without a sample size is not evidence.
"""
import math

Z95 = 1.959963984540054


def score_to_elo(score):
    """Elo difference implied by a fractional score, or None at the extremes."""
    if score <= 0.0:
        return float("-inf")
    if score >= 1.0:
        return float("inf")
    return 400.0 * math.log10(score / (1.0 - score))


def finite_or_none(value):
    """Return `value` if it is finite, else None.

    JSON has no representation for infinities or NaN, and writing "Infinity"
    produces a document that strict parsers reject, so unbounded Elo estimates
    are serialised as null while `elo_text` still prints "-inf" for humans.
    """
    return value if isinstance(value, (int, float)) and math.isfinite(value) else None


def elo_text(value):
    if value == float("-inf"):
        return "-inf"
    if value == float("inf"):
        return "+inf"
    return f"{value:+.1f}"


def wilson(scores):
    n = len(scores)
    if not n:
        return {"games": 0}
    p = sum(scores) / n
    denominator = 1 + Z95 * Z95 / n
    center = (p + Z95 * Z95 / (2 * n)) / denominator
    half = Z95 * math.sqrt(p * (1 - p) / n + Z95 * Z95 / (4 * n * n)) / denominator
    lo, hi = max(0.0, center - half), min(1.0, center + half)
    return {"games": n, "score": p, "ci95": [lo, hi],
            "method": "Wilson on fractional game scores (ignores pair dependence)"}


def pentanomial(pair_scores):
    """Estimate Elo and its interval from per-pair combined scores."""
    pairs = len(pair_scores)
    if pairs < 2:
        return {"pairs": pairs, "note": "too few opening pairs for an interval"}
    mean_pair = sum(pair_scores) / pairs
    variance = sum((s - mean_pair) ** 2 for s in pair_scores) / (pairs - 1)
    stderr = math.sqrt(variance / pairs)
    score = mean_pair / 2.0
    counts = [pair_scores.count(v) for v in (2.0, 1.5, 1.0, 0.5, 0.0)]
    out = {
        "pairs": pairs,
        "score": score,
        "pair_score_mean": mean_pair,
        "pair_score_stderr": stderr,
        "pentanomial_counts_2_1.5_1_0.5_0": counts,
        "elo_difference": finite_or_none(score_to_elo(score)),
        "method": "pentanomial over opening pairs; normal interval on the pair mean",
    }
    if variance <= 0.0:
        # Every pair scored the same, so the sample carries no variance
        # information at all; a zero-width interval would claim certainty.
        out["elo_ci95"] = [None, None]
        out["elo_ci95_note"] = (
            "all pairs scored identically: the sample gives no variance "
            "information, so no interval is reported")
        return out
    lo_score = max(0.0, min(1.0, (mean_pair - Z95 * stderr) / 2.0))
    hi_score = max(0.0, min(1.0, (mean_pair + Z95 * stderr) / 2.0))
    out["elo_ci95"] = [finite_or_none(score_to_elo(lo_score)),
                       finite_or_none(score_to_elo(hi_score))]
    return out


# Two-sided 95 % Student-t critical values for the small cluster counts this
# script realistically sees. Above the table the normal value is used, which is
# conservative for df > 120 only by a fraction of a percent.
_T975 = {
    1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365,
    8: 2.306, 9: 2.262, 10: 2.228, 11: 2.201, 12: 2.179, 13: 2.160, 14: 2.145,
    15: 2.131, 16: 2.120, 17: 2.110, 18: 2.101, 19: 2.093, 20: 2.086,
    21: 2.080, 22: 2.074, 23: 2.069, 24: 2.064, 25: 2.060, 26: 2.056,
    27: 2.052, 28: 2.048, 29: 2.045, 30: 2.042, 40: 2.021, 60: 2.000,
    120: 1.980,
}


def _t95(df):
    if df in _T975:
        return _T975[df]
    keys = sorted(_T975)
    lower = max((k for k in keys if k < df), default=None)
    upper = min((k for k in keys if k > df), default=None)
    if lower is None:
        return Z95
    if upper is None:
        return _T975[lower]
    # Linear interpolation between table entries (conservative enough).
    a, b = _T975[lower], _T975[upper]
    return a + (b - a) * (df - lower) / (upper - lower)


def opening_clustered(pair_scores, pair_openings):
    """Cluster-robust interval for the mean pair score, clustered by opening.

    Games sharing an opening are not independent, and this suite replays each
    opening many times, so treating every pair as an independent observation
    understates the uncertainty. This estimator sums the pair scores inside each
    opening and uses the CR1 variance of the cluster totals with a Student-t
    critical value on G-1 degrees of freedom.
    """
    n = len(pair_scores)
    if n < 2 or len(pair_openings) != n:
        return {"clusters": 0, "note": "clustered interval needs pairs and their openings"}
    clusters = {}
    for score, opening in zip(pair_scores, pair_openings):
        clusters.setdefault(opening, []).append(score)
    groups = len(clusters)
    if groups < 2:
        return {"clusters": groups,
                "note": "fewer than two distinct openings: no clustered interval"}
    mean_pair = sum(pair_scores) / n
    total = 0.0
    for scores in clusters.values():
        studentised = sum(scores) - len(scores) * mean_pair
        total += studentised * studentised
    variance = groups / (groups - 1.0) * total / (n * n)
    stderr = math.sqrt(variance)
    critical = _t95(groups - 1)
    score = mean_pair / 2.0
    lo_score = max(0.0, min(1.0, (mean_pair - critical * stderr) / 2.0))
    hi_score = max(0.0, min(1.0, (mean_pair + critical * stderr) / 2.0))
    out = {
        "clusters": groups,
        "pair_score_mean": mean_pair,
        "pair_score_stderr": stderr,
        "critical_value": critical,
        "elo_difference": finite_or_none(score_to_elo(score)),
        "method": ("opening-clustered (CR1) variance of the pair mean with a "
                   "Student-t interval on G-1 degrees of freedom"),
    }
    if variance <= 0.0:
        out["elo_ci95"] = [None, None]
        out["elo_ci95_note"] = "zero variance across openings: no interval reported"
        return out
    out["elo_ci95"] = [finite_or_none(score_to_elo(lo_score)),
                       finite_or_none(score_to_elo(hi_score))]
    return out


def lmr_step(pair_scores, elo0, elo1, alpha=0.05, beta=0.05, sigma=None):
    """Normal-approximation SPRT on pair scores.

    elo0 / elo1 are the two hypotheses in Elo. Returns the log-likelihood ratio
    and the decision bound state. This is a stopping aid, not a proof: the
    reported interval should always accompany it.
    """
    def pair_mean(elo):
        p = 1.0 / (1.0 + 10.0 ** (-elo / 400.0))
        return 2.0 * p

    m0, m1 = pair_mean(elo0), pair_mean(elo1)
    if sigma is None:
        if len(pair_scores) < 2:
            return {"llr": 0.0, "decision": "continue", "note": "insufficient pairs"}
        mean = sum(pair_scores) / len(pair_scores)
        sigma = math.sqrt(sum((s - mean) ** 2 for s in pair_scores) / (len(pair_scores) - 1))
    if sigma is None or sigma <= 0:
        return {"llr": 0.0, "decision": "continue", "note": "degenerate variance"}
    total = sum(pair_scores)
    # Sum of log-likelihood ratios for a normal model with equal variance.
    llr = (m1 - m0) / (sigma * sigma) * (total - len(pair_scores) * (m0 + m1) / 2.0)
    lower = math.log(beta / (1.0 - alpha))
    upper = math.log((1.0 - beta) / alpha)
    decision = "accept H1" if llr >= upper else "accept H0" if llr <= lower else "continue"
    return {"llr": llr, "lower_bound": lower, "upper_bound": upper,
            "h0_elo": elo0, "h1_elo": elo1, "sigma_pair_scores": sigma,
            "decision": decision,
            "method": "normal-approximation SPRT on paired scores (approximation)"}


def summarise(game_scores, pair_scores, sprt=None, pair_openings=None):
    naive = wilson(game_scores)
    paired = pentanomial(pair_scores)
    out = {
        "games": len(game_scores),
        "wins": game_scores.count(1.0),
        "draws": game_scores.count(0.5),
        "losses": game_scores.count(0.0),
        "naive": naive,
        "paired": paired,
    }
    if pair_openings is not None:
        out["opening_clustered"] = opening_clustered(pair_scores, pair_openings)
    if sprt is not None:
        out["sprt"] = sprt
    return out


def _num_or_inf(value, sign):
    """Map a null (unbounded) Elo value to -inf/+inf for human-readable text.

    The direction has to come from the caller: a null can mean an unbounded
    lower end (0 % score) or an unbounded upper end (100 % score), and guessing
    "-inf" printed +inf as -inf for won or lost matches.
    """
    return float("inf") * sign if value is None else value


def _bounds_sign(pair_score_mean):
    """Direction of the unbounded endpoints implied by the pair mean."""
    if pair_score_mean <= 0.0:
        return -1.0, -1.0
    if pair_score_mean >= 2.0:
        return 1.0, 1.0
    return -1.0, 1.0


def format_report(summary):
    """Human readable multi-line summary used by the tournament CLI."""
    lines = []
    wins = summary.get("wins", 0)
    draws = summary.get("draws", 0)
    losses = summary.get("losses", 0)
    lines.append(f"games {wins + draws + losses}: +{wins} ={draws} -{losses}")
    naive = summary.get("naive", {})
    if naive.get("games"):
        lo, hi = naive["ci95"]
        lines.append(
            f"naive      : score {naive['score']:.3f} "
            f"[{lo:.3f}, {hi:.3f}], Elo {elo_text(score_to_elo(naive['score']))} "
            f"[{elo_text(score_to_elo(lo))}, {elo_text(score_to_elo(hi))}]")
    paired = summary.get("paired", {})
    if paired.get("pairs", 0) >= 2:
        lo, hi = paired["elo_ci95"]
        # Unbounded (0% or 100%) results are stored as null so the JSON stays
        # valid; print them the way a human reads them, in the right direction.
        low_sign, high_sign = _bounds_sign(paired.get("pair_score_mean", 1.0))
        point_sign = 1.0 if paired.get("pair_score_mean", 1.0) >= 1.0 else -1.0
        bounds = ("[interval not estimable]"
                  if paired.get("elo_ci95_note")
                  else f"[{elo_text(_num_or_inf(lo, low_sign))}, "
                       f"{elo_text(_num_or_inf(hi, high_sign))}]")
        lines.append(
            f"paired     : {paired['pairs']} opening pairs, score {paired['score']:.3f}, "
            f"Elo {elo_text(_num_or_inf(paired['elo_difference'], point_sign))} {bounds}")
        if paired.get("elo_ci95_note"):
            lines.append(f"             note: {paired['elo_ci95_note']}")
        counts = paired["pentanomial_counts_2_1.5_1_0.5_0"]
        lines.append(f"             pair scores 2/1.5/1/0.5/0 = {counts}")
    clustered = summary.get("opening_clustered", {})
    if clustered.get("clusters", 0) >= 2:
        low_sign, high_sign = _bounds_sign(clustered.get("pair_score_mean", 1.0))
        point_sign = 1.0 if clustered.get("pair_score_mean", 1.0) >= 1.0 else -1.0
        if clustered.get("elo_ci95") and not clustered.get("elo_ci95_note"):
            lo, hi = clustered["elo_ci95"]
            lines.append(
                f"clustered  : {clustered['clusters']} openings, "
                f"Elo {elo_text(_num_or_inf(clustered['elo_difference'], point_sign))} "
                f"[{elo_text(_num_or_inf(lo, low_sign))}, "
                f"{elo_text(_num_or_inf(hi, high_sign))}] "
                f"(t={clustered['critical_value']:.3f} on {clustered['clusters'] - 1} df)")
        else:
            lines.append(f"clustered  : {clustered['clusters']} openings, "
                         f"{clustered.get('elo_ci95_note', 'no interval')}")
    elif clustered.get("note"):
        lines.append(f"clustered  : {clustered['note']}")
    sprt = summary.get("sprt")
    if sprt:
        if "lower_bound" in sprt:
            lines.append(f"sprt       : LLR {sprt['llr']:.2f} "
                         f"(bounds {sprt['lower_bound']:.2f}, {sprt['upper_bound']:.2f}) "
                         f"-> {sprt['decision']}")
        else:
            # Too few pairs or a degenerate sample: say so instead of inventing
            # a decision.
            note = sprt.get("note", "no decision possible")
            lines.append(f"sprt       : no decision ({note})")
    return "\n".join(lines)


if __name__ == "__main__":
    # Tiny self-check so the module can be exercised without a match.
    import sys
    print(format_report(summarise([1.0, 1.0, 0.5, 0.0], [2.0, 0.5],
                                  lmr_step([2.0, 0.5], 0, 5),
                                  pair_openings=["A", "B"])))
    sys.exit(0)
