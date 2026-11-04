# exp-0041 — losing-capture pruning at ALL remaining depths: CLOSED / ABANDONED

Frozen registration: `docs/DEV6_PREREG_EXP0041.md`, SHA-256
`2f5c1b08ebd991f84e570b90afd48adcc7694f5d355beda492e1b6b18d98d392`
(committed BEFORE any evaluation game, in the same commit as the dispatch).

## Identity / provenance (Gate 4 linkage for this experiment)
| item | value |
|---|---|
| exact source SHA | `87f82854db525da05c5bc5bcc746dd4cf7014698` |
| build flags | `-mpopcnt -mbmi2 -mlzcnt -DSB_SEE_CACHE=1 -flto=4` |
| built == packaged == tested binary SHA-256 | `cd647fa0fd5a6fe2d4fd0a46b88bf9365ecd7101228d122a31f8ccd39bb11a56` |
| immutable dev5 baseline SHA-256 | `391cb50e13ab99168aba0255482554ab5e59d1a34af810bf8f4d2c88e5bdb918` |
| frozen prereg SHA-256 | `2f5c1b08ebd991f84e570b90afd48adcc7694f5d355beda492e1b6b18d98d392` |
| Tier-1 benchmark run | `41782954038` (4 isolated `ubuntu-latest` VMs, all SUCCESS) |
| Tier-1 export run | `41784088471` (SUCCESS, `[skip ci]` evidence commit) |
| CI against exact candidate source | `41782954037` on `87f8285`, SUCCESS |
| artifact IDs / bytes | `13300765132`/939928 B, `13300325887`/733418 B, `13300296352`/736939 B, `13300132017`/944410 B |
| local checksum re-verification | 4/4 `SHA256SUMS.txt`, **0 failures** |
| control | **FIXED TIME 40+4 ms**, Hash 16, Threads 1, max-plies 240, **no `--nodes`** |

ONE binary, single scope switch: candidate
`BadCapturePruning=true, BadCaptureAllDepths=true` versus the validated
exp-0036 control `BadCapturePruning=true`. Both arms receive identical 40+4 ms
clocks, `EvalParams=research-data/params_abc.txt` and `TTEval=true`; there is
no toolchain, time-allocation or condition difference. Raw PGN / JSONL / CSV /
summaries / audit.txt / fingerprint / manifest / SHA256SUMS / UCI probe /
run.log and the exact packaged `.tar.gz` are mirrored at `benchmarks/exp-runs/tier1-export/run-41782954038/`.

## Frozen Stage-0 validity gate — PASS
Control-vs-control self-match, 399 adjudicated games,
`6.9846 [-11.4958, 25.5046]`
Elo, CI includes 0, **0 TIME_FORFEIT, 0 illegal moves, 0 engine/UCI failures**.
The isolated-VM 40+4 ms measurement is valid.

## Results (CR1/t, opening-clustered two-sided 95 % CI)
| arm | games | W/D/L | score | Elo | 95 % CI |
|---|---|---|---|---|---|
| batchA | 998 | 346/313/339 | 0.503507 | +2.4419 | [-11.4054, 16.2969] |
| batchB | 997 | 322/316/359 | 0.481444 | -12.5887 | [-27.3582, 2.1355] |
| null (candidate vs candidate) | 398 | 135/128/135 | 0.500000 | -1.7547 | [-20.3714, 16.8518] |
| **frozen combined A+B** | **1995** | **668/629/698** | **0.4924812** | **-5.0635** | **[-15.1810, 5.0454]** |

995 opening clusters; null CI includes 0; 0 forfeits / illegal /
UCI failures; unadjudicated games excluded by the pre-existing
`score_a=null` rule. Paired pentanomial and LLR labelled a normal
approximation; no batch selection, no post-hoc combination, no threshold
change after results.

## Independent recomputation — AUDIT PASS
`scripts/dev6_exp0038_audit.py 41782954038 exp0041 20 10` re-parsed all four
raw `match.jsonl` files from scratch and verified **44 stored values** with
**0 issues, AUDIT PASS**. The frozen thresholds (ADVANCE point >= +20 and
LCB > 0, both batches >= −5, null present, clean correctness; CLOSE UCB < +10
or point <= 0) were passed as explicit arguments taken verbatim from
`docs/DEV6_PREREG_EXP0041.md` §5 BEFORE any result was read. Independent
Elo-from-score `-5.2250` vs stored CR1
`-5.0635`; independently coded seeded opening-cluster bootstrap
(20,000 resamples, seed 2026112501) `[-15.0242,
5.0635]`, in close agreement with CR1/t.
Machine-readable output:
`benchmarks/dev6-baseline/exp0041_independent_audit.json`.

## Frozen decision — CLOSE (scope extension rejected)
ADVANCE requires combined point >= +20 AND LCB > 0 AND both batches >= −5 AND
null including 0 AND clean correctness. `point -5.0635 >= +20` is
**FALSE**, `LCB -15.1810 > 0` is **FALSE**, and batchB
`-12.5887 >= −5` is **FALSE** -> no ADVANCE. CLOSE rule:
UCB `5.0454 < +10` is **TRUE** AND point <= 0 is **TRUE** ->
**CLOSED, ABANDONED, not retuned**. `BadCaptureAllDepths` stays default OFF;
`BadCaptureMargin=100` remains frozen.

## Root-cause classification and diagnosis
Class: **unsuitable hypothesis / search-eval interaction**, not an
implementation defect. Release ctest 11/11, ASan+UBSan ctest 11/11, exact
default-off bench/d16/d12 signatures, 3x determinism, 0 illegal/forfeit/UCI
failures. Pre-result profiling proved the mechanism was LIVE (`go depth 12`
startpos: 757,239 -> 438,131 nodes, −42.1 %), yet the fixed-time result is
slightly negative. A capture with SEE < −100 is apparently often a sound deep
sacrifice, a necessary interposition, or a move whose removal destabilises
ordering; pruning it higher in the tree loses more tactical accuracy than the
extra depth buys. This reproduces the project's recorded warning that fixed-
node/throughput proxies are MISLEADING for strength: portable flags gave
+12–20 % NPS but only `+3.6 [−19.6,+26.9]` Elo, and qlite gave +23 % NPS but
`−32.1 [−55.8,−8.6]` Elo. No fixed-depth node count is presented as
fixed-time strength.

## Gate verdict (unchanged, `docs/DEV6_PREREG.md` §8 not weakened)
- **Gate 1 UNMET** — no >= +75 Elo point with two-sided opening-clustered
  LCB > +50 on two independent preregistered FIXED-TIME batches.
- **Gate 2 direction-supported**, **Gate 3 PASS**.
- **Gate 4 UNMET for a final candidate** — every experiment's own packaged
  artifact/binary/CI linkage is complete and verified, but no final candidate
  release artifact exists.
- **Mission ACTIVE.** No strength claim, no PR/merge/tag/release/deploy/dev7.
