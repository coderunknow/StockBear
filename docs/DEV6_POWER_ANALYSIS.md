# dev6 decisive-confirmation power analysis

Derived from the **exp-0024 raw per-game records** (`benchmarks/exp-runs/exp0024-shard*/match.jsonl`),
the exact released-dev5 portable-artifact confirmation. Primary estimator throughout dev6 is the
opening-clustered CR1 variance with a two-sided 95% Student-t interval (G-1 df), logistic Elo.

## Observed exp-0024 baseline

- 3284 scored pairs over 1748 distinct openings (1.88 pairs/cluster).
- Clustered Elo +61.7, 95% CI [+54.3, +69.2], pair-score SE 0.01050.
- Independent pair-score variance s^2 = 0.29095; variance inflated by exp-0024's
  within-opening clustering = 0.36230.

## Proposed dev6 design

Two independent batches, each 3300 **distinct** paired openings x 2 colour-reversed games
= 6600 games/batch, 13200 games combined, **one pair per opening cluster** (no repeated
opening positions within a batch, no overlap between batches). With one pair per cluster
the CR1 variance reduces to s^2/G with a Student-t critical value on G-1 df.

## Expected 95% CI half-width (at a true +75 Elo point)

| scope | pairs | s^2 used | Elo half-width | expected CI |
|---|---|---|---|---|
| one batch (independent) | 3300 | 0.2910 | 6.6 | [+68.4, +81.6] |
| combined (independent) | 6600 | 0.2910 | 4.7 | [+70.3, +79.7] |
| one batch (exp-0024 cluster effect) | 3300 | 0.3623 | 7.4 | [+67.6, +82.4] |
| combined (exp-0024 cluster effect) | 6600 | 0.3623 | 5.2 | [+69.8, +80.2] |

At a true +75 Elo point, the combined 13200-game design has an expected half-width of
~5.2 Elo (conservative), so LCB95 would be ~69.8,
comfortably above +50 **if** the candidate truly were +75. The design also has power to
decisively reject +75 for a ~0-Elo candidate (its CI excludes +50 and +75 by a wide margin).

## Sample size for the gate itself

For LCB95 > +50 at a true +75 point (half-width < 25 Elo):
- with independent clusters: ~462 games;
- carrying exp-0024's cluster effect: ~576 games.
Both are far below the planned 13200 games, i.e. the sample size is not the binding
constraint; the binding constraint is a candidate whose true strength gain is >= +75.
The planned 13200 games therefore has ample power and is not reduced.

Machine-readable: `benchmarks/dev6-baseline/power_analysis.json`.
