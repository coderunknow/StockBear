# StockBear 0.1.0-dev1

StockBear is an **independently implemented**, single-threaded UCI chess engine written in C++17. This is an early development prerelease, not a stable or top-strength engine. It implements its own board, legal move generation, evaluation, search and UCI protocol; it does not wrap or require another engine. There is no neural-network evaluation.

Current evidence and limitations are in [the versioned benchmark report](benchmarks/results/0.1.0-dev1/REPORT.md) and [release notes](RELEASE_NOTES.md). A small exploratory match against Stockfish 11 was lost 0–8; no match against Stockfish 19 was performed, and no superiority claim is made.

## Requirements

- 64-bit Linux or Windows 10 x64 target; a C++17 compiler (GCC, Clang or MSVC) and CMake 3.16+ to build (CMake 3.21+ with Visual Studio 2022).
- A CPU with a portable x86-64 baseline; no AVX2, AVX-512, GPU or external engine is required. The released Linux build statically links the C++ runtime but uses the system glibc; the Windows MSVC build uses the static C++ runtime.
- Normal execution needs only the executable and operating-system libraries. Python 3 is optional for black-box tests; the separate reference/tournament tools additionally use the optional `chess==1.11.2` Python package. See [third-party notices](THIRD_PARTY.md).
- One search thread. The default Hash budget is 16 MiB, configurable from 1 to 512 MiB. Tables and the rest of the process use additional memory.

## Build and test

Linux terminal:

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
.\build\Release\stockbear.exe
```

For Debug, replace `Release` with `Debug`. The CTest UCI integration tests need a Python 3 interpreter; CMake warns if it is absent. The CI configuration supplies it and runs the complete suite. A release executable does not need the source checkout or Python. Run `stockbear --help` for the command summary.

## Connect a GUI / use UCI

Register the executable as a **UCI engine** in a UCI-compatible GUI, select one search thread, and set the Hash option if desired. Launching without arguments starts UCI mode. A manual session can use:

```text
uci
isready
setoption name Hash value 32
ucinewgame
position startpos moves e2e4 e7e5
go depth 5
```

Wait for `bestmove` before issuing the next position. To analyze a FEN, use `position fen <six FEN fields> [moves <uci moves>...]`. `go depth N`, `go nodes N`, `go movetime N`, `go wtime N btime N winc N binc N movestogo N`, and `go infinite` are supported; times and increments are milliseconds. Negative remaining-clock values are clamped to zero; other negative limits are rejected. `stop` interrupts a search; `quit` stops and exits. `isready` remains responsive during search. A terminal position returns `bestmove 0000`.

The only advertised option is `Hash`. Ponder, `searchmoves`, MultiPV, Chess960, an opening book, tablebases and multiple search threads are **not** implemented. Malformed commands are reported as UCI `info string` messages and do not replace a valid position.

### ScrispChess-Extended import

On Windows x64 or Linux x64, unpack the appropriate StockBear executable; on
Linux make it executable (`chmod +x stockbear`). In ScrispChess-Extended open
Settings → **Engine Manager — Add Custom UCI Engines** → **Add Engine**, choose
the executable path, and allow its UCI handshake to discover identity and Hash.
StockBear is single-threaded and does not advertise Threads. The app's CLI
fixed-depth match is not a clock-controlled tournament. No dev2 release exists
until the [hard-gate investigation](docs/DEAD_POSITION_RESEARCH.md) is complete.

## Perft and benchmarks

```sh
./build/stockbear perft 4
./build/stockbear perft 3 --fen 'r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1' --divide
./build/stockbear bench --perft
./build/stockbear bench --depth 5 --hash 16
./build/stockbear bench --nodes 100000 --hash 16
```

In PowerShell, replace `./build/stockbear` with `.\build\Release\stockbear.exe`. Benchmark suites are compiled into the executable. Perft prints expected and actual counts, wall time, NPS and pass/fail. Search CSV records the last completed iteration, move, score, PV, nodes, wall time and sampled hash occupancy. Depth-one perft bulk-counts legal moves, so its NPS is not comparable to search NPS. See [benchmark methodology](docs/BENCHMARKING.md).

## Rules and search

The core supports standard chess moves, castling, en passant, all promotions, check, mate and stalemate. It tracks halfmove/fullmove clocks, castling, en passant and position history. Threefold and fifty-move claims, including claims by an intended move, are distinguished from fivefold and seventy-five-move automatic draws. Checkmate takes precedence over the automatic move-count rule. Repetition hashing includes an en-passant square **only when a legal en-passant capture exists**, while FEN serialization preserves the raw FEN target.

Search uses iterative deepening, negamax alpha-beta/PVS, quiescence, move ordering, killer/history heuristics, limited check extensions and a transposition table. Its handcrafted tapered evaluation includes material, piece-square activity, pawn structure, passed pawns, bishop pair, mobility, king safety and rook files. The search assumes available draw claims are taken and treats cycles inside its own search as draws. UCI has no claim command; the GUI or tournament arbiter must adjudicate the actual game. The material detector covers common provably dead material configurations, not every possible blocked-position dead draw. FEN alone cannot reconstruct previous repetition history. Further limitations are in [architecture](docs/ARCHITECTURE.md).

## Documentation

- [Architecture and rule/search details](docs/ARCHITECTURE.md)
- [Testing and independent validation](docs/TESTING.md)
- [Benchmarking and matches](docs/BENCHMARKING.md)
- [Baseline results](benchmarks/results/0.1.0-dev1/REPORT.md)
- [Roadmap](docs/ROADMAP.md), [changelog](CHANGELOG.md), [release notes](RELEASE_NOTES.md)
- [License](LICENSE) (Apache-2.0) and [third-party notices](THIRD_PARTY.md)
