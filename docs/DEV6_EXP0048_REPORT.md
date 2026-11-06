# DEV6 exp-0048 — NEGATIVE candidate-development result (full per-square PST)

**Verdict: CLOSED — accuracy threshold NOT met. exp-0047 stays DORMANT.
Zero screen games, zero decisive games, zero strength games played.**

This report records a negative result. Nothing here is a strength claim, and no
protocol, threshold, seed or hyperparameter was changed after seeing the data.

---

## 1. What was run

| stage | identity |
|---|---|
| Prereg (frozen before any game) | `docs/DEV6_PREREG_EXP0048.md`, SHA-256 `ea1d397e6728818715fa80c3f39171ebe9c696695163ef31176ef1e41f726623` |
| Source the corpus was generated from | `49018e96a6abdba5091c1b39d2473b6f14819894` |
| Corpus run | GitHub Actions **42169244756**, 8/8 shards SUCCESS |
| Corpus export | run **42170087975** SUCCESS → commit `631a13a`, path `benchmarks/exp-runs/corpus-export/run-42169244756/` |
| Baseline (both sides) | immutable `benchmarks/binaries/stockbear-dev5-release`, SHA-256 `391cb50e13ab99168aba0255482554ab5e59d1a34af810bf8f4d2c88e5bdb918` |
| Conditions | 40+4 ms, Hash 16, Threads 1, max-plies 240, `EvalParams=research-data/params_abc.txt`, `TTEval=true` |
| Openings | seed 2026110601, 3,000 openings x2, 8 disjoint shards, zero overlap with 150 earlier suites (40,441 excluded positions) |
| Match seed | 2026110603 |

Corpus integrity (independently re-verified from the git export with
`sha256sum -c`): **6,000 games, 260,042 positions, 5,943 contributing games,
0 engine failures, 0 time forfeits.** Terminations: 4,012 checkmate, 1,800
threefold, 164 insufficient material, 9 fifty-move, 15 unadjudicated at the
240-ply cap (those contribute no positions, by the frozen extractor rule).

Split (frozen seed 2026110602, by game): 4,754 train games / 1,189 holdout games
= 207,782 train rows / 52,260 holdout rows.

## 2. Frozen metric and the measured outcome

Metric: held-out Texel log-loss `L = -mean[t*log10 p + (1-t)*log10(1-p)]`,
`p = 1/(1+10^(-s/400))`. Threshold frozen before the corpus existed:
**`L_cand <= 0.97 * L_champ` AND `B_cand <= B_champ`.**

| quantity | value |
|---|---|
| `L_champ` (holdout) | 0.2424826561 |
| `L_cand` (holdout) | 0.2424337459 |
| required `L_cand` ceiling | **0.2352081765** |
| relative log-loss reduction | **0.0202 %** (required >= 3 %) |
| `B_champ` / `B_cand` | 0.1034279593 / 0.1033744014 |
| accuracy threshold met | **FALSE** |

The Brier condition passed, but the log-loss condition missed by a factor of
~149 (0.0202 % vs 3 %). The conjunction is not satisfied, so the candidate does
not qualify. Evidence: `benchmarks/dev6-baseline/exp0048_results/FIT_REPORT.json`.

Three exact identity checks passed on **all 260,042 rows** before any metric was
computed, so the number above describes the real engine, not a Python model:
(a) the champion design matrix reproduces `evaluate()`; (b) the Python rebuild
of the formulaic PST equals the engine's PST term; (c) the engine loaded with
the fitted `--pst` equals the fitted model row-for-row.

## 3. Cost gate (measured, passed, and irrelevant to the verdict)

`benchmarks/dev6-baseline/exp0048_results/NPS_GATE.json`: node counts
bit-identical on all 7 included positions across 3 alternating repetitions,
champion median 2,497,826 nps, candidate median 2,521,968 nps,
**ratio 1.0097**, inside `[0.97, 1.03]`. A cheap evaluator that is not more
accurate is still not a stronger engine.

> **CORRECTION (2026-11-06, after exp-0049).** The original text here concluded
> "the mechanism is indeed free at the node level". **That conclusion is
> withdrawn.** A later A/A calibration of this same instrument
> (`benchmarks/dev6-baseline/nps_gate_calibration/`) ran BOTH arms as the
> identical champion binary — true ratio exactly 1.0 — and the frozen statistic
> still false-rejected **8/10** evaluations at 3 reps and **7/12** at 5 reps,
> returning ratios from **0.894 to 1.035**. The shared 2-core sandbox cannot
> resolve a ±3 % band, so this measurement supports **neither** "free per node"
> **nor** any slowdown. The recorded numbers stand as measured; only the
> interpretation is retracted. **The exp-0048 verdict is unchanged**: it closed
> on the accuracy gate, which is timing-independent.

## 4. Root cause — recorded, NOT used to retune

`GRADIENT_DIAGNOSIS.json`. The fitted table barely moved:
**max |delta| 1.22 cp, RMS |delta| 0.124 cp**, 0 entries clipped, 0 clamped rows.

The objective is the *mean* loss, so each entry's data gradient is divided by
207,782 rows. For a square appearing in ~5 % of rows the data gradient is
~8.6e-5, while the frozen L2 term `2 * 1e-5 * delta` reaches ~2e-5 at just 1 cp.
The regulariser is therefore the same order of magnitude as the signal at
~1 cp and pins the table to the formulaic initialisation.

**What this means honestly:** the experiment as frozen tested
"formulaic PST + sub-1.3 cp perturbation", not an expressive 768-parameter
table. The negative result is a valid negative for *this frozen protocol*; it is
**not** evidence that an expressive per-square table cannot help. That
distinction is recorded so a future hypothesis is not wrongly foreclosed — and
equally so this run is not wrongly reported as a fair test of the strong version.

**What was NOT done:** the L2 weight, iteration count, learning rate and split
seed were frozen before the corpus existed. They were **not** adjusted after
seeing the result. No second fit was run. No sweep, no best-of-N, no
"corrected" rerun on the same data. Doing that would convert a preregistered
test into a tuning loop on its own holdout.

## 5. Consequences under the frozen rules

- exp-0048 candidate-development outcome: **NEGATIVE / CLOSED**.
- exp-0047 activation: **NOT activated.** Conditions 1 (accuracy) and 3
  (expected-effect argument for >= +75) are unmet; its Activation Record stays
  empty. Zero games under exp-0047.
- The §6 diagnostic screen was **not** run: it is gated on the accuracy
  threshold, and spending 2,000 games on a candidate already known to be
  ~0.02 % better would be compute waste and an invitation to selective reading.
- Gate 1 UNMET, Gate 2 direction-only, Gate 3 PASS, Gate 4 UNMET.
- No PR presenting a strength improvement. No merge, tag, release, prerelease
  or deploy.

## 6. Reusable assets produced (engineering value, independent of the verdict)

The mechanism and its measurement infrastructure are sound and remain in the
tree, default-OFF and bit-exact: the `PstFile` UCI option, `bench --pst`,
`evaldata --pst`, the isolated-runner corpus lane with checksummed export, the
by-game splitter, and a fitter that refuses to report a metric until the engine
agrees with its model on every row. A future expressive-evaluator hypothesis
can reuse all of it with its own, properly scaled, pre-registered objective.

## 7. Evidence index

- `benchmarks/dev6-baseline/exp0048_results/FIT_REPORT.json` — metrics, hashes, hyperparameters, identity checks
- `benchmarks/dev6-baseline/exp0048_results/GRADIENT_DIAGNOSIS.json` — root cause
- `benchmarks/dev6-baseline/exp0048_results/NPS_GATE.json` — cost gate, 3 reps, raw per-position rows
- `benchmarks/dev6-baseline/exp0048_results/exp0048.sbpst` — the exact fitted table, SHA-256 `ba22b73d58d33c9afd8f7ee9e6b6e0d92ab4edc7a59c1fd65226413fef7e695f`
- `benchmarks/dev6-baseline/exp0048_results/SHA256SUMS.txt`
- `benchmarks/exp-runs/corpus-export/run-42169244756/` — raw PGN/JSONL/EPD (gzip), per-shard manifests, `MANIFEST.json`, `SHA256SUMS.txt`
- `benchmarks/dev6-baseline/exp0048_corpus_suites.json`, `exp0048_screen_suites.json` — suite provenance (screen suites generated but **unused**)

---

## 8. Post-closure exploratory follow-up (does NOT change the verdict above)

After closing exp-0048, one exploratory question was asked before spending any
further compute: does an expressive per-square table carry real outcome signal
at all, or was the mechanism empty? `scripts/dev6_exp0048_exploratory_ceiling.py`
re-fitted the same closed corpus across an L2 grid. Result
(`benchmarks/dev6-baseline/exp0048_exploratory/EXPLORATORY_CEILING.json`):

| L2 | held-out log-loss reduction | RMS delta (cp) |
|---|---|---|
| 0 | **4.4721 %** | 276.8 |
| 1e-8 | 1.6495 % | 21.4 |
| 1e-7 | 0.7088 % | 5.5 |
| 1e-6 | 0.1735 % | 0.98 |
| **1e-5 (the frozen exp-0048 value)** | **0.0202 %** | **0.124** |

This confirms the §4 root cause quantitatively: the frozen L2 sits at the
degenerate end of the curve, where the optimum IS the initialisation. The
mechanism itself is not empty.

**Limits, stated explicitly:** these are EXPLORATORY numbers on a BURNED corpus.
They do not rehabilitate exp-0048, do not activate exp-0047, and are not a
strength claim. The exp-0048 verdict in §1–§5 stands exactly as written. Any
successor must be a NEW preregistration, frozen before its own FRESH corpus,
disjoint from this one and from every prior suite. A 4.47 % accuracy gain is
also NOT evidence of +75 Elo; only a fixed-time match can establish that.
