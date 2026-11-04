# exp-0044 — SEE-losing-capture ordering (screen + bounded confirmation)

## Status: CLOSED AS INCONCLUSIVE / ABANDONED at the FROZEN addendum compute bound

Experiment status: **CLOSED AS INCONCLUSIVE**, direction abandoned. Overall
DEV6 mission status: **ACTIVE / NOT COMPLETE**. Gates 1 and 4 remain UNMET;
Gates 2 (direction-supported) and 3 (PASS) unchanged. No strength claim, no
default change, no bundle, no retune, no third run, no PR/merge/tag/release/
deploy/dev7.

IMPORTANT: the generic `scripts/dev6_exp0038_audit.py` prints the prereg §6
default ("INCONCLUSIVE -> more samples"). The exp-0044 ADDENDUM, FROZEN BEFORE
any confirmation game, explicitly OVERRIDES that branch: "If neither condition
is met, exp-0044 is CLOSED AS INCONCLUSIVE ... This is an experiment-level
COMPUTE BOUND, not a threshold change." `scripts/dev6_exp0044_confirm_decision.py`
reproduces that override from the raw games. No further exp-0044 games are
authorised.

## Provenance

| item | screen | bounded confirmation |
|---|---|---|
| Tier-1 benchmark run | `41812595433` | `41814069967` |
| exact source SHA | `2ae4e68fc882991c3484eede22a4622f713da5e2` | `0691b9affd36006425ac23605f4a0cc8922a55bb` |
| frozen prereg | `docs/DEV6_PREREG_EXP0044.md` SHA `73ae460981a09bbf5d605205f8b77bf799b6d92a0fed4dc4abaa3a4ebc3820a5` | same prereg + `docs/DEV6_PREREG_EXP0044_ADDENDUM.md` SHA `17d90a790697bb05de108d4b5fb5f7cf745fdb611899c5237c7ccce2b73af835` |
| frozen plan | `benchmarks/exp-runs/tier1-plan-exp0044.json` | `benchmarks/exp-runs/tier1-plan-exp0044-confirm.json` (`no_pooling_with_screen`) |
| dispatch | `mode=benchmark`, attempt 15 | `mode=benchmark`, attempt 17 |
| export run | `41813751266` SUCCESS | attempt 18 `41815187170` FAILED at transient push; repaired + retried as new run `41815428066` SUCCESS |
| CI on exact source | `41812595476` SUCCESS | `41814069925` SUCCESS |
| packaged = tested binary | from screen bundles | `1ea31331a950…` (built = packaged in all 4 bundles) |
| evidence | `benchmarks/exp-runs/tier1-export/run-41812595433/` | `benchmarks/exp-runs/tier1-export/run-41814069967/` |
| checksums | 9/9 SHA256SUMS.txt OK per bundle, 0 failures | 9/9 SHA256SUMS.txt OK per bundle, 0 failures |
| control | FIXED TIME 40+4 ms, Hash16/Threads1/240 plies, never `--nodes` | identical |

ONE default-off binary switch `BadCaptureOrdering=true` (candidate) vs `false`
(control), both arms `EvalParams=research-data/params_abc.txt`, `TTEval=true`.
Default-off bit-exact bench `243f9a1c1ba5b36f`, d16 `a14ab62224f837e5`,
d12 params `e45fa2ec2287eb41`; Release ctest 11/11, ASan+UBSan ctest 11/11
(`benchmarks/dev6-baseline/exp0044_asan_ctest.log`), UCI default false. All
dev6 strength switches remain OFF. Immutable dev5 baseline
`391cb50e13ab99168aba0255482554ab5e59d1a34af810bf8f4d2c88e5bdb918` VERIFIED.

Opening suites: screen `scripts/dev6_exp0044_openings.py` seed `2026120201`
(1,400 openings, ZERO overlap / 33,441 earlier positions in 125 files);
confirmation `scripts/dev6_exp0044_confirm_openings.py` seed `2026120401`
(1,400 openings, ZERO overlap / 34,841 earlier positions in 130 files). Each
has four mutually disjoint slices (stage0 200 / null 200 / batchA 500 /
batchB 500) and zero duplicates within the 1,400. Screen and confirmation are
**NEVER pooled**.

## Mechanism and mandatory pre-result diagnostic
`Search::score_moves` scored SEE-losing captures at ~2,000,000, ABOVE killers
(1,500,000) and every quiet history move (|h| <= 60,000). exp-0044 demotes
SEE<0 non-promotion captures to the tail in the MAIN search ONLY. NO move is
removed (unlike exp-0036/0041), NO SEE/eval call added, NO stand-pat rewrite,
NO pruning/extension decision change, quiescence excluded. Frozen
`BadCaptureOrderScore=-2000000`, frozen threshold SEE<0, no tunable margin.

Instrumented `SB_BADCAP_DEBUG` build from the frozen source: fixed depth 10
over 16 suite positions OFF 2,655,145 nodes / ON 2,961,866 nodes
(+11.6 % TREE change, ZERO added per-node work), 424,155 demotions, live
16/16; FIXED TIME 40+4 ms over 24 positions x 2 repeats OFF 228,643/236,838
nodes, ON 203,245/214,462 nodes, median depth 6 both, 22,024/24,413
demotions, LIVE 24/24. The node increase was disclosed BEFORE results as a
risk, never spun as a positive. These are validity/overhead checks, NOT
strength evidence.

## Screen — INCONCLUSIVE (run `41812595433`)

| job | games | W/D/L | Elo | 95 % CI | forfeits/illegal/failures |
|---|---|---|---|---|---|
| Stage-0 validity null | 400 | 133/145/122 | +9.5569 | [−6.6563,+25.8118] | 0/0/0 |
| candidate-options null | 400 | 138/124/138 | 0.0000 | [−17.9335,+17.9335] | 0/0/0 |
| batchA | 1,000 | 341/336/320 | +6.6419 | [−8.1259,+21.4338] | 0/0/0 |
| batchB | 996 | 335/328/336 | 0.0000 | [−15.0949,+15.0949] | 0/0/0 |
| **frozen combined A+B** | **1,996** | **676/664/656** | **+3.3140** | **[−7.2389,+13.8730]** | **0/0/0** |

Score 0.5050100, 996 clusters, independent Elo-from-score +3.4814, seeded
cluster bootstrap `[−7.1520,+13.7861]`, 44/0 AUDIT PASS. ADVANCE false
(point < +20, LCB < 0), CLOSE false (UCB +13.8730 >= +10, point > 0) =>
INCONCLUSIVE, which mandated exactly ONE bounded fresh confirmation.

## Bounded confirmation — neither ADVANCE nor CLOSE (run `41814069967`)

| job | games | W/D/L | Elo | 95 % CI | forfeits/illegal/failures |
|---|---|---|---|---|---|
| Stage-0 validity null | 400 | 123/143/134 | −9.5569 | [−32.6787,+13.4804] | 0/0/0 |
| candidate-options null | 398 | 142/123/133 | +6.1422 | [−14.8210,+27.1502] | 0/0/0 |
| batchA | 999 | 360/328/311 | +17.0722 | [+0.6984,+33.5222] | 0/0/0 |
| batchB | 998 | 339/348/311 | +10.1190 | [−5.8209,+26.1015] | 0/0/0 |
| **frozen combined A+B** | **1,997** | **699/676/622** | **+13.5977** | **[+2.1746,+25.0503]** | **0/0/0** |

Score 0.5192789, 997 clusters, independent Elo-from-score +13.4030, seeded
cluster bootstrap `[+2.4394,+24.9592]`, 44/0 AUDIT PASS. ADVANCE false
(point +13.5977 < +20; LCB > 0 is true but insufficient), CLOSE false
(UCB +25.0503 >= +10, point > 0). Per the FROZEN ADDENDUM compute bound =>
**CLOSED AS INCONCLUSIVE**, `BadCaptureOrdering` abandoned, no retune, no
bundle, no third run. Screen and confirmation CIs overlap; NEVER pooled.

## Technical failure and repair (no scientific change)
Export attempt 18 (`41815187170`) succeeded at artifact download and checksum
verification but failed ONLY at the evidence `git push` with a transient
GitHub `Internal Server Error` (the same transient rejection observed on
direct pushes this session). NO evidence commit reached the remote. The export
job was repaired with a bounded 4-attempt push retry and re-dispatched as a
NEW valid run (attempt 19, `41815428066` SUCCESS); 9/9 checksums OK in each
of 4 bundles, 0 failures. Benchmark jobs, frozen prereg, plan, suites,
thresholds and gates were untouched. This is a technical repair, not a
strength result.

## What was learned
A pure ordering change with ZERO added per-node work produced two consecutive
non-negative frozen combined points (`+3.3140`, `+13.5977`) — the first
non-negative results since exp-0038 — but neither reached the frozen ADVANCE
threshold of +20 with a positive LCB, and the preregistered compute bound
closes the experiment. Even an ADVANCE would not approach Gate 1 (+75 /
LCB > +50). No strength claim is valid: the two runs are separate experiments
and are NEVER pooled; the confirmation's positive LCB is a within-experiment
quantity only. The `BadCaptureOrdering` mechanism and any retune of it are
ABANDONED. A DIFFERENT mechanism with a genuinely new hypothesis would need
its OWN frozen prereg, fresh suites and dispatch; no exp-0044 data may be
reused.

## Gate verdict (unchanged)
Gate 1 UNMET (no >= +75 / LCB > +50 on two independent preregistered
FIXED-TIME batches); Gate 2 direction-supported; Gate 3 PASS; Gate 4 UNMET
for a final candidate (Tier-1 linkage verified, but no exact final candidate
artifact tested). Gate definitions quoted from `docs/DEV6_PREREG.md` §8 and
not weakened. Mission ACTIVE / NOT COMPLETE.
