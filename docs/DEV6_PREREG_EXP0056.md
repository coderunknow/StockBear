# exp-0056 preregistration — INTEGRAL candidate vs released dev5 (Gate-1 test)
# FROZEN BEFORE ANY exp-0056 GAME (2026-11-07)

## §1 What this is

This is the **direct measurement of the integral candidate against the gate
baseline**. It is the run that `docs/DEV6_PREREG.md` §8 actually governs, and it is
the only kind of run that can satisfy Gate 1.

The candidate carries **both** banked components, enabled together in one
configuration:

- `ThreatDetection` mg 1 / eg 1 — CONFIRMED by exp-0054 at **+23.5374
  [+15.6937, +31.4052]** vs dev5.
- `PassedPawnRace` mg 0 / eg 2 — SCREEN ADVANCE by exp-0055 at **+25.9606
  [+17.5818, +34.3697]**, measured as an *increment* over the threat term by
  same-binary ablation.

**Those two numbers are NOT added.** +23.54 and +25.96 are separate estimates on
disjoint openings with different comparators; summing them would be exactly the
inference the mission prohibits. Terms interact — the race term changes which
positions the threat term is even evaluated in — so the integral must be, and here
is, measured **directly**.

**Honest expectation, stated before the run.** If the components were perfectly
additive the integral would land near **+50**, which is **below** the +75 point
requirement. Gate 1 is therefore **likely to fail on the point estimate**, and
this preregistration says so in advance rather than reinterpreting afterwards.
The run is still required: it is the only admissible way to learn the integral's
strength, and a valid negative answer is a real result that directs the next
direction.

## §2 What this is NOT

- **NOT** a re-run of exp-0054 or exp-0055, and **NOT** pooled with either. Their
  openings and games are burned for selection.
- **NOT** a rescale, retune or bundle of inconclusive candidates. Both components
  are individually supported: one CONFIRMED, one SCREEN ADVANCE with a clean
  same-binary ablation.
- **NOT** a reopening of exp-0048/0049/0050/0051/0052. **exp-0047 stays DORMANT.**
- **NOT** a same-binary ablation. Arm B is the **exact released dev5 artifact**.

## §3 Frozen arms and control

| arm | binary | sha256 | options |
|---|---|---|---|
| A | candidate (built from the pinned source SHA) | recorded per job | `EvalParams=research-data/params_exp0055_race.txt`, `TTEval=true` |
| B | **released dev5** `benchmarks/binaries/stockbear-dev5-release` | `391cb50e13ab99168aba0255482554ab5e59d1a34af810bf8f4d2c88e5bdb918` | `EvalParams=research-data/params_abc.txt`, `TTEval=true` |

Candidate configuration `research-data/params_exp0055_race.txt` sha256
`82f93ba7a7b7e8e757c245098f5e2c4f42c866aa25124c73d0ad67ad11f89f01` —
**byte-identical to the configuration used in the exp-0055 screen**. No parameter
is changed between screen and this run.

Fixed **TIME 40+4 ms** (never `--nodes`), Hash 16, Threads 1, max-plies 240,
build flags `-mpopcnt -mbmi2 -mlzcnt -DSB_SEE_CACHE=1 -flto=4`.
Adjudication policy unchanged and symmetric: "claimable draws automatically
claimed; capped games unadjudicated". A capped game is `*` and is excluded via
complete pairs; it is **not** a forfeit.

Both parameter files travel in every job's `assets`, and the runner must record a
positive **per-arm `EvalParams loaded:`** proof on the exact binary, checked
against the **per-role** expected digest.

## §4 Frozen design, sample and openings

Openings: `scripts/dev6_exp0056_openings.py`, seed **2026110656**, **3,400** 8-ply
paired openings, **zero** exact final-position overlap with all **204** earlier
committed files / **58,741** positions; four mutually disjoint slices.
Verification: `benchmarks/recovery/exp0056_suite_verification.json` (PASS).

| job | games | openings | arm A | arm B | role |
|---|---|---|---|---|---|
| stage0 | 400 | 200 | candidate `params_abc` | candidate `params_abc` | control/control null + fresh ctest on the packaged binary |
| batchA | 3,000 | 1,500 | candidate + threats + race | **released dev5** | frozen primary |
| batchB | 3,000 | 1,500 | candidate + threats + race | **released dev5** | frozen primary, independent seed, disjoint openings |
| null | 400 | 200 | candidate + threats + race | candidate + threats + race | candidate-options null; CI must include 0 |

**Frozen combined = batchA + batchB ONLY (6,000 games).** stage0 and null are
validity instruments and are never pooled into the estimate.

**Power.** 6,000 games give roughly **±7.5 Elo** half-width. That is enough to
separate a ~+50 integral from the +75 requirement and to place a lower bound
relative to +50 with useful precision. It is **not** enough to certify LCB > +50
if the true effect is only ~+52; in that case the honest verdict is that the gate
is not demonstrated. **No post-hoc sample increase is permitted.**

## §5 Frozen validity conditions (any failure ⇒ INVALID, not a strength result)

1. **0** forfeits, illegal moves, crashes or engine failures in every job.
2. Positive per-arm `EvalParams loaded:` proof on the exact binary with the
   per-role expected digest.
3. Arm B's binary digest equals the released dev5 digest above in **both** primary
   batches; arm A's equals the packaged candidate digest.
4. Both **stage0** and **null** 95% CIs include 0.
5. **0** exact opening-position overlap between batchA and batchB and with every
   earlier suite.
6. Every exported blob and per-job checksum verified; package self-contained.
7. **Full PGN replay** of all 6,800 games with **0** inconsistencies.
8. Fresh **ctest** on the packaged candidate binary in stage0 passes.

Independent recomputation from the **raw** per-game JSONL by
`scripts/recovery_independent_audit.py --pgn-replay`, reading the frozen plan at
its pinned commit SHA. A green CI summary is not evidence.

## §6 Frozen decision rules — the actual gate, registered BEFORE any game

Let `E` be the frozen combined two-sided opening-clustered CR1 point estimate and
`L`/`U` its 95% bounds, computed on batchA+batchB only.

- **GATE 1 PASS** iff **`E ≥ +75` AND `L > +50`** (strictly greater; `L = +50`
  fails) AND both batches positive AND all §5 validity conditions hold.
- **CONFIRMED IMPROVEMENT, GATE 1 FAIL** iff `L > 0` but the gate conjunction
  above is not satisfied. This banks a real gain and **does not** complete the
  mission.
- **INCONCLUSIVE** iff the CI includes 0.
- **NEGATIVE** iff `U < 0`.
- Any §5 failure ⇒ **INVALID MEASUREMENT**: no strength claim of any kind.

Additional binding consequences:

- No criterion in this document may be altered after results are observed.
- A GATE 1 FAIL, INCONCLUSIVE or NEGATIVE outcome does **not** license rescaling,
  retuning, re-running on new openings, or increasing the sample. The next action
  must be a **conceptually distinct** direction with its own preregistration.
- Only a **GATE 1 PASS** with every mandatory checklist item evidenced unlocks the
  completion push. Until then the mission stays **INCOMPLETE**, both new
  parameters stay shipped **0**, and no default change, merge, tag, release or
  deploy is authorized.

## §7 Integrity

Public release identity stays **`v0.1.0-dev5`**; no dev6/dev7 tag or release.
`origin/main` is untouched. Historical artifacts and append-only logs are
preserved. Commits pushed to the working branch are the CI experiment-dispatch
mechanism, **not** a completion push, which remains **BLOCKED**.
