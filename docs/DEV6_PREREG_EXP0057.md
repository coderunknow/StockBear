# exp-0057 preregistration — Tier-1 SCREEN of BadCapturePruning
# FROZEN BEFORE ANY exp-0057 GAME (2026-11-07)

## §1 Question, and why this direction

Does enabling **`BadCapturePruning`** — skipping captures with `SEE < -100` at
shallow depth, guarded away from PV nodes, the hash move, checks and mate windows
— play better than the same engine without it, on top of the threats+race
evaluation, at 40+4 ms?

**Why it is credible and genuinely open.** exp-0036 measured **+21.52
[+10.28,+32.81]** for this switch, but that was **Tier 2 (a local dedicated core)**,
explicitly *not* a GitHub-hosted isolated VM, and its own report says Tier-2
results "cannot satisfy Gate 4's packaged-artifact requirement". It has therefore
**never had a Tier-1 test**. It is a **search-efficiency** mechanism, orthogonal
to the two evaluation terms, which is exactly the family the mission asked to be
considered alongside eval.

**Why now.** exp-0056 showed the threats+race integral **cannot** reach Gate 1
even at face value (point +41 < +75; CI upper bound +47.69 < the required LCB
+50). Roughly **+35 Elo** of additional independent strength is needed, so the
binding need is a new mechanism, not more measurement of the same one.

**Honest prior: +0 to +25 Elo.** The Tier-2 anchor is suggestive but not Tier-1
evidence, and exp-0017 already taught that screen-selected gains regress. **This
does not reach Gate 1 alone and is not presented as if it does.**

## §2 Frozen arms — same-binary ablation

Both arms run the **identical candidate binary** and the **identical** EvalParams
(`research-data/params_exp0055_race.txt`, sha256
`82f93ba7a7b7e8e757c245098f5e2c4f42c866aa25124c73d0ad67ad11f89f01`). Exactly one
UCI option differs:

| arm | options |
|---|---|
| A | `EvalParams=…params_exp0055_race.txt`, `TTEval=true`, **`BadCapturePruning=true`** |
| B | `EvalParams=…params_exp0055_race.txt`, `TTEval=true`, **`BadCapturePruning=false`** |

`BadCaptureAllDepths` stays **false** in both arms, so the depth ≤ 3 guard is the
frozen exp-0034/0035/0036 behaviour. **One knob only.** No parameter is retuned.

This measures an **increment**, not a Gate-1 quantity, and must never be summed
with exp-0054's or exp-0055's estimates.

## §3 Pre-game evidence (already executed)

- The switch is a registered UCI option and loads correctly.
- **Liveness: 12/12 positions change the search tree** at fixed depth 10; 5
  bestmoves change; total nodes −1.26 %.
  `benchmarks/recovery/exp0057_liveness.json`, probe
  `scripts/probes/switch_liveness.cpp`.
- dev5 and the candidate were verified to have **identical UCI defaults**
  (0 differences), so the comparison carries no silent default handicap.
- Mechanism inspected in `src/search/search.cpp:724`: guarded by
  `!isQuiet && !isHash && !pvNode && !inCheck && !mateWindow && depth <= 3`,
  pruning when `SEE < -BadCaptureMargin`.
- Node-count comparators for three alternative ordering switches were measured at
  the same time and are recorded in the liveness JSON; they are **not** tested
  here and no claim is made about them.

## §4 Frozen design — with a POWERED null

Fixed **TIME 40+4 ms**, Hash 16, Threads 1, max-plies 240, build flags
`-mpopcnt -mbmi2 -mlzcnt -DSB_SEE_CACHE=1 -flto=4`. Adjudication unchanged and
symmetric ("claimable draws automatically claimed; capped games unadjudicated").

Openings: `scripts/dev6_exp0057_openings.py`, seed **2026110657**, **2,900** 8-ply
paired openings, **0** overlap with all **209** earlier files / **62,141**
positions; four disjoint slices. Verification PASS.

| job | games | openings | role |
|---|---|---|---|
| stage0 | 600 | 300 | control/control null (both arms switch OFF) + fresh ctest |
| batchA | 2,000 | 1,000 | frozen primary |
| batchB | 2,000 | 1,000 | frozen primary, independent seed, disjoint openings |
| null | 1,200 | 600 | candidate-options null (both arms switch ON) |

**Frozen combined = batchA + batchB ONLY (4,000 games).**

**The null is deliberately powered.** exp-0056 was invalidated by a **400-game**
null whose ~±19 Elo resolution fails by chance ~5 % of the time. At **1,200 games**
the null's resolution is ~±11 Elo, and stage0 is raised to 600. This is a design
correction adopted *before* seeing any exp-0057 result, in response to a documented
failure — not a relaxation: the "CI must include 0" criterion is **unchanged**.

## §5 Frozen validity conditions (any failure ⇒ INVALID)

1. 0 forfeits, illegal moves, crashes or engine failures.
2. Positive per-arm load proof for `EvalParams`, and the exported configuration
   must show `badcapturepruning` **true** for arm A and **false** for arm B in the
   primary batches (and equal within each null).
3. Both arm binaries identical (declared same-binary ablation).
4. **Both** nulls' 95 % CIs include 0.
5. 0 opening overlap between batches and with every earlier suite.
6. All blobs and per-job checksums verify; package self-contained.
7. Full PGN replay of all 5,800 games, 0 inconsistencies.
8. Fresh ctest on the packaged candidate in stage0.

**The auditor's `TOTAL ISSUES: 0` banner is NOT a validity verdict.** Null
adequacy is a separate field; every condition above must be evaluated explicitly.
This is recorded because exp-0056's banner was green while its null failed.

## §6 Frozen decision rules

- **ADVANCE** iff combined point ≥ **+15** Elo AND combined 95 % **LCB > 0** AND
  **|batchA − batchB| ≤ 20 Elo** AND both nulls include 0 AND all §5 holds.
- **CLOSE (rejected)** iff combined **UCB < +5** OR combined point ≤ 0.
- **Otherwise CLOSED AS INCONCLUSIVE**: no claim, no default change, no rescale,
  no retune, no re-run, no post-hoc sample increase.

The **batch-consistency clause is new and pre-declared**, in direct response to
exp-0056's 18.4 Elo batch gap. The ADVANCE bar is +15 rather than +20 because the
Tier-2 anchor is weaker evidence than exp-0053's had; this is fixed now, before
any game, and may not be moved afterwards.

A CLOSE or INCONCLUSIVE result does not license re-running; the next action must
be a conceptually distinct direction. **ADVANCE does not satisfy Gate 1** and
authorizes no default change, merge, tag, release or deploy.

## §7 Integrity

Public identity stays `v0.1.0-dev5`. `origin/main` untouched. Both eval
parameters stay shipped **0** and `BadCapturePruning` stays shipped **false**
regardless of the outcome. Gate 1 remains **UNMET** and the mission
**INCOMPLETE**. Branch commits are the CI dispatch mechanism, not a completion
push, which remains **BLOCKED**.
