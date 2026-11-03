# StockBear

**An independent C++17 UCI chess engine for reproducible search and evaluation research.**

[![CI](https://github.com/coderunknow/StockBear/actions/workflows/ci.yml/badge.svg)](https://github.com/coderunknow/StockBear/actions/workflows/ci.yml)
[![Latest release](https://img.shields.io/github/v/release/coderunknow/StockBear?include_prereleases&sort=semver)](https://github.com/coderunknow/StockBear/releases)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

StockBear is a **standalone, single-threaded chess engine** with its own board
representation, legal move generator, alpha-beta search, evaluation, UCI
controller and FIDE dead-position analysis. It does not wrap, embed or require
another chess engine. It runs on Linux and Windows, supports portable x86-64
builds, and connects to any GUI that speaks UCI.

## Why StockBear?

- **A real engine, not a demo:** legal moves, castling, en passant, promotion,
  repetition, draw claims, MultiPV and standard UCI time controls.
- **Research you can reproduce:** deterministic benchmarks, seeded tournaments,
  raw match records, confidence intervals and benchmark signatures committed
  alongside the code.
- **NNUE experimentation end to end:** feature extraction, incremental
  accumulators, quantised network files, scalar and AVX2 inference, self-play,
  training, conversion and an independent verifier.
- **Unusually careful draw handling:** a general FIDE Article 5.2.2
  dead-position procedure with witnesses, exhaustive validation and explicit
  `unknown` results when a proof budget is exhausted.
- **Honest engineering:** features that do not improve play stay disabled, and
  negative results remain documented instead of being presented as strength
  claims.

> **Status:** StockBear is an early development prerelease and is not a
> top-strength or stable engine. The default configuration prioritises
> correctness, inspectability and measurable experiments over an inflated Elo
> claim.

## Quick start

```sh
git clone https://github.com/coderunknow/StockBear.git
cd StockBear
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --parallel 2
cmake -E chdir build ctest --output-on-failure
./build/stockbear --version
```

Launching `stockbear` without arguments starts UCI mode. Add the executable to
your chess GUI as a UCI engine, or try a direct analysis:

```text
uci
isready
position startpos moves e2e4 e7e5
go depth 8
```

See [Build and test](#build-and-test) for Windows, and
[Connect a GUI / use UCI](#connect-a-gui--use-uci) for options and integration.

## What dev4 demonstrates

The current release is valuable as a **measurement case study**, not as a
claim of playing strength. It builds a complete neural evaluation of its own,
then measures it against the classical evaluation in the same binary. At 2,500
nodes per move, the network loses 708 Elo (95% CI `[-1011, -405]`), so NNUE and
the new search refinements ship disabled. The default configuration preserves
the dev3 behaviour and its depth-6/depth-7 benchmark signatures
(`e06c4352681ae8eb`, `5bceff035f2a4ae4`).

That result is intentional project evidence: the pipeline is verified, the
measurement method can resolve small effects, and the repository preserves the
raw data and negative result. Start with the [dev4 evidence report](benchmarks/results/0.1.0-dev4/REPORT.md),
[research notes](docs/DEV4_RESEARCH.md) or [release notes](RELEASE_NOTES.md).

## Requirements

- 64-bit Linux or Windows 10 x64 target; a C++17 compiler (GCC, Clang or MSVC)
  and CMake 3.16+ to build (CMake 3.21+ with Visual Studio 2022).
- A portable x86-64 baseline; no AVX2, AVX-512, GPU or external engine is
  required. The released Linux build statically links the C++ runtime but uses
  the system glibc; the Windows MSVC build uses the static C++ runtime.
- Normal execution needs only the executable and operating-system libraries.
  Python 3 is optional for black-box tests; the reference/tournament tools
  additionally use the optional `chess==1.11.2` package. See
  [third-party notices](THIRD_PARTY.md).
- One search thread. The default Hash budget is 16 MiB, configurable from 1 to
  512 MiB. Tables and the rest of the process use additional memory.

## Build and test

Linux:

```sh
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --parallel 2
cmake -E chdir build ctest --output-on-failure
./build/stockbear --version
./build/stockbear
```

Windows PowerShell with the Visual Studio C++ workload:

```powershell
cmake -S . -B build -A x64
cmake --build build --config Release --parallel 2
cmake -E chdir build ctest -C Release --output-on-failure
.\build\Release\stockbear.exe --version
```

For Debug, replace `Release` with `Debug`. The CTest UCI integration tests need a
Python 3 interpreter; CMake warns if it is absent. A release executable does not
need the source checkout or Python. Run `stockbear --help` for the command
summary.

## Connect a GUI / use UCI

Register the executable as a **UCI engine**, use one search thread, and set Hash
if desired. Launching without arguments starts UCI mode:

```text
uci
isready
setoption name Hash value 32
ucinewgame
position startpos moves e2e4 e7e5
go depth 5
```

Wait for `bestmove` before sending the next position. `position fen <six FEN
fields> [moves <uci moves>...]` is supported. `go depth N`, `go nodes N`,
`go movetime N`, `go wtime N btime N winc N binc N movestogo N` and `go infinite`
work; times are milliseconds. Negative remaining clocks are clamped to zero;
other negative limits are rejected. Unknown `go` tokens (for example `ponder`)
are ignored as the UCI specification requires. `stop` interrupts a
search, `quit` stops and exits, and `isready` stays responsive during search. A
terminal position returns `bestmove 0000`.

Options: `Hash` (spin, 1–512 MiB), `MultiPV` (spin, 1–8), `EvalParams` (string,
a parameter file; empty restores the shipped set), `NNUE` (check) and `NnueFile`
(string, a network file), plus boolean search-feature switches `NullMove`, `LMR`,
`Aspiration`, `Futility`, `ReverseFutility`, `SEEPruning`, `CheckExtension`,
`CounterMoves`, `ContinuationHistory`, `CaptureHistory`, `HistoryMaluses`,
`LMRHistory`, `ModernLMR`, `MoveCountPruning`, `IIR`, `Improving` and `TTEval`.
The first seven default to the released behaviour; the five `dev3` ordering
switches and the five `dev4` switches default to **off** because they measured
neutral to negative (see the evidence report). Every switch exists so ablations
can be measured by matches, and a GUI that never sends them is unaffected.

`NNUE` defaults to **false** and the release binary embeds no network, so
`setoption name NNUE value true` reports that no network is available;
`setoption name NnueFile value <path>` loads one from disk and switches to it,
and an empty path restores the compiled-in network (none in this build). The
dev4 network used in the experiments is in
[`benchmarks/training/`](benchmarks/training/README.md) and can be loaded the same
way; it is **not** recommended for play, because it measured 708 Elo weaker than
the classical evaluation.

There is no `Threads` option because the search is single-threaded. Ponder,
Chess960, an opening book and tablebases are not implemented. Malformed commands are reported
as `info string` messages and never replace a valid position.

`go searchmoves <moves>` restricts the search to the listed legal root moves:
illegal entries are reported and dropped, and a list with nothing legal in it is
reported and ignored rather than answered with `bestmove 0000`. `MultiPV N`
reports the best N root moves as ranked `multipv` lines with exact scores and a
principal variation that starts with its own move.

### ScrispChess-Extended

Open its **Custom UCI Engine Manager**, add a new engine entry, and point the
executable path at the StockBear binary (`stockbear` on Linux,
`stockbear.exe` on Windows). Leave the argument list empty, set the working
directory to the folder containing the binary, and leave the thread setting at
one. After saving, select StockBear as the analysis/play engine; if the manager
offers engine options, `Hash` is the usual setting to tune, so 32–256 MiB is a
reasonable choice. The remaining options (`NullMove`, `LMR`, `Aspiration`,
`Futility`, `ReverseFutility`, `SEEPruning`, `CheckExtension`) are experimental
search-feature switches kept for ablations; changing them *does* change playing
strength, so leave them at their defaults for play. StockBear answers `uci`, `isready` and all
standard `position`/`go` commands, and it never claims draws itself — the GUI
remains responsible for adjudicating repetition, move-count and dead-position
draws. Nothing in ScrispChess-Extended is modified or required at run time.

## Rules, draws and dead positions

The core supports standard moves, castling, en passant, all promotions, check,
mate and stalemate. It tracks halfmove/fullmove clocks, castling, en passant and
position history. Threefold and fifty-move claims, including claims by an
intended move, are distinguished from fivefold and 75-move automatic draws, and
checkmate takes precedence. Repetition hashing includes an en-passant square only
when a legal capture exists, while FEN serialisation preserves the raw target.

**Article 5.2.2 (dead positions) is decided by a general procedure**, not by
material signatures: `stockbear deadpos --fen '<fen>'` proves `alive` with a
checkmate witness or `dead` by exhaustively enumerating the reachable state
component, and answers `unknown` when its budget is exhausted. See
[docs/DEAD_POSITIONS.md](docs/DEAD_POSITIONS.md) for the algorithm, the
correctness argument, the measurements and the resource limits.

Search uses iterative deepening, negamax alpha-beta/PVS, quiescence, aspiration
windows, null-move pruning, late move reductions, futility pruning, static
exchange evaluation, killer/history ordering and a context-checked transposition
table; its
handcrafted tapered evaluation covers material, piece-square activity, pawn
structure, passed pawns, bishop pair, mobility, king safety and rook files. The
search assumes available draw claims are taken and treats cycles inside its own
search as draws; UCI has no claim command. FEN alone cannot reconstruct earlier
repetition history.

## Perft, benchmarks and matches

```sh
./build/stockbear perft 4
./build/stockbear perft 3 --fen 'r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1' --divide
./build/stockbear bench --perft
./build/stockbear bench --depth 6 --hash 16
./build/stockbear bench --movetime 200
./build/stockbear bench --depth 7 --param nullMove=0
./build/stockbear bench --depth 7 --params benchmarks/params/dev3-shipped.txt
./build/stockbear bench --depth 7 --no-nnue          # compare without the network
./build/stockbear bench --depth 7 --network net.nnue # compare with a network
./build/stockbear bench --depth 7 --param iir=1      # in-binary ablation
./build/stockbear eval --fen 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1' --top 5
python3 scripts/run_suite.py --engine ./build/stockbear \
  --epd benchmarks/tactics/mate_suite.epd --mode tactics --nodes 60000 \
  --json /tmp/tactics.json --raw /tmp/tactics.txt
./build/stockbear deadpos --fen '8/3k4/p1p2p1p/PpPp1PpP/1P1P2P1/4K3/8/8 w - - 6 49'
python3 scripts/tournament.py --engine-a ./build/stockbear --engine-b /path/to/other \
  --games 400 --base-ms 80 --inc-ms 8 --pgn match.pgn --jsonl match.jsonl --csv match.csv
```

`bench` prints CSV plus a `# signature` fingerprint that is deterministic for a
given build and parameter set in `--depth`/`--nodes` mode, so behaviour changes
are visible without comparing timings. `--movetime` mode is time-limited, so it
prints `# signature unavailable` instead of a fingerprint that would differ
between runs of the same build. `tournament.py` reports Elo only with confidence intervals and paired
(pentanomial) uncertainty, never turns a capped game into a draw, and records
time forfeits and illegal moves as losses. See
[benchmark methodology](docs/BENCHMARKING.md).

## Documentation

- [Architecture and rule/search details](docs/ARCHITECTURE.md)
- [Dead positions (FIDE 5.2.2): specification, proof, limits](docs/DEAD_POSITIONS.md)
- [Testing and independent validation](docs/TESTING.md)
- [Benchmarking and match methodology](docs/BENCHMARKING.md)
- [dev4 evidence report](benchmarks/results/0.1.0-dev4/REPORT.md)
- dev4 research, architecture, training, benchmarks and limitations:
  [research](docs/DEV4_RESEARCH.md), [architecture](docs/DEV4_ARCHITECTURE.md),
  [training](docs/DEV4_TRAINING.md), [benchmarks](docs/DEV4_BENCHMARKS.md),
  [limitations](docs/DEV4_LIMITATIONS.md)
- [dev3 evidence report](benchmarks/results/0.1.0-dev3/REPORT.md)
- [Evaluation tuning: pipeline, dataset and the negative result](docs/TUNING.md)
- [dev2 evidence report](benchmarks/results/0.1.0-dev2/REPORT.md)
- [Roadmap](docs/ROADMAP.md), [changelog](CHANGELOG.md), [release notes](RELEASE_NOTES.md)
- [License](LICENSE) (Apache-2.0) and [third-party notices](THIRD_PARTY.md)

---

## 2026-11-03 — v0.1.0-dev6 research cycle (this branch)

> This section is an **appended status note**; the released version of the
> project remains `v0.1.0-dev5`. On the research branch
> `arena/3e6dd5b6-stockbear`, `VERSION` is `0.1.0-dev6`, but **no dev6 release,
> tag, merge or PR exists** — the mandatory strength gate is an honest,
> independently-confirmed >= +75 Elo (LCB95 > +50) against the exact released
> dev5 artifact, and no misleading release PR is opened while it is unmet.

- Immutable baseline: `benchmarks/binaries/stockbear-dev5-release`
  (SHA-256 `391cb50e13ab99168aba0255482554ab5e59d1a34af810bf8f4d2c88e5bdb918`),
  verified against the official dev5 release `SHA256SUMS.txt`.
- dev6 research: six gated, independently-verified extended evaluation features
  (`docs/DEV6_EVAL_FEATURES.md`), pre-registered decisive matches
  (`docs/DEV6_PREREG.md`), power analysis (`docs/DEV6_POWER_ANALYSIS.md`),
  external-rating-ladder status (`docs/DEV6_EXTERNAL_LADDER.md`), and the
  evidence-driven 3,000-Elo roadmap (`docs/DEV6_3000_ROADMAP.md`).
- Older `docs/DEV6_*.md` / `DEV5_REPORT.md` / `DEV7_CONFIRMATION.md` are
  **historical dev5-cycle documents** (measured against dev4); see their
  appended superseding notices. The dev6 gate is against released **dev5**.
