# Changelog

## Unreleased — dev2 investigation (blocked)

- Add a bounded movement-only mate-reachability research probe, not a general FIDE adjudicator.
- Avoid fabricated results for time forfeits; record opening seeds and file hashes, and omit unsupported Elo intervals.
- Add reduced-state independent validation and document unresolved release gates.
- Include third-party notices in packages and add release archive and uploaded-byte checks (not yet exercised in a release).


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
