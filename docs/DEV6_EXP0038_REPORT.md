# exp-0038 — dedicated qsearch transposition table: CLOSED / ABANDONED

Frozen registration: `docs/DEV6_PREREG_EXP0038.md`, SHA-256
`6161061783d745e10eb5c54017a344d4eb54730778c4f64684b88da3c2cf12dc`
(committed BEFORE any evaluation game, in the same commit as the dispatch).

## Identity / provenance (Gate 4 linkage for this experiment)
| item | value |
|---|---|
| exact source SHA | `2aacf4a643d5066526a33dd1d0f7f504b52e87f9` |
| build flags | `-mpopcnt -mbmi2 -mlzcnt -DSB_SEE_CACHE=1 -flto=4` |
| built == packaged == tested binary SHA-256 | `30874fbc1e6c7da03b4571d1c316fb082b0b151350d1d7ea86e5a7abb18931f0` |
| immutable dev5 baseline SHA-256 | `391cb50e13ab99168aba0255482554ab5e59d1a34af810bf8f4d2c88e5bdb918` |
| Tier-1 benchmark run | `41780333569` (4 isolated `ubuntu-latest` VMs, all SUCCESS) |
| Tier-1 export run | `41781546677` (SUCCESS, `[skip ci]` evidence commit `6540d6e`) |
| CI against exact candidate source | `41780333461` on `2aacf4a`, SUCCESS |
| artifact IDs / bytes | `13298354527`/733530 (stage0), `13298614709`/920621 (batchA), `13299405640`/734006 (null), `13299640420`/926265 (batchB) |
| local checksum re-verification | 4/4 `SHA256SUMS.txt`, **0 failures** |
| control | **FIXED TIME 40+4 ms**, Hash 16, Threads 1, max-plies 240, **no `--nodes`** |

One binary, one default-off switch: `QSearchTT=true` vs `QSearchTT=false`,
so there is no toolchain or build confound. Raw PGN / JSONL / CSV / summaries /
audit.txt / fingerprint / manifest / SHA256SUMS / UCI probe / run.log and the
exact packaged `.tar.gz` are mirrored at
`benchmarks/exp-runs/tier1-export/run-41780333569/`.

## Frozen Stage-0 validity gate — PASS
`QSearchTT=false` vs `false` self-match, 399 adjudicated /400 games,
`−8.7314 [−27.2458, +9.7335]` Elo, 199 clusters, CI includes 0,
**0 TIME_FORFEIT, 0 illegal moves, 0 engine failures, 0 UCI failures**.
The isolated-VM 40+4 ms measurement is valid; no forfeit confound.

## Results (CR1/t, opening-clustered two-sided 95 % CI)
| arm | games | W/D/L | score | Elo | 95 % CI | clusters |
|---|---|---|---|---|---|---|
| batchA | 999 | 351/330/318 | 0.516517 | **+11.1440** | [−0.9681, +23.2833] | 499 |
| batchB | 997 | 347/314/336 | 0.505517 | **+4.1946** | [−8.4247, +16.8249] | 497 |
| null (ON vs ON) | 397 | 132/133/132 | 0.500000 | +0.8818 | [−15.6419, +17.4096] | 197 |
| **frozen combined A+B** | **1,996** | **698/644/654** | **0.5110220** | **+7.6755** | **[−1.0670, +16.4278]** | **996** |

2 batches positive, both >= −5; null CI includes 0; 0 forfeits/illegal/UCI
failures; 6 unadjudicated games across all arms, excluded by the pre-existing
`score_a=null` rule. Paired pentanomial, LLR labelled a normal approximation,
no post-hoc batch selection, no post-hoc combining to manufacture significance.

## Independent recomputation — AUDIT PASS
`scripts/dev6_exp0038_audit.py 41780333569` re-parsed all four raw
`match.jsonl` files from scratch and compared **44 stored values** (W/D/L,
games, unadjudicated, score, independent Elo-from-score, CR1 Elo, forfeit /
illegal / failure counts): **0 issues, AUDIT PASS**. Combined independent
Elo-from-score `+7.6601` vs stored CR1 `+7.6755`. An independently coded
seeded opening-cluster bootstrap (20,000 resamples, seed 2026112501) gave
`[−1.0465, +16.4072]`, in close agreement with CR1/t. Machine-readable output:
`benchmarks/dev6-baseline/exp0038_independent_audit.json`; console log:
`/tmp/exp0038_audit.txt` reproduced in the ledger entry.

## Frozen decision — CLOSE (inert / overhead), no Stage 2a
§6: ADVANCE requires combined point >= +20 AND LCB > 0 AND both batches >= −5
AND null including 0 AND clean correctness. `point +7.6755 >= +20` is **FALSE**,
`LCB −1.0670 > 0` is **FALSE** → no ADVANCE. CLOSE rule: combined UCB
`+16.4278 < +20` is **TRUE** → **CLOSED, ABANDONED, not retuned**.

## Root-cause classification and diagnosis
Class: **unsuitable hypothesis / search interaction**, not an implementation
defect (default-off was bit-exact, ctest 11/11 Release and ASan+UBSan,
UCI/perft/oracle/determinism all PASS, 0 illegal/forfeit/failure). Pre-result
profiling predicted the outcome: d16 −0.0006 % nodes but +3.86 % time; the
instrumented build showed millions of cache hits (e.g. 2,741,602 hits /
99,346,894 probes on one position) concentrated on stand-pat, delta and
no-capture nodes that already return immediately. A direct-mapped bound cache
therefore pays a probe and a store at EVERY qsearch node while saving almost
no subtree work. At a ~4 ms effective increment that overhead roughly cancels
the small genuine reuse benefit — the measured +7.68 has UCB < +20 and LCB < 0.

`QSearchTT` stays **default OFF**. No cache-size/hash/margin retune, no repeat
of this mechanism this cycle, no Stage 2a, no bundle including it (the frozen
ADVANCE condition was not met), and no fixed-node result is presented as
fixed-time strength.

## Gate verdict (unchanged, `docs/DEV6_PREREG.md` §8 not weakened)
- **Gate 1 UNMET** — no >= +75 Elo point with two-sided opening-clustered
  LCB > +50 on two independent preregistered FIXED-TIME batches.
- **Gate 2 direction-supported** (exp-0036), **Gate 3 PASS** (both nulls).
- **Gate 4 UNMET for a final candidate** — this experiment's own packaged
  artifact/binary/CI linkage is complete and verified, and Tier-1 isolated-VM
  infrastructure is operational, but there is no final candidate release
  artifact yet.
- **Mission ACTIVE.** No strength claim, no PR/merge/tag/release/deploy/dev7.
