# StockBear v0.1.0-dev3 — development prerelease

StockBear is an independent C++17 UCI chess engine. Its board, legal move
generation, state management, alpha-beta search, evaluation, dead-position
analysis and UCI controller are implemented in this repository; it neither
embeds nor calls another engine to select moves. This is an early development
release, not a stable or leading-strength engine.

## What is new in dev3

- **Real `MultiPV`.** `MultiPV 1–8` reports that many distinct legal root moves
  as ranked `multipv` lines, each with its own score, principal variation, node
  count and a `bestmove` that equals line 1. Fewer legal moves than requested is
  handled by reporting fewer lines. Previously the option did not exist.
- **Real `go searchmoves`.** The list is parsed, validated against the legal root
  moves, and enforced under every kind of limit. Illegal entries are reported and
  dropped; a list with nothing legal in it is reported and ignored instead of
  answered with a dummy move; a list followed by another keyword does not swallow
  it. MultiPV and searchmoves are covered by black-box CTest entries over depth,
  nodes, movetime and clock limits.
- **The evaluation is data, not constants.** Every weight is a named parameter in
  a documented table with ranges and a provenance comment, dumpable and loadable
  (`stockbear bench --params FILE`, UCI `EvalParams`), with the dev2 values kept
  as `benchmarks/params/dev2-baseline.txt` so the previous behaviour is
  identifiable and reproducible byte for byte.
- **An offline tuning pipeline.** `scripts/tune_eval.py` fits the parameter table
  to a generated self-play corpus with separate training/holdout splits, recorded
  seeds, checksums and command lines. It is reproducible and it is honest: the
  three candidates it produced were matched against the shipped evaluation and
  **none of them improved on it** (−132.5 Elo, confirmed worse by both reported
  intervals; 0.0 and −9.2 Elo, indistinguishable from the shipped set; 582–600
  decided games each), and a fourth, more conservative fit moves
  seven positional terms by one or two points without a match to justify them.
  The shipped release therefore keeps the dev2 coefficients. Record and
  reproduction commands: [docs/TUNING.md](docs/TUNING.md).
- **Five new search-ordering features, implemented, tested and left off.**
  Counter-move history, continuation history, capture history, history maluses and
  a history-aware LMR adjustment each have an independent UCI switch and a
  documented rationale. Two matches measured them: all five on scored +1.3 Elo
  [−17.9, +20.5] against the dev2 binary, and the history-malus + history-LMR
  subset scored −16.2 Elo [−33.0, +0.5] against the same binary with them off.
  They are off by default, and with them off the rewrite reproduces dev2's
  benchmark signatures exactly (`e06c4352681ae8eb` at depth 6,
  `5bceff035f2a4ae4` at depth 7).
- **Tactics and endgame suites with an independent oracle.**
  `benchmarks/tactics/mate_suite.epd` (26 mate positions from StockBear self-play
  games, each re-proved by a python-chess oracle that lists *all* mating moves)
  and `benchmarks/tactics/endgame_suite.epd` (24 three-man endgames). Fixed-node,
  reproducible runs with raw output retained: **26/26** mates solved at 60 k
  nodes, **24/24** endgames converted at 400 k nodes.
- **A search audit with fixes.** The mate-score, transposition-table, repetition
  and fifty-move, null-move-zugzwang, interruption and PV-construction paths were
  re-derived and covered by new unit tests, including MultiPV ordering, MultiPV
  versus single-PV agreement, searchmoves restriction, and immediate termination in
  terminal positions. The `counterMoves` comment inconsistency was resolved by
  documenting what the code actually does rather than by changing behaviour.
- **Determinism and option honesty.** The advertised default of every check option
  is now read from the live configuration instead of being hard-coded, so a
  default can never drift from what the search uses.

## Strength statement for dev3

**dev3 does not claim to be stronger than dev2, and is not.** Its search and
evaluation are the dev2 ones with the new features switched off; a 200-game
paired regression match against a rebuilt `v0.1.0-dev2` binary scored 0.5000
(70 =60 −70), with 70 pairs split one win each way and 30 pairs drawn twice, so
every one of the 100 pairs scored 1.0. dev2's own
strength result stands unchanged: **+235.4 Elo over dev1** (400 paired games,
opening-clustered 95 % interval +193.4 to +284.5) and **0.5/20 against
Stockfish 11**. No match against Stockfish 19 was possible in the release
environment (its NNUE network assets are unreachable there and every archived
network available was architecture-incompatible); the attempts are recorded in
the evidence report. No superiority or parity claim is made against any engine.

## Evidence

[benchmarks/results/0.1.0-dev3/REPORT.md](benchmarks/results/0.1.0-dev3/REPORT.md)
— build identity, benchmark signatures and per-set nodes, both search-feature
matches, the regression match, the three evaluation matches, the suite runs with
raw engine output, and the blocked Stockfish 19 attempts with their error text.
[benchmarks/results/0.1.0-dev3/tuning/](benchmarks/results/0.1.0-dev3/tuning/) —
the generated dataset manifest, the three parameter variants and their matches.

Verification: CTest entries `unit` (37 tests), `position_extra`, `regression`,
`perft_quick`, `perft_full`, `stress`, `deadpos`, `uci_integration` and
`uci_fuzz`; Linux GCC Debug/Release, ASan+UBSan and ThreadSanitizer runs; Clang
Release and minimum-CMake-3.16 CI jobs; Windows Debug/Release CI. Check the CI
runs for the exact release commit — this document does not substitute for them.

## Compatibility

Standard UCI: `uci`, `isready`, `ucinewgame`, `position`, `go`
(depth/nodes/movetime/clocks/increments/movestogo/infinite/searchmoves), `stop`,
`quit`, `debug`, and `info` lines with depth, seldepth, multipv, score, nodes, nps,
hashfull, time and pv. Options: `Hash` (1–512 MiB), `MultiPV` (1–8),
`EvalParams` (a parameter file), plus the boolean search-feature switches. The
five dev3 ordering switches default to off. There is no `Threads` option: the
search is single-threaded and advertising a thread option that does nothing would
be misleading. A terminal position returns `bestmove 0000`.

## Platforms and limitations

Linux x64 and Windows x64 are the release targets; CI builds and tests Linux and
Windows Debug/Release and produces the Release archives. No AVX2/AVX-512, GPU or
external engine is required at run time, and builds are portable (no
`-march=native`).

Known limitations: the search has no fifty-move or progress term, so a won
endgame can in principle still be shuffled into a claimable repetition (no
position in the committed suite does at 400 k nodes, but the mechanism is
unchanged); the evaluation tuning did not improve play; all matches are
node-limited and therefore measure strength per node rather than per second;
there is no Stockfish 19 measurement.

The dead-position analysis is exact but exponential in the worst case; positions
whose reachable component exceeds the configured budget return `unknown` rather
than a guess. FEN cannot encode earlier repetition history, so a GUI/referee must
still adjudicate claims. No Chess960, pondering, tablebases, opening book, neural
evaluation or training system is provided.

Apache-2.0. Optional validation and opponent software is recorded in
[THIRD_PARTY.md](THIRD_PARTY.md).

---

# Earlier release: StockBear v0.1.0-dev2 — development prerelease

The notes for the previous prerelease are kept verbatim below for provenance.

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
  108,910 nodes (622 ms → 49 ms, measured alternately in one idle session), the
  depth-7 suite from 8,276,659 to 250,053 nodes, and 400 paired games against dev1
  scored +277 =82 −41, i.e. **Elo +235.4 with a 95 % interval of +193.4 to
  +284.5** (opening-clustered over the 31 distinct openings; the plain pentanomial
  interval over the 200 opening pairs, which treats them as independent, is the
  narrower +202.8 to +272.2).
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

Verification: CTest entries `unit`, `position_extra` (null-move integrity),
`regression`, `perft_quick`, `perft_full`, `stress`, `deadpos` (including the
exhaustive two- and three-piece state-space sweeps), `uci_integration` and
`uci_fuzz`; Linux GCC Debug/Release,
ASan+UBSan and ThreadSanitizer runs; Clang Release and minimum-CMake-3.16 CI
jobs; Windows Debug/Release CI; and python-chess differential and reference
checks. Check the CI runs for the exact release commit — this document does not
substitute for them.

## Strength statement

Against dev1 the improvement is supported (400 paired games, +277 =82 −41, +235.4
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
