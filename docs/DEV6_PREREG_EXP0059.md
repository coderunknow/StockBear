# exp-0059 — confirmation of exp-0055's passed-pawn race increment
# FROZEN BEFORE ANY exp-0059 GAME (2026-11-07)

## 1. Scope and immutable history

exp-0055 is a **VALID SCREEN ADVANCE**, +25.9606 [+17.5818,+34.3697], for
`PassedPawnRace` on top of threat detection. Its prereg §8 requires a separately
registered confirmation. exp-0056 instead measured the integral against dev5
and is **INVALID** because its candidate null excluded zero. It is neither a
valid race confirmation nor valid evidence of integral strength. Its +41.01
face value is permanently withheld from strength claims. exp-0057 remains
INCONCLUSIVE and exp-0058 REJECTED. None is reopened, rescored or pooled here.

This experiment repeats the **same scientific contrast**, not the openings:
the race increment in an identical binary. A later integrated candidate must
still be measured directly against the published dev5 artifact. Confirmation
of this increment is not Gate 1 and does not establish the integral's Elo.

## 2. Frozen arms and configuration

| arm | executable | EvalParams | other option |
|---|---|---|---|
| A | packaged candidate | `research-data/params_exp0055_race.txt` | `TTEval=true` |
| B | identical packaged candidate | `research-data/params_exp0053_threats.txt` | `TTEval=true` |

A SHA-256: `82f93ba7a7b7e8e757c245098f5e2c4f42c866aa25124c73d0ad67ad11f89f01`.
B SHA-256: `7266eb4c2d17f226b31e8e435c118be1abd06b412e07256c4f793c2f8e097548`.
Frozen `PassedPawnRace = (mg 0, eg 2)`; `ThreatDetection = (1,1)` in both.
All other parameters and search switches unchanged. No scale sweep or retune.

The mechanism is exactly exp-0055 §2: passed-pawn advancement weighted by own
king escort, enemy king blockade and a blocked forward file; fixed weights
2/2/6 and symmetric cap 64. The engine implementation, tests, CMake and both
configs have **zero diff** from exp-0055 implementation commit `2594479` to
the continuation starting HEAD `2d814ded1b1d56917a8047b1c2284f9f970e0bbe`.
The new source pin will include this prereg/plan and can be verified against
that implementation tree before dispatch. No engine change is permitted in
this experiment's source pin.

Although dev5 is not a primary arm, its published artifact remains pinned:
`benchmarks/binaries/stockbear-dev5-release`, SHA-256
`391cb50e13ab99168aba0255482554ab5e59d1a34af810bf8f4d2c88e5bdb918`.
The runner verifies it and records its identity; it does not substitute it for
B. The per-arm digest/load assertions must prove the actual same-binary design.

## 3. Prospective cost gate and numeric compute budget

`docs/DEV6_CONTINUATION_POLICY.md` is frozen before the new measurements/games.
The historical exp-0055 cost JSON had no numeric budget and is not retroactively
budgeted. Before this confirmation, remeasure the **unchanged** config on the
same deterministic 4,000-position corpus (seed 20261116):

- 60 A/A blocks: p90–p10 < 0.10 and median in [0.98,1.02];
- 90 A/B blocks: race increment median ≤ 1.05;
- 90 A/B blocks: threats+race vs champion median ≤ 1.10;
- 12 evaluation passes per block, alternating order, raw times preserved.

Failure blocks dispatch; no post-hoc budget relaxation. At most two A/A
calibration attempts. Cost is a resource diagnostic, never a strength proxy.

**Exact game budget:** 7,800 games, four benchmark jobs, one benchmark dispatch,
one export dispatch. Four 420-minute job ceilings = 1,680 benchmark VM-minutes;
prepare/export at most 10 minutes each = 1,700 workflow VM-minutes maximum.
Public GitHub-hosted runners only. No adaptive sample increase or result-driven
rerun. A failed null closes this measurement INVALID. Infrastructure failure
before any games permits at most one documented retry of the identical plan.

## 4. Protocol, openings and sample

Fixed **40+4 ms**, Hash 16, Threads 1, max-plies 240, TTEval=true;
flags `-mpopcnt -mbmi2 -mlzcnt -DSB_SEE_CACHE=1 -flto=4`.
Claimable draws automatically claimed; 240-ply capped games unadjudicated,
excluded symmetrically through complete opening pairs. No node-budget games.

Fresh generator `scripts/dev6_exp0059_openings.py`, seed **2026110659**,
3,900 distinct 8-ply openings, four disjoint slices, independently verified
against every earlier committed opening suite. No screen games are reused.

| job | games | pairs | A | B | purpose |
|---|---:|---:|---|---|---|
| stage0 | 600 | 300 | candidate/champion | identical | control null + fresh ctest |
| batchA | 3,000 | 1,500 | candidate/race | candidate/threats | primary |
| batchB | 3,000 | 1,500 | candidate/race | candidate/threats | independent primary |
| null | 1,200 | 600 | candidate/race | identical | powered candidate null |

Primary estimate is **batchA + batchB only**, two-sided opening-clustered CR1
95% Student-t interval; independent cluster bootstrap is a cross-check. Nulls
are never pooled. The larger null follows the documented exp-0056 instrument
weakness, not its result: the “CI includes zero” rule is unchanged.

At 6,000 primary games, expected half-width is about 7–9 Elo depending on draw
rate. This can confirm the preregistered +20 effect, but cannot establish +75.
A smaller true effect may honestly remain inconclusive.

## 5. Validity — every condition required

1. Exact frozen prereg/plan/source/config/opening identities enforced.
2. Zero time forfeits, illegal moves, engine failures or crashes. Capped `*`
   games are the declared symmetric exclusion, not failures; count them.
3. Both primary arms use the identical packaged candidate; per-arm parameter
   digests match A=race and B=threats, with positive load confirmations.
4. Stage0 and candidate-null 95% intervals **each include zero**. Audit banner
   alone is insufficient; inspect the explicit condition results.
5. Primary slices disjoint from one another and all previous suites.
6. All committed blobs and per-job SHA256SUMS verify; assets self-contained.
7. Every one of the 7,800 PGNs replayed, all moves legal, zero inconsistencies.
8. Fresh ctest on the packaged candidate in stage0 passes, 17 registered groups.
9. Exact fixed-time protocol and recorded effective defaults in every job.

Any failure => **INVALID MEASUREMENT**, no strength claim. No rerun to obtain
a favorable null. Preserve all raw data and the failure verdict.

## 6. Frozen decision and continuation

On the fixed 6,000-game combined primary sample:

- **CONFIRMED INCREMENT** iff point ≥ **+20**, LCB **> 0**, both batch points
  ≥ **−5**, and every validity condition passes. These are exp-0055's advance
  thresholds, now applied to an independent confirmation sample.
- **REJECTED** iff UCB **< +10** or point **≤ 0**, with valid measurement.
- Otherwise **INCONCLUSIVE**. No rescale, retune, additional games or pooling.

A confirmed increment supports the component, not a default change or release.
Do not add its Elo to exp-0054. The next integrated gate run needs its own fresh
preregistration and direct published-dev5 comparison. Architectural research
may proceed while games run, but no new feature is inserted into this pin.

Gate 1 stays **point ≥ +75 AND LCB strictly > +50 directly vs dev5**. No merge,
tag, release, prerelease, deploy or completion push follows from this experiment.
