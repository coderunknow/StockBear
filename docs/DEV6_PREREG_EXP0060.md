# exp-0060 — confirmation of exp-0055's passed-pawn race increment
# FROZEN BEFORE ANY exp-0060 COST MEASUREMENT OR GAME (2026-11-07)

## 1. Scope, history, and technical replacement

exp-0055 remains a **VALID SCREEN ADVANCE**, +25.9606 [+17.5818,+34.3697], for
`PassedPawnRace` on top of threat detection. Its §8 requires confirmation.
exp-0056 is **INVALID** (candidate null excluded zero) and is not a race
confirmation or valid integral evidence. exp-0057 is INCONCLUSIVE; exp-0058 is
REJECTED. None is reopened or pooled.

exp-0059 attempted this confirmation but closed **BEFORE GAMES** because its
prospective single-pair cost instrument failed A/A calibration twice
(0.1167 and 0.1143 spread; limit <0.10). See `docs/DEV6_EXP0059_REPORT.md`.
No exp-0059 strength data exists. This replacement changes only the
**pre-game cost instrument and execution environment**, not the scientific
contrast, configs, scale, strength thresholds, null rule, or gate. It is a
technical correction, not a result-driven strength retry.

## 2. Frozen arms and configuration

| arm | executable | EvalParams | other option |
|---|---|---|---|
| A | packaged candidate | `research-data/params_exp0055_race.txt` | `TTEval=true` |
| B | identical packaged candidate | `research-data/params_exp0053_threats.txt` | `TTEval=true` |

A SHA-256: `82f93ba7a7b7e8e757c245098f5e2c4f42c866aa25124c73d0ad67ad11f89f01`.
B SHA-256: `7266eb4c2d17f226b31e8e435c118be1abd06b412e07256c4f793c2f8e097548`.
Frozen `PassedPawnRace = (0,2)`; `ThreatDetection = (1,1)` in both. No retune.
The engine implementation, tests, CMake and both configs must have zero diff
from exp-0055 implementation commit `2594479` to this plan's source pin.
Published dev5 remains pinned for provenance only, SHA-256
`391cb50e13ab99168aba0255482554ab5e59d1a34af810bf8f4d2c88e5bdb918`; it is not
a primary arm. Per-arm digest/load assertions must prove the same-binary design.

## 3. Prospective cost gate — new noise-resistant instrument

Executed by `.github/workflows/dev6-tier1.yml` in the isolated **prepare** job
on a GitHub-hosted VM, before any benchmark matrix job. Script:
`scripts/dev6_cost_gate.py`. It is fail-closed: nonzero exit prevents games.

- Same deterministic 4,000-position corpus as exp-0059, seed 20261116, SHA-256
  `a1046aa3e7e3bfac3b016203e8d9dafef99432e3552a2719204a19da28ec1cb3`.
- **Three paired repetitions per block**; the block statistic is the **median
  of the three B/A ratios**. Order alternates across blocks and repetitions.
  No repetition or block is discarded. Each repetition is 12 evaluation passes.
- 60 A/A blocks: p90–p10 < 0.10 and median in [0.98,1.02]. If this fails, stop
  before A/B and before games. **One** CI attempt; no local calibration reuse.
- 90 A/B blocks: race increment median ≤ 1.05 over threats-only.
- 90 A/B blocks: threats+race median ≤ 1.10 over champion `params_abc.txt`.
- Preserve every raw pair, block median, input/binary/corpus hash, command,
  runtime, logs and an independent verdict. Cost is a resource diagnostic only.

This estimator is frozen before measurement because the previous single-pair
wall-clock instrument was demonstrably too noisy. The numeric limits are not
relaxed. If the CI gate fails, exp-0060 closes pre-game with no strength claim;
the confirmation remains technically blocked rather than silently retried.

## 4. Numeric compute budget and protocol

**Exact game budget:** 7,800 games = 6,000 primary + 1,200 candidate null +
600 stage0. Four benchmark jobs, `timeout-minutes: 420` each = 1,680 benchmark
VM-minutes. Prepare (including cost gate) and export are each capped at 10
minutes: **1,700 workflow VM-minutes maximum**. One benchmark dispatch, one
export dispatch. Public GitHub-hosted runners only. No adaptive games or
result-driven rerun. Infrastructure failure before any game permits at most one
documented retry of the identical plan; a failed null is INVALID, not a retry.

Fixed **40+4 ms**, Hash 16, Threads 1, max-plies 240, TTEval=true; flags
`-mpopcnt -mbmi2 -mlzcnt -DSB_SEE_CACHE=1 -flto=4`. Claimable draws claimed;
240-ply capped games unadjudicated and excluded symmetrically by complete pair.
Fresh generator `scripts/dev6_exp0060_openings.py`, seed **2026110660**, 3,900
distinct 8-ply openings, four disjoint slices, independently verified against
every earlier committed suite. No screen games reused.

| job | games | pairs | A | B | purpose |
|---|---:|---:|---|---|---|
| stage0 | 600 | 300 | candidate/champion | identical | control null + fresh ctest |
| batchA | 3,000 | 1,500 | candidate/race | candidate/threats | primary |
| batchB | 3,000 | 1,500 | candidate/race | candidate/threats | independent primary |
| null | 1,200 | 600 | candidate/race | identical | powered candidate null |

Primary estimate is batchA+batchB only, two-sided opening-clustered CR1 95%
Student-t; independent bootstrap cross-check. Nulls never pooled. At 6,000
games expected half-width ~7–9 Elo; this can confirm +20 but cannot establish
+75. A smaller true effect may honestly remain inconclusive.

## 5. Validity — every condition required

1. Exact frozen prereg/plan/source/config/opening identities enforced.
2. Cost gate PASS recorded before games; raw A/A and A/B evidence preserved.
3. Zero time forfeits, illegal moves, engine failures or crashes. Capped `*`
   games are the declared symmetric exclusion; count them.
4. Both primary arms use the identical packaged candidate; per-arm parameter
   digests match A=race and B=threats, with positive load confirmations.
5. Stage0 and candidate-null 95% intervals **each include zero**. Audit banner
   alone is insufficient; inspect explicit condition results.
6. Primary slices disjoint from one another and all previous suites.
7. All committed blobs and per-job SHA256SUMS verify; assets self-contained.
8. Every one of the 7,800 PGNs replayed, all moves legal, zero inconsistencies.
9. Fresh ctest on the packaged candidate in stage0 passes, 17 registered groups.
10. Exact fixed-time protocol and recorded effective defaults in every job.

Any failure => **INVALID MEASUREMENT**, no strength claim. No favorable rerun.

## 6. Frozen decision and continuation

On the fixed 6,000-game combined primary sample:

- **CONFIRMED INCREMENT** iff point ≥ **+20**, LCB **> 0**, both batch points
  ≥ **−5**, and every validity condition passes.
- **REJECTED** iff UCB **< +10** or point **≤ 0**, with valid measurement.
- Otherwise **INCONCLUSIVE**. No rescale, retune, additional games or pooling.

A confirmed increment supports the component, not a default change or release.
Do not add its Elo to exp-0054. A later integrated gate run needs its own fresh
preregistration and direct published-dev5 comparison. Architectural research
may proceed while games run, but no new feature is inserted into this pin.

Gate 1 stays **point ≥ +75 AND LCB strictly > +50 directly vs dev5**. No merge,
tag, release, prerelease, deploy or completion push follows from this experiment.
