# Third-party and algorithm notices

StockBear's core is independently implemented under the repository's Apache-2.0
license. It does not incorporate or call another engine for move selection.
There are no mandatory third-party engine, library or Python runtime
dependencies.

Optional **development/validation** software used in the recorded tests:

| Tool | Version | License | Use |
|---|---|---|---|
| python-chess distribution `chess` | 1.11.2 | GPL-3.0-or-later | Independent perft/move validation, independent dead-position reference implementation, legal-game adjudication and PGN in the tournament harness. Not linked into or required by StockBear. [Project](https://github.com/niklasf/python-chess). |
| Stockfish | 19 (`sf_19`) source archive | GPL-3.0 | External match opponent only; not packaged, not vendored and never used for StockBear's search. The dev2 build environment could not obtain the NNUE network files required by this version, so no Stockfish 19 match was run. [Project](https://github.com/official-stockfish/Stockfish). |
| Stockfish | 11 (`sf_11`) source archive | GPL-3.0 | External match opponent only, used for the recorded dev2 external check because it builds from source without any downloaded network file. [Project](https://github.com/official-stockfish/Stockfish). |
| PyTorch (`torch`, CPU build) | 2.15.0 | BSD-3-Clause | **Training only.** Runs `scripts/train_nnue.py` to fit the neural evaluation; never linked into, shipped with, or required by the engine. The shipped `.nnue` file is data produced by this script. |
| NumPy | 2.4.6 | BSD-3-Clause | Feature extraction, quantisation and verification in the training/conversion scripts. Not a runtime dependency. |
| CMake | 3.16.8 (CI minimum) up to 4.x locally | BSD-3-Clause | Build tool, not a runtime dependency. |
| GitHub Actions checkout/setup-python/upload-artifact/download-artifact | SHA-pinned v4/v5 | MIT | Hosted CI and release automation, not runtime dependencies. |

Source and checksums recorded for the dev2 external opponent:

* `Stockfish-sf_11.tar.gz` from
  `https://codeload.github.com/official-stockfish/Stockfish/tar.gz/refs/tags/sf_11`,
  SHA-256 `802261cc601b67bed00c0ef7d21e2125959630f0852a06db9fc9bd74f440b199`;
  built with `make build ARCH=x86-64-bmi2 COMP=gcc`; resulting binary SHA-256
  `700613c69279b5697d29344b139e4999c7a5652319cf22012bc577cdb91bbb6c`.
* `Stockfish-sf_19.tar.gz` from
  `https://codeload.github.com/official-stockfish/Stockfish/tar.gz/refs/tags/sf_19`,
  SHA-256 `519b653d0d1ffb96531d982ccbe5c6a19425e8388e0e3c2f70f34b424ab32d76`.
  It was downloaded and unpacked but **not built**: Stockfish 19 requires NNUE
  network files served from hosts outside this build environment's allow-list,
  so the build fails at `network.o`.

## Neural evaluation (dev4)

The neural evaluation in `src/evaluation/nnue*.{hpp,cpp}`, the feature function,
the quantised serialisation format, the SIMD kernels, the trainer
(`scripts/train_nnue.py`), the quantiser (`scripts/convert_nnue.py`), the
embedding generator and the self-play data generator
(`src/utilities/selfplay.cpp`) were all written for this project.

* **No third-party network weights, no third-party training data, and no code
  from another engine were used.** The shipped `.nnue` file (when a network is
  embedded) is the output of this repository's own training pipeline, trained on
  self-play games produced by this repository's own engine.
* The *idea* of an incrementally-updated first layer with a side-to-move-first
  perspective ordering, and the general family of small quantised networks used
  as chess evaluation, are published techniques (the "NNUE" line of work, and
  its chess adaptations such as the HalfKP feature set). Only the published
  algorithm description was used; the code, the feature set, the file format
  and every weight in this repository were produced here.
* `scripts/embed_nnue.py` carries the SHA-256 of the network it embeds, and
  `stockbear nnue --info` / `bench --network` print the network identity, so a
  binary's network can be attributed without unpacking it.
* Self-play corpora (`.txt`/`.npy`) are generated locally and are not committed
  to the repository; only their hashes, sizes and generation commands are
  recorded under `benchmarks/training/`.

Standard algorithms used include alpha-beta/negamax, principal variation search,
quiescence search, aspiration windows, null-move pruning, late move reductions,
reverse futility and futility pruning, static exchange evaluation, Zobrist
hashing, magic-bitboard indexing, a pentanomial match model with Wilson and
normal-approximation intervals, SPRT, and SplitMix64 for deterministic
key/constant generation. These describe algorithmic ideas; the implementation and
the generated magic constants in this repository were written for this project,
not copied from another engine. The C++ compiler/runtime and OS libraries are
supplied by the build/target environment; GitHub Actions and Python are
build/test infrastructure, not engine runtime components.
