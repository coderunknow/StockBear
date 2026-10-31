# StockBear v0.1.0-dev2 — development prerelease

StockBear is an independent C++17 UCI chess engine. Its board, legal move
generation, state management, alpha-beta search, evaluation, dead-position
analysis and UCI controller are implemented in this repository; it neither
embeds nor calls another engine to select moves. This is an early development
release, not a stable or leading-strength engine.

## What is new in dev2

- **A general FIDE Article 5.2.2 dead-position decision procedure.** The
  detector proves `Alive` with a checkmate witness or `Dead` by exhaustively
  enumerating the complete reachable state component, and says `Unknown`
  otherwise. It finds dead positions that no material rule can see (14 blocked
  pawns: 768 distinct states; locked pawn chains with bishops: 152,352 distinct
  states reached by 1,268,497 move applications) and
  refuses to call provably alive positions dead (`KNN` v `K`, `KB` v `KN`,
  `KN` v `KN`). New CLI: `stockbear deadpos --fen FEN`. Details, correctness
  argument and limits: [docs/DEAD_POSITIONS.md](docs/DEAD_POSITIONS.md).
- **A substantially faster and stronger search**: aspiration windows, null-move
  pruning, late move reductions, reverse futility and futility pruning, static
  exchange evaluation, delta pruning in quiescence, mate-distance pruning, a
  better move picker and a real soft/hard time budget.
- **Measurable evidence**: the depth-6 benchmark suite went from 1,683,192 to
  106,558 nodes (685 ms → 57 ms, measured alternately in one session), the
  depth-7 suite from 8,276,659 to 252,556
  nodes, and 400 paired games against dev1 scored +250 =103 −47, i.e.
  **Elo +194.3 with a 95 % interval of +158.5 to +234.4** (opening-clustered over
  the 31 distinct openings; the plain pentanomial interval over the 200 opening
  pairs, which treats them as independent, is the narrower +164.5 to +227.0).
- **Honest tournament statistics**: Wilson intervals, a pentanomial model over
  opening pairs, an approximate SPRT, seeded opening shuffling, 31 verified
  openings, and a harness that records time forfeits and capped games instead of
  inventing draws.
- **Safer draw and protocol behaviour**: dead-position adjudication is separate
  from the search's cheap material heuristic, the null-move counter drift is
  fixed, and unknown `go` tokens are ignored as UCI requires instead of
  refusing the search.
- **Ablation switches**: `bench --param feature=0|1` and the matching UCI check
  options make every search feature measurable by nodes *and* by match.

## Evidence

Raw data, commands and interpretation:
[benchmarks/results/0.1.0-dev2/REPORT.md](benchmarks/results/0.1.0-dev2/REPORT.md)
— benchmark CSV for two depths, the feature-ablation CSV, 400-game PGN/JSONL/CSV
against dev1, a 20-game match against Stockfish 11, and the dead-position corpus
and its independent reference comparison.

Verification: CTest entries `unit`, `regression`, `perft_quick`, `perft_full`,
`stress`, `deadpos` (including exhaustive two- and three-piece state-space
sweeps), `uci_integration` and `uci_fuzz`; Linux GCC Debug/Release,
ASan+UBSan and ThreadSanitizer runs; Clang Release and minimum-CMake-3.16 CI
jobs; Windows Debug/Release CI; and python-chess differential and reference
checks. Check the CI runs for the exact release commit — this document does not
substitute for them.

## Strength statement

Against dev1 the improvement is supported (400 paired games, +250 =103 −47, +194.3
Elo). Against a mature engine the gap remains very large: dev2 scored **0.5/20**
against Stockfish 11 at 100 ms + 10 ms (one draw, nineteen losses), with no
forfeits. The latest stable Stockfish (19) could **not** be built in the release
environment because its NNUE network files are not reachable there, so no
Stockfish 19 match was played and no claim about Stockfish 19 is made. No
superiority or parity claim is made against any engine.

## Compatibility

Standard UCI: `uci`, `isready`, `ucinewgame`, `position`, `go`
(depth/nodes/movetime/clocks/increments/movestogo/infinite), `stop`, `quit`,
`debug`, and `info` lines with depth, seldepth, score, nodes, nps, hashfull, time
and pv. Options: `Hash` (1–512 MiB) plus the boolean ablation switches. There is
no `Threads` option: the search is single-threaded and advertising a thread
option that does nothing would be misleading. A terminal position returns
`bestmove 0000`. See the README for the ScrispChess-Extended Custom UCI Engine
Manager instructions.

## Platforms and limitations

Linux x64 and Windows x64 are the release targets; CI builds and tests Linux and
Windows Debug/Release and produces the Release archives. No AVX2/AVX-512, GPU or
external engine is required at run time.

The dead-position analysis is exact but exponential in the worst case; positions
whose reachable component exceeds the configured budget return `unknown` rather
than a guess. With the default budget of 3,000,000 expanded positions a run needs
roughly 90 MiB and 1.5 s in the measured environment; memory grows with the
number of distinct states, so `--states` raises both the time and the memory. FEN cannot
encode earlier repetition history, so a GUI/referee must still adjudicate claims.
No Chess960, pondering, MultiPV, tablebases, opening book, neural evaluation or
training system is provided.

Apache-2.0. Optional validation and opponent software is recorded in
[THIRD_PARTY.md](THIRD_PARTY.md).
