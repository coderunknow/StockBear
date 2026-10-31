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
Node counts and signatures are deterministic; timings vary by a few percent.

**Depth 6, 12 positions (dev2 signature `733440501ed37d3d`):**

| Measure | dev1 | dev2 | ratio |
|---|---:|---:|---:|
| Total nodes | 1,683,192 | 106,558 | **0.063×** (15.8× fewer) |
| Total wall time | 1,041.3 ms | 52.3 ms | **0.050×** (19.9× faster) |

**Depth 7 (`4e96e77c6c849463`):** 8,276,659 → 252,556 nodes (**0.031×**, 32.8×
fewer) and 3,604.9 ms → 121.7 ms (29.6× faster).

Per position at depth 6:

| Position | dev1 nodes | dev2 nodes | ratio | dev1 ms | dev2 ms | dev1 move | dev2 move | dev1 score | dev2 score |
|---|---:|---:|---:|---:|---:|---|---|---:|---:|
| Starting position | 69,191 | 12,539 | 0.181 | 64.7 | 6.2 | `b1c3` | `d2d4` | 0 | 0 |
| Complex middlegame | 723,143 | 63,542 | 0.088 | 631.3 | 32.2 | `e2a6` | `e2a6` | +7 | +7 |
| Mate in one | 62,173 | 163 | 0.003 | 28.8 | 0.0 | `f7g7` | `f7g7` | mate 1 | mate 1 |
| Rook and pawn ending | 22,991 | 3,823 | 0.166 | 13.8 | 1.4 | `b4c4` | `b4f4` | +38 | +126 |
| Promotion race | 2,976 | 1,244 | 0.418 | 1.5 | 0.3 | `g1h2` | `g1h2` | +998 | +998 |
| Hanging queen | 852 | 452 | 0.531 | 0.4 | 0.2 | `e4d5` | `e4d5` | 0 | 0 |
| Developed middlegame | 542,997 | 20,310 | 0.037 | 238.9 | 10.8 | `b1a3` | `b1a3` | +441 | +457 |
| Bare kings drawn | 0 | 0 | — | 0.0 | 0.0 | `e1d1` | `e1d1` | 0 | 0 |
| Mate in two | 244,870 | 556 | 0.002 | 58.5 | 0.1 | `b2c3` | `b2c3` | mate 2 | mate 2 |
| Forced check evasion | 4,113 | 805 | 0.196 | 0.9 | 0.3 | `g1h1` | `g1h1` | mate −3 | mate −3 |
| Avoid immediate mate | 5,998 | 2,362 | 0.394 | 1.6 | 0.6 | `a1a3` | `a1a3` | −1017 | −1011 |
| Stalemate avoidance | 3,888 | 762 | 0.196 | 0.9 | 0.2 | `f1f2` | `f1e2` | mate 3 | +1033 |

The two changed moves are equal-scoring alternatives at this depth (start
position: `d2d4` and `b1c3` both 0 cp; stalemate avoidance: dev2 finds a
non-mating but winning capture). Tactical results are unchanged: both builds find
the mate-in-one, the mate-in-two, the forced evasion and the promotion.

## Feature ablations (depth 7, dev2)

| Configuration | Nodes | Time (ms) | Signature |
|---|---:|---:|---|
| all features on (baseline) | 252,556 | 119.7 | `4e96e77c6c849463` |
| `aspiration=0` | 331,215 | 152.7 | `c372ce4355e0fd02` |
| `nullMove=0` | 231,094 | 110.9 | `7a98a1a2c3e5ddf9` |
| `lmr=0` | 466,352 | 221.3 | `bea0c8645b4457ea` |
| `reverseFutility=0` | 351,275 | 191.3 | `f6f7e99bd82b63e4` |
| `futility=0` | 329,343 | 139.7 | `f02b4259e6eaf791` |
| `seePruning=0` | 650,548 | 262.6 | `a0ea0d32b426a8f1` |
| `checkExtension=0` | 213,373 | 97.5 | `7132842d4634dc15` |

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

* Result: **+250 =103 −47** over 400 games, score 0.7538.
* Naive Wilson 95 %: [0.709, 0.793] → Elo +194.3 [+154.9, +233.8] (ignores pair
  dependence).
* Paired pentanomial estimate: 200 opening pairs, pair-score mean 1.5075 ± 0.0339,
  **Elo +194.3 [95 %: +164.5, +227.0]**, pair scores 2/1.5/1/0.5/0 =
  `[76, 66, 45, 11, 2]`.
* SPRT (H0 = 0 Elo, H1 = +5 Elo, α = β = 0.05): LLR 6.26 > 2.94 → **accept H1**.
* Terminations: 297 checkmate, 94 threefold repetition, 8 insufficient material,
  1 fifty-move. **No time forfeits, no illegal moves, no capped/unadjudicated
  games.** Median game length 106 plies (24–268).
* dev2 is engine A, so positive scores favour dev2.

Interpretation: at 80 ms + 8 ms per move the dev2 build scores 75 % against dev1,
about **+194 Elo with a 95 % interval of +165 to +227**, and the sequential test
stops for H1 at this sample size. The improvement is much larger than the earlier
draft measurement because it includes the static-exchange-evaluation fix found in
review (see below); the discarded earlier figure (+44 Elo) came from a build whose
SEE dropped the final recapture and therefore treated losing captures as winning.
This is a statement about dev1 at this time control, not about absolute strength
or about other engines.

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
* The SPRT's H0 (0 Elo) is accepted, i.e. the data exclude "dev2 is equal to
  Stockfish 11".

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
  14 blocked pawns 768 / 3,809 in ~7 ms; locked pawn chains with bishops
  152,352 / 1,268,497 in 0.58–0.75 s; `KNN` v `K` 100,745 / 300,000 in 148 ms;
  `KN` v `KN` 1,194,884 / 7,908,228 in 2.5 s. Budget exhaustion returns `unknown`,
  never `dead`; the default 3,000,000-expansion budget peaks at 85–105 MiB.

## Tests run for this evidence

Local, on the committed head: CTest Release 9/9, Debug 9/9, ASan+UBSan 9/9,
ThreadSanitizer 4/4 (`unit|position_extra|regression|uci_integration`).
Independent scripts: `reference_perft.py` (9 positions),
`differential.py --samples 2000 --seed 20261030` (exact move sets and per-move
depth-2 counts, 2,000 generated + 8 curated positions), `test_tournament.py`,
`test_statistics.py` (8 known-value tests), `dead_position_corpus.py` (23/23) and
`dead_position_reference.py --full` (10 compared, 2 skipped, 0 failures).
Exact-commit CI on the PR head, merge commit and tag is the authoritative record.

## Rejected and failed experiments

- **A 400-game run was discarded.** It started while a Release reconfigure and a
  Python reference job competed for the two CPU threads; from game ~358 almost
  every game ended in `TIME_FORFEIT` at 10–25 ms per move and reported
  +191 =109 −100. Contaminated runs were discarded rather than published. Lesson:
  verify the engines' self-reported identity and the termination distribution
  before trusting a match.
- **The first SEE implementation was wrong and the first match measured it.**
  Review found that the exchange fold dropped the final recapture, so a knight
  taking a defended pawn returned +100 instead of −220. Fixed, covered by
  known-value tests, and every measurement in this report was re-run afterwards.
  The pre-fix 400-game result (+159 =132 −109, +43.7 Elo) was discarded because it
  described a build that could not be released.
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
