# Third-party and algorithm notices

StockBear's core is independently implemented under the repository's Apache-2.0 license. It does not incorporate or call another engine for move selection. There are no mandatory third-party engine or Python runtime dependencies.

Optional **development/validation** software used in the recorded tests:

| Tool | Version | License | Use |
|---|---|---|---|
| python-chess distribution `chess` | 1.11.2 | GPL-3.0-or-later | Independent perft/move validation; legal-game adjudication and PGN in the optional tournament harness. Not linked into or required by StockBear. [Project](https://github.com/niklasf/python-chess). |
| Stockfish | 11 (`sf_11`) | GPL-3.0 | External match opponent only; not packaged or used for StockBear's search. [Project](https://github.com/official-stockfish/Stockfish). |
| CMake | 3.16.8 and 4.4.4 locally | BSD-3-Clause | Build tool, not a runtime dependency. |
| PyYAML | 6.0.3 locally | MIT | One-off workflow syntax validation; not required by the project or CI. |
| zizmor / kjanat actionlint | 1.31.1 / 1.17.0 locally | MIT / MIT | One-off workflow security and syntax checks, not project runtime dependencies. |
| GitHub Actions checkout/setup-python/upload-artifact/download-artifact | SHA-pinned v4/v5 | MIT | Hosted CI and release automation, not runtime dependencies. |

Standard algorithms used include alpha-beta/negamax, principal variation search, quiescence, Zobrist hashing, magic-bitboard indexing, and SplitMix64 for deterministic key/constant generation. These describe algorithmic ideas; the implementation and generated magic constants in this repository were written for this project, not copied from another engine. The C++ compiler/runtime and OS libraries are supplied by the build/target environment; GitHub Actions and Python are build/test infrastructure, not engine runtime components.
