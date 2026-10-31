#!/usr/bin/env python3
"""Match statistics helpers for StockBear's tournament harness (standard library only).

Two estimators are produced for a paired-opening match:

* the naive binomial/Wilson estimate over all games, which ignores the fact that
  games sharing an opening are correlated, and
* a *pentanomial* estimate that treats the two games of an opening pair as one
  observation with score in {0, 0.5, 1, 1.5, 2}. The pentanomial variance
  captures the within-pair dependence, so its confidence interval is the honest
  one when openings are reused with reversed colours.

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
    lo_score = max(0.0, min(1.0, (mean_pair - Z95 * stderr) / 2.0))
    hi_score = max(0.0, min(1.0, (mean_pair + Z95 * stderr) / 2.0))
    counts = [pair_scores.count(v) for v in (2.0, 1.5, 1.0, 0.5, 0.0)]
    return {
        "pairs": pairs,
        "score": score,
        "pair_score_mean": mean_pair,
        "pair_score_stderr": stderr,
        "pentanomial_counts_2_1.5_1_0.5_0": counts,
        "elo_difference": score_to_elo(score),
        "elo_ci95": [score_to_elo(lo_score), score_to_elo(hi_score)],
        "method": "pentanomial over opening pairs; normal interval on the pair mean",
    }


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


def summarise(game_scores, pair_scores, sprt=None):
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
    if sprt is not None:
        out["sprt"] = sprt
    return out


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
        lines.append(
            f"paired     : {paired['pairs']} opening pairs, score {paired['score']:.3f}, "
            f"Elo {elo_text(paired['elo_difference'])} "
            f"[{elo_text(lo)}, {elo_text(hi)}]")
        counts = paired["pentanomial_counts_2_1.5_1_0.5_0"]
        lines.append(f"             pair scores 2/1.5/1/0.5/0 = {counts}")
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
                                  lmr_step([2.0, 0.5], 0, 5))))
    sys.exit(0)
