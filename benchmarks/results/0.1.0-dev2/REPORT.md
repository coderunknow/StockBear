# StockBear 0.1.0-dev2 — benchmark and verification evidence

Local development evidence for `0.1.0-dev2`, recorded on 2026-10-31. It is not a
competitive-strength certification; the exact-commit CI runs for the PR head, the
merge commit and the tag are the authoritative verification (links are recorded in
the PR and release).

Raw, intentionally retained outputs in this directory:

| File | Contents |
|---|---|
| `bench-dev1-depth6.csv`, `bench-dev2-depth6.csv` | fixed-depth-6 search CSV for dev1 and dev2 |
| `bench-dev1-depth7.csv`, `bench-dev2-depth7.csv` | fixed-depth-7 search CSV for dev1 and dev2 |
| `ablation-dev2-depth7.csv` | dev2 feature ablations at depth 7 |
| `match-dev1.pgn`, `.jsonl`, `.csv` | dev2 vs dev1, 400 paired games |
| `match-stockfish11.pgn`, `.jsonl`, `.csv` | dev2 vs Stockfish 11, 20 paired games |
| `dead-positions-corpus.md` | dead-position corpus: verdict, distinct states, expansions, timing, witness check |
| `dead-positions-reference.txt` | independent python-chess comparison of the same verdicts |

## Environment

- Linux x86-64 (Debian 12 base image), kernel 6.1.158+, glibc 2.36; virtualised
  Intel Xeon @ 2.60 GHz, **2 visible CPU threads**, ~3.8 GiB RAM. One search
  thread everywhere.
- StockBear dev2: GCC 12.2.0, CMake Release, `-std=c++17 -O3 -Wall -Wextra
  -Wshadow -Wpedantic`, no `-march=native`. Linux binary statically links
  libstdc++/libgcc, glibc dynamic. Hash requested 16 MiB.
- dev1 baseline: `/home/user/artifacts/stockbear-dev1`, the released dev1 binary
  (self-reports `StockBear 0.1.0-dev1`).
- Adjudicator/reference: python-chess 1.11.2.
- External opponent: Stockfish 11 (`sf_11` source, SHA-256
  `802261cc601b67bed00c0ef7d21e2125959630f0852a06db9fc9bd74f440b199`), built with
  `make build ARCH=x86-64-bmi2 COMP=gcc`, binary SHA-256
  `700613c69279b5697d29344b139e4999c7a5652319cf22012bc577cdb91bbb6c`.

Only one benchmark or match process ran at a time, on an otherwise idle machine
(an earlier attempt that overlapped compilation was discarded; see "Rejected and
failed experiments").

## Search performance

Identical embedded suite (`bench`), identical hash, one thread, same machine.
Node counts and signatures are deterministic; timings vary with machine load, so
the two engines were run alternately in the same session (three passes each) and
the committed CSVs are the last pass of that alternation. An earlier draft quoted
a dev1 timing measured while the machine was compiling, which inflated the speed
ratio; the numbers below are the matched ones.

**Depth 6, 12 positions (dev2 signature `e06c4352681ae8eb`):**

| Measure | dev1 | dev2 | ratio |
|---|---:|---:|---:|
| Total nodes | 1,683,192 | 108,910 | **0.065×** (15.5× fewer) |
| Total search time | 622.1 ms | 48.6 ms | **0.078×** (12.8× faster) |

**Depth 7 (`5bceff035f2a4ae4`):** 8,276,659 → 250,053 nodes (**0.030×**, 33.1×
fewer) and 2,896.0 ms → 125.3 ms (**0.043×**, 23.1× faster).

Per position at depth 6:

| Position | dev1 nodes | dev2 nodes | ratio | dev1 ms | dev2 ms | dev1 move | dev2 move | dev1 score | dev2 score |
|---|---:|---:|---:|---:|---:|---|---|---:|---:|
| Starting position | 69,191 | 12,539 | 0.181 | 26.9 | 5.4 | `b1c3` | `d2d4` | 0 | 0 |
| Complex middlegame | 723,143 | 64,442 | 0.089 | 291.9 | 30.1 | `e2a6` | `e2a6` | +7 | +7 |
| Mate in one | 62,173 | 163 | 0.003 | 12.8 | 0.0 | `f7g7` | `f7g7` | mate 1 | mate 1 |
| Rook and pawn ending | 22,991 | 5,275 | 0.229 | 6.5 | 1.7 | `b4c4` | `b4c4` | +38 | +41 |
| Promotion race | 2,976 | 1,244 | 0.418 | 0.7 | 0.3 | `g1h2` | `g1h2` | +998 | +998 |
| Hanging queen | 852 | 452 | 0.531 | 0.2 | 0.1 | `e4d5` | `e4d5` | 0 | 0 |
| Developed middlegame | 542,997 | 20,310 | 0.037 | 226.0 | 9.8 | `b1a3` | `b1a3` | +441 | +457 |
| Bare kings drawn | 0 | 0 | — | 0.0 | 0.0 | `e1d1` | `e1d1` | 0 | 0 |
| Mate in two | 244,870 | 556 | 0.002 | 53.8 | 0.1 | `b2c3` | `b2c3` | mate 2 | mate 2 |
| Forced check evasion | 4,113 | 805 | 0.196 | 0.9 | 0.2 | `g1h1` | `g1h1` | mate -3 | mate -3 |
| Avoid immediate mate | 5,998 | 2,362 | 0.394 | 1.6 | 0.5 | `a1a3` | `a1a3` | -1017 | -1011 |
| Stalemate avoidance | 3,888 | 762 | 0.196 | 0.9 | 0.2 | `f1f2` | `f1e2` | mate 3 | +1033 |

Three positions changed their chosen move, and they are not all equivalent.

* Starting position: `d2d4` and `b1c3` are equal-scoring alternatives at this
  depth (both 0 cp).
* Rook and pawn ending: both builds choose the same move, `b4c4`, and the score
  differs only slightly (+38 versus +41).
* Stalemate avoidance (`8/1P6/8/8/8/8/8/5K1k w - - 0 1`): dev1 announces mate in
  3 at depth 6, dev2 plays `f1e2` with `+1033`. Re-searching that position at
  depth 12 shows both builds agree on `f1f2 h1h2 b7b8q h2h1 b8h8`, mate in 3, so
  the mate is real and this is a shallower search at depth 6, not a rules or
  evaluation defect. It is reported as a difference rather than as parity.

Tactical results are unchanged where they are verified: both builds find the
mate-in-one, the mate-in-two, the forced evasion and the promotion.

## Feature ablations (depth 7, dev2)

| Configuration | Nodes | Time (ms) | Signature |
|---|---:|---:|---|
| all features on (baseline) | 250,053 | 110.0 | `5bceff035f2a4ae4` |
| `aspiration=0` | 367,761 | 164.5 | `3c18011ef06ed16c` |
| `nullMove=0` | 227,376 | 108.1 | `8709493fb370ebcc` |
| `lmr=0` | 463,963 | 215.2 | `e75fc23609899ce1` |
| `reverseFutility=0` | 352,246 | 194.7 | `407aaa48b99eba34` |
| `futility=0` | 326,199 | 149.7 | `da6f376a7704de87` |
| `seePruning=0` | 650,548 | 248.6 | `a0ea0d32b426a8f1` |
| `checkExtension=0` | 217,620 | 101.4 | `cac9faedd0b1cdc1` |

Reading this honestly: disabling **aspiration windows, LMR, reverse futility,
futility or SEE pruning** increases both nodes and time, so those features do the
intended work on this suite. Disabling **null move** or the **check extension**
*reduces* nodes and time at a fixed depth — a tree-shape artefact, since a
fixed-depth search with one feature removed enumerates different subtrees. Node
ablation therefore cannot justify those two features; they are justified only as
part of the aggregate build, which is measured by strength in the match below, and
per-feature match ablations are the next step in
[the roadmap](../../../docs/ROADMAP.md). The same switches are UCI options
(`NullMove`, `LMR`, `Aspiration`, `Futility`, `ReverseFutility`, `SEEPruning`,
`CheckExtension`) and `tournament.py --a-option`/`--b-option` runs that experiment
without a code change.

The ablation timings come from a separate run than the depth-7 table above; node
counts are the comparison, not milliseconds.

## dev2 vs dev1 — 400 paired games

Command (also recorded in the JSONL `configuration` line):

```sh
python3 scripts/tournament.py --engine-a ./build/stockbear \
  --engine-b /home/user/artifacts/stockbear-dev1 --games 400 \
  --base-ms 80 --inc-ms 8 --hash 16 --seed 20261031 \
  --pgn benchmarks/results/0.1.0-dev2/match-dev1.pgn \
  --jsonl benchmarks/results/0.1.0-dev2/match-dev1.jsonl \
  --csv benchmarks/results/0.1.0-dev2/match-dev1.csv
```

Both engines: `Hash` 16 MiB, one thread, same clocks, 31 openings in
`benchmarks/positions/openings.txt` shuffled with seed `20261031`, each opening
played twice with colours reversed, `--max-plies 300`. python-chess adjudicated
every game and validated every move.

* Result: **+277 =82 −41** over 400 games, score 0.7950.
* Naive Wilson 95 %: [0.753, 0.832] → Elo +235.4 [+193.4, +277.5] (ignores pair
  dependence).
* Paired pentanomial estimate: 200 opening pairs, pair-score mean 1.59 ± 0.0330,
  **Elo +235.4 [95 %: +202.8, +272.2]**, pair scores 2/1.5/1/0.5/0 =
  `[95, 57, 39, 7, 2]`.
* Opening-clustered estimate (CR1 on the 31 distinct openings, Student-t with 30
  degrees of freedom, `match_stats.opening_clustered`): **Elo +235.4
  [95 %: +193.4, +284.5]**. The suite replays each opening about 6.5 times, so the
  200 pairs are *not* independent; this interval is the headline one because it
  also absorbs the between-opening correlation. The `summary` line of
  `match-dev1.jsonl` was recomputed from the unchanged game records by
  `scripts/recompute_summary.py`, which adds this block without replaying games.
* SPRT (H0 = 0 Elo, H1 = +5 Elo, α = β = 0.05), evaluated after the match on the
  recorded pair scores: LLR 7.69 > 2.94, i.e. the upper bound is crossed. The
  harness did not stop early — it played the full 400 requested games and the LLR
  was computed from the finished sample, so this is an upper-bound crossing, not a
  sequential stopping event.
* Terminations: 318 checkmate, 75 threefold repetition, 6 insufficient material,
  1 fifty-move. **No time forfeits, no illegal moves, no capped/unadjudicated
  games.** Median game length 111 plies (24–256).
* dev2 is engine A, so positive scores favour dev2.

Interpretation: at 80 ms + 8 ms per move the dev2 build scores 79.5 % against dev1,
about **+235 Elo with a 95 % interval of +193 to +285** once opening clustering is
accounted for. Earlier drafts of this match quoted +44 and then +194 Elo; both were
measured on builds with a broken static exchange evaluation (see "Rejected and
failed experiments"), so they described engines that could not be released. This
is a statement about dev1 at this time control, not about absolute strength or
about other engines.

## External opponent: Stockfish

**Stockfish 19 (latest stable) could not be built in this environment.** The
source archive downloads fine (tag `sf_19`, SHA-256
`519b653d0d1ffb96531d982ccbe5c6a19425e8388e0e3c2f70f34b424ab32d76`), but Stockfish
19 requires NNUE network files (`nn-1a298aa575a0.nnue`, 98,511,183 bytes) served
from hosts this sandbox cannot reach, so the build stops at `network.o`. No
Stockfish 19 match was run and nothing here is a claim about Stockfish 19.

As a pinned external check, **Stockfish 11** was built from source (version,
source checksum and binary checksum above) and played 20 games under the same
protocol at 100 ms + 10 ms, 16 MiB hash, one thread each:

* **0 wins, 1 draw, 19 losses** (no forfeits, no capped games), score 0.025.
* Naive Wilson 95 %: [0.003, 0.200] → Elo −636.4 [−1032.5, −240.3].
* Paired pentanomial: 10 pairs, pair scores `[0, 0, 0, 1, 9]`, Elo −636.4 with a
  lower bound that is unbounded (−inf, −439.0); the JSON stores the unbounded end
  as `null`, because `Infinity` is not valid JSON.
* Opening-clustered: 10 openings, Elo −636.4 [−inf, −420.7] (t = 2.262 on 9 df).
* The SPRT's H0 (0 Elo) is accepted over H1 (+5 Elo) and the LLR is −5.51. That
  decision alone does not *prove* equal strength — H0 here is the "not better"
  hypothesis — but the paired and clustered intervals both lie entirely below
  −420 Elo, so the data do exclude equality at this time control.

This confirms the gap to a mature engine is large; 20 games cannot size it
precisely, and Stockfish 11 is not the latest release.

## FIDE dead positions (Article 5.2.2)

`docs/DEAD_POSITIONS.md` holds the specification, correctness argument and
limits. Recorded evidence:

* corpus (`dead-positions-corpus.md`): 23 cases, 0 failures. Dead classes (bare
  kings ×2 sides, `KB` v `K`, `KN` v `K`, same-coloured bishops, one
  same-coloured bishop each, 14 blocked pawns ×2 sides, locked pawn chains with
  bishops ×2 sides) and alive classes (`KNN` v `K`, opposite-coloured bishops,
  `KN` v `KN`, `KQ`/`KR`/`KP` v `K`, castling and en-passant states, start
  position, Kiwipete, Italian middlegame) plus terminal checkmate/stalemate, which
  are excluded from 5.2.2. Every `alive` witness was replayed and ends in
  checkmate.
* independent reference (`dead-positions-reference.txt`): python-chess
  re-implements the component enumeration and agrees on all **10** positions it can
  enumerate within a 400,000-state cap — bare kings both sides, `KB` v `K` both
  sides, `KQ` v `K`, `KR` v `K`, a blocked e6/e7 pawn structure both sides (not a
  `KP` v `K` position, despite the pawns) and the 14-blocked-pawn structure both
  sides. The two `KN` v `K` rows print `SKIP` because their component exceeds the
  400,000-state reference cap; StockBear decides them statically, and they are
  covered by the corpus and by the exhaustive three-piece sweep. The reference
  reports 768 distinct states for the blocked-pawn structure, exactly matching
  StockBear's `component_states`.
* exhaustive reduced spaces (CTest `deadpos`): all legal two-king placements with
  either side to move, and all legal three-piece placements with a bishop or
  knight and either side to move, are classified correctly, with stalemates
  recognised as terminal rather than dead.
* measured cost (distinct states / positions expanded): static proofs ~0 ms;
  14 blocked pawns 768 / 3,809 in 5.0–5.3 ms; locked pawn chains with bishops
  152,352 / 1,268,497 in 0.44–0.75 s; `KNN` v `K` 100,745 / 300,000 in 136–145 ms;
  `KN` v `KN` 1,194,884 / 7,908,228 in 1.9–3.3 s; `KB` v `KB` opposite colours
  446,393 / 4,053,677 in 1.1 s; starting position 44,368 / 135,973 in 38 ms. Budget exhaustion returns `unknown`,
  never `dead`; the default 3,000,000-expansion budget peaks at 85–105 MiB.

## Tests run for this evidence

Local, on the committed head: CTest Release 9/9, Debug 9/9, ASan+UBSan 9/9,
ThreadSanitizer 9/9 (the same CTest set compiled with `-fsanitize=thread`).
Independent scripts: `reference_perft.py` (9 positions),
`differential.py --samples 2000 --seed 20261030` (exact move sets and per-move
depth-2 counts, 2,000 generated + 8 curated positions), `test_tournament.py`,
`test_statistics.py` (11 tests), `recompute_summary.py`, `dead_position_corpus.py` (23/23) and
`dead_position_reference.py --full` (10 compared, 2 skipped, 0 failures).
Exact-commit CI on the PR head, merge commit and tag is the authoritative record.

## Rejected and failed experiments

- **A 400-game run was discarded.** It started while a Release reconfigure and a
  Python reference job competed for the two CPU threads; from game ~358 almost
  every game ended in `TIME_FORFEIT` at 10–25 ms per move and reported
  +191 =109 −100. Contaminated runs were discarded rather than published. Lesson:
  verify the engines' self-reported identity and the termination distribution
  before trusting a match.
- **Static exchange evaluation was wrong twice, and matches measured it both
  times.** (1) The negamax fold dropped the final recapture, so a knight taking a
  defended pawn returned +100 instead of −220; fixed and covered by known-value
  tests. (2) The king's exchange value was 0, so SEE believed an illegal king
  recapture was available and turned a won pawn (`d2d7` in
  `4k3/3p4/8/8/8/8/3R4/3R2K1`) into −400; fixed by giving the king a dominant
  value, covered by a known-value test. Two intermediate 400-game results
  (+159 =132 −109, +43.7 Elo, and +250 =103 −47, +194.3 Elo) were superseded by
  the run recorded below because they described builds that could not be
  released. The direction was stable across all of them; the magnitude was not.
- **`aspiration=0` apparently reducing nodes** in an early patch was an ordering
  artefact, not a bug; after the SEE fix the expected direction appears.
- **Stockfish 19 build** failed for the NNUE-network reason above. Stockfish 11 is
  the only recent release that builds here from source without downloaded
  networks, which is why it is the external opponent.
- **LTO Stockfish build** failed to link in the 2-thread / 3.8 GiB sandbox
  (`lto-wrapper failed`); the recorded binary is a non-LTO (`optimize=no`) build.
  That makes the opponent slightly slower, which can only make StockBear's result
  look better, not worse.
- **`bench --csv` does not exist**: `bench` writes its CSV to stdout. The recorded
  `.csv` files are that stdout, including the `#` header and signature lines.

## Limitations

Clock time is measured by the controller as wall time and includes protocol
overhead; 80 ms + 8 ms is a short control dominated by search overhead. The
machine has two vCPUs and is virtualised, so absolute NPS figures are only
comparable within this machine. The Elo transform is a model. The dead-position
analysis is exponential in the worst case and reports `unknown` when its budget is
exhausted. Nothing here establishes behaviour on macOS, ARM, 32-bit targets, chess
variants, or with multiple search threads.

Check [CHANGELOG.md](../../../CHANGELOG.md), [RELEASE_NOTES.md](../../../RELEASE_NOTES.md)
and the CI runs for the exact commit before relying on these numbers.
