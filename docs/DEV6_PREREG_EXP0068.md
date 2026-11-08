# Preregistration — exp-0068: joint persistence of graded ordering state (valid re-registration)

**Status: FROZEN before any exp-0068 measurement and before any exp-0068 game.**
This file must never be edited after its freeze commit. Any change requires a new
experiment id.

## 1. One question

Does applying the **age-instead-of-erase** lifetime intervention to the graded
ordering state **as a unit** — the quiet history table *and* the continuation table
together — beat the shipped erase-every-search behaviour at fixed time?

Exactly one question. No per-table attribution is attempted; that was exp-0065
(history) and exp-0066 (continuation), whose verdicts, thresholds and evidence are
preserved untouched.

## 2. Why this id exists, and why it is not a forbidden retry

**exp-0067 is CLOSED INVALID because of an author error in the dispatched plan.**
Its generator emitted a single `persist` flag into **both** arms, so its primary
batches compared **joint versus joint** — an accidental A/A null with **no causal
contrast**. Its "primary" number (+1.9186 [−3.3021, +7.1402]) is therefore an A/A
measurement and carries **no information whatsoever** about the joint-versus-erase
contrast.

exp-0067's frozen prereg §8 states that **partial-game reruns require a new
experiment id**, and its §11 forbids result-driven retry. This id follows that
instruction exactly. It is **not** a retry motivated by a result: the invalidity is
a configuration defect that is logically independent of any outcome, and no valid
measurement of this contrast has ever existed. The exp-0067 plan was **not**
repaired and re-dispatched under its original id, and its evidence is preserved.

**Consequence for thresholds.** Because no valid contrast data exists, the
thresholds below are **not result-informed**. They are carried over **unchanged**
from exp-0067's frozen prereg (+10 / +3), which was itself written before any
result. Nothing is relaxed, tightened, or re-derived after observation.

## 3. Candidate selection (measured, inherited, unchanged)

Selection was performed for exp-0067 by read-only measurement on committed
evidence and is not re-litigated here:

| Candidate | Measured feasibility | Decision |
|---|---|---|
| Opposite-coloured-bishop scaling | Pure OCB in **58/3000 games (1.93 %)**, **0.56 %** of positions; absolute ceiling **+6.71 Elo** assuming every pure-OCB game converts from draw to win | **REJECTED** — underpowered by construction |
| Bad bishop | r = **−0.5247** with existing `MobilityBishop` ⇒ **27.5 %** shared variance; mobility already excludes own-pawn-blocked squares | **DEFERRED** — partially redundant |
| Space | r = **−0.3931** with existing total mobility ⇒ **15.4 %** shared variance | **DEFERRED** — partially redundant |
| Tempo | Constant side-to-move offset; no differential ordering information | **DEFERRED** — weak prior |
| **Joint persistence** | Two independent valid in-engine measurements of the same intervention per table: exp-0065 **+9.7673 [+3.3767,+16.1645]**, exp-0066 **+11.3524 [+5.3008,+17.4110]**, both LCB > 0 | **SELECTED** |

Evidence: `benchmarks/recovery/exp0067_ocb_incidence.json`,
`benchmarks/recovery/exp0067_term_redundancy.json`.

**Honest prior, unchanged.** Independent-and-additive would give ≈ +21; fully
overlapping ≈ +11. Both tables feed the **same** quiet-ordering score
(`history + clamp(continuation/4, ±8000)`, `search.cpp:296–301`), so
**sub-additivity is the likelier outcome**. Prior range **+11 to +21**, central
expectation **≈ +14**.

**Pre-game signal already measured and disclosed (not favourable).** The joint
node ratio is **0.974289**, *worse* than either single table (0.965386 / 0.966264),
and joint per-node cost is **1.026725**, giving time-to-depth ≈ **1.0003** —
essentially neutral, materially worse than exp-0066's ≈ 0.938. This weakens the
prior and is recorded **before** the games. It is a node/time diagnostic, never an
Elo estimate.

## 4. Exact intervention, control, and why this is one factor

Both tables are erased at the **same site** in the **same reset block** of
`Search::run()`, and the intervention for each is identical in kind: replace
`fill(0)` with a bounded halving (`value /= 2`). "The graded ordering state ages
across root searches within a game" is one mechanism as a statement about the code.

- **Arm A (treatment):** `PersistentHistory=true`, `PersistentContinuation=true`.
- **Arm B (control):** `PersistentHistory=false`, `PersistentContinuation=false`.
- **Both arms:** `ContinuationHistory=true`, `TTEval=true`,
  `EvalParams=research-data/params_exp0055_race.txt`, identical binary.

`ContinuationHistory=true` in **both** arms is mandatory: the continuation update
sites are gated on that feature and it ships **false**, so otherwise the table is
never written and half the intervention is a no-op. Arm B is exactly exp-0066's
control arm.

**The two options must always move together.** A mixed arm (one true, one false)
is a *different* experiment and is forbidden here; the pre-dispatch validator
asserts this.

`CounterMoves` persistence is **excluded** (categorical `Move[PieceNB][64]`,
saturates after one write; `search.hpp:282`, `search.cpp:375,291–293`).
`correction_`, `captureHistory_`, `qcache_`, `moveStack_`, `evalStack_` remain
erased exactly as shipped.

**Attribution.** Two option values change but select one intervention on one state
class at one site. The claim is for the **joint configuration only**; it may not be
decomposed, added to, averaged with, or pooled with exp-0065, exp-0066 or the
invalid exp-0067.

## 5. Implementation and pre-game gates (all must pass before any game)

No new search semantics are introduced: both switches already exist and ship
**false**. The packaged binary is expected to be byte-identical to exp-0066/0067's
`36fe761f20f28a252a977e24bff9a0addf798088619cea97d047ebf202fd87c8`; a difference
must be explained before dispatch. Mechanism-level evidence from exp-0067 is
reused **unchanged**, re-verified at freeze, and pinned by SHA-256 in the plan.

1. **Bench** exact: d4 `243f9a1c1ba5b36f`, d6 `e06c4352681ae8eb`,
   d7 `5bceff035f2a4ae4`.
2. **ctest**: all registered groups pass; total **22**.
3. **Composition source audit**: branches independent, each halving exactly once,
   all five non-graded tables still erased, UCI reuse is `||`, and **6/6**
   `handle_setoption` TT-clear paths reset persisted state.
4. **Interactive UCI oracle** (8 checks): persistence of both tables across `go`;
   cross-game isolation ON and OFF; cross-configuration isolation ON and OFF;
   determinism across **fresh** engines; joint differs from **each** single-table
   arm.
5. **Mutations**: ≥ 8 killable, **all** killed, equivalence controls survive.
   Detectors must include all three persistence groups and all three UCI oracles.
6. **Sequential-replay efficacy**: first 20 complete games with ≥ 40 positions from
   run-42356232866 batchA, depth 7, Hash 16, both arms `ContinuationHistory=true`.
   Total node ratio ON/OFF **≤ 0.98** AND a majority of games **≤ 1.00**.
7. **Per-node cost**: fixed **20,000 nodes × 250 positions**, both arms feature ON,
   alternating A/B, 3 passes. ON/OFF wall-time ratio **≤ 1.10**, A/A spread
   **< 0.10**. Regression gate, never an Elo predictor.
8. **NEW — mandatory pre-dispatch plan validation.**
   `scripts/recovery_validate_plan.py` must return **SAFE_TO_DISPATCH** on the
   exact plan file to be dispatched, proving primary arms differ, differ **only**
   by the two intervention options, carry the declared treatment/control values,
   that both options move together, that null arms are identical, and that
   features, protocol, counts and slices are correct. Its JSON verdict must be
   committed and its digest pinned in the plan **before** dispatch. **This gate
   exists because exp-0067 was invalidated by exactly this defect.**

A failed gate blocks the games. No gate may be relaxed after observation.

## 6. Sample size, seeds, compute budget (fixed, non-adaptive)

- **Exactly 7,800 games**: stage0 **600**, batchA **3,000**, batchB **3,000**,
  candidate null **1,200**. **Primary = batchA + batchB only (6,000)**.
- Openings: seed **2026110668**, **3,900** positions, four **disjoint** slices
  (stage0 300, null 600, batchA 1500, batchB 1500), generated by
  `scripts/dev6_exp0068_openings.py`, independently re-verified for disjointness and
  exclusion of every previously used opening (including exp-0067's).
- Job seeds: stage0 **2026110792**, batchA **2026110793**, batchB **2026110794**,
  null **2026110795**.
- **Four** isolated benchmark jobs, `timeout-minutes: 420` each; prepare and export
  ceilings 10 minutes ⇒ **1,700 workflow VM-minutes** upper bound.
- **One** benchmark dispatch, **one** evidence-export dispatch. Public
  GitHub-hosted runners only; no paid service.
- Protocol: fixed time **40+4 ms**, Hash **16**, Threads **1**, max **240** plies.
  Never `--nodes` for strength games.

**Power.** exp-0066's primary CI half-width was 6.05 Elo at 6,000 games ⇒ SE ≈ 3.09.
Detecting the central prior (+14) with LCB > 0 needs an observed point > 6.06, so
power against the prior is high; even a fully overlapping +11 outcome is likely to
clear LCB > 0. No adaptive extension is permitted near a threshold.

## 7. Statistical method

Two-sided **opening-clustered** 95 % CI on the Elo estimate, clustering by opening
pair; plus a cluster bootstrap as an independent cross-check. Per-batch estimates
reported separately. Nulls reported, never pooled into the primary. Component Elo
from different experiments is **never summed**.

## 8. Validity rules (fail closed)

**INVALID** unless every condition holds: identical binary in every arm and across
jobs (built == packaged == A == B); explicit per-arm option values with
`ContinuationHistory=true` in both arms of every job; **primary arms differ ONLY by
the two persistence options and actually differ**; both options move together;
`EvalParams` load proof for both arms; both persistence defaults recorded `false`;
identical recorded defaults for A and B; exact protocol; openings disjoint;
**7,800/7,800** PGN replay with 0 inconsistencies; 0 time forfeits, 0 illegal moves,
0 engine failures; committed blobs and per-job checksums verify; stage0 ctest
passes; **both** powered nulls have 95 % CIs **including zero**; independent auditor
issue count 0; **and the pre-dispatch plan-validation verdict is SAFE_TO_DISPATCH
for the dispatched plan digest**.

An auditor banner is **not** validity — exp-0067 passed the integrity audit while
being scientifically empty. A null failure is **INVALID**, not permission to rerun.
Infrastructure failure **before any game** may be retried once with the identical
plan and the failure documented; any rerun after games require a new experiment id.

## 9. Frozen decision thresholds

Let `P` be the primary point estimate, `L`/`U` its 95 % bounds, `Pa`,`Pb` the batch
points.

- **PROMOTE:** `P ≥ +10` **AND** `L > 0` **AND** `Pa ≥ −5` **AND** `Pb ≥ −5`
  **AND** every validity condition passes.
- **CLOSE:** `U < +3` **OR** `P ≤ 0` (with validity passing).
- **INCONCLUSIVE:** otherwise. Preserve as inconclusive; do not promote, extend, or
  re-read the criteria.

Carried over **unchanged** from exp-0067's frozen prereg. The bar is **+10 ≈ 3.2 ×
SE**, the repository's component-screen convention (exp-0064, exp-0065). It is
lower than exp-0066's +15 because a component screen decides only "should this
enter the champion?", not "does this close Gate 1?"; the gate is decided by a
separate integral run against published dev5. This reasoning predates any valid
measurement of this contrast. **exp-0065 and exp-0066 keep their original
thresholds, verdicts and default-OFF outcomes.**

**What PROMOTE authorises:** recording the joint configuration as champion
candidate for later, separately documented work. It authorises **no** gate claim,
merge, tag, release or deployment. Gate 1 stays **UNMET** until an integral run
against dev5 satisfies point ≥ +75 and LCB > +50.

## 10. Failure and confirmation criteria

- **Confirmation** = PROMOTE on a VALID run with both nulls null.
- **Failure** = CLOSE: the joint mechanism is not worth its cost, and the
  persistence direction is closed for this engine state.
- **Inconclusive** = neither: record it, leave defaults OFF, move to a different
  mechanism. Two prior single-table increments already landed near +10; a sub-bar
  joint result closes this direction rather than inviting another variant.

## 11. Prohibitions

No pooling with any earlier experiment, including the invalid exp-0067. No summing
or averaging of component Elo. No favourable-batch selection. No rounding across a
threshold. No result-driven retry, extension or additional dispatch. No threshold
relaxation. No editing this file. No dispatch without a SAFE_TO_DISPATCH plan
validation. No merge, PR creation, tag, release or deployment while Gate 1 is
UNMET; the existing PR state is preserved.

## 12. Records to write on closure

`docs/DEV6_EXP0068_REPORT.md`; entries in `benchmarks/FAILURE_LEDGER.md` and
`docs/DEV6_RESEARCH_MATRIX.md`; `AGENTS_LOG.md`; `DESIGN_LOG.md`; an updated
`docs/DEV6_MISSION_CHECKPOINT.md` with exact gate status; the independent audit
JSON, validity JSON, plan-validation JSON, gate evidence and the exported raw
evidence directory. The report must state the exact mission-level gate status and
must not describe experiment completion as mission completion.