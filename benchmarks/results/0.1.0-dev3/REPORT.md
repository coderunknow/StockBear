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
| dev3 with the tuned candidate A | 6 | — | — | `269a852faa999f37` |

The raw output of each run is committed: `bench-depth6.csv`, `bench-depth7.csv`
and `bench-depth7-allon.csv`.

The shipped build's depth-6 and depth-7 signatures are byte-identical to dev2's:
with the new switches off, the rewritten search produces the same moves, scores,
depths, node counts and principal variations on every benchmark position. That is
a statement about these twelve positions, and this release provides a concrete
counter-example to reading it as "identical behaviour everywhere": the review fix
that makes a null move clear the previous-move slot leaves both signatures
untouched and changes play in deeper endgames (see
[the endgame suite](#tactics-and-endgame-suites)).

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

| configuration (engine A) | decided | W/D/L | A score | Elo, pentanomial | Elo, opening-clustered | pairs 0/0.5/1/1.5/2 | unadj. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| all five switches on | 571 | 205/152/214 | 0.5018 | **+1.3 [−17.9, +20.5]** | **+1.3 [−62.9, +65.6]** | 10/68/126/48/19 | 29 |
| historyMaluses + historyLMR | 600 | 195/182/223 | 0.4767 | **−16.2 [−33.0, +0.5]** | **−16.2 [−71.6, +38.3]** | 19/29/166/77/9 | 0 |

Both matches were replayed from the reviewed build with **all five switches set
explicitly on both engines** and reproduce the earlier numbers exactly; the
records' `configuration` line now lists every option sent to each side and every
default each engine advertised.

Both results are inside the noise band by both intervals, and neither shows an
improvement; the all-on configuration additionally costs about 8 % more time at a
fixed depth. The switches therefore default to **off**. Raw records:
`match-dev2-search-allon.jsonl`, `match-dev2-search-subset.jsonl`.

Every record's `config` object names the options that were actually sent to each
engine and the defaults the engine advertised, so the configuration can be read
out of the evidence instead of being inferred from a build's defaults — which
matter here, because those defaults changed during this release.

### Evaluation: tuned candidates against the shipped evaluation

One binary on both sides, so the search is identical and only the parameter file
differs (`--b-option EvalParams=…`).

| candidate | decided | engine A (shipped) W/D/L | candidate Elo, pentanomial | candidate Elo, opening-clustered | verdict |
| --- | --- | --- | --- | --- | --- |
| A (`--ridge 0.02 --max-delta-fraction 0.35 --no-preserve-sign`) | 590 | 339/133/118 | **−132.5 [−158.6, −107.7]** | **−132.5 [−227.3, −53.6]** | worse by both intervals |
| B (`--ridge 0.10 --max-delta-fraction 0.20`) | 600 | 204/192/204 | **0.0 [−22.1, +22.1]** | **0.0 [−74.5, +74.5]** | indistinguishable |
| C (`--ridge 0.04 --max-delta-fraction 0.30`) | 582 | 162/234/186 | **−9.2 [−32.4, +13.8]** | **−9.2 [−87.6, +68.2]** | indistinguishable |

A fourth fit (`D`) pins the Texel scale at K = 400 (so fitted scores stay
calibrated against the search's pruning margins), uses ridge 0.10, a 20 % movement
cap, sign preservation and anchored material values. It moves seven positional
terms by one or two points and lowers the holdout loss from 0.5777 to 0.5719. It
was not matched and not shipped: the changes are smaller than the resolution of
the matches above, and the objective's improvement comes from shrinking already
small terms, not from a direction the games can confirm.

The candidate with the best tuning-loss improvement (A) was the worst in play, in
both the first run (−119.1 Elo) and the replay from the reviewed build (−132.5).
Only A is separated from the baseline by both intervals; for B and C the claim is
"no improvement was demonstrated", which is enough to reject them without
overstating the measurement. As the seeding and 600-game budget are identical,
the difference between a candidate's two runs is the same measurement repeated —
A moved by about 13 Elo between runs, which is a useful reminder of how wide these
intervals are in practice.
Details, dataset hashes and the reproduction commands: [../../../docs/TUNING.md](../../../docs/TUNING.md).

### Regression check: the shipped configuration against dev2

The shipped configuration has the dev2 search and the dev2 evaluation, so the
honest check is that it *plays* like dev2. `scripts/tournament.py` with 100
opening pairs (200 games), `--nodes 4000`, seed `20261108`:

| decided | W/D/L | score | pairs scoring 1.0 | pentanomial | unadj. |
| --- | --- | --- | --- | --- | --- |
| 200 (replayed from the reviewed build) | 70/60/70 | **0.5000** | **100 of 100** | 0/0/100/0/0 | 0 |

The 100 pairs are 70 pairs split one win each way plus 30 pairs of two draws;
every pair therefore scored 1.0, which is what identical play under colour
reversal looks like. The harness reports a null interval because the sample has
zero variance. That is the intended outcome: the protocol layer and
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

`benchmarks/tactics/mate_suite.epd` — **25** positions taken from StockBear
self-play games that ended in checkmate, each re-proved by
`scripts/chess_oracle.py` (an independent mate proof written on top of
python-chess, sharing no code with the engine). Every position lists **all** moves
that force mate *within the stated number of plies*, so a pass means "found a
mating move in time", not "agreed with one arbitrary choice".

The suite was regenerated after the review fixed the oracle, and that changed the
evidence in two directions that both matter. The old oracle scored every mate as
`MATE - 1` and so could not tell a mate in three plies from a mate in five; it
therefore accepted moves that mate *later* than the position's label. The
corrected oracle counts the distance at every ply and accepts strictly fewer
moves — for example `mate02-3ply` drops from 31 accepted moves to 7. One position
(`mate07-5ply`) no longer contains its own game move among the proven moves and is
gone, which is why the suite is 25 positions and not 26. The earlier "26/26" was
measured against the looser sets and is not comparable: the honest sequence is
25/25 on the strict suite.

| run | node budget | solved | notes |
| --- | --- | --- | --- |
| dev3 shipped (`e96cb712…`), strict suite | 60,000 | **25/25** | no position reached the budget; every mate is proved within 2–5 plies of first report |
| dev3 shipped, earlier looser suite | 60,000 | 26/26 | not comparable: the sets accepted late mates (see above) |

Once a forced mate is proved, each further iteration is nearly free because the
mate bounds cut the tree immediately, so the engine keeps deepening to its
horizon (depth 243) in a few thousand nodes instead of stopping. That is the
behaviour dev2 had and it is kept, but it means the *last* reported depth says
nothing useful; the JSON records both `depth` (last) and `mate_depth` (first mate
line), and only the latter is quoted.

`benchmarks/tactics/endgame_suite.epd` — 24 constructed three-man endgames
(12 K+Q v K, 12 K+R v K), all theoretical wins, played out with the engine on both
sides and adjudicated by python-chess.

| run | node budget | mate inside 120 plies | failures |
| --- | --- | --- | --- |
| dev3 shipped (`e96cb712…`) | 400,000 | **24/24** | none |
| pre-review build of the same source | 400,000 | 22/24 | `kqk-12`, `krk-17` |
| pre-review build | 200,000 | 22/24 | `kqk-04`, `kqk-09` (different positions) |
| pre-review build | 20,000 | 12/24 | 12 repeats/fifty-move |

The difference between the first two rows is a real bug that the review found: a
null move left the "previous move" slot untouched, so the child of a null move
read a stale move from an earlier branch and ordered its quiets against the wrong
context. Bench signatures did not change, because the benchmark positions do not
reach that case at depth 6 or 7, but the play did — the two repetitions that
spoiled `kqk-12` and `krk-17` no longer occur. The engine's search behaviour is
now *not* bit-identical to dev2's in positions with null-move pruning and history
ordering; the benchmark signatures are identical, and the regression match below
was replayed after the fix.

The pre-review failures were not crashes: in both the winning side allowed a
**second** repetition, which lets the defender claim the third, and a repetition
is only scored as a draw once it is claimable, so from a distance the shuffle
looks free. After the null-move fix neither occurs, but the underlying weakness —
a search with no fifty-move or progress term can still walk into a claim in a
position it cannot yet see is drawn — is unchanged, and it is why the suite also
records the termination of every game rather than only the score.

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
  fewer legal moves than requested, return to single-PV output), and
  **`EvalParams`** (a candidate file whose path contains spaces, an unreadable
  file reported and ignored, and a reset that provably restores the shipped
  evaluation).
* `uci_fuzz` — 300 seeded malformed inputs and cancellations, unchanged.

Everything the engine advertises it implements; pondering, Chess960 and threads
are neither implemented nor advertised.

## Environment and reproducibility

* Linux x86-64, 2 vCPU, GCC 12.2.0, CMake 3.25.
* `python3` with `chess==1.11.2`; the engine itself needs neither.
* Every match file records the exact command line, seed, opening suite, node
  budget, hash size and thread count in its `config` object.

## Review record

CodeRabbit's first pass reported the pull request as skipped, so the review was
triggered explicitly on `21d0d46`. It then produced a real review of that commit
(20 inline findings, 3 major / 17 minor) and the commit after this one addresses
them. What changed as a result:

| finding | severity | resolution |
| --- | --- | --- |
| null move left a stale previous move in the ordering context | minor, correctness | fixed; endgame suite went 22/24 → 24/24, bench signatures unchanged |
| `EvalParams` reset reported success without restoring the table | major, correctness | fixed, plus a black-box test that compares the score before and after |
| `EvalParams` rejected paths containing spaces | minor | fixed, with a test using a directory whose name contains a space |
| parameter-file parser could not read the `Name = mg eg` form it advertised | minor | fixed, both forms unit-tested |
| `120junk` parsed as 120 | minor | fixed, five malformed inputs unit-tested |
| `bench --params ""` silently benchmarked the default evaluation | minor | fixed, now an error |
| oracle could certify a mate while a defensive reply was unproven | major, correctness | fixed; a negative score now requires every reply to be proven |
| oracle did not advance the mate distance per ply | minor, correctness | fixed |
| suite runner could block forever in `readline()` | major, stability | fixed with a reader thread and a real deadline |
| suite runner recorded an illegal endgame move twice | minor | fixed |
| tuner ignored its own sign-preserving bounds | minor | fixed |
| tuner stopped at the first unchanged coarse sweep | major | fixed; the variant D record was regenerated |
| matches did not record what each engine was set to | major, evidence | fixed; both matches replayed with explicit switches |
| report links, stale suite manifest hash, candidate-A `K` and coefficients, pair-outcome wording | minor | fixed |
| bench signature described as proof of unchanged search | minor | corrected to a suite-level statement, with the endgame counter-example added |

The finding that the suite records identified `StockBear 0.1.0-dev2` was real and
was resolved the expensive way: both suites were re-run from the reviewed build
rather than relabelled, and the records now name `StockBear 0.1.0-dev3` with the
binary hash `e96cb712…`. The endgame suite's 22/24 in that record was a genuine
bug, not a flaky result, which is the clearest argument for keeping raw records
with the engine identity inside them.

A second pass reviewed `a6a32f1` and raised seven findings, all minor-except-one
and none of them new defects:

* three (the `EvalParams` reset, the null-move ordering slot, `bench --params ""`)
  pointed at hunks that were already fixed in `e063209`–`a4c27a7`; the reviewer was
  reading an older patch region. Verified against the code rather than accepted on
  its word;
* three (the paired-score label, the per-match pair counts, multiword option
  defaults in `tournament.py`) were fixed in `a6a32f1`, the very commit under
  review;
* one was real and still stood: the tuning page said "all three candidates" and
  listed three report files while the table below it and the directory on disk have
  four. Fixed after the review, along with the manifest keys written by the suite
  generator, which disagreed with the committed manifest.

Both passes reviewed real commits and both findings lists were checked against the
code before being believed. No human review is claimed. Kilo Code and Qodo
were out of credits and ChatGPT Codex was over its review quota for this
repository during the session, so those services did not review this change;
CodeRabbit's first attempt on the final commit was rate limited and the review was
requested again later, and only the completed run is counted.

## Known limitations

* **Endgame conversion is node-budget sensitive.** With the null-move ordering
  fix in place all 24 three-man endgames convert at 400 k nodes, but the margin is
  the budget, not a fortress: at 200 k two of them still fail and at 20 k ten do.
  A tablebase or a fifty-move/progress term would remove the sensitivity; neither
  is in this release because neither was validated here.
* **No Stockfish 19 measurement.** See above.
* **The evaluation did not improve.** The tuning pipeline works and is
  reproducible, but its candidates lost their matches; see
  [TUNING.md](../../../docs/TUNING.md).
* **Node-limited matches.** All matches use a fixed node budget per move, so they
  measure strength per node, not per second. The all-on search configuration costs
  8 % more time at equal depth, which a time control would expose; that is part of
  why it is not the default.
* **Single thread, ordinary hardware.** No SMP, no tablebases, no opening book,
  no NNUE, and no claim beyond the recorded matches.
