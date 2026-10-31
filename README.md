# StockBear 0.1.0-dev2

StockBear is an **independently implemented**, single-threaded UCI chess engine
written in C++17. This is an early development prerelease, not a stable or
top-strength engine. It implements its own board, legal move generation,
evaluation, search, FIDE dead-position analysis and UCI protocol; it does not
wrap or require another engine. There is no neural-network evaluation.

Evidence and limitations are in the [dev2 benchmark report](benchmarks/results/0.1.0-dev2/REPORT.md),
the [dead-position specification](docs/DEAD_POSITIONS.md) and the
[release notes](RELEASE_NOTES.md). Summary: dev2 uses 15.8× fewer nodes (12×
less time) than dev1 on the depth-6 suite and scored +194 Elo (95 % interval
+159 to +234, opening-clustered) over 400 paired games; it scored 0.5/20 against
Stockfish 11 (one draw, nineteen losses). No match against Stockfish 19 was
possible in the build environment, and no superiority claim is made.

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
other negative limits are rejected. Unknown `go` tokens (for example `ponder` or
`searchmoves`) are ignored as the UCI specification requires. `stop` interrupts a
search, `quit` stops and exits, and `isready` stays responsive during search. A
terminal position returns `bestmove 0000`.

Options: `Hash` (spin, 1–512 MiB), plus boolean search-feature switches
`NullMove`, `LMR`, `Aspiration`, `Futility`, `ReverseFutility`, `SEEPruning` and
`CheckExtension`. All default to the released behaviour; they exist so feature
ablations can be measured by matches, and a GUI that never sends them is
unaffected. There is no `Threads` option because the search is single-threaded.
Ponder, MultiPV, Chess960, an opening book and tablebases are not implemented.
Malformed commands are reported as `info string` messages and never replace a
valid position.

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
./build/stockbear deadpos --fen '8/3k4/p1p2p1p/PpPp1PpP/1P1P2P1/4K3/8/8 w - - 6 49'
python3 scripts/tournament.py --engine-a ./build/stockbear --engine-b /path/to/other \
  --games 400 --base-ms 80 --inc-ms 8 --pgn match.pgn --jsonl match.jsonl --csv match.csv
```

`bench` prints CSV plus a `# signature` fingerprint that is deterministic for a
given build and parameter set, so behaviour changes are visible without comparing
timings. `tournament.py` reports Elo only with confidence intervals and paired
(pentanomial) uncertainty, never turns a capped game into a draw, and records
time forfeits and illegal moves as losses. See
[benchmark methodology](docs/BENCHMARKING.md).

## Documentation

- [Architecture and rule/search details](docs/ARCHITECTURE.md)
- [Dead positions (FIDE 5.2.2): specification, proof, limits](docs/DEAD_POSITIONS.md)
- [Testing and independent validation](docs/TESTING.md)
- [Benchmarking and match methodology](docs/BENCHMARKING.md)
- [dev2 evidence report](benchmarks/results/0.1.0-dev2/REPORT.md)
- [Roadmap](docs/ROADMAP.md), [changelog](CHANGELOG.md), [release notes](RELEASE_NOTES.md)
- [License](LICENSE) (Apache-2.0) and [third-party notices](THIRD_PARTY.md)
