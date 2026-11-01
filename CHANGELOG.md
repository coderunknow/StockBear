# Changelog

## 0.1.0-dev3 — 2026-11-01

Third development prerelease. The search was rewritten with auditable feature
switches, MultiPV and `go searchmoves` became real, and the evaluation was made
fully parameterisable with an offline tuning pipeline. Three tuned evaluation
candidates were measured by paired matches, all were equal or worse than the
existing one, and the release therefore keeps the dev2 evaluation: the pipeline
and the negative result are documented instead of shipping an unvalidated set.

- **Search rewrite (`src/search/search.{hpp,cpp}`).** `SearchParams` now owns
  every pruning and ordering decision, with an independent switch for each.
  Integer static exchange evaluation replaces the recursive form. New ordering
  and history machinery: counter moves, continuation history, capture history,
  history maluses for quiets that do not cut off, and a history-adjusted late
  move reduction. `search_root(position, depth, alpha, beta, pvIndex)` implements
  MultiPV by re-running the root with the reported moves excluded, and swaps the
  alpha-improving move into the reported slot so `(move, score, pv)` cannot
  disagree. With every new switch off, the depth-6 and depth-7 bench signatures
  are exactly dev2's (`e06c4352681ae8eb`, `5bceff035f2a4ae4`), so the rewrite
  reproduces dev2 on the benchmark suite; that is a suite-level regression guard,
  not a proof of identical behaviour everywhere, and a null-move ordering fix
  found in review leaves both signatures unchanged while changing play.
- **Real MultiPV.** `setoption name MultiPV value 1..8` is advertised and
  implemented; lines are reported best-first with `multipv N`, exact scores and
  a PV that starts with its own move. A position with fewer legal moves than
  requested reports only the lines that exist; a terminal position still reports
  `bestmove 0000`.
- **`go searchmoves`.** The move list is parsed up to the next known keyword,
  validated against the position, and used to restrict the root. Illegal entries
  are reported with `info string` and dropped; a list with no legal move is
  reported and ignored, because answering `bestmove 0000` for a legal position
  would be worse. Covered by black-box tests over depth, nodes, movetime and
  clock limits.
- **Evaluation parameters as data.** Every evaluation weight is one entry in a
  32-entry table with a legal range; `stockbear eval --dump-params`,
  `stockbear bench --params FILE` and `setoption name EvalParams value FILE`
  expose it. The parameterised evaluation reproduces dev2 bit-for-bit
  (`evaldata --check`, `tests/unit/test_eval_baseline.cpp`).
- **Offline tuning pipeline.** `scripts/build_tuning_data.py`,
  `scripts/tune_eval.py` and a 2,000-game self-play dataset
  (`benchmarks/tuning/`) produce parameter sets by coordinate descent on a Texel
  logistic loss, with a game-level holdout split. Three candidates were produced
  and measured against the shipped evaluation (590–591 decided games each, paired
  colour-reversed, fixed node budget): −119.1 Elo (worse by both the pentanomial
  and the opening-clustered interval), −51.3 and +12.0 Elo (neither shown to be
  worse, neither an improvement). A fourth, conservative fit (Texel scale pinned
  at 400, ridge 0.10, 20 % movement cap, anchored material) moves seven positional
  terms by one or two points. None justified a change, so dev3 ships the dev2
  values. Full record: [docs/TUNING.md](docs/TUNING.md).
- **Tactics and endgame regression suites.** `benchmarks/tactics/mate_suite.epd`
  (26 forced mates, certified by an independent mate proof on python-chess with
  *all* mating moves accepted) and `benchmarks/tactics/endgame_suite.epd`
  (24 constructed KQK/KRK conversions, all converted at 400 k nodes after the
  null-move ordering fix). `scripts/run_suite.py` records per
  position the move, depth, node count, time and whether the node budget was
  exhausted, and keeps the raw engine output.
- **Deterministic match control** (from the dev2 line, now released):
  `scripts/tournament.py --nodes N` plays every move under a node budget so a
  match is reproducible on a shared machine; the tournament smoke test uses it.

## Unreleased (after 0.1.0-dev3)

- **Deterministic match control.** `scripts/tournament.py` gained `--nodes N`,
  which plays every move with `go nodes N` instead of the clock and records
  `nodes_per_move` in the JSONL configuration and summary. A node budget cannot
  be lost on the clock, so a match or a test can be reproduced on a shared
  machine. The tournament smoke test now uses it, removing a clock-dependent
  intermittent failure (one occurrence observed while the release CI ran in
  parallel with other jobs; the same tree passed every other run).
- `--nodes` is validated like the other limits (negative values are rejected).

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
  behaviour). Measured with both builds run alternately in one idle session:
  depth-6 suite 1,683,192 → 108,910 nodes and 622 → 49 ms (15.5× fewer nodes,
  12.8× faster); depth-7 33.1× fewer nodes and 23.1× faster; 400 paired games vs
  dev1 scored +277 =82 −41 (Elo +235.4; paired pentanomial 95 % interval +202.8
  to +272.2, opening-clustered interval +193.4 to +284.5; the LLR computed on the
  finished sample crosses the +5 Elo upper bound).
- **Transposition table.** Bucketed entries with a depth/generation replacement
  policy, mate-score conversion at store/probe, and context separation retained.
- **Time management.** Documented soft/hard budget contract, `movestogo` handling,
  a 30-move default, a 1 ms floor and usage-based stopping, covered by new
  contract tests.
- **Static exchange value of a king.** `SeeValue[King]` was 0, so SEE treated an
  illegal king recapture as available: `4k3/3p4/8/8/8/8/3R4/3R2K1 w - - 0 1`,
  `d2d7` returned −400 instead of +100 because the king appeared to win the rook
  back while the second rook still x-rayed the square. The king now has a huge
  value (so it is ordered last and its "capture" is never profitable), covered by
  a known-value test. This changes search behaviour, so every dev2 measurement in
  this release was taken after the fix.
- **Time safety.** The hard-timer polling interval in `Search::visit` is back to
  64 nodes (dev1's value): 1024 allowed a `go movetime` search to overrun its hard
  budget by up to a thousand nodes and risk a clock forfeit.
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
  feature=0|1` ablations and a deterministic `# signature` fingerprint (depth and
  node modes only; time-limited runs report it as unavailable);
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
