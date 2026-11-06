# exp-0052 report — quadratic king-danger concentration
## VALID MEASUREMENT · CLOSED AS INCONCLUSIVE · Gate 1 UNMET · mission ACTIVE

**Date:** 2026-11-06 · **Branch:** `arena/6a6a2ba3-stockbear`
**Prereg:** `docs/DEV6_PREREG_EXP0052.md`, SHA-256
`c3a022d5686d4d5485f890ea23884dcc10e36e209e5a9902626c2a505f74d578` (frozen before
any game, verified against the plan by the runner in every job)
**Pinned source:** `2927c50fff072817f27d7e05cb3e3a44c659256f`
**Tier-1 run:** 42231550633 (SUCCESS, 5 isolated VMs) · **Export run:** 42233030585
**Raw evidence:** `benchmarks/exp-runs/tier1-export/run-42231550633/`
**Independent audit:** `benchmarks/recovery/exp0052_independent_raw_audit.json`

---

## 1. Result

Fixed time **40+4 ms**, Hash 16, Threads 1, max-plies 240. Arm A = candidate with
`KingSafetyQuadratic 1 0`; arm B = the **exact released `v0.1.0-dev5` artifact**
`391cb50e13ab99168aba0255482554ab5e59d1a34af810bf8f4d2c88e5bdb918`.
All figures below are **independently recomputed from raw per-game JSONL**, not
read from the runner's summaries.

| Scope | W/D/L | Clusters | CR1 Elo | 95% CI (opening-clustered, two-sided) |
|---|---|---|---|---|
| batchA | 360/300/334 | 494 | **+8.7933** | [−7.4260, +25.0509] |
| batchB | 329/339/330 | 498 | **−0.3488** | [−15.7768, +15.0777] |
| **FROZEN COMBINED (A+B)** | **689/639/664** | **992** | **+4.2031** | **[−6.9678, +15.3826]** |
| stage0 null | 152/104/144 | 200 | +6.9496 | [−10.7068, +24.6421] |
| candidate null | 136/134/129 | 199 | +5.2381 | [−13.8177, +24.3256] |
| baseline-equivalence | 138/125/137 | 200 | +0.8686 | [−20.8079, +22.5519] |

Independent cluster bootstrap of the combined estimate: **[−7.0057, +15.2451]**,
agreeing with the CR1 interval. Batch label overlap **0**. Design effect 1.0.

## 2. Frozen decision rules applied verbatim

From prereg §7, registered before any game:

| Rule | Test | Outcome |
|---|---|---|
| **ADVANCE** | point ≥ +20 **and** LCB > 0 | **NO** — point +4.2031 < +20; LCB −6.97 < 0 |
| **CLOSE (rejected)** | UCB < +10 **or** point ≤ 0 | **NO** — UCB +15.38 ≥ +10; point > 0 |
| **Otherwise** | CLOSED AS INCONCLUSIVE | **YES** |

### → **CLOSED AS INCONCLUSIVE**

No strength claim is made. **The direction is not shown to work, and it is not
shown to fail.** The interval [−6.97, +15.38] is compatible with anything from a
small regression to a modest gain; it excludes both the +20 ADVANCE bar and the
+75 Gate-1 target. Per §7 this outcome **does not license re-scaling the term and
re-running it** — that would be a strength sweep. No default change, no bundle,
no confirmation, no post-hoc sample increase.

This was explicitly anticipated: prereg §8 named INCONCLUSIVE "a likely and
honest outcome" because the +10…+35 prior sits near this run's ~±13 Elo
resolution.

## 3. Validity — PASS, independently established

- **0 TIME_FORFEIT, 0 ILLEGAL, 0 ENGINE_FAILURE in all five jobs.**
- Both validity nulls include 0 (stage0 [−10.71, +24.64]; candidate [−13.82, +24.33]).
- **PGN replay: 3,200/3,200 games**, every move legal, every final outcome
  consistent with its record, **0 inconsistent**.
- **67/67** committed blobs and **55/55** per-job `SHA256SUMS` verified.
- **Per-arm `EvalParams LOAD VERIFIED`** in every job, cross-checked against the
  raw probe output *and* against the frozen plan re-read from the pinned commit.
- Arm binary digests verified against the **declared design**: arm A =
  packaged candidate `62db6e3ecdb7…`, arm B = exact dev5 `391cb50e…5bdb918`.
- No negative clocks; minimum remaining 13.57 ms.
- Unadjudicated max-plies games (6/2/0/1/0) are excluded pairwise, never counted
  as draws; 1,984 of 1,992 scored games enter the primary combined estimate.
- **TOTAL ISSUES: 0 — INDEPENDENT AUDIT PASS.**

### 3.1 Baseline-equivalence: attribution is clean

The preregistered `equiv` job played the candidate with the knob **off** against
the exact dev5 artifact: **+0.87 [−20.81, +22.55]**, CI includes 0. Per §5.1 the
candidate default is therefore play-equivalent to dev5, and the combined effect
is attributable to `KingSafetyQuadratic` rather than to unrelated dev6-lineage
differences. This job was never pooled into the combined estimate.

### 3.2 One auditor assumption corrected — disclosed, not hidden

The first audit pass returned 3 issues, all of the form *"arms use different
binaries (not an ablation)"*. That check was written for exp-0051's same-binary
ablation and is **wrong for this design**, which deliberately uses the exact
released dev5 artifact as the baseline. It was replaced with a **stronger**
check: each arm's digest must equal the digest its declared role requires, and
the declared options/binaries/games/seed/openings/control/prereg digest are
compared against the frozen plan re-read from the pinned source commit.

Two facts make this a correction rather than a rationalisation: it was applied
**before** looking at whether it helped, and it **does not change the verdict** —
the result is INCONCLUSIVE either way. Regression: re-auditing the exp-0051
export with the strengthened auditor still yields **0 issues** and reproduces
its verdict exactly (**−159.5439 [−173.4477, −146.1023]**, 992 clusters, 50/50
blobs, 40/40 sums). **exp-0051 CLOSED/NEGATIVE stands.**

## 4. What was learned

**The mechanism is real, cheap, correct and live — and unproven at this scale.**

| Property | Evidence |
|---|---|
| Correct | independent python-chess oracle, 1,000 positions, 0 mismatches |
| Consistent | breakdown/evaluate invariant, 3,997 positions, 0 mismatches |
| Cheap | paired A/A-calibrated eval cost **+0.65%** median |
| Live | 10/11 positions change the search tree at fixed depth |
| Default-off | all three bench signatures bit-exact; dev5 reproduces them |
| Robust | ASan+UBSan ctest 15/15; 3 mutants applied, all killed |
| **Stronger?** | **Not established. +4.20 [−6.97, +15.38].** |

Three transferable lessons:

1. **Passing every pre-game check still does not imply Elo.** exp-0050 passed
   comparable checks and measured −1.57; exp-0051 passed correctness checks and
   measured −159.5; exp-0052 passed everything and is indistinguishable from
   zero. Correctness, cost, scale and liveness are **necessary, not sufficient**.
2. **The scale discipline worked as intended, and cost effect size.** Confining
   the perturbation to RMS 13.87 cp avoided exp-0049's pruning detuning, but a
   term bounded at 64 cp/side simply cannot move many decisions. The honest
   reading is that this is a **small mechanism conservatively scaled**, not a
   broken one — and that combination is exactly what a ±13 Elo screen cannot
   resolve.
3. **Two silent-failure instruments were found and fixed at zero games.** The
   `king_safety` group had no `add_test()` entry (ctest reported 14/14 PASS while
   the binary failed), and `EvalParams` shared `PstFile`'s silent-fallback hole
   that would have manufactured a fake result. Both are now guarded and the
   guards were exercised on the real runner with zero games.

## 5. Disposition

- `KingSafetyQuadratic` **remains shipped 0 (default-OFF)**. No default change.
- The code and tests are retained as inert, verified, default-off research code,
  consistent with prior closed experiments. Baseline behaviour is bit-exact.
- **exp-0052 is CLOSED AS INCONCLUSIVE and may not be re-run, re-scaled or
  pooled.** Its 1,600 openings and 3,200 games are burned for selection purposes.
- Public identity stays **`v0.1.0-dev5`**. No version bump, no tag, no release,
  no deploy, no PR strength claim, no merge. `origin/main` untouched.

## 6. Gate status

| Gate | Requirement | Status |
|---|---|---|
| 1 | +75 point, combined 95% LCB > +50, both batches positive, validity pass | **UNMET** |
| 2 | Plausible mechanism, evidence-backed | Direction-supported (exp-0036 +21.52 remains best measured) |
| 3 | Baseline preserved, features default-off, evidence intact | **PASS** |
| 4 | Independent raw audit of the decisive run | **UNMET** — no decisive run; this was a screen |

**Mission ACTIVE. Nothing here is completion.**

## 7. Strongest next action

**Direction 2 — threat / hanging-piece awareness** (`docs/STOCKBEAR_RECOVERY_RESEARCH.md`
§3). StockBear has **no threat term at all**: undefended pieces and pieces
attacked by cheaper attackers are invisible to static evaluation, which
dominates at median depth 5. It is conceptually distinct from king-local danger
and from the abandoned six-feature bundle, and `attacks_by_color` already
exists. It must enter under its **own** preregistration with the same pre-game
scale/cost/liveness discipline and its own fresh openings.

Two honest caveats to carry forward. First, no clean isolated public Elo number
was found for threats, so its prior (**+0…+40**) is weaker in *evidence quality*
than exp-0052's was. Second, and more important: **three consecutive eval-side
candidates have now failed to produce a confirmed gain**, and the external
anchors say no single term reaches +75. Gate 1 realistically requires several
separately preregistered, independently confirmed gains measured finally as one
frozen configuration — or a genuinely different class of change. Reaching it by
adding more small eval terms one at a time is not supported by the evidence
accumulated so far, and that should inform how much compute the next screen
gets.
