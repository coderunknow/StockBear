# Roadmap

## v0.1.0-dev2 priorities — status

1. **Independent move-generation and property tests.** Done: the dev2 suite adds
   null-move round-trip and counter-drift tests, a dedicated CTest entry for the
   dead-position group, exhaustive two- and three-piece state-space sweeps, a
   statistics unit test, and a stricter UCI fuzz oracle that distinguishes
   rejected `go` commands from ignored unknown tokens.
2. **FIDE dead-position adjudication beyond material signatures, and better draw
   claim decisions.** Done: `src/chess/dead_position.{hpp,cpp}` is a general
   decision procedure with an impossible-material proof stage, a cooperating
   helpmate witness search and a bounded exhaustive reachable-component
   enumeration; it returns `Alive`/`Dead` only with a proof and `Unknown`
   otherwise. Claim handling now distinguishes automatic dead positions from
   fivefold/75-move and claimable threefold/fifty-move, with checkmate
   precedence and a search-versus-adjudication split. Specification:
   [DEAD_POSITIONS.md](DEAD_POSITIONS.md).
3. **Time management, search ordering, evaluation and performance.** Done:
   aspiration windows, null-move pruning, late move reductions, reverse
   futility, futility pruning, SEE for ordering and pruning, delta pruning in
   quiescence, a selection-sort move picker, history/killer improvements, a
   soft/hard time budget with an early-stability stop, and UCI switches for
   every feature so ablations can be measured by matches. Recorded effect: 15.5x
   fewer nodes on the depth-6 suite and +235.4 Elo (opening-clustered 95 %
   interval +193.4 to +284.5; paired pentanomial +202.8 to +272.2) over dev1 in
   the retained 400-game paired match; the exact figures are in
   `benchmarks/results/0.1.0-dev2/REPORT.md`.
4. **Tournament statistics, opening diversity and uncertainty.** Done:
   `scripts/match_stats.py` (Wilson, pentanomial over opening pairs,
   opening-clustered CR1/t interval for the replayed-opening suite,
   normal-approximation SPRT), a 31-opening suite with seeded shuffling, CSV
   output, explicit time-forfeit/illegal-move handling, and no fabricated
   draws at the ply cap. Statistics are unit-tested against known values.
5. **Compiler/platform coverage and release provenance.** Done: CI keeps the
   Linux/Windows × Debug/Release matrix and adds ThreadSanitizer, a
   search-determinism check, build provenance, a Clang Release job, a minimum
   CMake 3.16 job and an independent-reference job that now runs the
   dead-position evidence. The manual release workflow verifies an annotated
   tag, default-branch ancestry and a successful exact-commit CI run before
   publishing checksummed archives.

## v0.1.0-dev3 priorities — status

1. **A real evaluation-parameter layer and an offline tuning pipeline.** Done in
   form, negative in result. Every evaluation weight is now a named parameter
   (`src/evaluation/eval_params.{hpp,cpp}`, `benchmarks/params/*.txt`,
   `stockbear bench --params FILE`, UCI `EvalParams`), the training data is a
   generated self-play corpus with a separate holdout split and recorded
   checksums, and `scripts/tune_eval.py` fits it reproducibly. Three tuned
   parameter sets were produced and all three were matched against the shipped
   evaluation: −119.1 [−140.8, −98.2], −51.3 [−72.2, −30.8] and +12.0
   [−10.3, +34.4] Elo over 590–591 decided games. None was shipped; the release
   keeps the dev2 coefficients. Record: [TUNING.md](TUNING.md).
2. **Search-feature work with independent switches and ablations.** Done in form,
   negative in result. Counter-move history, continuation history, capture
   history, history maluses and a history-aware LMR adjustment were implemented,
   unit-tested and measured: all five on scored +1.3 [−17.9, +20.5] Elo against
   the dev2 binary over 571 decided games, and the history-malus/LMR/continuation
   subset scored −16.2 [−33.0, +0.5] against the same binary with them off over
   600 games. All five default to **off**, which makes the shipped search
   behaviourally identical to dev2 (`bench` signatures match exactly).
3. **Tactics and endgame suites.** Done: `benchmarks/tactics/` holds a 26-position
   mate suite (sourced from StockBear self-play games, every position re-proved
   by an independent python-chess oracle that lists all mating moves) and a
   24-position three-man endgame suite. Fixed-node runs, raw output retained:
   26/26 mates at 60 k nodes; 22/24 endgames converted at 400 k nodes.
4. **UCI completeness.** Done: `go searchmoves` parses, validates, restricts the
   root, reports illegal and all-illegal lists and never swallows the following
   keyword; real `MultiPV 1–8` reports ranked distinct root moves with exact
   scores and consistent principal variations. Both are exercised black-box over
   depth, nodes, movetime and clock limits by `uci_integration`.
5. **Strength measurement discipline.** Done: every claim above is a paired
   colour-reversed match with a recorded seed, pentanomial and
   opening-clustered intervals, unadjudicated games excluded from the score and
   the exact commands retained in `benchmarks/results/0.1.0-dev3/`.

The honest summary of dev3 is that it improved the *capability* of the codebase
(parameterised evaluation, switchable search, testable protocol, reproducible
suites) and did **not** improve playing strength. The measurements that say so
are retained rather than dropped.

## Next (v0.1.0-dev4 candidates)

- Convert the endgame suite failures (`kqk-12`, `krk-17`) into a repetition-aware
  eval or a claim-aware root policy; both currently draw games that are won.
- Re-run the tuning pipeline on a much larger corpus from a stronger baseline.
  The dev3 analyser's data was produced by a 6,000-node search, and the fitted
  parameters' disagreement with play suggests the labels, not the optimiser, are
  the limit; a deeper label set is the next experiment.
- A larger external match against a current Stockfish build in an environment
  that can fetch its NNUE networks; the dev2 external check used Stockfish 11
  and the dev3 attempts are recorded as blocked.
- Optional opening-book support.
- Investigate bounded parallel search (Lazy SMP) only with ThreadSanitizer
  evidence and a measured strength/time benefit at the same node budget.

## Longer-term research (not implemented)

An evaluation interface and independent position/search code allow later
experimentation with independently trained NNUE, transformer evaluation,
policy-value networks, supervised learning, self-play, reinforcement learning,
MCTS or alpha-beta/MCTS hybrids, distributed training, GPU inference, parameter
optimization and evolutionary approaches. None of this is included in this
development release. Training/data provenance, licenses, cost, testing and
credible tournament evidence must precede any strength claim. Surpassing a
leading engine is an aspirational research goal, not a result established by
this release.
