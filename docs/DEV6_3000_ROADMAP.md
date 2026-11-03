# v0.1.0-dev6 — Long-term 3,000 Elo roadmap (evidence-driven, pool-specific)

## Ground rules

"3,000 Elo" is a **long-term strategic target**, not a property of dev6 and not a
universally comparable number. StockBear does **not** currently have a measured
absolute rating in any specified external pool (see
`docs/DEV6_EXTERNAL_LADDER.md`, status NOT COMPLETED). Therefore:

- The **numeric distance to 3,000 is unknown** and is deliberately **not estimated**
  or projected; no timeline is manufactured.
- The roadmap is expressed as **measurable relative strength milestones** against
  the immutable dev5 baseline and, once available, as pool-specific ladder ratings.
- Every milestone names the pool, opponents, time control, hardware, versions and
  statistical uncertainty. Published CCRL/CEGT/FIDE ratings are contextual only.

## Measured starting point (verified)

- Baseline: exact released dev5 portable binary (SHA `391cb50e…`) at champion
  config (`params_abc` + `TTEval`), which measured **+64.7 [+57.5,+72.0] Elo vs
  dev4** at 40+4 ms / 6600 games (exp-0024). dev4 is pinned in-repo.
- dev6 cycle result: see `docs/DEV6_CONFIRMATION.md` / `benchmarks/FAILURE_LEDGER.md`.
  The +75 gate was the acceptance criterion for this cycle; it is reported
  honestly whether met or not.
- Absolute external rating: **STILL NOT DEFENSIBLY CALIBRATED** (ladder executed but fixed-node/pool-specific; SF11 `UCI_Elo` contextual anchor has ~199 Elo residual SD). Gap to 3,000: **UNKNOWN, NOT ASSERTED**.

## Weakness inventory (from the Failure Ledger and this cycle's evidence)

- **Evaluation / positional**: 36→38-term linear tapered eval; pawn structure,
  king safety (attack-count only), mobility (geometric), no proper pawn hash, no
  endgame-specific knowledge (opposition, rook activity, fortresses), no NNUE.
  dev6 added 6 correctly-verified pawn/coordination features but they are small
  linear terms; measured effect is reported in the confirmation report.
- **Tactical**: at 40+4 the search reaches only depth ~3–7 (~7k nodes/move);
  qsearch stand-pat quality is critical (qsearch-lite −32 Elo, exp-0007). Every
  pruning/extension is load-bearing at this depth (exp-0011).
- **Endgame**: no tablebases, no 50-move/progress term in search, dead-position
  analysis exists but is not a strength lever; passed-pawn/king-activity terms
  are rudimentary.
- **Search**: single-threaded alpha-beta with aspiration, null-move, LMR,
  reverse futility, SEE, check extension; no singular extensions, ProbCut, or
  SMP. Knob sweeps are neutral at bullet (exp-0006).
- **Time management**: at 40+4 the sustainable budget is the 4 ms increment
  (exp-0004/0015); "use more clock" causes forfeits. Only NPS gains help.
- **Performance**: popcnt/BMI2/LZCNT + LTO + SEE-cache already in the portable
  build; PGO/THP/TT-packing neutral, incremental eval −27% NPS (exp-0013).
- **Data/training**: NNUE attempts (479k/310k positions, CPU-only) were −650..−760
  Elo and ~4x slower (exp-0001); outcome tuning plateaus at ~+40..+48 true over
  dev4 (exp-0016/0017); best-of-N param selection is noise.

## Staged, measurable milestones (no dates, no fabricated ratings)

Milestones are gated by pre-registered paired colour-reversed matches at 40+4 ms
with opening-clustered CR1 95% CIs and clean nulls, against SHA-pinned baselines.

1. **M0 — Rating foundation (BLOCKER, first).** Complete the external ladder
   (exp-0030+): pilot for non-saturated anchors, BTD fit, pool-specific rating
   for dev5 and the current champion + 95% CI, explicit pool/hardware/opponents.
   *Exit*: a reproducible internal ladder rating with CI, and the numeric gap to
   3,000 stated with uncertainty. Without M0 no absolute claim is possible.
2. **M1 — Reliably beat dev5.** A candidate that clears a pre-registered
   +75 [LCB>+50] gate vs exact dev5 (the dev6 objective). *Exit*: two disjoint
   confirmation suites, clean nulls, independent audit, green CI, exact-SHA.
   Highest-EV directions: a genuinely stronger evaluator (modern NNUE trained on
   a large, diverse, bullet-matched self-play corpus with fast SIMD/quantised
   inference — materially different from exp-0001's failed small CPU net), or a
   bit-exact NPS step-change verified by profiling.
3. **M2 — Close the mid-game eval gap.** Introduce a stronger evaluation with a
   credible accuracy→strength link: pawn/king-safety hash, tapered endgame
   knowledge, or a properly engineered NNUE with measured inference cost at 40+4.
   *Exit*: each feature independently ablated, correctness-tested against an
   independent reference, cost-measured, and fixed-time-confirmed.
4. **M3 — Search depth & quality at bullet.** Singular extensions / ProbCut /
   aspiration recalibration / improved qsearch, only with new hypotheses and
   fixed-time evidence after any eval-scale change (recalibrate cp margins).
   *Exit*: no tactical regression on tactics/endgame suites; clustered gain.
5. **M4 — Time & parallelism.** Consider Lazy SMP only with TSan evidence,
   determinism/race analysis and a measured strength/time benefit at the same
   node budget; verify deployment compatibility. *Exit*: measured per-thread
   gain, no race/reproducibility regression.
6. **M5 — Absolute scale.** Re-run the ladder (M0) on the improved engine; report
   the pool-specific rating and remaining distance to 3,000 with CIs; update this
   roadmap with the new measurement. Repeat M1–M5 as an evidence-driven loop.

## Cross-cutting requirements for every milestone

- Pre-registration before results; append-only Failure Ledger (never erase
  negatives); independent recomputation from raw records; exact-SHA CI/review;
  append-only design/agents logs; no merge/tag/release without user approval;
  portable artifact verification (no `-march=native` without dispatch).
- Preserve independence: Stockfish/others are opponents/teachers only, never
  copied into StockBear source or networks.
- Efficiency: profile before optimising; a few informative experiments over
  dozens of arbitrary toggles; close directions the ledger shows are negative.

## Honest current verdict

Verified: dev5 baseline pinned; dev6 extended-feature implementation and
correctness; decisive confirmation data (see confirmation report). Not verified /
blocked: external rating ladder, absolute 3,000-Elo gap, any claim that StockBear
has an absolute rating. The 3,000 target remains a strategic direction, gated
first on M0 (a measured pool-specific rating) and then on M1 (a genuine,
independently-confirmed strength gain over dev5).
