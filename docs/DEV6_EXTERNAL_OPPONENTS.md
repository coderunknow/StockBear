# exp-0031/0032 — external ladder opponent pool (pinned identities)

All opponents were built from **official source archives fetched via `codeload.github.com`** (an allowed host) with a pinned GCC 12.2.0 / ld 2.40 / glibc 2.36 toolchain, no `-march=native` in the pinned commands, no NNUE network files (classical-eval releases), and committed as immutable binaries under `benchmarks/binaries/external/`. GPL-3.0 notices: see `THIRD_PARTY.md`. These are OPPONENTS/benchmark references only; no Stockfish or Weiss source, weights, or implementation code was copied into StockBear.

| id | engine / version | tag | source commit | binary SHA-256 (short) | go nodes | license |
|---|---|---|---|---|---|---|
| sf8 | Stockfish 8 64 POPCNT | sf_8 | `369eff437cc0` | `1f573009fcdbcb4f…` | True | GPL-3.0 |
| sf9 | Stockfish 9 64 POPCNT | sf_9 | `378c8bdbb8f9` | `865ca8119e05c354…` | True | GPL-3.0 |
| sf10 | Stockfish 10 64 POPCNT | sf_10 | `b4c239b62528` | `39a43e237b1acd5d…` | True | GPL-3.0 |
| sf11 | Stockfish 11 64 POPCNT | sf_11 | `c3483fa9a7d7` | `59503c6023b94bdc…` | True | GPL-3.0 |
| weiss2 | Weiss 2.0 | v2.0 | `0db49c7270f5` | `de9ab5285863cc5d…` | False | GPL-3.0 |

Full archive/binary SHAs, exact build commands, UCI option sets and rating-source qualifications: `benchmarks/dev6-baseline/external_opponents.json`.

## Rating-system qualifications (critical)

- Stockfish 8/9/10/11 and Weiss 2.0 are exact official releases with exact source commits and binary SHAs. Published CCRL/CEGT ratings are **contextual anchors only** — different hardware, time control, engine population and methodology; they are NOT interchangeable with this ladder's internal rating.
- SF11 `UCI_Elo` is an **internal, approximate, self-reported** strength limiter anchored by Stockfish's own CCRL/Ordo fit (`E = 1346.6 + 143.4·level^0.806`, from `src/search.cpp`). Integer `Skill Level` is used for reproducible anchors; its mapped Elo is recorded as approximate context, not a certified external rating.
- `Skill::pick_best` uses a time-seeded PRNG, so individual games are not bitwise reproducible; the ladder is statistically reproducible (fixed binaries, options, openings, seeds, reported CIs).
- This ladder reports a **pool-specific internal rating** (fixed-node control, this hardware, these exact binaries) with CIs. NO absolute/CCRL/FIDE-comparable Elo is claimed, and the gap to 3,000 Elo is NOT asserted from it.

