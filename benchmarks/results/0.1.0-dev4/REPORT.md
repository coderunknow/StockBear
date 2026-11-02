# StockBear 0.1.0-dev4 — evidence report

Fourth development prerelease. This report contains only what was measured on the
machine described in §16. Where something was not measured, it says so. Where a
number belongs to dev3 rather than dev4, it says so.

**Verdict up front:** dev4's default configuration plays exactly as dev3's, and
the release **does not claim a measurable strength gain**. Every candidate it
introduces was measured with a null-controlled, paired, opening-clustered
protocol; all of them were neutral or negative, and none was enabled. The learned
evaluation — the main engineering work of this release — loses 708 Elo to the
evaluation it was supposed to replace. What dev4 adds is verified neural-evaluation
infrastructure, a match harness that can actually resolve small effects, and the
negative results themselves. Details in §6–§9 and §20.

## 1. Release identity

| Item | Value |
| --- | --- |
| Version (`VERSION`) | `0.1.0-dev4` |
| Base commit | `32e7d9d1bde0bf65e2b500b653ff18be8c771c35` (`v0.1.0-dev3`, `main`) |
| Development branch | `arena/75415e79-stockbear` |
| Merge target | `main`, fast-forward-free merge commit, then annotated tag `v0.1.0-dev4` |
| Engine name reported over UCI / in bench header | `StockBear 0.1.0-dev4` |
| Default evaluation | classical (hand-tuned tapered model) |
| Embedded neural network | **none** (`network=none` in the bench header) |
| Search features enabled by default | exactly dev3's set; the five dev4 switches are off |

> **Post-publication record.** This report was written before the release
> existed, so its §1 rows describe the *intended* identity. The publication
> actually happened on `9b5778c97ba3d3141ea61fbf3398b7fc231bbf64` (merge commit of
> PR #6), tagged `v0.1.0-dev4`, with CI run `41392388489` green for that exact
> commit. The published assets, their SHA-256 digests, and the verification that
> was run against the downloadable archives after publication are recorded in
> [`RELEASE_ASSETS.md`](RELEASE_ASSETS.md) — including what was *not* verified.

## 2. Scope and acceptance gates

Scope: make dev4 measurably stronger than dev3 under equal thinking time, without
copying another engine, without paid services, and without unverifiable claims.
Gates, as set for this work:

| Band | Elo | Requirement |
| --- | --- | --- |
| regression | < 0 | fails the release gate |
| unproven | 0 … +49 | may ship only labelled as unproven |
| meaningful | +50 … +99 | CI lower bound > 0 |
| major | +100 … +149 | plus an independent confirmation match |
| breakthrough | ≥ +150 | plus an independent confirmation match |

dev4 lands in the **first band for its default configuration (no change)**, and
therefore ships no strength claim. See §20.

## 3. What changed

**Neural evaluation (new, disabled by default).**
`src/evaluation/nnue.cpp`, `nnue.hpp`, `nnue_forward.cpp`,
`nnue_forward_avx2.cpp`, `nnue_embedded.hpp`, generated `nnue_net_data.cpp`;
incremental accumulator maintained in the position's move/unmake path; a
versioned, length-validated `.nnue` format; scalar and AVX2 kernels that must be
bit-identical; UCI options `NNUE` (check, default false) and `NnueFile` (string).

**Training pipeline (new, `scripts/`, `src/utilities/`).**
`stockbear selfplay` (seeded data generation), `nnue_features.py`,
`train_nnue.py`, `convert_nnue.py`, `verify_nnue.py`, `embed_nnue.py`.

**Five search refinements (new, disabled by default).**
`ModernLMR`, `MoveCountPruning`, `IIR`, `Improving`, `TTEval`.

**Measurement work.**
`tournament.py` gained `--nodes-jitter`, because fixed-node play is deterministic
and colour-reversed pairs scored identically, leaving the pentanomial with zero
variance; `scripts/make_openings.py` and `benchmarks/positions/openings_dev4.txt`
(240 openings); `scripts/experiment_table.py`.

**Tests.**
`tests/unit/test_nnue.cpp` (7 tests: feature layout, incremental-vs-scratch,
perspective ordering, scalar-vs-AVX2, serialisation and rejection, fallback),
`tests/integration/test_nnue_features.py` (engine feature function vs an
independent implementation), both registered in CTest.

**Documentation.** `docs/DEV4_RESEARCH.md`, `DEV4_ARCHITECTURE.md`,
`DEV4_TRAINING.md`, `DEV4_BENCHMARKS.md`, `DEV4_LIMITATIONS.md`,
`benchmarks/training/README.md`, this report, updated `CHANGELOG.md`, `README.md`,
`THIRD_PARTY.md`, `VERSION`.

## 4. Build and artifacts

| Item | Value |
| --- | --- |
| Compiler | GCC 12.2.0, C++17, `-O3` (CMake `Release`), `-Wall -Wextra -Wshadow -Wpedantic`, no `-march=native` |
| Configure | `cmake -S . -B build-dev4 -DCMAKE_BUILD_TYPE=Release -DSTOCKBEAR_BUILD_TESTS=ON` |
| Build | `cmake --build build-dev4 --parallel 2` — no warnings |
| Binary | `build-dev4/stockbear`, 1,790,576 bytes, SHA-256 `1c5b61a755215134a030b9bf3b55876f7d287e1c965591ff0d22b485c0743aae` |
| dev3 baseline binary | `/home/user/baseline/build/stockbear` (rebuilt from `git archive 32e7d9d`), 1,694,912 bytes, SHA-256 `e96cb712da0dc4431e5513184f31dfec9b58b5b53e801ec1c500735e71d0dd27` |
| SIMD | AVX2 kernel compiled in its own translation unit, selected at run time (`kernel=avx2` here); the scalar kernel is always available |

The baseline was re-exported and rebuilt during this session and reproduced the
same SHA-256, so the dev3 opponent is the released artifact's source.

## 5. Measurement protocol and controls

* Paired, colour-reversed games, both from the same opening; 240-opening suite.
* Two intervals per match: pentanomial over opening pairs, and opening-clustered
  (CR1) with a Student-t interval on `G−1` degrees of freedom. The clustered one
  is quoted.
* A **null control** for every condition: the same binary on both sides.
* Fixed nodes (3,000/move, ±12 % seeded jitter, 16 MB hash, 1 thread) and fixed
  time (40 ms + 4 ms, 16 MB hash, 1 thread).
* Real adjudication only: checkmate, stalemate, repetition, fifty-move,
  insufficient material, or a real clock loss; 240-ply cap, no resign.
* Raw records: `benchmarks/results/0.1.0-dev4/experiments/*.jsonl` (one line per
  game plus a summary), `dev3-vs-dev4-time40_4.pgn`, and
  `experiments/summary.csv`, regenerated by `scripts/experiment_table.py`.

## 6. Regression gate: dev3 versus dev4

| Experiment | Games | Score (dev4) | Elo (dev4 − dev3) | 95 % CI (clustered) |
| --- | --- | --- | --- | --- |
| fixed nodes 3,000 | 398 | 0.4823 | −12.3 | [−34.2, +9.5] |
| fixed time 40+4 ms | 240 | 0.5417 | +29.0 | [+1.5, +56.9] |

The fixed-node run reproduced the same-binary null control **identically, game by
game**: dev4's defaults are dev3's, the node counts at depth 6/7 are unchanged
(105,743 / 87,419), and both bench signatures are dev3's (`e06c4352681ae8eb`,
`5bceff035f2a4ae4`). Play is therefore bit-identical at a fixed node budget, which
is the strongest possible statement that the default was not changed.

The fixed-time run's +29 Elo with a lower bound above zero is **not** a result: the
same binary against itself at the same control measured −30.5 [−65.9, +4.3], the
two builds' bench throughput is identical within noise (2.57 vs 2.63 Mnps at depth
6; 2.67 vs 2.65 Mnps at depth 7), and nothing in the binaries can differ at fixed
time. It is a demonstration that a single fixed-time match on a shared machine can
produce a confident-looking interval from scheduling noise. **Verdict: no
measurable difference between dev3 and dev4 in either condition.**

## 7. Search candidates

Each option was measured against the same binary with only that option flipped,
so the comparison cannot pick up a build difference.

| Candidate | Fixed nodes 3,000 (≈400 games) | Fixed time 40+4 ms (≈160 games) | Shipped |
| --- | --- | --- | --- |
| `ModernLMR` | −28.7 [−52.0, −5.7] | −30.9 [−69.0, +6.5] | no |
| `MoveCountPruning` | −39.3 [−67.9, −11.1] | −104.2 [−154.6, −57.7] | no |
| `IIR` | −14.9 [−37.3, +7.4] | +6.6 [−32.2, +45.5] | no |
| `Improving` | −26.4 [−49.3, −3.7] | −13.0 [−44.6, +18.3] | no |
| `TTEval` | not matched (depth-6 node count unchanged: 105,743) | — | no |

Null controls for those conditions: −12.3 [−34.2, +9.5] and −30.5 [−65.9, +4.3].

Depth-6 node counts explain the pattern: `ModernLMR` 139,989 (+32 %, i.e. it
reduces *less* than the existing schedule), `MoveCountPruning` 20,915 (−80 %, far
too aggressive for this move ordering), `IIR` 103,310 (−2 %), `Improving` 97,287
(−8 %), `TTEval` 105,743 (exactly unchanged: with a per-position table the stored
eval equals the computed one). `TTEval` was therefore not worth a match: it is a
no-op on this search.

`razoring` is declared in the search parameters but **not implemented**; it is not
advertised as a UCI option, so nothing can be switched on that does not work.

## 8. Learned evaluation: training

Full detail in `docs/DEV4_TRAINING.md`.

| Item | Value |
| --- | --- |
| Data | 3,072,845 positions from 24,942 self-play games (three corpora, hashes in `benchmarks/training/README.md`) |
| Split | by game: 2,706,666 train / 212,708 validation / 153,471 test |
| Architecture | 768 → 128 → 32 → 1, clipped ReLU, MSE on `sigmoid`, output = 300 cp/unit |
| Training | 11 epochs, batch 8,192, SparseAdam 3e-4 + Adam 1.2e-3, cosine decay, seed 20261101, 8 min 26 s on 2 threads |
| Validation MSE | 0.1470 best (epoch 10); constant predictor 0.2071 |
| Checkpoint used | best-validation epoch, not the last |

The one failure worth recording in this report: early runs converged to a constant
0.5 because the network input was assembled in *colour* order rather than
side-to-move order, so the same board mapped to the same input with opposite
targets. The measured signature was a correlation of −0.0003 between
colour-ordered material and the side-to-move result, versus +0.572 for
side-to-move material. Fixing the order made training work; the property is now a
documented contract pinned by `tests/unit/test_nnue.cpp`.

## 9. Learned evaluation: playing strength and decision

| Experiment | Games | Score (NNUE) | Elo (NNUE − classical) | 95 % CI |
| --- | --- | --- | --- | --- |
| NNUE vs classical, fixed nodes 2,500 | 60 | 0.0167 (0 W, 2 D, 58 L) | **−708** | **[−1011, −405]** |
| control: NNUE on both sides | 40 | 0.5875 | +61 | [−28, +160] |

The control rules out the obvious explanations (crash, illegal move, unusable
network): with the network on both sides the engine plays self-consistent games.
The network is simply a much weaker evaluator than the hand-tuned one at this
budget, which §8's validation loss predicted.

**Decision: the network is not embedded and is not the default.** It remains
loadable (`setoption name NnueFile`), the file is committed
(`benchmarks/training/dev4-l1-128-l2-32.nnue`, SHA-256
`ba0bc040ebe1ec36baa564ac1c08ba9bb89a3e3b3163934d873f686bf395460d`), and every
measurement above can be reproduced from it.

## 10. Neural evaluation: correctness verification

| Check | Result |
| --- | --- |
| Integer vs float evaluation, 2,000 positions | max 45.5 cp, mean +0.06, rms 11.67, correlation 0.999908 |
| Engine vs independent integer reference (`scripts/verify_nnue.py`), 2,000 positions | **0 differences** |
| Scalar vs AVX2 kernel | bit-identical (unit test) |
| Incremental accumulator vs from-scratch rebuild | identical on every move of the dev3 perft/regression/stress suites (`verify_state`) |
| Format rejection | truncated, bad magic, wrong length, oversized dimensions, accumulator overflow — all rejected |
| Feature function vs independent implementation (`nnue_features` CTest entry) | 11 positions × 2 perspectives, 0 mismatches |
| Rounding | both kernels and the converter round rather than truncate; truncation biased the score by ~4 % and was fixed |

The integer/float gap is quantisation error and is reported, not hidden: a 128-wide
layer with 7-bit activations cannot match float weights exactly.

## 11. Performance

| Configuration | Bench depth 6 | Bench depth 7 |
| --- | --- | --- |
| dev4 default (classical) | 105,743 nodes / 41,089 µs (2.57 Mnps) | 87,419 nodes / 32,666 µs (2.68 Mnps) |
| dev3 baseline (rebuilt) | 105,743 nodes / 40,182 µs (2.63 Mnps) | 87,419 nodes / 33,029 µs (2.65 Mnps) |
| dev4 with the network loaded | — | 0.735 µs/node vs 0.543 µs/node classical (+35 %) |

Node counts are identical between dev3 and dev4 by construction; the throughput
difference is measurement noise. Raw CSV: `bench-depth6.csv`, `bench-depth7.csv`.

## 12. Correctness and QA

| Item | Result |
| --- | --- |
| Full CTest suite (`Release`) | 11/11 passed, 4.8 s |
| `unit` group | 39 tests (39 at dev3 as well; the dev3 notes' "37" was a miscount — see §15) |
| `nnue` group (new) | 7/7 passed |
| `nnue_features` differential entry (new) | passed |
| Warnings with `-Wall -Wextra -Wshadow -Wpedantic` | none |
| Bench signature, defaults | unchanged from dev3 (`e06c4352681ae8eb` d6, `5bceff035f2a4ae4` d7) |
| Bench signature, each dev4 switch alone | `d1f7df69fcac85cf` (ModernLMR), `7f5d1172e6340969` (MoveCountPruning), `21f35ef2d43eae47` (IIR), `43b43c09655d6fc2` (Improving), `e06c4352681ae8eb` (TTEval, unchanged as expected) |
| Sanitisers, clang, Windows, CMake 3.16 | CI-only; not runnable on this sandbox (see §16) |

The dev4 code is covered by tests in both directions: the C++ tests exercise the
evaluation through the public API, and the Python test compares the engine's
feature output with an independent implementation, so a change to either side of
the training/engine boundary fails CI.

## 13. Tactics and endgame suites (this binary)

| Suite | Budget | Result |
| --- | --- | --- |
| `mate_suite.epd` (25 positions, strict oracle) | 60,000 nodes | **25/25 solved**, no position reached the budget |
| `endgame_suite.epd` (24 K+Q/K+R vs K) | 20,000 nodes | 16/24 |
| `endgame_suite.epd` | 400,000 nodes | **24/24** |

The 20,000-node row is the honest low-budget measurement for **this** binary; it
should not be conflated with dev3's 12/24 at the same budget, which was measured
on a pre-review build with a different defect. Raw output:
`tactics-mate.json`, `tactics-mate.raw.txt`, `endgame-conversion.json`,
`endgame-conversion-400k.json` and their `.raw.txt` companions.

## 14. Protocol and compatibility

* No UCI command was removed or changed in meaning. `NNUE` and `NnueFile` are
  additive.
* `Threads` is still not advertised, because multi-threaded search does not exist
  in this codebase; nothing in dev4 changed that.
* `setoption name NNUE value false` always succeeds, even with no network
  available; `value true` reports the reason it cannot be honoured. A network
  loaded with `NnueFile` is not silently replaced by a later `NNUE true`.
* The pass-through of string options with spaces (`EvalParams`, `NnueFile`) is
  covered by the existing integration tests and by a manual check.
* The `bench` header now includes `network=` and `kernel=`, which is
  additive output that no UCI consumer parses.

## 15. Audit corrections

| Finding | Resolution |
| --- | --- |
| Dev3 notes said the `unit` group had 37 tests | Recounted from the source at `32e7d9d` with `git grep "TEST(unit,"`: **39**. Fixed in the dev4 notes; the dev3 report is a historical record and is not rewritten. |
| "Untested evaluation candidate D described as a match loss" | Checked: the dev3 report already says D "was not matched and not shipped". No change needed; dev4's own documents keep "not tested" and "tested and lost" strictly separate. |
| 20k/200k endgame conversion figures from dev3 could be read as properties of this binary | All endgame figures in this release were **re-measured on the dev4 binary** (§13). Dev3's numbers are quoted only as dev3's. |
| Stale dev3 benchmark figures in dev4 docs | Every number in the dev4 documents was measured in this release; the only dev3/dev2 numbers quoted are explicitly attributed (e.g. the dev2 baseline history in `README.md`). |

## 16. Environment and reproducibility

| Item | Value |
| --- | --- |
| CPU | 2 logical cores / 1 physical core (shared sandbox) |
| Memory | 3 GB (no swap) |
| OS / compiler | Debian 12, GCC 12.2.0 |
| Python for tooling | 3.11, python-chess 1.11.2, NumPy 2.4.6, PyTorch 2.15.0 CPU |
| CMake | 4.x installed locally; CI also covers the 3.16 minimum |
| GPU | none; no paid service was used at any point |
| CI configurations | ASan/UBSan, TSan, clang, Windows Debug/Release, CMake 3.16 — run by GitHub Actions, not reproducible in this sandbox |

Reproduction: `docs/DEV4_BENCHMARKS.md` §7 gives the exact match commands;
`benchmarks/training/README.md` gives the data generation and training commands;
every match JSONL records its full configuration, including the jitter and seed.

## 17. Provenance and licensing

* The engine and every dev4 component are original work under the repository's
  Apache-2.0 license; no external engine is linked, wrapped or called.
* No third-party network weights or training data are used or distributed. The
  committed `.nnue` file was produced by this repository's pipeline from this
  repository's self-play data.
* Algorithmic ideas (incremental first-layer accumulators, side-to-move-first
  perspective ordering, log-log LMR schedules, IIR, LMP, reverse futility) are
  published techniques; only the descriptions were used, and the implementations
  here are independent.
* Python tooling used for training and validation (PyTorch, NumPy, python-chess,
  CMake) is documented in `THIRD_PARTY.md` with licenses and roles; none is a
  runtime dependency of the engine.
* Corpora are not committed (185 MB); their SHA-256 hashes, sizes and generation
  commands are recorded in `benchmarks/training/README.md`.

## 18. Review record

Self-review performed against the project's own gates, in the order the gates
apply:

1. **Does the default change?** No — proven by identical bench signatures and by
   game-by-game identical records against the null control.
2. **Is every shipped option real?** Yes: each of the five options has a UCI
   handler and a measured effect or a measured no-op; `razoring` is deliberately
   *not* advertised because it is not implemented.
3. **Does the new evaluation corrupt state?** No: `verify_state` compares the
   incremental accumulator with a rebuild on every tested move; the accumulator
   check was additionally run over a full depth-6/7 bench during development
   (temporarily instrumented, then removed), with no mismatch.
4. **Can the training-data claim be reproduced?** Yes: hashes and commands are
   recorded, and the shipped-network identity is printed by the engine.
5. **Is any claim overstated?** The fixed-time regression row is the risk case and
   is explicitly labelled inconclusive with the control that proves why (§6).
6. **Licensing/independence** — §17. **No fabricated results** — every number here
   has a committed raw record; the Windows binary is CI-built and was not executed
   by hand on Windows, which is stated rather than glossed.

Independent review by another person was **not** performed; this section records a
self-review and does not claim otherwise.

## 19. Limitations and threats to validity

`docs/DEV4_LIMITATIONS.md` holds the full list. The four that most affect how this
report should be read:

* **Resolution.** ±35 Elo at fixed nodes and ±65 Elo at fixed time for a single
  experiment; a real +20 Elo effect is invisible here.
* **Time control.** 40 ms/move, not tournament time. Results are not guaranteed to
  transfer.
* **Self-play only.** No external opponent exists in this environment, so the
  report says nothing about absolute strength or about how the changes interact
  with stronger opposition.
* **Fixed-time false positives.** Demonstrated in §6: two identical-in-play builds
  produced a 95 % interval excluding zero. Fixed-time numbers here are only used
  as a secondary signal and are labelled accordingly.

## 20. Verdict

* **Is dev4 stronger than dev3?** **No measurable difference.** Point estimates:
  −12.3 Elo at fixed nodes (within the harness's own null of −12.3) and +29.0 Elo
  at fixed time (against a null of −30.5). Neither is evidence of a change, and
  the binaries play identically at a fixed node budget.
* **By how much?** Zero, within a resolution of roughly ±35 Elo at fixed nodes.
* **Strength band achieved:** *none* — dev4 is a "no regression, no gain"
  release. It does not claim the 0…+49 "unproven" band either, because there is no
  positive point estimate to report at fixed nodes.
* **Evidence strength:** the negative results are strong (large effects with
  intervals far from zero: −708 Elo for the network, −39 and −104 Elo for two
  pruning candidates); the null result for the default is strong at fixed nodes
  (bit-identical play) and weak at fixed time (scheduler noise).
* **Top contributors, in order of measured effect on the shipped engine:**
  nothing positive; the largest *technical* contributions are the verified neural
  infrastructure, the ordering-bug diagnosis, and the measurement harness.
* **Failed experiments (all documented, none hidden):** the neural evaluation
  (−708), `ModernLMR` (−29/−31), `MoveCountPruning` (−39/−104), `IIR` (−15/+7),
  `Improving` (−26/−13), `TTEval` (no-op), razoring (never implemented, declared
  but not advertised), and SMP/tablebases/opening book (out of scope or
  unverifiable on this hardware).
* **dev5 priorities:** king-bucketed features with search-derived labels and more
  data; then re-test `IIR` with several thousand games (its fixed-time point
  estimate is positive but unresolved); then a proper time-control study at 1 s+
  per move once compute allows. Nothing else in the search is worth re-testing
  before the evaluation is genuinely better, because every search change measured
  here was neutral-to-negative on top of dev3's search.
