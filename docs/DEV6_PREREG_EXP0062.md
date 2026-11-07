# exp-0062 — decisive integrated threats+race gate measurement vs published dev5
# FROZEN BEFORE ANY exp-0062 GAME (2026-11-07)

## 1. Purpose and immutable history

exp-0054 confirmed ThreatDetection directly vs published dev5: +23.5374
[+15.6937,+31.4052]. exp-0060 confirmed the PassedPawnRace increment over
threats: +27.0085 [+20.8746,+33.1592]. These are **not additive**. exp-0056's
integral attempt is INVALID and its face value is withheld. This experiment
measures the **integrated threats+race candidate directly against the exact
published dev5 artifact** under the governing Gate 1. It does not reopen any
closed experiment and does not include the exp-0061 battery (shipped row remains
0; the battery cost gate failed pre-game).

Gate 1: **combined point estimate ≥ +75 Elo AND two-sided opening-clustered 95%
LCB strictly > +50**, fixed time 40+4 ms, Hash 16, Threads 1, max-plies 240.

## 2. Frozen arms and identities

| arm | executable | EvalParams | other option |
|---|---|---|---|
| A (candidate) | packaged source-pin candidate | `research-data/params_exp0055_race.txt` | `TTEval=true` |
| B (baseline) | exact published dev5 | `research-data/params_abc.txt` | `TTEval=true` |

Candidate config SHA-256:
`82f93ba7a7b7e8e757c245098f5e2c4f42c866aa25124c73d0ad67ad11f89f01`
(ThreatDetection 1/1, PassedPawnRace 0/2, KingSliderBattery 0/0 by default).
Baseline binary: `benchmarks/binaries/stockbear-dev5-release`, SHA-256
`391cb50e13ab99168aba0255482554ab5e59d1a34af810bf8f4d2c88e5bdb918`.
Champion params SHA-256:
`8a9dc81fa5921e5b642c790ffa3cf84c2ba68f2193023c19dc7f3f7cea86d0be`.
The source pin may contain the default-off battery row, but all shipped bench
signatures are exact and the battery parameter is zero in the candidate config;
no non-qualifying feature is enabled.

## 3. Protocol, openings, sample and compute budget

Fixed **40+4 ms**, Hash 16, Threads 1, max-plies 240, TTEval=true; flags
`-mpopcnt -mbmi2 -mlzcnt -DSB_SEE_CACHE=1 -flto=4`. Claimable draws claimed;
240-ply capped games unadjudicated and excluded symmetrically by complete pair.
Fresh generator `scripts/dev6_exp0062_openings.py`, seed **2026110662**, 7,500
distinct 8-ply openings, four disjoint slices, independently verified against
every earlier committed suite. No earlier games pooled.

| job | games | pairs | A | B | purpose |
|---|---:|---:|---|---|---|
| stage0 | 600 | 300 | candidate/champion | identical | control null + fresh ctest |
| batchA | 6,600 | 3,300 | candidate/race | published dev5/champion | primary |
| batchB | 6,600 | 3,300 | candidate/race | published dev5/champion | independent primary |
| null | 1,200 | 600 | candidate/race | identical | powered candidate null |

Primary estimate is batchA+batchB only (13,200 games), two-sided opening-clustered
CR1 95% Student-t; independent bootstrap cross-check. Nulls never pooled.
Power: exp-0024/0028/0029 methodology gives ~±5 Elo half-width at this size near
+75; a true effect far below +75 will honestly fail the gate.

**Exact compute budget:** 15,000 games total. Four benchmark jobs at 420 minutes
= 1,680 benchmark VM-minutes; prepare/export at most 10 minutes each = **1,700
workflow VM-minutes maximum**. One benchmark dispatch, one export dispatch.
Public GitHub-hosted runners only. No adaptive games or result-driven rerun.
Infrastructure failure before any game permits at most one documented retry of
the identical plan; a failed null is INVALID, not a retry.

No new feature-cost gate is run because no new feature is enabled. The enabled
threats+race configuration passed the prospective exp-0060 CI cost gate
(combined median 1.09025 ≤ 1.10) and the default-off battery row preserves all
three bench signatures. Compute is bounded by the game budget above.

## 4. Validity — every condition required

1. Exact frozen prereg/plan/source/config/opening identities enforced.
2. Baseline binary digest equals the published dev5 artifact; baseline options
   are champion params_abc + TTEval=true, with positive load proof.
3. Candidate arm uses the packaged source-pin binary and race config, with
   positive load proof; stage0/null prove candidate control behavior.
4. Zero time forfeits, illegal moves, engine failures or crashes. Capped `*`
   games are the declared symmetric exclusion; count them.
5. Stage0 and candidate-null 95% intervals **each include zero**. Audit banner
   alone is insufficient; inspect explicit condition results.
6. Primary slices disjoint from one another and all previous suites.
7. All committed blobs and per-job SHA256SUMS verify; assets self-contained.
8. Every one of the 15,000 PGNs replayed, all moves legal, zero inconsistencies.
9. Fresh ctest on the packaged candidate in stage0 passes, 18 registered groups.
10. Exact fixed-time protocol and recorded effective defaults in every job.

Any failure => **INVALID MEASUREMENT**, no strength claim and no gate decision.

## 5. Frozen decision

On the fixed 13,200-game combined primary sample, with all validity conditions:

- **GATE MET** iff point ≥ **+75** and LCB **> +50**.
- Otherwise **GATE UNMET** (including point < +75, LCB ≤ +50, or a negative
  effect). An invalid measurement is **INVALID**, not “gate unmet” evidence.

No merge, tag, release, prerelease, deploy or completion push is authorized by
this prereg. If the gate is unmet, preserve the verdict and continue distinct
source-grounded research; never sum component estimates or rescale after close.
