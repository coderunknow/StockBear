# exp-0063 — king-slider battery after semantics-preserving cost optimization
# FROZEN BEFORE ANY exp-0063 COST MEASUREMENT OR GAME (2026-11-07)

## 1. Purpose and relation to exp-0061

exp-0061 implemented a king-facing slider battery / x-ray term and passed all
correctness/liveness/scale checks, but **failed the prospective CI cost gate
before games** (increment median 1.17094 > 1.05; combined 1.25063 > 1.10). It is
closed as BLOCKED with zero games and no strength verdict. exp-0063 is a **new
identity** for the **same scientific mechanism and frozen scale**, after a
semantics-preserving implementation optimization. It does **not** reuse exp-0061
as a budget pass, does not relax any limit, and does not pool any earlier games.

Mechanism (unchanged): for each side, count enemy sliders aligned with its king
behind **exactly one** intervening blocker; orthogonal rook/queen weight 4,
diagonal bishop/queen weight 3, per-side cap 16; one appended scale row
`KingSliderBattery=(10,0)` on top of threats+race. Zero-blocker contact and
two-blocker screens are not counted.

Optimization (semantics-preserving): alignment is tested with hoisted ray masks
(`FileBB|RankBB` and a static empty-occupancy diagonal-ray table), and only
sliders already on those rays are visited in a separate fused count path. The
old per-slider `abs(df)/abs(dr)` geometry and the extra branch inside the
king-danger attack loop are removed. The counted set, weights, cap and sign are
identical; independent oracle/breakdown agreement and mutation tests below
verify this. Default-off shipped behavior remains bit-exact.

## 2. Frozen arms, identities and scale

Same-binary ablation; primary batches do **not** play dev5.

| arm | executable | EvalParams | other |
|---|---|---|---|
| A | packaged source-pin candidate | `research-data/params_exp0061_battery.txt` | TTEval=true |
| B | identical candidate | `research-data/params_exp0055_race.txt` | TTEval=true |

Candidate config SHA-256:
`7e529623cb9f5994a11503825eef6f9e1ad871ef92a39650f2bfa402bb6bea43`
(ThreatDetection 1/1, PassedPawnRace 0/2, KingSliderBattery 10/0).
Ablation config SHA-256:
`82f93ba7a7b7e8e757c245098f5e2c4f42c866aa25124c73d0ad67ad11f89f01`.
Champion params SHA-256:
`8a9dc81fa5921e5b642c790ffa3cf84c2ba68f2193023c19dc7f3f7cea86d0be`.
Published dev5 binary digest (provenance only):
`391cb50e13ab99168aba0255482554ab5e59d1a34af810bf8f4d2c88e5bdb918`.

Scale is frozen from exp-0061's pre-game distribution study on the 4,000-position
diagnostic corpus: mg10/eg0 gives RMS 14.43 cp, p99 40, max 96.25 (envelope
RMS < 40, p99 ≤ 120). Because exp-0063 is semantics-preserving, the scale is not
re-tuned; the oracle/breakdown checks prove the count distribution is unchanged.

## 3. Prospective cost gate — same limits, fail-closed

Before any game, the workflow runs `scripts/dev6_cost_gate.py` with the frozen
median-of-3 paired CI instrument on corpus
`benchmarks/positions/diagnostic_exp0059_eval.epd` (sha
`a1046aa3e7e3bfac3b016203e8d9dafef99432e3552a2719204a19da28ec1cb3`, n=4000):

- A/A: 60 blocks, 3 repeats, 12 passes/block; spread **< 0.10** and median in
  **[0.98, 1.02]**.
- A/B increment (battery vs race): 90 blocks; median **≤ 1.05**.
- Combined (battery vs champion): median **≤ 1.10**.
- **max_attempts = 1**. Any failure => BLOCKED BEFORE GAMES, zero games, no
  strength verdict; export the cost evidence. No favorable rerun or threshold
  relaxation. A local exploratory estimate (median ~1.03–1.05) is **not** the
  gate and is not used as a pass.

## 4. Protocol, openings, sample and compute budget

Fixed **40+4 ms**, Hash 16, Threads 1, max-plies 240, TTEval=true; flags
`-mpopcnt -mbmi2 -mlzcnt -DSB_SEE_CACHE=1 -flto=4`. Claimable draws claimed;
240-ply capped games unadjudicated and excluded symmetrically by complete pair.
Fresh generator `scripts/dev6_exp0063_openings.py`, seed **2026110663**, 2,900
distinct 8-ply openings, four disjoint slices, independently verified against
every earlier committed suite. No earlier games pooled.

| job | games | pairs | A | B | purpose |
|---|---:|---:|---|---|---|
| stage0 | 600 | 300 | champion | identical | control null + fresh ctest |
| batchA | 2,000 | 1,000 | battery | race | primary screen |
| batchB | 2,000 | 1,000 | battery | race | independent primary |
| null | 1,200 | 600 | battery | identical | powered candidate null |

Primary estimate is batchA+batchB only (4,000 games), two-sided opening-clustered
CR1 95% Student-t; independent bootstrap cross-check. Nulls never pooled.
Power: exp-0053/0055 screens at this size resolve ~±10–12 Elo near +15; a true
effect near zero will not advance.

**Exact compute budget:** 5,800 games total. Four benchmark jobs at 420 minutes
= 1,680 benchmark VM-minutes; prepare/export at most 10 minutes each = **1,700
workflow VM-minutes maximum**. One benchmark dispatch, one export dispatch.
Public GitHub-hosted runners only. No adaptive games or result-driven rerun.
Infrastructure failure before any game permits at most one documented retry of
the identical plan; a failed null is INVALID, not a retry.

## 5. Pre-game correctness evidence (already run locally)

- Independent python-chess ray/blocker oracle: **800 positions, 0 mismatches,
  197 non-zero** (`benchmarks/recovery/exp0063_battery_oracle.json`).
- `evaldata --check` on the 4,000-position diagnostic corpus with the frozen
  battery params: **4,000 positions, 0 mismatches**
  (`benchmarks/recovery/exp0063_battery_evaldata_check.log`).
- Mutation matrix: **11/11 KILLED**, including live-path-disabled,
  computed-never-applied, both weights, exactly-one-blocker, live cap, queen
  ignored on both ray classes, both ray masks empty, and breakdown sign
  (`benchmarks/recovery/exp0063_battery_mutation_matrix.json`).
- Fixed-depth liveness probe depth 8: **12/12 node trees changed, 2/12 bestmoves
  changed** (`benchmarks/recovery/exp0063_battery_liveness.json`). Proxy only.
- ctest **18/18** registered groups; all three established bench signatures
  exact with the shipped default-off row: depth-4 `243f9a1c1ba5b36f`, depth-6
  `e06c4352681ae8eb`, depth-7 `5bceff035f2a4ae4`.

## 6. Validity — every condition required

1. Exact frozen prereg/plan/source/config/opening identities enforced.
2. Prospective cost gate PASS before games (or the experiment is BLOCKED).
3. All primary/null arms use the identical packaged candidate binary; positive
   per-arm file-option load proof; no silent fallback.
4. Zero time forfeits, illegal moves, engine failures or crashes. Capped `*`
   games are the declared symmetric exclusion; count them.
5. Stage0 and candidate-null 95% intervals **each include zero**. Audit banner
   alone is insufficient; inspect explicit condition results.
6. Primary slices disjoint from one another and all previous suites.
7. All committed blobs and per-job SHA256SUMS verify; assets self-contained.
8. Every one of the 5,800 PGNs replayed, all moves legal, zero inconsistencies.
9. Fresh ctest on the packaged candidate in stage0 passes, 18 registered groups.
10. Exact fixed-time protocol and recorded effective defaults in every job.

Any failure => **INVALID MEASUREMENT**, no strength claim.

## 7. Frozen decision and continuation

On the fixed 4,000-game combined primary sample:

- **SCREEN ADVANCE** iff point ≥ **+15**, LCB **> 0**, both batch points ≥ **−5**,
  and every validity condition passes. A separate confirmation is then required.
- **CLOSE (mechanism rejected)** iff UCB **< +5** or point **≤ 0**, valid.
- Otherwise **INCONCLUSIVE**. No rescale, retune, additional games or pooling.

Gate 1 stays **point ≥ +75 AND LCB strictly > +50 directly vs dev5**. This screen
cannot meet Gate 1 and does not authorize any merge, tag, release, prerelease,
deploy or completion push. If it advances, the next step is a preregistered
confirmation and then a new direct integrated dev5 measurement; component Elo
is never summed.
