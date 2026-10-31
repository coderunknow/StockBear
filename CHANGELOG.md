# Changelog

## 0.1.0-dev2 — 2026-10-31

Second development prerelease. Playing-strength and search changes were chosen by
ablation and validated by a paired match; the dead-position requirement is now
met by a general decision procedure.

- **FIDE Article 5.2.2 dead positions (new).** `src/chess/dead_position.{hpp,cpp}`
  implements a general decision procedure: an impossible-material proof stage, a
  cooperating helpmate witness search, and a bounded exhaustive enumeration of the
  complete reachable state component identified by 128-bit state fingerprints.
  `Dead` is returned only after a complete enumeration, `Alive` only with a
  checkmate witness, and every other outcome is `Unknown`. New CLI
  `stockbear deadpos --fen FEN [--states N] [--depth N]`, new
  `DrawStatus::AutomaticDeadPosition`, exhaustive two- and three-piece
  state-space tests, a 23-case corpus and an independent python-chess reference.
  `states` counts distinct reachable states and `expanded` counts applied moves
  (the budget applies to the latter). Two documented exceptions: a terminal
  position (checkmate/stalemate) is reported as `alive` with a `terminal:` reason
  and no witness, and the impossible-material class is `dead` by static proof
  without enumeration. Specification and limits: `docs/DEAD_POSITIONS.md`.
- **Search strength and speed.** Aspiration windows, null-move pruning with guards,
  late move reductions with integer scheduling, reverse futility, futility
  pruning, static exchange evaluation for ordering and pruning, delta pruning in
  quiescence, mate-distance pruning, a selection-sort move picker, improved
  history/killer updates and a soft/hard time budget with an early-stability stop.
  `static_exchange_evaluation()` is a public, unit-tested function.
  UCI options `NullMove`, `LMR`, `Aspiration`, `Futility`, `ReverseFutility`,
  `SEEPruning`, `CheckExtension` expose every switch (all default to the released
  behaviour). Measured: depth-6 suite 1,683,192 → 106,558 nodes and 1,041 → 52 ms
  (15.8× fewer nodes, 19.9× faster); depth-7 32.8× fewer nodes; 400 paired games
  vs dev1 scored +250 =103 −47 (Elo +194.3 [95 %: +164.5, +227.0], paired
  pentanomial, SPRT accept H1).
- **Transposition table.** Bucketed entries with a depth/generation replacement
  policy, mate-score conversion at store/probe, and context separation retained.
- **Time management.** Documented soft/hard budget contract, `movestogo` handling,
  a 30-move default, a 1 ms floor and usage-based stopping, covered by new
  contract tests.
- **Bug fixes.** Static exchange evaluation dropped the final recapture in its
  negamax fold, so a knight taking a defended pawn scored +100 instead of −220 and
  losing captures were ordered and pruned as if they were wins; fixed, unit-tested
  against hand-computed values, and every measurement in this release was taken
  after the fix. `unmake_null_move()` decremented the fullmove counter that
  `make_null_move()` never incremented, drifting the FEN after every null move;
  fixed and covered by null-move round-trip tests. `go` commands with unknown
  tokens are now ignored (as UCI requires) instead of being refused.
  `format_report()` no longer crashes when the SPRT cannot decide, and the match
  summary now reports the game count.
- **Benchmark and measurement tooling.** `bench --movetime`, `bench --param
  feature=0|1` ablations and a deterministic `# signature` fingerprint;
  `scripts/match_stats.py` (Wilson, pentanomial over opening pairs,
  normal-approximation SPRT) with known-value unit tests; `tournament.py` gains
  `--csv`, `--seed`, `--sprt-elo` and `--a-option`/`--b-option`; the opening suite
  grew to 31 verified openings.
- **CI.** Adds a ThreadSanitizer job, a search-determinism check, recorded build
  provenance, dead-position corpus/reference/exhaustive steps and statistics
  tests. All actions remain SHA-pinned.

See [release notes](RELEASE_NOTES.md) and
[the dev2 evidence report](benchmarks/results/0.1.0-dev2/REPORT.md). This
prerelease makes no strength-parity claim; against Stockfish 11 it scored 0.5/20.

## 0.1.0-dev1 — 2026-10-30

First independent development prerelease.

- Added standard-chess bitboard/mailbox position state, legal move generation, reversible moves, FEN and repetition-aware Zobrist hashing.
- Added castling, en passant, promotion, check/mate/stalemate, claimable and automatic draw status, and a conservative material dead-position detector.
- Added a single-threaded iterative-deepening alpha-beta/PVS search with quiescence, a context-aware transposition table, move ordering, killer/history heuristics, check extensions, time controls and cancellation.
- Added an independent tapered handcrafted evaluation and a UCI interface with Hash configuration.
- Added perft/divide, fixed-depth and fixed-node search benchmarks, a paired UCI tournament harness with PGN/JSONL and approximate confidence intervals, and a versioned baseline report.
- Added C++ unit/regression/perft/stress tests, UCI integration and fuzz tests, optional python-chess differential checks, Linux/Windows CI and sanitizer configuration.
- Deliberately deferred neural evaluation, training, tablebases, pondering, Chess960, MultiPV, speculative pruning and multithreaded search. Full arbitrary dead-position adjudication and polished time/evaluation strength remain future work.

See [release notes](RELEASE_NOTES.md) and [benchmark evidence](benchmarks/results/0.1.0-dev1/REPORT.md). This prerelease does not claim strength parity or superiority with Stockfish.
