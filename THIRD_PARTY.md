# Third-party and algorithm notices

StockBear's core is independently implemented under the repository's Apache-2.0 license. It does not incorporate or call another engine for move selection. There are no mandatory third-party engine or Python runtime dependencies.

Optional **development/validation** software used in the recorded tests:

| Tool | Version | License | Use |
|---|---|---|---|
| python-chess distribution `chess` | 1.11.2 | GPL-3.0-or-later | Independent perft/move validation; legal-game adjudication and PGN in the optional tournament harness. Not linked into or required by StockBear. [Project](https://github.com/niklasf/python-chess). |
| Stockfish | 11 (`sf_11`) | GPL-3.0 | External match opponent only; not packaged or used for StockBear's search. [Project](https://github.com/official-stockfish/Stockfish). |
| CMake | 4.4.4 locally | BSD-3-Clause | Build tool, not a runtime dependency. |

Standard algorithms used include alpha-beta/negamax, principal variation search, quiescence, Zobrist hashing, magic-bitboard indexing, and SplitMix64 for deterministic key/constant generation. These describe algorithmic ideas; the implementation and generated magic constants in this repository were written for this project, not copied from another engine. The C++ compiler/runtime and OS libraries are supplied by the build/target environment; GitHub Actions and Python are build/test infrastructure, not engine runtime components.
