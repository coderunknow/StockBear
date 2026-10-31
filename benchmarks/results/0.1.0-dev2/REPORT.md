# dev2 investigation — NOT A RELEASE

Baseline: annotated `v0.1.0-dev1` -> `dab34b0adb278ed474d64e1a700f7555e416ef4e`,
also current main at preflight. The candidate measured here was the uncommitted
prototype based on that commit; it adds a research-only object to the static
library, not used by the engine. The linker produced byte-identical executables:
SHA-256 `350895eacbc85734e3f723667cd211ba90caff05b265ed9ee1ec63cf3d1218db`
for both the clean dev1 rebuild and the prototype. Thus the playing engine
is unchanged, and neither strength nor performance improvement can be claimed.
The eventual PR commit also includes documentation and tests; it is not the
source commit of this preliminary measurement.

Build: Linux x86-64, virtual Intel Xeon @ 2.60 GHz, 2 visible CPUs; GCC 12.2.0,
CMake 3.16.8, Release `-O3`, C++17, no native-architecture option. Both one
thread, requested 16 MiB hash. Twelve fixed-depth-5 positions ran once each;
[dev1 CSV](dev1-search-depth5.csv), [prototype CSV](prototype-search-depth5.csv).
All moves, score, PV and node counts agree. Timings were collected while other
jobs were running and cannot support a performance comparison. No ablation,
paired dev1-vs-candidate tournament or statistical confidence estimate was
performed; W/D/L and Elo are unavailable. Historical dev1 vs Stockfish 11 was
0/0/8 under its earlier conditions, not a dev2 strength baseline.

GitHub's official latest-release API on 2026-10-31 identified Stockfish 19,
`sf_19`, published 2026-09-05. Its official Linux universal asset API digest is
`sha256:9defc0d4e55d49c65a6d042f3e571a39fcea499ade6dbe741b53b8c65e03611f`;
the asset was not downloaded, independently checksummed or played in this
investigation. Stockfish is strictly an external reference/opponent, not an
engine dependency. There are no new PGN/JSONL match results to report.

Correctness: Release, Debug and GCC ASan+UBSan CTest each passed 7/7 locally;
2,000 newly seeded differential positions plus eight curated positions matched
python-chess depth-two divides (`20261031`). The two independent reduced-graph
counts are documented in [research](../../../docs/DEAD_POSITION_RESEARCH.md).
These measurements are not a general correctness proof. Windows, Clang, exact
PR-head CI, CodeRabbit and release binaries remain to be verified separately.

**Decision:** general FIDE dead-position implementation, performance and
strength gates are not satisfied. No release or tag should be created.
