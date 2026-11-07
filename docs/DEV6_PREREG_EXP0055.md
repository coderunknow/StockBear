# exp-0055 preregistration — Tier-1 SCREEN of the passed-pawn promotion race
# FROZEN BEFORE ANY exp-0055 GAME (2026-11-07)

## §1 What this is, and what it is NOT

**This is a SCREEN, not a Gate-1 decisive run.** One question: on top of the
already-CONFIRMED threat term, does scoring the **promotion race** of a passed
pawn — own king escorting, enemy king blockading, path blocked — play better than
the same engine without it, at 40+4 ms?

- It is **NOT** a retune, **NOT** a switch ablation, **NOT** a repackage of any
  earlier candidate, and **NOT** a reopening of a closed experiment.
  exp-0048/0049/0050/0051/0052 verdicts stand unchanged and are not rescored.
  **exp-0047 remains DORMANT.**
- **No pooling.** exp-0053's screen and exp-0054's confirmation are **never**
  pooled with exp-0055, and exp-0055's own screen will never be pooled with any
  later confirmation of it.
- **A positive screen does NOT satisfy Gate 1.** The governing gate is unchanged:
  `docs/DEV6_PREREG.md` §8 — combined point ≥ **+75** Elo AND combined two-sided
  opening-clustered 95% **LCB strictly > +50** against the exact released
  `v0.1.0-dev5` artifact at 40+4 ms. Equal to +50 fails.

**Why this mechanism is genuinely new.** The shipped evaluation scores a passed
pawn as **`advance² × PassedPawnAdvance`** and nothing else. A grep of the
parameter table confirms **no king-proximity term of any kind existed** before
this experiment. The engine therefore cannot distinguish a passer its own king
is shepherding from one the enemy king has firmly blockaded — yet in an endgame
that distinction is frequently the whole game.

The abandoned exp-0026 bundle contained `ConnectedPassed` and `RookBehindPassed`,
but it **never touched king geometry and never touched the `advance²` core**.
This is a different mechanism, not a re-run of that bundle.

**Honest prior.** The largest clean external anchor found for this family is a
published **MadChess passed-pawn rework at roughly +119 Elo**, which establishes
that the family can matter a great deal but is **not** an effect size for this
implementation. Stockfish is used as a reference only; no Stockfish code is
copied. Prior for this conservative single-knob version: **+0 to +40 Elo**.
**It does not reach Gate 1 alone and is not presented as if it does.**

## §2 Frozen mechanism and arms (ONE knob, ONE configuration)

One appended `EvalParamId`, **`PassedPawnRace`**, shipped **0** (default-OFF,
bit-exact). Table is **41** entries. Frozen candidate scale **mg = 0, eg = 2**.

```
passed(us,s)   := no enemy pawn in PassedPawnMaskBB[us][s]
                  AND no own pawn strictly ahead on the file
                  (EXACTLY the shipped PassedPawnAdvance rule)
advance        := relative rank of s (1..7)
stop           := s + 8 (White) / s - 8 (Black)
ownD           := min(chebyshev(ownKing,   stop), 7)
enemyD         := min(chebyshev(enemyKing, stop), 7)
blocked        := any enemy piece on the file strictly ahead of s
units(us)      := clamp( Σ_passers advance * ( 2*(7-ownD)
                                             - 2*(7-enemyD)
                                             - (6 if blocked else 0) ),
                         -64, +64 )
term           := PassedPawnRace · (units(White) - units(Black))
```

Fixed internal weights (2 / 2 / 6) and a fixed symmetric cap (64) with **one**
scale parameter, so the experiment has a single attributable knob. Chebyshev
distance is used because a king moves diagonally.

**Arms — same-binary ablation.** Both arms run the **identical candidate binary**;
only the parameter file differs:

| arm | binary | EvalParams | meaning |
|---|---|---|---|
| A | candidate | `params_exp0055_race.txt` | threats **ON** + race **ON** |
| B | candidate | `params_exp0053_threats.txt` | threats **ON** + race **OFF** |

This isolates the **race increment** exactly, with no binary, compiler-flag or
build confound. Because arm B is the threats-only candidate rather than dev5,
**this run measures an increment, not a Gate-1 quantity**, and its Elo number
must never be added to exp-0054's to claim a total. Any integral claim requires a
separate, directly-measured run against dev5 (§8).

`params_exp0055_race.txt` sha256
`82f93ba7a7b7e8e757c245098f5e2c4f42c866aa25124c73d0ad67ad11f89f01`
`params_exp0053_threats.txt` sha256
`7266eb4c2d17f226b31e8e435c118be1abd06b412e07256c4f793c2f8e097548`

Both files travel in every job's `assets`, and the runner asserts a **positive
per-arm `EvalParams loaded:` proof on the exact binary**. A missing file silently
retains the previous table, so without that proof the result would be INVALID.

## §3 Scale selection — declared BEFORE any game, criterion unchanged

The magnitude criterion was written to
`benchmarks/recovery/exp0055_scale_criterion.json` **before** any distribution was
measured: **p99 |Δcp| ≤ 120 and RMS Δcp < 40**, because pruning margins are
cp-calibrated (futility 110, rev-futility 85, delta 200) and exp-0049 at
RMS 111.83 cp lost ~160 Elo.

Both candidate scales were then measured with **zero exp-0055 games played**:

| scale | corpus | RMS | p99 | max | criterion |
|---|---|---|---|---|---|
| eg = 1 | all (4,000) | 7.14 | 29 | 48 | PASS |
| **eg = 2** | all (4,000) | **14.28** | **58** | 96 | **PASS** |
| **eg = 2** | endgame (1,241) | **35.66** | **106** | 128 | **PASS** |

**eg = 2 is frozen.** Rationale, recorded a priori: eg = 1's overall RMS of 7.14
is **half** of exp-0052's 13.87, and exp-0052 was **INCONCLUSIVE** at 3,200 games.
Repeating a magnitude already known to be unresolvable would waste the corpus.
eg = 2 sits close to the **CONFIRMED** threat term's 16.88 (which produced
+23.5 Elo) while staying inside the unchanged envelope on **both** corpora.

The original pre-declared values are preserved verbatim; the change is recorded
as an appended, timestamped amendment with `thresholds_changed: false`. **The
criterion was never relaxed.** The scale is now frozen: a CLOSE or INCONCLUSIVE
outcome does **not** license rescaling and re-running.

## §4 Pre-game correctness, liveness and cost evidence (all already executed)

| gate | result | artifact |
|---|---|---|
| Independent python-chess oracle | **800 positions, 0 mismatches**, 352 non-zero | `exp0055_race_oracle.json` |
| Breakdown vs live invariant, race ON | **4,000 / 0 mismatches** | recorded in §4 logs |
| Breakdown vs live invariant, race OFF | **4,000 / 0 mismatches** | — |
| Registered unit suite | **7 tests, 0 failures**; `unit` **41 / 0**; ctest **17/17** | `CMakeLists.txt` `add_test` |
| Mutation matrix (physically applied) | **10 / 10 KILLED, 0 survivors** | `exp0055_mutation_matrix.json` |
| Liveness, fixed depth 10 | **11 / 11 positions change the tree** | `exp0055_liveness.json` |
| Cost, A/A control first | spread **0.0380 < 0.10** ⇒ interpretable | `exp0055_eval_cost.json` |
| Cost, A/B increment | **+1.97 %** on full `evaluate()` | `exp0055_eval_cost.json` |
| ASan + UBSan ctest | **17/17 passed, exit 0** (84.8 s) | build-asan run |
| Shipped-default bit-exactness | **3 bench signatures unchanged** | `a289a6f0ee34a6e5` (nodes 3000) |
| Opening suite integrity | **PASS**, 0 overlap vs 199 files / 56,841 positions | `exp0055_suite_verification.json` |

The mutation set deliberately includes **`live_path_disabled`** (forces the live
gate false) and **both** clamp mutants separately, because the live path and the
breakdown path each have their own clamp. A suite that cannot kill
`live_path_disabled` cannot detect a dead mechanism; this one does.

**A measured cost dead end, and the fix.** Implemented naively as a second scan
over all pawns, the term cost **+12.36 %** on `evaluate()` (90 paired blocks,
A/A spread 0.0558). It was therefore **fused into the pawn walk that already
exists** in `features()` and already detects passers by the identical rule,
cutting the cost to **+1.97 %**. The fusion was proven **value-identical on all
4,000 positions** (pre-fusion and fused Δ vectors equal element-wise, and the
race-OFF baseline unchanged), so it is a pure optimisation, not a semantic
change. The standalone walker is retained for the breakdown path and the two are
cross-checked by the invariant above.

## §5 Frozen design, sample and openings

Fixed **TIME 40+4 ms** (never `--nodes`), Hash 16, Threads 1, max-plies 240,
`TTEval=true`, build flags `-mpopcnt -mbmi2 -mlzcnt -DSB_SEE_CACHE=1 -flto=4`.

Openings: `scripts/dev6_exp0055_openings.py`, seed **2026110655**, **1,900**
8-ply paired openings, **zero** exact final-position overlap with every earlier
committed suite, four mutually disjoint slices.

| job | games | openings | arm A | arm B | role |
|---|---|---|---|---|---|
| stage0 | 400 | 200 | candidate `params_abc` | candidate `params_abc` | control/control null + fresh ctest on the packaged binary |
| batchA | 1,500 | 750 | candidate + race | candidate, threats only | frozen primary |
| batchB | 1,500 | 750 | candidate + race | candidate, threats only | frozen primary, independent seed, disjoint openings |
| null | 400 | 200 | candidate + race | candidate + race | candidate-options null; CI must include 0 |

**Frozen combined = batchA + batchB ONLY (3,000 games).** stage0 and null are
validity instruments and are **never** pooled into the estimate.

3,000 primary games give roughly **±11 Elo** half-width — powered for the +20
ADVANCE bar and to rule out a material regression, **not** to resolve a small
effect. **INCONCLUSIVE is a plausible honest outcome and is pre-acknowledged.**

## §6 Frozen validity conditions (any failure ⇒ INVALID, not a strength result)

1. **0** forfeits, illegal moves, crashes or engine failures in every job.
2. Positive per-arm **`EvalParams loaded:`** proof on the exact binary, with the
   **per-role expected digest** (A = race config, B = threats config).
3. Both **stage0** and **null** 95% CIs **include 0**.
4. **0** exact opening-position overlap between batchA and batchB, and with every
   earlier suite.
5. Every exported blob and checksum verified; package self-contained (both
   parameter files declared in `assets`).
6. **Full PGN replay** of every game with **0** inconsistencies.
7. Fresh **ctest** on the packaged candidate binary in stage0 passes.

Independent recomputation is performed from the **raw** records by
`scripts/recovery_independent_audit.py --pgn-replay`, reading the frozen plan at
its pinned commit SHA. A green CI summary is not accepted as evidence.

## §7 Frozen decision rules (registered BEFORE any game)

- **ADVANCE** to a separately preregistered confirmation ONLY if frozen combined
  point ≥ **+20** Elo AND combined two-sided opening-clustered 95% **LCB > 0**
  AND both batches ≥ **−5** AND both null CIs include 0 AND all §6 validity
  conditions hold.
- **CLOSE (mechanism rejected)** if combined 95% **UCB < +10** Elo OR combined
  point ≤ **0**.
- **Otherwise CLOSED AS INCONCLUSIVE**: no strength claim, no default change, no
  bundle, no rescale, no retune, no confirmation, no post-hoc sample increase.
- A CLOSE or INCONCLUSIVE outcome **does not license re-scaling and re-running** —
  that is a strength sweep. The next action must be a **conceptually distinct**
  direction.
- **ADVANCE does NOT satisfy Gate 1** and authorizes no default change, PR
  strength claim, merge, tag, release or deploy. `PassedPawnRace` stays shipped
  **0** regardless of the outcome until a Gate-1 run says otherwise.

## §8 Relationship to Gate 1, and what would still be missing

exp-0054 **CONFIRMED** the threat term at **+23.5374 [+15.6937, +31.4052]** vs
dev5. That is the mission's only banked gain and it meets **neither** +75 nor
+50. Even a successful exp-0055 screen would leave the gate unmet.

Therefore, if this screen ADVANCES, the next step is a **new preregistered
confirmation measuring the INTEGRAL candidate (threats + race) DIRECTLY against
the exact released dev5 artifact**. The two Elo estimates are **never summed**:
interaction between terms is real and only a direct measurement is admissible.

Speed alone cannot close the gap (+75 needs ~1.78× nodes; the whole eval is only
~33% of node time), and no single eval term is credibly a +75 lever. Gate 1
remains **UNMET** and the mission remains **INCOMPLETE** throughout this run.

## §9 Integrity

Public identity stays **`v0.1.0-dev5`**; `VERSION` is internal. No tag, release,
merge to main, or deploy is authorized by this document. Historical artifacts and
append-only logs are preserved. The completion push stays **BLOCKED** until every
mandatory checkbox in `STOCKBEAR_COMPLETION_CHECKLIST.md` is genuinely evidenced;
commits pushed to the working branch here are the CI experiment-dispatch
mechanism, not a completion push.
