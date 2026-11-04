# exp-0043 — TT-evidence singular extension (Tier-1 fixed-time 40+4 ms)

## Status: CLOSED / ABANDONED at the FROZEN prereg rule

Experiment status: **CLOSED/ABANDONED**. Overall DEV6 mission status:
**ACTIVE / NOT COMPLETE**. Gates 1 and 4 remain UNMET; Gates 2
(direction-supported) and 3 (PASS) unchanged. No strength claim, no default
change, no bundle, no retune, no PR/merge/tag/release/deploy/dev7.

## Provenance

| item | value |
|---|---|
| exact source SHA | `5ea5ad21348f39dabad1da3e8cb098f798087295` (dispatch commit, `source_sha=HEAD`) |
| frozen prereg | `docs/DEV6_PREREG_EXP0043.md`, SHA-256 `e9fe40f053c9f479835c05efc3bf592547024090c1a315281ec727f0096f31dc` |
| frozen plan | `benchmarks/exp-runs/tier1-plan-exp0043.json`, SHA-256 `3141fb1f487184459b52d644d3187f201dbd70216455469768613e0aebff2e70` |
| dispatch | `mode=benchmark`, `experiment_id=exp0043`, attempt 13 |
| Tier-1 benchmark run | `41809643084` (prepare + 4 isolated VMs, SUCCESS) |
| Tier-1 export run | `41810711486` (SUCCESS) |
| CI on exact source | `41809642415` SUCCESS |
| packaged = tested binary | `c2ef506c5c6ebf9c3197c52903f61ccbf5326f16221c3c96a5bb3a8dc4420409` (built, packaged and extracted SHA identical in all 4 bundles) |
| dev5 immutable baseline | `391cb50e13ab99168aba0255482554ab5e59d1a34af810bf8f4d2c88e5bdb918` VERIFIED in run.log |
| evidence | `benchmarks/exp-runs/tier1-export/run-41809643084/`, 4 bundles, 9/9 SHA256SUMS.txt OK per bundle, 0 failures |
| control | FIXED TIME 40+4 ms, Hash16/Threads1/240 plies, **never `--nodes`**, identical clocks |

ONE default-off binary switch `TTSingularExtension=true` (candidate) vs `false`
(control), both arms `EvalParams=research-data/params_abc.txt`, `TTEval=true`.
Default-off build is bit-identical: bench `243f9a1c1ba5b36f`, d16
`a14ab62224f837e5`, d12 params `e45fa2ec2287eb41`; Release ctest 11/11,
ASan+UBSan ctest 11/11 (`benchmarks/dev6-baseline/exp0043_asan_ctest.log`),
UCI `TTSingularExtension` default false. All dev6 strength switches remain OFF.

Opening suites: `scripts/dev6_exp0043_openings.py`, seed `2026120201`, 1,400
fresh 8-ply openings, **ZERO** exact-final-position overlap with 32,041
earlier positions in 120 earlier files and ZERO duplicates within the 1,400;
four mutually disjoint slices (stage0 200 / null 200 / batchA 500 / batchB
500). Slice hashes in `benchmarks/dev6-baseline/exp0043_suites.json`.

## Mechanism and the mandatory pre-result diagnostic

A slightly-shallower main-TT LOWER bound >= beta + 50 cp at depth >= 3 marks
the always-first hash move singular; that ONE move is searched one ply deeper.
`SingularDepthSlack=3`, `MaxSingularExtensions=2` (path-scoped counter restored
on every return). **NO verification subtree** (exp-0037 CLOSED at
`+3.7766 [−9.3368,+16.9008]`), NO stand-pat rewrite, NO new lossy qsearch
rule, NO default-ON feature disabled. The deviation from the matrix's "genuine
re-search" wording was DECLARED IN ADVANCE in §2 of the prereg; the canonical
re-search variant is DEFERRED, not abandoned.

Instrumented `SB_SINGULAR_DEBUG` build from the FROZEN source, real exp-0043
suite positions (VALIDITY / overhead only, NEVER strength evidence):
- fixed depth 10, 16 positions: OFF 2,655,145 nodes / 0 triggers,
  ON 3,024,895 nodes / 15,000 triggers / 8,072 extensions => **+13.9 % nodes**;
- FIXED TIME 40+4 ms, 24 positions x 2 repeats: OFF 222,636 / 217,259 nodes,
  ON 218,959 / 225,368 nodes; median completed depth 6 for BOTH; 1,093 / 1,092
  triggers and 548 / 516 extensions; LIVE on **23 of 24** positions.

So the mechanism demonstrably changed the search tree at the EXACT Tier-1
control at bounded cost. A startpos `go depth 12` probe found 0 triggers;
suite positions are the preregistered probe. Three prior experiments recorded
that fixed-depth/node-count proxies DO NOT predict fixed-time strength.

## Results (independent recomputation from raw `match.jsonl`)

| job | games | W/D/L | Elo | 95 % CI | clusters | forfeits/illegal/failures |
|---|---|---|---|---|---|---|
| Stage-0 validity null (control options both sides) | 399 (1 unadjudicated) | 128/129/142 | −13.1005 | [−29.9568, +3.6943] | 199 | 0/0/0 |
| null (candidate options both sides) | 400 | 145/123/132 | +11.2956 | [−7.4505, +30.1078] | 200 | 0/0/0 |
| batchA | 997 (3 unadjudicated) | 333/302/362 | −9.7895 | [−25.2667, +5.6489] | 497 | 0/0/0 |
| batchB | 997 (3 unadjudicated) | 321/325/351 | −10.8390 | [−25.2969, +3.5814] | 497 | 0/0/0 |
| **FROZEN combined batchA+batchB** | **1,994** | **654/627/713** | **−10.3142** | **[−20.8915, +0.2440]** | **994** | **0/0/0** |

Combined score 0.4852056; independent Elo-from-score −10.2832; independent
seeded cluster bootstrap 95 % [−20.6467, +0.1748]. No post-hoc selection, no
pooling of the nulls into the combined result, no threshold change.

`scripts/dev6_exp0038_audit.py 41809643084 exp0043 20 10`: **44 stored values
checked, 0 issues, AUDIT PASS**.

## Frozen decision

`docs/DEV6_PREREG_EXP0043.md` §6: ADVANCE needs combined point >= +20 AND
LCB > 0 AND both batches >= −5 AND both null CIs include 0 AND clean.
Observed: point −10.3142 (< +20), LCB −20.8915 (< 0), batchA −9.7895 and
batchB −10.8390 (both < −5); nulls present and clean (both CIs include 0).
CLOSE triggers: UCB +0.2440 < +10 **AND** point <= 0. => **CLOSE /
ABANDONED**. No "more samples" clause applies (this was not INCONCLUSIVE), so
no confirmation run and no fresh suites were spent.

Consequences: `TTSingularExtension` stays default OFF; the frozen constants
`SingularMinDepth=3`, `SingularDepthSlack=3`, `SingularMargin=50`,
`MaxSingularExtensions=2` are NOT retuned; no bundle; no strength claim.
The +13.9 % fixed-depth node overhead is recorded as a plausible contributor
to the loss but is NOT a causal proof. Both nulls including zero and zero
forfeits/illegal/failures mean this was a VALID measurement, not a technical
failure.

## What was learned (feeds the next ranking)

exp-0041 (delete nodes, −5.06), exp-0042 (re-decide qsearch nodes, +2.61 /
−10.83) and now exp-0043 (spend an extra ply on non-PV hash moves, −10.31)
have ALL lost at 40+4 ms. Three consecutive mechanisms that change which
main/quiescence nodes are searched, or add a ply at non-PV nodes, have failed
to convert to fixed-time strength. The engine's shallow iterative-deepening
tree appears sensitive to extra work: at a ~4 ms increment, an extra ply on a
non-PV hash move costs more than the tactical accuracy buys. Positive
fixed-time evidence still sits with exp-0036 (`+21.5238 [10.2819,32.8108]`,
shallow losing-capture pruning) and exp-0038 (`+7.6755 [−1.0670,+16.4278]`,
qsearch information reuse). The next direction should therefore avoid adding
work or changing pruning/extension DECISIONS, and prefer a pure ordering or
information-reuse change with measured ZERO or near-zero per-node overhead.

## Gate verdict (unchanged)

Gate 1 UNMET (no >= +75 / LCB > +50 on two independent preregistered
FIXED-TIME batches); Gate 2 direction-supported; Gate 3 PASS; Gate 4 UNMET
for a final candidate (Tier-1 linkage is verified, but no exact final
candidate artifact has been tested). Gate definitions are quoted verbatim from
`docs/DEV6_PREREG.md` §8 and were not weakened. Mission ACTIVE / NOT COMPLETE.
