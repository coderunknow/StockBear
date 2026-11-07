# exp-0058 preregistration — Tier-1 SCREEN of CaptureHistory
# FROZEN BEFORE ANY exp-0058 GAME (2026-11-07)

## §1 Question, and why this direction

Does enabling **`CaptureHistory`** — a bounded ±1024 ordering tie-break among
captures, keyed by (attacker type, target square, victim type) and updated from
search results — play better than the same engine without it, on top of the threats+race
evaluation, at 40+4 ms?

**Why it is credible and genuinely open.** `CaptureHistory` is fully implemented
(`src/search/search.cpp:214` scoring, `:293-298` updates, table
`captureHistory_[PieceTypeNB][SQ_NB][PieceTypeNB]`) but is shipped **false in BOTH
the released dev5 binary and the candidate** — verified by a direct UCI-default
diff showing **0 differences**. exp-0014's "CaptureHistory-off" ablation was
therefore a **no-op on an already-off switch**, which is why it read as neutral
within ±25 screen noise at 480 games. **It has never had a Tier-1 turn-ON test.**

Of four ordering switches probed at fixed depth 10, this one needed the **fewest
nodes (−4.65 %)** while changing the tree on 12/12 positions — the classic
ordering-efficiency signal. Capture ordering also feeds the SEE-based pruning
paths, so the mechanism is coherent rather than cosmetic.

**Why now.** exp-0056 showed the threats+race integral **cannot** reach Gate 1
even at face value (point +41 < +75; CI upper bound +47.69 < the required LCB
+50). Roughly **+35 Elo** of additional independent strength is needed, so the
binding need is a new mechanism, not more measurement of the same one.

**Honest prior: +0 to +20 Elo.** There is **no** clean external or internal anchor
for this switch; the node-count signal is a mechanism check, not an effect size.
exp-0057 just showed a Tier-2 anchor of +21.5 regressing to +11.7 at Tier 1. **This
does not reach Gate 1 alone and is not presented as if it does.**

## §2 Frozen arms — same-binary ablation

Both arms run the **identical candidate binary** and the **identical** EvalParams
(`research-data/params_exp0055_race.txt`, sha256
`82f93ba7a7b7e8e757c245098f5e2c4f42c866aa25124c73d0ad67ad11f89f01`). Exactly one
UCI option differs:

| arm | options |
|---|---|
| A | `EvalParams=…params_exp0055_race.txt`, `TTEval=true`, **`CaptureHistory=true`** |
| B | `EvalParams=…params_exp0055_race.txt`, `TTEval=true`, **`CaptureHistory=false`** |

`BadCapturePruning` and `BadCaptureAllDepths` stay **false** in both arms, so no
pruning behaviour changes — this isolates **ordering only**. **One knob only.**
No parameter is retuned.

This measures an **increment**, not a Gate-1 quantity, and must never be summed
with exp-0054's or exp-0055's estimates.

## §3 Pre-game evidence (already executed)

- The switch is a registered UCI option and loads correctly.
- **Liveness: 12/12 positions change the search tree** at fixed depth 10; 3
  bestmoves change; total nodes **−4.65 %**.
  `benchmarks/recovery/exp0058_liveness.json`, probe
  `scripts/probes/switch_liveness.cpp`.
- dev5 and the candidate were verified to have **identical UCI defaults**
  (0 differences), so the comparison carries no silent default handicap.
- Mechanism inspected in `src/search/search.cpp:214`: among captures only,
  `score += clamp(captureHistory_[attacker][target][victim], -1024, +1024)`;
  the table is updated from search outcomes at `:293-298`. It cannot reorder
  captures across the winning/losing boundary (±1024 vs the 1e6 band).
- Node-count comparators for three alternative ordering switches were measured at
  the same time and are recorded in the liveness JSON; they are **not** tested
  here and no claim is made about them.

## §4 Frozen design — with a POWERED null

Fixed **TIME 40+4 ms**, Hash 16, Threads 1, max-plies 240, build flags
`-mpopcnt -mbmi2 -mlzcnt -DSB_SEE_CACHE=1 -flto=4`. Adjudication unchanged and
symmetric ("claimable draws automatically claimed; capped games unadjudicated").

Openings: `scripts/dev6_exp0058_openings.py`, seed **2026110658**, **2,900** 8-ply
paired openings, **0** overlap with all **214** earlier files / **65,041**
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
correction adopted *before* seeing any exp-0058 result, in response to a documented
failure — not a relaxation: the "CI must include 0" criterion is **unchanged**.

## §5 Frozen validity conditions (any failure ⇒ INVALID)

1. 0 forfeits, illegal moves, crashes or engine failures.
2. Positive per-arm load proof for `EvalParams`, and the exported configuration
   must show `capturehistory` **true** for arm A and **false** for arm B in the
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
exp-0056's 18.4 Elo batch gap. The ADVANCE bar stays **+15**, identical to exp-0057's, so the two screens are
judged by the same rule; it is fixed before any game and may not be moved.

A CLOSE or INCONCLUSIVE result does not license re-running; the next action must
be a conceptually distinct direction. **ADVANCE does not satisfy Gate 1** and
authorizes no default change, merge, tag, release or deploy.

## §7 Integrity

Public identity stays `v0.1.0-dev5`. `origin/main` untouched. Both eval
parameters stay shipped **0** and `CaptureHistory` stays shipped **false**
regardless of the outcome. Gate 1 remains **UNMET** and the mission
**INCOMPLETE**. Branch commits are the CI dispatch mechanism, not a completion
push, which remains **BLOCKED**.
