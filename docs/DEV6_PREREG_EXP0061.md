# exp-0061 — king-slider-battery screen over confirmed threats+race
# FROZEN BEFORE ANY exp-0061 COST MEASUREMENT OR GAME (2026-11-07)

## 1. Hypothesis and mechanism

The shipped `KingDanger*` rows count immediate zone hits; exp-0052 added a
nonlinear concentration of those hits. Neither represents an enemy slider
aligned with our king behind **exactly one** intervening blocker (an x-ray
battery). This is a distinct representational gap in king safety.

Candidate `KingSliderBattery`: for each enemy Bishop/Rook/Queen aligned with our
king orthogonally (R/Q) or diagonally (B/Q), if `popcount(occupancy & between) == 1`,
add 4 (orthogonal) or 3 (diagonal); cap per side at 16. One appended scale row,
frozen **mg=10, eg=0**. Default shipped row remains 0. The live path is fused
into the existing king-danger loop; the breakdown path uses the shared helper.

Falsifiable hypothesis: on top of the confirmed threats+race evaluation, the
battery increment yields a fixed-time screen point ≥ +15 Elo with LCB > 0 and
valid nulls. This is a component screen, **not** Gate 1 and not an integral
dev5 estimate. No node-efficiency claim is used as strength evidence.

## 2. Frozen arms and configuration

| arm | executable | EvalParams | other option |
|---|---|---|---|
| A | packaged candidate | `research-data/params_exp0061_battery.txt` | `TTEval=true` |
| B | identical packaged candidate | `research-data/params_exp0055_race.txt` | `TTEval=true` |

A SHA-256: `7e529623cb9f5994a11503825eef6f9e1ad871ef92a39650f2bfa402bb6bea43`.
B SHA-256: `82f93ba7a7b7e8e757c245098f5e2c4f42c866aa25124c73d0ad67ad11f89f01`.
A = B plus `KingSliderBattery 10 0`; threats `(1,1)` and race `(0,2)` unchanged.
Implementation commit `0a6e1473029905510f23dc3c256b36bd5672cd53`; no engine
change is permitted in this experiment's source pin after freezing.
Published dev5 remains pinned for provenance only, SHA-256
`391cb50e13ab99168aba0255482554ab5e59d1a34af810bf8f4d2c88e5bdb918`.

## 3. Pre-game correctness/design evidence (no games)

- Independent oracle: `scripts/check_king_slider_battery.py`, 800 positions,
  0 mismatches, 197 non-zero (`benchmarks/recovery/exp0061_battery_oracle.json`).
- Registered CTest group `king_slider_battery`, 4 tests; full suite 18/18
  (`benchmarks/recovery/exp0061_ctest.log`). Default bench signatures exact
  (`benchmarks/recovery/exp0061_bench_signatures.log`).
- Mutation matrix: 8/8 KILLED, survivors [] (`exp0061_battery_mutation_matrix.json`),
  including live-path-disabled, computed-but-never-applied, weights, blocker
  count, cap, queen ignore, breakdown sign.
- Scale selected before games on the 4,000-position diagnostic corpus:
  mg1 RMS 1.44 and mg2 RMS 2.89 were too small to resolve; frozen mg10 gives
  RMS 14.43, p99 40, max 96.25, inside the pre-declared envelope RMS<40/p99≤120
  (`exp0061_battery_scale.json`). No strength sweep.
- Liveness depth 8: 12/12 node trees changed, 2/12 bestmoves changed
  (`exp0061_battery_liveness.json`). Diagnostic only.
- `evaldata --check` on 4,000 positions: 0 mismatches
  (`exp0061_battery_evaldata_check.log`).

## 4. Prospective cost gate and numeric compute budget

The fail-closed CI prepare-job gate (`scripts/dev6_cost_gate.py`) runs before any
benchmark job, using the exp-0060 median-of-3 paired instrument and the same
4,000-position corpus. Limits are not relaxed:

- 60 A/A blocks: p90–p10 < 0.10 and median in [0.98,1.02]; one CI attempt.
- 90 A/B blocks: battery increment over race median ≤ 1.05.
- 90 A/B blocks: battery+race+threats vs champion median ≤ 1.10.

If the combined limit fails, exp-0061 closes pre-game; optimize semantics-
preservingly and remeasure under the same limit in a new identity, never relax.

**Exact game budget:** 5,800 games = 4,000 primary + 1,200 candidate null +
600 stage0. Four benchmark jobs at 420 minutes = 1,680 VM-minutes; prepare and
export at most 10 minutes each = **1,700 workflow VM-minutes maximum**. One
benchmark dispatch, one export dispatch. No adaptive games or result-driven
rerun. Infrastructure failure before any game permits at most one documented
retry of the identical plan; a failed null is INVALID, not a retry.

## 5. Protocol, openings, sample

Fixed **40+4 ms**, Hash 16, Threads 1, max-plies 240, TTEval=true; flags
`-mpopcnt -mbmi2 -mlzcnt -DSB_SEE_CACHE=1 -flto=4`. Claimable draws claimed;
240-ply capped games unadjudicated and excluded symmetrically by complete pair.
Fresh generator `scripts/dev6_exp0061_openings.py`, seed **2026110661**, 2,900
distinct 8-ply openings, four disjoint slices, independently verified against
every earlier committed suite. No earlier games pooled.

| job | games | pairs | A | B | purpose |
|---|---:|---:|---|---|---|
| stage0 | 600 | 300 | candidate/champion | identical | control null + fresh ctest |
| batchA | 2,000 | 1,000 | candidate/battery | candidate/race | primary |
| batchB | 2,000 | 1,000 | candidate/battery | candidate/race | independent primary |
| null | 1,200 | 600 | candidate/battery | identical | powered candidate null |

Primary estimate is batchA+batchB only, two-sided opening-clustered CR1 95%
Student-t; independent bootstrap cross-check. Nulls never pooled. At 4,000
games expected half-width ~9–10 Elo; a true +15 effect is detectable, smaller
effects may honestly remain inconclusive.

## 6. Validity — every condition required

1. Exact frozen prereg/plan/source/config/opening identities enforced.
2. Cost gate PASS recorded before games; raw A/A and A/B evidence preserved.
3. Zero time forfeits, illegal moves, engine failures or crashes. Capped `*`
   games are the declared symmetric exclusion; count them.
4. Both primary arms use the identical packaged candidate; per-arm parameter
   digests match A=battery and B=race, with positive load confirmations.
5. Stage0 and candidate-null 95% intervals **each include zero**. Audit banner
   alone is insufficient; inspect explicit condition results.
6. Primary slices disjoint from one another and all previous suites.
7. All committed blobs and per-job SHA256SUMS verify; assets self-contained.
8. Every one of the 5,800 PGNs replayed, all moves legal, zero inconsistencies.
9. Fresh ctest on the packaged candidate in stage0 passes, 18 registered groups.
10. Exact fixed-time protocol and recorded effective defaults in every job.

Any failure => **INVALID MEASUREMENT**, no strength claim. No favorable rerun.

## 7. Frozen decision and continuation

On the fixed 4,000-game combined primary sample:

- **SCREEN ADVANCE** iff point ≥ **+15**, LCB **> 0**, both batch points ≥ **−5**,
  and every validity condition passes. A separate confirmation is then required.
- **CLOSE (mechanism rejected)** iff UCB **< +5** or point **≤ 0**, valid.
- Otherwise **INCONCLUSIVE**. No rescale, retune, additional games or pooling.

Gate 1 stays **point ≥ +75 AND LCB strictly > +50 directly vs dev5**. No merge,
tag, release, prerelease, deploy or completion push follows from this experiment.
