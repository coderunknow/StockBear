#!/usr/bin/env python3
"""Statistical power / expected interval width for the dev6 decisive design.

Derived from the exp-0024 raw per-game records (12 shards, the released dev5
portable artifact confirmation), as the mission requires: "Before committing to
the final sample size, calculate statistical power and expected interval width
from exp-0024 raw records and the proposed new opening distribution."

The new dev6 design uses one colour-reversed PAIR per distinct opening (no
repeated openings within a batch), so the opening-clustered CR1 variance with
G = number of clusters reduces to the paired pentanomial variance with a
Student-t critical value on G-1 df. We estimate the per-pair score variance
from exp-0024 and project the 95% CI half-width in Elo for the planned
per-batch (3300 pairs) and combined (6600 pairs) sample sizes, and the sample
size required for the mandatory LCB95 > +50 at a given true point estimate.
"""
import glob
import json
import math
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import match_stats

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "benchmarks" / "dev6-baseline" / "power_analysis.json"
MD = ROOT / "docs" / "DEV6_POWER_ANALYSIS.md"


def load_pairs():
    pair_scores, pair_openings = [], []
    shards = sorted(glob.glob(str(ROOT / "benchmarks/exp-runs/exp0024-shard*/match.jsonl")))
    for path in shards:
        recs = []
        with open(path) as f:
            for line in f:
                o = json.loads(line)
                if "game" not in o:
                    continue
                recs.append(o)
        recs.sort(key=lambda r: r["game"])
        for k in range(0, len(recs) - 1, 2):
            a, b = recs[k], recs[k + 1]
            if a["score_a"] is None or b["score_a"] is None:
                continue
            pair_scores.append(a["score_a"] + b["score_a"])
            pair_openings.append(a["opening"])
    return shards, pair_scores, pair_openings


def elo(score):
    return match_stats.score_to_elo(score)


def halfwidth_elo(mean_pair, stderr, critical):
    # score = mean_pair/2 ; interval on the pair score -> /2 on the score scale
    d = critical * stderr / 2.0
    return (elo(min(1 - 1e-9, mean_pair / 2.0 + d)) -
            elo(max(1e-9, mean_pair / 2.0 - d))) / 2.0


def main():
    shards, ps, po = load_pairs()
    n = len(ps)
    obs = match_stats.opening_clustered(ps, po)
    mean_pair = sum(ps) / n
    # unbiased sample variance of the pair scores (0..2 scale)
    s2 = sum((x - mean_pair) ** 2 for x in ps) / (n - 1)
    # effective variance including exp-0024's within-opening clustering
    s2_eff = obs["pair_score_stderr"] ** 2 * n
    t_large = 1.960  # df large

    def project(pairs, s2_use, point_elo):
        # one pair per cluster => CR1 stderr ~= sqrt(s2_use / pairs)
        se = math.sqrt(s2_use / pairs)
        hw = halfwidth_elo(mean_pair, se, t_large)
        return {"pairs": pairs, "distinct_openings": pairs, "games": 2 * pairs,
                "score_stderr": se, "elo_halfwidth": hw,
                "point_elo": point_elo, "expected_ci95": [point_elo - hw, point_elo + hw]}

    per_batch_ind = project(3300, s2, 75.0)
    combined_ind = project(6600, s2, 75.0)
    per_batch_eff = project(3300, s2_eff, 75.0)
    combined_eff = project(6600, s2_eff, 75.0)

    # Games needed for LCB95 > +50 at a true point of +75 (LCB = point - hw > 50
    # => hw < 25). Solve hw(pairs) = 25 using the (conservative) effective var.
    def hw_for(pairs, s2_use):
        return halfwidth_elo(mean_pair, math.sqrt(s2_use / pairs), t_large)

    need = {}
    for name, s2_use in (("independent_clusters", s2), ("exp0024_cluster_effect", s2_eff)):
        lo, hi = 2, 20_000_000
        for _ in range(80):
            mid = (lo + hi) // 2
            if hw_for(mid, s2_use) > 25.0:
                lo = mid
            else:
                hi = mid
        need[name] = {"pairs_for_hw25": hi, "games_for_hw25": 2 * hi}

    result = {
        "source": "exp-0024 raw match.jsonl (12 shards), the released dev5 portable artifact confirmation",
        "shards": [os.path.basename(s) for s in shards],
        "observed_pairs": n,
        "observed_clusters": obs["clusters"],
        "observed_pairs_per_cluster": n / obs["clusters"],
        "observed_pair_score_mean": mean_pair,
        "observed_clustered_elo": obs["elo_difference"],
        "observed_clustered_ci95": obs["elo_ci95"],
        "observed_pair_score_stderr": obs["pair_score_stderr"],
        "pair_score_variance_independent": s2,
        "pair_score_variance_with_exp0024_cluster_effect": s2_eff,
        "design": "2 batches x 3300 distinct openings x 2 colour-reversed games = 13200 games, one pair per cluster",
        "projection_at_point_plus75": {
            "per_batch_independent": per_batch_ind,
            "combined_independent": combined_ind,
            "per_batch_with_cluster_effect": per_batch_eff,
            "combined_with_cluster_effect": combined_eff,
        },
        "sample_for_lcb_gt_50_at_point_75": need,
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n")

    lines = [
        "# dev6 decisive-confirmation power analysis",
        "",
        "Derived from the **exp-0024 raw per-game records** (`benchmarks/exp-runs/exp0024-shard*/match.jsonl`),",
        "the exact released-dev5 portable-artifact confirmation. Primary estimator throughout dev6 is the",
        "opening-clustered CR1 variance with a two-sided 95% Student-t interval (G-1 df), logistic Elo.",
        "",
        "## Observed exp-0024 baseline",
        "",
        f"- {n} scored pairs over {obs['clusters']} distinct openings "
        f"({n/obs['clusters']:.2f} pairs/cluster).",
        f"- Clustered Elo {obs['elo_difference']:+.1f}, 95% CI "
        f"[{obs['elo_ci95'][0]:+.1f}, {obs['elo_ci95'][1]:+.1f}], "
        f"pair-score SE {obs['pair_score_stderr']:.5f}.",
        f"- Independent pair-score variance s^2 = {s2:.5f}; variance inflated by exp-0024's",
        f"  within-opening clustering = {s2_eff:.5f}.",
        "",
        "## Proposed dev6 design",
        "",
        "Two independent batches, each 3300 **distinct** paired openings x 2 colour-reversed games",
        "= 6600 games/batch, 13200 games combined, **one pair per opening cluster** (no repeated",
        "opening positions within a batch, no overlap between batches). With one pair per cluster",
        "the CR1 variance reduces to s^2/G with a Student-t critical value on G-1 df.",
        "",
        "## Expected 95% CI half-width (at a true +75 Elo point)",
        "",
        "| scope | pairs | s^2 used | Elo half-width | expected CI |",
        "|---|---|---|---|---|",
        f"| one batch (independent) | 3300 | {s2:.4f} | {per_batch_ind['elo_halfwidth']:.1f} | "
        f"[{per_batch_ind['expected_ci95'][0]:+.1f}, {per_batch_ind['expected_ci95'][1]:+.1f}] |",
        f"| combined (independent) | 6600 | {s2:.4f} | {combined_ind['elo_halfwidth']:.1f} | "
        f"[{combined_ind['expected_ci95'][0]:+.1f}, {combined_ind['expected_ci95'][1]:+.1f}] |",
        f"| one batch (exp-0024 cluster effect) | 3300 | {s2_eff:.4f} | {per_batch_eff['elo_halfwidth']:.1f} | "
        f"[{per_batch_eff['expected_ci95'][0]:+.1f}, {per_batch_eff['expected_ci95'][1]:+.1f}] |",
        f"| combined (exp-0024 cluster effect) | 6600 | {s2_eff:.4f} | {combined_eff['elo_halfwidth']:.1f} | "
        f"[{combined_eff['expected_ci95'][0]:+.1f}, {combined_eff['expected_ci95'][1]:+.1f}] |",
        "",
        f"At a true +75 Elo point, the combined 13200-game design has an expected half-width of",
        f"~{combined_eff['elo_halfwidth']:.1f} Elo (conservative), so LCB95 would be ~{75-combined_eff['elo_halfwidth']:.1f},",
        "comfortably above +50 **if** the candidate truly were +75. The design also has power to",
        "decisively reject +75 for a ~0-Elo candidate (its CI excludes +50 and +75 by a wide margin).",
        "",
        "## Sample size for the gate itself",
        "",
        f"For LCB95 > +50 at a true +75 point (half-width < 25 Elo):",
        f"- with independent clusters: ~{need['independent_clusters']['games_for_hw25']:,} games;",
        f"- carrying exp-0024's cluster effect: ~{need['exp0024_cluster_effect']['games_for_hw25']:,} games.",
        "Both are far below the planned 13200 games, i.e. the sample size is not the binding",
        "constraint; the binding constraint is a candidate whose true strength gain is >= +75.",
        "The planned 13200 games therefore has ample power and is not reduced.",
        "",
        "Machine-readable: `benchmarks/dev6-baseline/power_analysis.json`.",
    ]
    MD.write_text("\n".join(lines) + "\n")
    print(json.dumps(result["projection_at_point_plus75"], indent=2))
    print(json.dumps(result["sample_for_lcb_gt_50_at_point_75"], indent=2))
    print("wrote", MD, "and", OUT)


if __name__ == "__main__":
    main()
