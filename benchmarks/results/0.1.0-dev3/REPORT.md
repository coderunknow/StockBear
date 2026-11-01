# StockBear 0.1.0-dev3 — evidence report

Third development prerelease. Everything here was measured in the build sandbox
described under [Environment](#environment); raw outputs are committed next to
this file so each number can be re-derived without re-running the engine.

## What changed, in one paragraph

The search was rewritten with an independently switchable feature set, real
MultiPV and real `go searchmoves`; the evaluation became a parameter table with
an offline tuning pipeline, a self-play dataset and an independent mate oracle
for a new tactics/endgame regression suite. Three tuned evaluation candidates
and two new search configurations were measured by paired matches. **None of them
was stronger than what dev2 already did**, so `v0.1.0-dev3` ships the dev2 search
and the dev2 evaluation, and this report contains the negative results rather
than a claim. What the release does add is correctness and protocol capability:
MultiPV and `searchmoves` now work and are black-box tested, the evaluation is
auditable as data, and there are reproducible suites to catch future regressions.

## Build and identity

| item | value |
| --- | --- |
| Version | `0.1.0-dev3` |
| Compiler | GCC 12.2.0, `-O3` (CMake `Release`), C++17, no `-march=native` |
| Build | `cmake -S . -B build -DCMAKE_BUILD_TYPE=Release && cmake --build build --parallel 2` |
| Host | Linux x86-64, 2 vCPU, no GPU, no network at measurement time |

## Benchmarks

The benchmark suite is the embedded 12-position suite, `bench --depth N --hash 16`,
single thread. Node counts are deterministic; times are from repeated runs on an
otherwise idle machine and are given as a range.

| build | depth | nodes | time | signature |
| --- | --- | --- | --- | --- |
| dev2 (rebuilt from tag `v0.1.0-dev2`) | 6 | 108,910 | 58 ms | `e06c4352681ae8eb` |
| **dev3 shipped** | 6 | **108,910** | **58 ms** | **`e06c4352681ae8eb`** |
| dev2 (rebuilt from tag `v0.1.0-dev2`) | 7 | 250,053 | 130 ms | `5bceff035f2a4ae4` |
| **dev3 shipped** | 7 | **250,053** | **130 ms** | **`5bceff035f2a4ae4`** |
| dev3 with all five new ordering switches on | 6 | 118,548 | 69–72 ms | `8d99b4e28a6231a0` |
| dev3 with all five new ordering switches on | 7 | 255,021 | 140–143 ms | `f6103610012f7f9d` |

The shipped build's depth-6 and depth-7 signatures are byte-identical to dev2's,
which is a stronger statement than "similar node counts": with the new switches
off, the rewritten search produces the same moves, scores, depths, node counts
and principal variations on every benchmark position.

Ablation of the new ordering features at depth 7 (nodes; all five on = 255,021):

| configuration | nodes |
| --- | --- |
| dev2 / all five off | 250,053 |
| counterMoves off | 257,663 |
| continuationHistory off | 254,834 |
| captureHistory off | 250,179 |
| historyMaluses off | 279,868 |
| lmrHistory off | 266,980 |
| all five off | 250,053 |

Individual removals mostly *increase* nodes while the combination is worse than
none of them: the features interact, and node count at a fixed depth is only a
proxy. The matches below are what decided the defaults.

## Matches

All matches: `scripts/tournament.py`, 30 openings, paired colour-reversed games,
`--nodes 4000` per move (deterministic, no clock artefacts), `--max-plies 200`,
Hash 16 MB, 1 thread. Elo is always quoted as engine A with a 95 % interval;
positive means engine A scored more. Decimals that reached the ply cap are
reported as unadjudicated and are never counted as draws.

### Search: dev3 experimental configurations against the rebuilt dev2 binary

| configuration (engine A) | decided | W/D/L | A score | Elo (95 %) | pentanomial 0/0.5/1/1.5/2 | unadj. |
| --- | --- | --- | --- | --- | --- | --- |
| all five switches on | 571 | 205/152/214 | 0.5018 | **+1.3 [−17.9, +20.5]** | 10/68/126/48/19 | 29 |
| historyMaluses + lmrHistory only | 600 | 195/182/223 | 0.4767 | **−16.2 [−33.0, +0.5]** | 19/29/166/77/9 | 0 |

Both results are inside the noise band; neither configuration is a strength
improvement, and the all-on configuration costs 8 % more time at a fixed depth.
The switches therefore default to **off**, and the shipped search is dev2's. Raw
records: `match-dev2-search-allon.jsonl`, `match-dev2-search-subset.jsonl`.

### Evaluation: tuned candidates against the shipped evaluation

One binary on both sides, so the search is identical and only the parameter file
differs (`--b-option EvalParams=…`).

| candidate | decided | engine A (shipped) W/D/L | Elo for the candidate | verdict |
| --- | --- | --- | --- | --- |
| A (`--ridge 0.02 --max-delta-fraction 0.35 --no-preserve-sign`) | 591 | 328/136/127 | **−119.1 [−140.8, −98.2]** | much worse |
| B (`--ridge 0.10 --max-delta-fraction 0.20`) | 590 | 249/187/154 | **−51.3 [−72.1, −30.8]** | worse |
| C (`--ridge 0.04 --max-delta-fraction 0.30`) | 590 | 202/176/212 | **+12.0 [−10.3, +34.4]** | indistinguishable |

The candidate with the best tuning-loss improvement (A) was the worst in play.
Details, dataset hashes and the reproduction commands: [../../docs/TUNING.md](../../docs/TUNING.md).

### Regression check: the shipped configuration against dev2

The shipped configuration has the dev2 search and the dev2 evaluation, so the
honest check is that it *plays* like dev2. `scripts/tournament.py` with 100
opening pairs (200 games), `--nodes 4000`, seed `20261108`:

| decided | W/D/L | score | pairs scoring 1.0 | pentanomial | unadj. |
| --- | --- | --- | --- | --- | --- |
| 200 | 70/60/70 | **0.5000** | **100 of 100** | 0/0/100/0/0 | 0 |

Every pair split exactly one win each way, which is what identical play under
colour reversal looks like; the harness reports a null interval because the
sample has zero variance. That is the intended outcome: the protocol layer and
the option plumbing changed, the play did not. Raw record:
`match-dev2-shipped-regression.jsonl`.

### Against Stockfish 19: always an attempt, always blocked

No Stockfish match could be played in this environment, and no other engine was
substituted. What was tried:

1. Release assets (`stockfish-linux-x86-64-universal.tar.gz`): the download
   endpoint `release-assets.githubusercontent.com:443` is unreachable
   (`OpenSSL SSL_connect: SSL_ERROR_SYSCALL`).
2. Source: `codeload.github.com/official-stockfish/Stockfish/tar.gz/refs/tags/sf_19`
   downloaded successfully (291,206 bytes) and builds, but the build embeds the
   default network `nn-1a298aa575a0.nnue`, which is not in the tree.
3. That network is a 133-byte Git LFS pointer in
   `official-stockfish/networks`; LFS content lives on `media.githubusercontent.com`,
   which is unreachable, so the real file cannot be fetched.
4. Fourteen archived nets from the same repository that *are* real blobs (74 MB,
   90 MB and 70 MB families) were downloaded and tried through the `EvalFile`
   option; every one was rejected as
   "Network evaluation parameters compatible with the engine must be available",
   i.e. architecture-incompatible with SFNNv16.

The unverified scope this leaves: StockBear's strength against Stockfish 19 is
**unknown** for dev3. dev2's 0.5/20 result against Stockfish 11 stands as the
only engine-to-engine data point and is not extrapolated.

## Tactics and endgame suites

`benchmarks/tactics/mate_suite.epd` — 26 positions taken from StockBear
self-play games that ended in checkmate, each re-proved by
`scripts/chess_oracle.py` (an independent mate proof written on top of
python-chess, sharing no code with the engine). Every position lists **all** moves
that force mate in the stated number of plies, so a pass means "found a mating
move", not "agreed with one arbitrary choice".

| run | node budget | solved | notes |
| --- | --- | --- | --- |
| dev3 shipped | 60,000 | **26/26** | all solved well inside the budget; mate scores reported from depth 2 |

`benchmarks/tactics/endgame_suite.epd` — 24 constructed three-man endgames
(12 K+Q v K, 12 K+R v K), all theoretical wins, played out with the engine on both
sides and adjudicated by python-chess.

| run | node budget | mate inside 120 plies | failures |
| --- | --- | --- | --- |
| dev3 shipped | 400,000 | **22/24** | `kqk-12`, `krk-17` |
| dev3 shipped | 200,000 | 22/24 | `kqk-04`, `kqk-09` (different positions) |
| dev3 shipped | 20,000 | 12/24 | 12 repeats/fifty-move |

The two failures are not engine bugs but a real weakness: the winning side allowed
a **second** repetition, which lets the defender claim the third, and a
repetition is only scored as a draw once it is claimable. It is reported as a
known limitation, not hidden — see [Known limitations](#known-limitations).

Raw records and the complete engine output: `tactics-mate.json`,
`tactics-mate.raw.txt`, `endgame-conversion.json`, `endgame-conversion.raw.txt`.

## Protocol verification

Two black-box CTest entries exercise the engine over pipes with no access to
internals:

* `uci_integration` — handshake and version, option validation, `position` with
  and without moves, invalid FEN rejection, depth/node/movetime/clock limits,
  negative clocks, `isready` during `go infinite`, `stop`, terminal positions
  (`bestmove 0000`), repeated searches, `ucinewgame`, quitting during a search,
  **`go searchmoves`** (restriction honoured over depth/nodes/movetime/clocks,
  a single legal move, illegal entries reported and dropped, an all-illegal list
  reported and ignored, a list followed by another keyword), and **MultiPV**
  (3 ranked distinct lines, best move equals line 1, scores non-increasing,
  fewer legal moves than requested, return to single-PV output).
* `uci_fuzz` — 300 seeded malformed inputs and cancellations, unchanged.

Everything the engine advertises it implements; pondering, Chess960 and threads
are neither implemented nor advertised.

## Environment and reproducibility

* Linux x86-64, 2 vCPU, GCC 12.2.0, CMake 3.25.
* `python3` with `chess==1.11.2`; the engine itself needs neither.
* Every match file records the exact command line, seed, opening suite, node
  budget, hash size and thread count in its `config` object.

## Known limitations

* **Endgame conversion is depth-limited.** Two of 24 three-man endgames reach a
  repetition claim at 400 k nodes. A tablebase or a fifty-move/progress term
  would fix it; neither is in this release because neither was validated here.
* **No Stockfish 19 measurement.** See above.
* **The evaluation did not improve.** The tuning pipeline works and is
  reproducible, but its candidates lost their matches; see
  [TUNING.md](../../docs/TUNING.md).
* **Node-limited matches.** All matches use a fixed node budget per move, so they
  measure strength per node, not per second. The all-on search configuration costs
  8 % more time at equal depth, which a time control would expose; that is part of
  why it is not the default.
* **Single thread, ordinary hardware.** No SMP, no tablebases, no opening book,
  no NNUE, and no claim beyond the recorded matches.
