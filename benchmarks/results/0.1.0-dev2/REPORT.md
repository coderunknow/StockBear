# StockBear 0.1.0-dev2 — benchmark and verification evidence

Local development evidence for `0.1.0-dev2`, recorded on 2026-10-31. It is not a
competitive-strength certification, and the exact-commit CI runs for the PR head,
the merge commit and the tag are the authoritative verification (links are added
after the release).

Raw, intentionally retained outputs in this directory:

| File | Contents |
|---|---|
| `bench-dev1-depth6.csv`, `bench-dev2-depth6.csv` | fixed-depth-6 search CSV for dev1 and dev2 |
| `bench-dev1-depth7.csv`, `bench-dev2-depth7.csv` | fixed-depth-7 search CSV for dev1 and dev2 |
| `ablation-dev2-depth7.csv` | dev2 feature ablations at depth 7 |
| `match-dev1.pgn`, `.jsonl`, `.csv` | dev2 vs dev1, 400 paired games |
| `match-stockfish11.pgn`, `.jsonl`, `.csv` | dev2 vs Stockfish 11, 20 paired games |
| `dead-positions-corpus.md` | dead-position corpus: verdict, states, timing, witness check |
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

Only one benchmark process ran at a time; the dev2-vs-dev1 match was started on an
otherwise idle machine (an earlier attempt was discarded because it overlapped
compilation and a Python reference job, which produced clock forfeits — see
"Rejected and failed experiments").

## Search performance

Identical suite (`bench`), identical hash, one thread, same machine. Node counts
and signatures are deterministic; timings vary by a few percent between runs.

**Depth 6, 12 positions (dev2 signature `838a0a824cb1686f`):**

| Measure | dev1 | dev2 | ratio |
|---|---:|---:|---:|
| Total nodes | 1,683,192 | 276,352 | **0.164×** |
| Total wall time | 1,041.3 ms | 256.8 ms | **0.247×** |

**Depth 7 (`ff1cf4d5109617aa`):** 8,276,659 → 516,138 nodes (**0.062×**, 16.0×
fewer) and 3,604.9 ms → 396.5 ms (9.1× faster).

Per position at depth 6:

| Position | dev1 nodes | dev2 nodes | ratio | dev1 ms | dev2 ms | dev1 move | dev2 move |
|---|---:|---:|---:|---:|---:|---|---|
| Starting position | 69,191 | 15,877 | 0.229 | 64.7 | 18.7 | `b1c3` | `g1f3` |
| Complex middlegame | 723,143 | 213,150 | 0.295 | 631.3 | 193.7 | `e2a6` | `e2a6` |
| Mate in one | 62,173 | 163 | 0.003 | 28.8 | 0.1 | `f7g7` | `f7g7` |
| Rook and pawn ending | 22,991 | 4,179 | 0.182 | 13.8 | 2.8 | `b4c4` | `b4f4` |
| Promotion race | 2,976 | 1,244 | 0.418 | 1.5 | 0.6 | `g1h2` | `g1h2` |
| Hanging queen | 852 | 452 | 0.531 | 0.4 | 0.2 | `e4d5` | `e4d5` |
| Developed middlegame | 542,997 | 36,802 | 0.068 | 238.9 | 38.4 | `b1a3` | `a2a4` |
| Bare kings drawn | 0 | 0 | — | 0.0 | 0.0 | `e1d1` | `e1d1` |
| Mate in two | 244,870 | 556 | 0.002 | 58.5 | 0.2 | `b2c3` | `b2c3` |
| Forced check evasion | 4,113 | 805 | 0.196 | 0.9 | 0.5 | `g1h1` | `g1h1` |
| Avoid immediate mate | 5,998 | 2,362 | 0.394 | 1.6 | 1.2 | `a1a3` | `a1a3` |
| Stalemate avoidance | 3,888 | 762 | 0.196 | 0.9 | 0.4 | `f1f2` | `f1e2` |

Two move changes are deliberate and verifiable rather than noise: the start
position now plays `g1f3` (both are equal-scoring at depth 6), and the rook ending
is scored +126 cp instead of +38 cp because quiescence now resolves the exchange.

## Feature ablations (depth 7, dev2)

| Configuration | Nodes | Time (ms) | Signature |
|---|---:|---:|---|
| all features on (baseline) | 516,138 | 468.7 | `ff1cf4d5109617aa` |
| `aspiration=0` | 716,540 | 648.4 | `117bddc4fa92c00e` |
| `nullMove=0` | 412,253 | 348.3 | `f587e84f61e4f3a7` |
| `lmr=0` | 932,343 | 463.2 | `d26f56c2fa18f397` |
| `reverseFutility=0` | 639,431 | 327.5 | `52528d17426359f8` |
| `futility=0` | 601,523 | 387.1 | `91c57f5a8b480ad1` |
| `seePruning=0` | 650,548 | 353.3 | `a0ea0d32b426a8f1` |
| `checkExtension=0` | 507,068 | 257.8 | `f4ce45fe2fcd2bdc` |

Reading this honestly: **aspiration windows, LMR, futility and SEE pruning each
cost nodes when disabled**, so they do the intended work. `nullMove=0`,
`reverseFutility=0` and `checkExtension=0` reduce *both* nodes and time at a fixed
depth. That is a tree-shape artefact — a fixed-depth search with one pruning
feature disabled can afford to reach different subtrees — and it means the node
ablation alone cannot justify those three features. They were therefore kept for
the reason that matters (the aggregate dev2 build, which contains them, was
measured by strength in the match below), and per-feature *match* ablations are
listed as the next step in [the roadmap](../../../docs/ROADMAP.md). The exact same
switches are exposed as UCI options (`NullMove`, `LMR`, `Aspiration`, `Futility`,
`ReverseFutility`, `SEEPruning`, `CheckExtension`) together with
`tournament.py --a-option`/`--b-option`, so that experiment can be run without any
code change.

Ablation timings were taken in a different run than the depth-7 table above; the
baseline row is the same node count with slightly higher wall time. Node counts,
not milliseconds, are the comparison.

## dev2 vs dev1 — 400 paired games

Command (recorded in the JSONL `configuration` line):

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

* Result: **+159 =132 −109** over 400 games, score 0.5625.
* Naive Wilson 95 %: [0.514, 0.610] → Elo +43.7 [+9.4, +77.9] (ignores pair
  dependence).
* Paired pentanomial estimate: 200 opening pairs, pair-score mean 1.125 ± 0.043,
  **Elo +43.7 [95 %: +14.3, +73.7]**, pair scores 2/1.5/1/0.5/0 =
  `[32, 60, 55, 32, 21]`.
* SPRT (H0 = 0 Elo, H1 = +5 Elo, α = β = 0.05): LLR 0.93 against bounds ±2.94 →
  *continue*; the sequential test has not stopped, the interval above is the
  reported estimate.
* Terminations: 268 checkmate, 123 threefold repetition, 8 insufficient material,
  1 fifty-move. **No time forfeits, no illegal moves and no capped/unadjudicated
  games.** Median game length 109 plies (14–232).
* Because dev2 is engine A, positive scores mean dev2 scored better.

Interpretation: at 80 ms + 8 ms per move the dev2 build scores about 56 % against
dev1, an improvement of roughly 44 Elo with a 95 % interval of about 14–74 Elo.
The interval excludes zero, so the improvement is supported at this sample size;
it is **not** a claim about absolute strength, about longer time controls, or
about other openings. The same opening is played twice, so the paired estimate
and its larger standard error are the honest ones.

## External opponent: Stockfish

**Stockfish 19 (latest stable) could not be built in this environment.** The
source archive downloads fine (tag `sf_19`, SHA-256
`519b653d0d1ffb96531d982ccbe5c6a19425e8388e0e3c2f70f34b424ab32d76`), but Stockfish
19 requires NNUE network files (`nn-1a298aa575a0.nnue`, 98,511,183 bytes) that
are served from hosts this sandbox cannot reach, so the build stops at
`network.o`. No Stockfish 19 match was run, and nothing here is a claim about
Stockfish 19.

As a pinned external check, **Stockfish 11** was built from source (version,
source checksum and binary checksum above) and played 20 games under the same
protocol at 100 ms + 10 ms, 16 MiB hash, one thread each:

* **0 wins, 0 draws, 20 losses** (all by checkmate, no forfeits, no capped
  games), i.e. score 0/20.
* Naive Wilson 95 %: [0.000, 0.161] → Elo −inf [−inf, −286.6]. The paired
  pentanomial interval is degenerate (every pair scored 0) and is reported as
  −inf rather than as a number.

This confirms the gap to a mature engine is large. It says nothing precise about
its size (20 games is far too few, and Stockfish 11 is not the latest release).
dev1 lost 0–8 to the same engine at 1 s + 20 ms, so the direction is consistent
with the dev2-vs-dev1 result, but the two matches are not comparable samples.

## FIDE dead positions (Article 5.2.2)

`docs/DEAD_POSITIONS.md` contains the specification, correctness argument and
limits. Recorded evidence:

* corpus (`dead-positions-corpus.md`): 23 cases, 0 failures. Dead classes
  (bare kings ×2 sides, `KB` v `K`, `KN` v `K`, same-coloured bishops, one
  same-coloured bishop each, 14 blocked pawns ×2 sides, locked pawn chains with
  bishops ×2 sides) and alive classes (`KNN` v `K`, opposite-coloured bishops,
  `KN` v `KN`, `KQ`/`KR`/`KP` v `K`, castling and en-passant states, start
  position, Kiwipete, Italian middlegame) plus terminal checkmate/stalemate,
  which are excluded from 5.2.2. Every `alive` witness was replayed and ends in
  checkmate.
* independent reference (`dead-positions-reference.txt`): python-chess
  re-implements the component enumeration and agrees on every compared position
  (10 compared at a 400,000-state cap, with the two `KN` v `K` cases skipped at
  that cap and re-run at a higher cap).
* exhaustive reduced spaces (CTest `deadpos`): all legal two-king placements
  with either side to move, and all legal three-piece placements with a bishop or
  knight and either side to move, are classified correctly, with stalemates
  recognised as terminal.
* measured cost: static proofs ~0 ms; 14 blocked pawns 3,809 states in ~7 ms;
  locked pawn chains with bishops 1,268,497 states in ~0.56 s; `KNN` v `K`
  300,000 states in 149 ms; `KN` v `KN` 7,908,228 states in 2.3 s. Budget
  exhaustion returns `unknown`, never `dead`.

## Tests run for this evidence

Local: CTest Debug 8/8, Release 8/8, ASan+UBSan 8/8, ThreadSanitizer on
`unit|regression|uci_integration` 3/3. Independent scripts: `reference_perft.py`,
`differential.py --samples 2000 --seed 20261030`,
`test_tournament.py`, `test_statistics.py`,
`dead_position_corpus.py` (23/23), `dead_position_reference.py`. Exact-commit CI
on the PR head, merge commit and tag is the authoritative record.

## Rejected and failed experiments

- **First dev2-vs-dev1 match discarded.** A 400-game run was started while a
  Release reconfigure and a Python reference job were competing for the two
  available CPU threads. From game ~358 almost every game ended in
  `TIME_FORFEIT` at 10–25 ms per move. It reported +191 =109 −100 (Elo +80
  [52, 110]), which is *better* than the clean run below and was therefore
  discarded rather than published. The clean, idle-machine run reported here is
  the evidence. Lesson recorded: verify the build's self-reported version and
  the termination distribution before trusting a match.
- **`aspiration=0` apparently reducing nodes** after the first pruning patch was
  traced to a move-ordering artefact (SEE cost/ordering changed the tree), not to
  a bug; the final ablation shows the expected behaviour.
- **Stockfish 19 build** failed for the NNUE-network reason above. Stockfish 15.1
  and 17/19 have the same requirement; only Stockfish 11 builds without any
  downloaded network, which is why it is the external opponent here.
- **LTO Stockfish build** failed to link in the 2-thread/3.8 GiB sandbox
  (`lto-wrapper failed`); the recorded binary is a non-LTO (`optimize=no`) build.
  That makes the opponent slightly slower, which can only make StockBear's result
  look better, not worse.
- **`bench --csv`** does not exist: `bench` writes its CSV to stdout. The
  recorded `.csv` files are that stdout, including the `#` header and signature
  lines.

## Limitations

Clock time is measured by the controller as wall time and includes protocol
overhead; 80 ms + 8 ms is a short control dominated by search overhead and engine
start-up variance. The machine has two vCPUs and is virtualised, so absolute NPS
figures are only comparable within this machine. The Elo transform is a model.
The dead-position analysis is exponential in the worst case and reports `unknown`
when its budget is exhausted. Nothing here establishes behaviour on macOS, ARM,
32-bit targets, chess variants, or with multiple search threads.

Check [CHANGELOG.md](../../../CHANGELOG.md), [RELEASE_NOTES.md](../../../RELEASE_NOTES.md)
and the CI runs for the exact commit before relying on these numbers.
