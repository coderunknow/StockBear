# Testing

The normal build has no third-party C++ test framework. CTest runs a small in-repository C++ runner and Python standard-library black-box UCI tests. In CI Python is installed explicitly; without Python, CMake warns and cannot register the UCI subprocess tests.

```sh
cmake -S . -B build-debug -DCMAKE_BUILD_TYPE=Debug
cmake --build build-debug --parallel 2
cmake -E chdir build-debug ctest --output-on-failure
cmake -S . -B build-release -DCMAKE_BUILD_TYPE=Release
cmake --build build-release --parallel 2
cmake -E chdir build-release ctest --output-on-failure
```

Windows with the multi-configuration Visual Studio generator uses `cmake -S . -B build -A x64`, followed by `cmake --build build --config Debug --parallel 2` and `cmake -E chdir build ctest -C Debug --output-on-failure` (also run `Release`).

Tests cover FEN validation/round trips, bitboard rays, attacks, pins, castling, en passant, all promotions, make/unmake and hash/accumulator invariants, claimable versus automatic draws, mate precedence, evaluation symmetry, mate-in-one/two, tactical/defensive/endgame positions, depth/node/time control, retained TT behavior, cancellation, malformed UCI, terminal `bestmove`, and repeated searches. The deterministic stress suite plays and unwinds 80 games of up to 180 plies, checking FEN/key/state after every move. The UCI fuzz test sends 300 seeded malformed/cancellation cases. CTest also runs the quick and full perft suites; a failure is a release blocker.

For independently implemented validation, install the optional external package in a development environment (not used by the engine):

```sh
python3 -m pip install chess==1.11.2
python3 scripts/reference_perft.py
python3 tests/integration/test_reference_perft.py
python3 scripts/differential.py ./build-release/stockbear --samples 2000 --seed 20261030
python3 tests/integration/test_tournament.py ./build-release/stockbear
```

The reference script checks all expected perft totals against python-chess. Differential testing compares the exact legal set and individual depth-two divide counts on curated cases plus reproducibly generated legal positions. One curated EP case deliberately has an impossible immediate history; it stress-tests the geometry rather than asserting reachability. The tournament test verifies paired openings, legal PGN and that move-limit games remain unadjudicated rather than fabricated draws.

Linux GCC/Clang sanitizer example:

```sh
cmake -S . -B build-sanitize -DCMAKE_BUILD_TYPE=Debug -DSTOCKBEAR_SANITIZE=address,undefined
cmake --build build-sanitize --parallel 2
ASAN_OPTIONS=detect_leaks=1:halt_on_error=1 UBSAN_OPTIONS=print_stacktrace=1:halt_on_error=1 \
  cmake -E chdir build-sanitize ctest --output-on-failure
```

The CI workflow tests Linux x64 and Windows x64 Debug and Release, Linux ASan+UBSan, and an independent-reference job. It uploads Release binaries only after the corresponding build/tests pass. Local evidence is recorded in the [versioned report](../benchmarks/results/0.1.0-dev1/REPORT.md); CI must be checked for the exact commit under review and after merge. Test success is evidence for the exercised cases, not a proof of a bug-free engine.

## Reachability investigation

`python scripts/reference_reachability.py` exhausts two small movement-only graphs independently and compares the recorded counts. The promotion case is relatively expensive. The C++ unit suite exercises the corresponding bounded probe, budget exhaustion and a mate witness; these cases do not prove general FIDE adjudication.
