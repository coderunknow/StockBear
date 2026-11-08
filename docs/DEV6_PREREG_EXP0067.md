# Preregistration — exp-0067: joint persistence of graded ordering state

**Status: FROZEN before implementation, before any exp-0067 measurement, and
before any exp-0067 game.** This file must never be edited after its freeze
commit. Any change requires a new experiment id.

## 1. One question

Does applying the **age-instead-of-erase** lifetime intervention to the graded
ordering state **as a unit** — the quiet history table *and* the continuation
table together — beat the shipped erase-every-search behaviour at fixed time?

Exactly one question. This experiment does **not** attempt per-table attribution;
that was the subject of exp-0065 (history) and exp-0066 (continuation), whose
verdicts and evidence are preserved untouched.

## 2. Why this mechanism, and why now (candidate selection with measurements)

The mission's remaining gate gap is **75 − 40.7732 = 34.2268 Elo**. Four
confirmed-missing evaluation terms and joint persistence were reassessed. The
selection below is based on **measurements taken on already-committed evidence**
(read-only), not on chess folklore. Scripts and raw outputs are committed:

| Candidate | Measured feasibility | Decision |
|---|---|---|
| Opposite-coloured-bishop scaling | Pure OCB reached in **58/3000 games (1.93 %)** and **1974/353605 positions (0.56 %)**. Absolute Elo ceiling **+6.71**, and that ceiling assumes converting *every* pure-OCB game from a draw to a win. | **REJECTED as underpowered by construction.** Evidence `benchmarks/recovery/exp0067_ocb_incidence.json`. |
| Bad bishop | Own-pawns-on-bishop-colour count correlates **r = −0.5247** with the **existing** `MobilityBishop` count ⇒ **27.5 %** shared variance. `mobility_count_at` is `attacks_bb(...) & ~own`, which already excludes own-pawn-blocked squares. | **DEFERRED**: partially redundant, marginal effect attenuated. |
| Space | Safe-centre-behind-pawns count correlates **r = −0.3931** with existing total mobility ⇒ **15.4 %** shared variance. | **DEFERRED**: partially redundant. |
| Tempo | A constant side-to-move offset carries no differential ordering information; it shifts only qsearch stand-pat and null-move margins. No incidence measurement can make a constant term large. | **DEFERRED**: weak prior. |
| **Joint persistence** | Two **independent, valid, in-engine** measurements of the same intervention applied to each table separately: exp-0065 **+9.7673 [+3.3767,+16.1645]**, exp-0066 **+11.3524 [+5.3008,+17.4110]**. Both LCB > 0. | **SELECTED.** |

Evidence `benchmarks/recovery/exp0067_term_redundancy.json`. Joint persistence is
the only candidate with **direct positive evidence in this engine** rather than an
imported prior, and the only one whose plausible effect is resolvable at an
affordable sample size.

**Honest prior.** If the two tables' contributions were independent and additive
the joint effect would be ≈ +21 Elo; if they were fully overlapping it would be
≈ +11 Elo. They feed the **same** quiet-ordering score
(`history + clamp(continuation/4, ±8000)`, `search.cpp:296–301`), so
**sub-additivity is the likelier outcome**. Prior range **+11 to +21**, central
expectation **≈ +14**. This is a genuine prediction that can fail.

## 3. Exact intervention, control, and why this is one factor

Both tables are erased at the **same site** in the **same reset block** of
`Search::run()`, and the shipped intervention for each is identical in kind:
replace `fill(0)` with a bounded halving (`value /= 2`). Treating "the graded
ordering state ages across root searches within a game" as one mechanism is
therefore a statement about the code, not a convenience.

- **Arm A (treatment):** `PersistentHistory=true`, `PersistentContinuation=true`,
  `ContinuationHistory=true`, `TTEval=true`, `EvalParams=research-data/params_exp0055_race.txt`.
- **Arm B (control):** `PersistentHistory=false`, `PersistentContinuation=false`,
  `ContinuationHistory=true`, `TTEval=true`, same `EvalParams`.

`ContinuationHistory=true` in **both** arms is mandatory: the continuation update
sites are gated on that feature and it ships **false**, so without it the
continuation table is never written and half the intervention would be a no-op.
Arm B is exactly exp-0066's control arm. Everything else is identical, including
the binary.

`CounterMoves` persistence is **excluded**: `counterMoves_` is a categorical
`Move[PieceNB][64]` reply table that saturates after one write
(`search.hpp:282`, `search.cpp:375,291–293`) — a different mechanism class.
`correction_`, `captureHistory_`, `qcache_`, `moveStack_` and `evalStack_` remain
erased exactly as shipped.

**Attribution statement.** Two option values change, but they select one
intervention (age vs erase) applied to one state class at one site. This
experiment claims an effect for **the joint configuration only**. It may not be
decomposed, and its result may not be added to, averaged with, or pooled with
exp-0065 or exp-0066.

## 4. Implementation scope

No new search semantics are introduced: both switches already exist and ship
**false**. The required work is to prove the **composition** is correct and safe:

1. Source audit confirming the two branches are independent, each halving is
   applied exactly once, and no other table's lifetime changes.
2. A new registered test group `joint_persistence` proving: both tables persist
   across `go`; each is halved exactly once per root search; `ucinewgame` resets
   both; every `handle_setoption` TT-clear path resets both; the all-OFF path is
   bit-identical to the shipped behaviour; no `evalStack_` leakage.
3. An adversarial mutation matrix over the composition (≥ 8 killable mutants must
   be killed; equivalence controls must survive).
4. Frozen bench signatures must remain **exact**: d4 `243f9a1c1ba5b36f`,
   d6 `e06c4352681ae8eb`, d7 `5bceff035f2a4ae4`.

If the composition audit finds a defect, it is fixed in scope, proven equivalent
when all persistence switches are OFF, and documented.

## 5. Pre-game gates (all must pass before any strength game)

1. **Bench** d4/d6/d7 exact as above.
2. **ctest**: every registered group passes; total becomes **22** with
   `joint_persistence`.
3. **Interactive UCI oracle**: persistence of both tables across `go`;
   cross-game isolation ON and OFF; cross-configuration isolation ON and OFF;
   determinism across **fresh** engines (never repeated searches inside one
   engine — the TT persists across `go` and would confound the check).
4. **Mutations**: ≥ 8 killable killed, all killed, equivalence controls survive.
5. **Sequential-replay efficacy**: the first 20 complete games with ≥ 40
   positions from run-42356232866 batchA (the same deterministic rule as
   exp-0065/0066), depth 7, Hash 16, both arms `ContinuationHistory=true`.
   Total node ratio ON/OFF **≤ 0.98** AND a majority of games **≤ 1.00**.
6. **Per-node cost**: fixed **20,000 nodes × 250 positions**, both arms feature
   ON, alternating A/B, 3 passes. ON/OFF wall-time ratio **≤ 1.10** and A/A
   spread **< 0.10**. This is a regression gate, never an Elo predictor.

A failed gate blocks the games. Gates may not be relaxed after observation.

## 6. Sample size, seeds, and compute budget (fixed, non-adaptive)

- **Exactly 7,800 games**: stage0 **600**, batchA **3,000**, batchB **3,000**,
  candidate null **1,200**. **Primary = batchA + batchB only (6,000)**.
- Openings: seed **2026110667**, **3,900** positions, four **disjoint** slices
  (stage0 300, null 600, batchA 1500, batchB 1500), generated by
  `scripts/dev6_exp0067_openings.py`, independently re-verified for disjointness
  and for exclusion of every previously used opening.
- Job seeds: stage0 **2026110782**, batchA **2026110783**, batchB **2026110784**,
  null **2026110785**.
- **Four** isolated benchmark jobs, `timeout-minutes: 420` each; prepare and
  export ceilings 10 minutes each ⇒ **1,700 workflow VM-minutes** upper bound.
- **One** benchmark dispatch and **one** evidence-export dispatch. Public
  GitHub-hosted runners only; no paid service.
- Protocol: fixed time **40+4 ms**, Hash **16**, Threads **1**, max **240** plies.
  Never `--nodes` for strength games.

**Power.** exp-0066 measured a primary CI half-width of 6.05 Elo at 6,000 games
⇒ SE ≈ **3.09**. Detecting the central prior (+14) with LCB > 0 requires an
observed point > 6.06, so power against the prior is high; even a fully
overlapping +11 outcome is likely to clear LCB > 0. No adaptive extension is
permitted if the result is near a threshold.

## 7. Statistical method

Two-sided **opening-clustered** 95 % confidence interval on the Elo estimate,
clustering by opening pair so the two games sharing an opening are not treated as
independent; plus a cluster bootstrap as an independent cross-check. Per-batch
estimates are reported separately. Nulls are reported, never pooled into the
primary. Component Elo estimates from different experiments are **never summed**.

## 8. Validity rules (fail closed)

The run is **INVALID** unless every condition holds: identical binary in every
arm and across jobs (built == packaged == engine A == engine B); explicit
per-arm option values recorded, with `ContinuationHistory=true` in both arms of
every job; primary arms differ **only** by the two persistence options;
`EvalParams` load proof for both arms; shipped defaults recorded and both
persistence defaults `false`; identical recorded defaults for A and B; exact
protocol; openings disjoint; **7,800/7,800** PGN replay with 0 inconsistencies;
0 time forfeits, 0 illegal moves, 0 engine failures; committed blobs and per-job
checksums all verify; stage0 ctest passes; **both** powered nulls (stage0 and
candidate) have 95 % CIs **including zero**; independent auditor issue count 0.

An auditor banner is not validity. A null failure is **INVALID**, not permission
to rerun. Infrastructure failure **before any game** may be retried once with the
identical plan and the failure documented; partial-game reruns require a new
experiment id.

## 9. Frozen decision thresholds

Let `P` be the primary point estimate, `L`/`U` its 95 % bounds, and `Pa`,`Pb` the
batch points.

- **PROMOTE:** `P ≥ +10` **AND** `L > 0` **AND** `Pa ≥ −5` **AND** `Pb ≥ −5`
  **AND** every validity condition passes.
- **CLOSE:** `U < +3` **OR** `P ≤ 0` (with validity passing).
- **INCONCLUSIVE:** otherwise. Preserve as inconclusive; do not promote, do not
  extend, do not re-read the criteria.

**Derivation, and an explicit disclosure.** The bar is **+10 ≈ 3.2 × SE**, i.e.
materially above measurement noise, and it is the repository's established
**component-screen** convention (exp-0064, exp-0065). It is **lower than
exp-0066's +15**, and that difference is deliberate and stated in advance:
exp-0066 derived its bar from the *whole remaining gate gap*, which conflated
"should this component enter the champion?" with "does this close Gate 1?". A
component screen decides only the former; the gate is decided by a separate
integral run against published dev5. This reasoning is recorded **before** any
exp-0067 result exists. It changes nothing retroactively: **exp-0065 and
exp-0066 remain CLOSED/INCONCLUSIVE with their original thresholds, evidence and
default-OFF outcomes.** No threshold in this file may be changed after
observation.

**What PROMOTE authorises:** recording the joint configuration as the new
champion candidate for subsequent work, and setting those defaults only in a
later, separately documented champion update. It authorises **no** gate claim,
**no** merge, tag, release or deployment. Gate 1 stays **UNMET** until an integral
run against dev5 satisfies point ≥ +75 and LCB > +50.

## 10. Failure and confirmation criteria

- **Confirmation** = PROMOTE above, on a VALID run, with both nulls null.
- **Failure** = CLOSE above: the joint mechanism is not worth its cost, and the
  persistence direction is then closed for this engine state.
- **Inconclusive** = neither: record it, leave defaults OFF, and move to a
  different mechanism. Two prior increments already landed near +10; a third
  sub-bar persistence result closes this direction rather than inviting another
  variant.

## 11. Prohibitions

No pooling with any earlier experiment. No summing or averaging of component
Elo. No favourable-batch selection. No rounding across a threshold. No
result-driven retry, extension, or additional dispatch. No threshold relaxation.
No editing this file. No merge, PR creation, tag, release or deployment while
Gate 1 is UNMET; the existing PR state is preserved.

## 12. Records to write on closure

`docs/DEV6_EXP0067_REPORT.md`; an entry in `benchmarks/FAILURE_LEDGER.md`; an
entry in `docs/DEV6_RESEARCH_MATRIX.md`; `AGENTS_LOG.md`; `DESIGN_LOG.md`; an
updated `docs/DEV6_MISSION_CHECKPOINT.md` with exact gate status; the independent
audit JSON, validity JSON, gate evidence and the exported raw evidence directory.
The report must state the exact mission-level gate status and must not describe
experiment completion as mission completion.
