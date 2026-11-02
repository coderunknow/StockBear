# dev5 testing and QA status

## What was run on the dev5 branch build (binary be2341455d59c92c...)

- Clean CMake/Ninja Release build from the working tree: succeeds, no warnings
  introduced by the dev5 changes.
- CTest: **11/11 passed** on the branch build (re-run after the sandbox wiped
  `build*/`; the test suite covers unit, differential, UCI, NNUE and
  serialization tests). The same 11/11 held before the wipe.
- `stockbear bench` depth-4 signature `243f9a1c1ba5b36f` — identical to the
  immutable dev4 binary, confirming the default-off `FullSoftBudget` switch
  changes no fixed-node search behavior.
- UCI smoke: `option name FullSoftBudget type check default false` is advertised;
  setting it clears the TT like every other feature switch (same code path as
  the existing ablation switches); `isready`/`quit` handshake normal.
- dev4 baseline rebuilt from tag `v0.1.0-dev4` after the wipe: SHA-256
  `1c5b61a755215134...` bit-identical to the pinned baseline; bench signature
  `243f9a1c1ba5b36f` identical.
- Safe-mobility research build (`-DSTOCKBEAR_SAFE_MOBILITY=ON`, commit
  728909b) rebuilt bit-identical: `13d3a684002fbd9e...`; its 11/11 CTest was
  recorded in DEV5_ARCHITECTURE.md.

## Not performed in this sandbox (gates still open)

- Clang build, Windows compile, sanitizer (ASan/UBSan) runs, GCC+Clang
  differential runs — no Clang/Windows toolchain here; CI covers Linux
  Ubuntu 22.04 + Windows 2022 Debug/Release, but no PR was opened, so CI has
  not run on this branch.
- Longer-time-control matches (>= 1 s/move) and the pinned Stockfish-opponent
  benchmark — not run (see DEV5_BENCHMARKS.md).
- No tests were weakened, removed or skipped at any point; the one historical
  evaluator-equality test touched by the safe-mobility experiment was extended
  with an independent oracle, not relaxed (DEV5_ARCHITECTURE.md).
