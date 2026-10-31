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
   every feature so ablations can be measured by matches. Recorded effect: 15.8x
   fewer nodes on the depth-6 suite and +194.3 Elo (opening-clustered 95 %
   interval +158.5 to +234.4; paired pentanomial +164.5 to +227.0) over dev1 in
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

## Next (v0.1.0-dev3 candidates)

- Run per-feature strength ablations with the new UCI switches on larger
  samples; the current node-count ablations are ambiguous for null-move and
  check extensions and are documented as such.
- Evaluation tuning with a recorded tuning procedure (nothing is tuned yet).
- A larger external match against a current Stockfish build in an environment
  that can fetch its NNUE networks; the dev2 external check used Stockfish 11
  for that reason.
- Optional opening-book support and MultiPV for analysis GUIs.
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
