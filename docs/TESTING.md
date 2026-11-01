# Testing

The normal build has no third-party C++ test framework. CTest runs an
in-repository C++ runner and Python standard-library black-box UCI tests. In CI
Python is installed explicitly; without Python, CMake warns and cannot register
the Python tests.

```sh
cmake -S . -B build-debug -DCMAKE_BUILD_TYPE=Debug
cmake --build build-debug --parallel 2
cmake -E chdir build-debug ctest --output-on-failure
cmake -S . -B build-release -DCMAKE_BUILD_TYPE=Release
cmake --build build-release --parallel 2
cmake -E chdir build-release ctest --output-on-failure
```

Windows with the multi-configuration Visual Studio generator uses
`cmake -S . -B build -A x64`, then `cmake --build build --config Debug` and
`cmake -E chdir build ctest -C Debug --output-on-failure` (repeat for Release).

## CTest entries

| Test | What it covers |
|---|---|
| `unit` | FEN, bitboards/attacks/pins, castling, en passant, promotions, make/unmake and hash/accumulator invariants, Zobrist/TT context, claimable versus automatic draws, mate precedence, time-manager contract, evaluation symmetry, the dev2 baseline reproduction (the shipped table evaluates exactly as dev2 did, pinned by checksum `da1921f604ae255e`), parameter-file validation and range checks, search behaviour and cancellation, malformed UCI |
| `position_extra` | null-move round trips and null-move/unmake counter integrity (separate entry so the `unit` group stays fast) |
| `regression` | capture/unmake, en-passant hashing, FEN symbols, king-capture API guard, retained TT context |
| `perft_quick`, `perft_full` | legal move generation against independently regenerated perft totals |
| `stress` | deterministic random games with FEN/key/state verification after every move |
| `deadpos` | FIDE Article 5.2.2: dead and alive classes, witness replay, closure property, terminal exclusion, budget-exhaustion safety, and exhaustive two-king and three-piece state-space sweeps (slower, labelled `slow`) |
| `uci_integration` | black-box protocol: handshake, options, `position`/`go` variants, clocks, `stop` during `infinite`, terminal positions, repeated searches, clean exit; `go searchmoves` over depth/nodes/movetime/clocks, illegal and empty move lists, a list followed by a real keyword; `MultiPV` 1–8 with distinct ranked lines, fewer legal moves than requested, and a return to single-PV output |
| `uci_fuzz` | 300 seeded malformed/cancellation cases, including `go` commands that must be rejected versus unknown tokens that must be ignored |

The `deadpos` entry runs the same tests as the CI step
`./build/stockbear_tests deadpos`; the exhaustive sweeps are why the whole suite
takes a few seconds in Release and roughly half a minute in Debug and under
sanitizers.

## Independent validation (optional, development only)

```sh
python3 -m pip install chess==1.11.2
python3 scripts/reference_perft.py
python3 tests/integration/test_reference_perft.py
python3 scripts/differential.py ./build-release/stockbear --samples 2000 --seed 20261030
python3 tests/integration/test_tournament.py ./build-release/stockbear
python3 tests/integration/test_statistics.py
python3 scripts/dead_position_corpus.py ./build-release/stockbear --markdown deadpos.md
python3 scripts/dead_position_reference.py ./build-release/stockbear --full
```

* `scripts/reference_perft.py` checks all expected perft totals against
  python-chess.
* `scripts/differential.py` compares the exact legal move set and depth-two
  divide counts on curated cases plus reproducibly generated legal positions.
  One curated en-passant case deliberately has an impossible immediate history;
  it stress-tests geometry, not reachability.
* `tests/integration/test_tournament.py` verifies paired openings, legal PGN,
  CSV/JSONL consistency and that move-limit games stay unadjudicated rather than
  becoming fabricated draws.
* `tests/integration/test_statistics.py` pins the statistics to known values
  (Wilson interval for 5/10, hand-computed pentanomial mean and standard error,
  Elo transform, SPRT decisions, degenerate-sample handling).
* `scripts/chess_oracle.py` proves forced mates with a search written from
  scratch on python-chess; every position in `benchmarks/tactics/mate_suite.epd`
  is certified by it and lists *all* moves that force mate inside the labelled
  number of plies, so a pass never depends on agreeing with one arbitrary choice
  and a slower mate does not count. Mate distances are counted at every ply, and
  a "this side is getting mated" score is only reported when every legal reply was
  proven.
* `scripts/run_suite.py` runs the engine over the EPD suites at a fixed node
  budget and records, per position, the search depth, the depth at which the mate
  was first proved, node count, time, whether the node budget was exhausted and
  the engine's raw output. The engine is read by a pump thread so a stuck engine
  fails the run instead of hanging it. Recorded results for
  this release are in `benchmarks/results/0.1.0-dev3/`.
* `scripts/dead_position_corpus.py` checks expected verdicts, witness legality,
  state counts and timings; `scripts/dead_position_reference.py` re-decides the
  positions it can compute with an independent python-chess implementation. That
  reference is not exhaustive over the corpus: the recorded `--full` run compares
  10 positions and skips 2 (the `KN` v `K` rows) at its own state cap.

## Sanitizers

```sh
cmake -S . -B build-san -DCMAKE_BUILD_TYPE=Debug -DSTOCKBEAR_SANITIZE=address,undefined
cmake --build build-san --parallel 2
ASAN_OPTIONS=detect_leaks=1:halt_on_error=1 UBSAN_OPTIONS=print_stacktrace=1:halt_on_error=1 \
  cmake -E chdir build-san ctest --output-on-failure

cmake -S . -B build-tsan -DCMAKE_BUILD_TYPE=Debug -DSTOCKBEAR_SANITIZE=thread
cmake --build build-tsan --parallel 2
TSAN_OPTIONS=halt_on_error=1 cmake -E chdir build-tsan ctest \
  -R 'unit|regression|uci_integration' --output-on-failure
```

ThreadSanitizer targets the threaded paths: the UCI controller thread, the
atomic stop flag, the shared transposition table and the position hand-off.

## CI matrix

The CI workflow runs, on every push and pull request:

* Linux (`ubuntu-22.04`) and Windows (`windows-2022`) Debug and Release builds
  with the full CTest suite, a build-provenance record and a search-determinism
  check (two identical `bench --depth 6` runs must agree on the `# StockBear`
  header, the `# signature` line and the deterministic CSV columns — name, best
  move, depth, score, nodes, PV; the `time_us`, `nps` and `hashfull` columns are
  ignored because they legitimately vary between runs);
* a Linux ASan+UBSan job;
* a Linux ThreadSanitizer job;
* a Linux Clang Release job;
* a minimum-CMake-3.16 job;
* an independent-reference job that installs python-chess and runs the perft
  reference, the 2,000-position differential check, the tournament smoke test,
  the statistics tests and the complete dead-position evidence (corpus,
  independent reference comparison, exhaustive sweeps).

Release binaries are packaged and uploaded only from the Release jobs. Test
success is evidence for the exercised cases, not a proof of a bug-free engine;
the exact-head CI result is checked before merge and after the merge commit.
