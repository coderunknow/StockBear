# exp-0052 preregistration — Tier-1 SCREEN of quadratic king-danger concentration
# FROZEN BEFORE ANY exp-0052 GAME (2026-11-06)

## §1 What this is, and what it is NOT

**This is a SCREEN, not a Gate-1 decisive run.** It asks one question: does a
superlinear king-danger term play better than the released baseline at 40+4 ms?

- It is **NOT** a retune of `KingDanger*`, **NOT** a switch ablation, **NOT** a
  repackage of ProbCut / pruning / history / time-management, and **NOT** a
  reopening of any closed experiment. exp-0048/0049/0050/0051 verdicts stand
  unchanged; the exp-0049 corpus stays **BURNED** and is not read here.
- **exp-0047 remains DORMANT.** Its activation conditions do not fit a new eval
  term, so this is registered under a new ID with its own frozen rules.
- **A positive screen does NOT satisfy Gate 1.** `docs/DEV6_PREREG.md` §8 is
  unchanged and unweakened: Gate 1 still requires point ≥ **+75** AND combined
  two-sided opening-clustered 95 % **LCB > +50** on two independent
  preregistered fixed-time batches, and Gate 4 still requires exact
  final-candidate packaged binary/source/CI linkage.

**Why this mechanism.** The existing danger term is
`KingDanger<Piece> × |attacks(piece) ∩ KingZone|`, i.e. **linear in each attacker
count**, so the total is linear in the whole attack. Measured ceilings: a lone
knight grazing the zone = 6 cp, queen = 21 cp, Q+R+B+N converging = 69 cp, with a
**constant marginal cp per additional attacker**. Real king danger is
superlinear. **No scalar value of those five parameters can express that** — this
is a representational limit, not a tuning error. Median depth at 40+4 ms is **5**
(`benchmarks/recovery/champion_depth_probe.json`), so static evaluation dominates
decisions and eval quality is most of the playing strength.

External anchors, with their original conditions: MadChess 2.0 non-linear
king-safety table **+27 Elo**; MadChess 3.0 **+63 Elo** but at 2 min + 1 s and
**bundled with a root aspiration-window change** (confounded). Stockfish's
+1.9…+3 Elo king-danger patches are **not** transferable — SF already has
non-linear danger. **Honest prior: +10…+35 Elo, reduced further by our
deliberately conservative scale (§4). No single eval term here is credibly a
+75 Elo change, and none is claimed to be.**

## §2 Frozen mechanism and arms (ONE knob, ONE configuration)

One appended `EvalParamId`, **`KingSafetyQuadratic`**, shipped **0** (default-OFF,
bit-exact). Table is 39 entries.

```
units(side) = Σ_{pt ∈ {N,B,R,Q}} weight[pt] · |attacks(pt) ∩ KingZone(enemy king)|
              weight = {N:2, B:2, R:3, Q:5}
curve(u)    = min(u, 32)² / 16
term        = KingSafetyQuadratic · curve(units)     [MIDGAME ONLY, eg = 0]
gate        = skipped entirely when the ATTACKING side has no queen
```

Attack sets are **reused from the loop that already computes them**; no attack is
recomputed. The existing linear `KingDanger*` terms remain active and unchanged.

- **Arm A (candidate):** packaged candidate binary,
  `EvalParams=research-data/params_exp0052_ks.txt`, `TTEval=true`.
  That file is champion `params_abc` **+ `KingSafetyQuadratic 1 0`** and nothing
  else. It is declared as a packaged **asset** in every job that references it.
- **Arm B (baseline):** the **exact released `v0.1.0-dev5` artifact**
  `benchmarks/binaries/stockbear-dev5-release`, SHA-256
  **`391cb50e13ab99168aba0255482554ab5e59d1a34af810bf8f4d2c88e5bdb918`**,
  `EvalParams=research-data/params_abc.txt`, `TTEval=true`.
- Hash 16, Threads 1, max-plies 240, **FIXED TIME 40+4 ms, never `--nodes`**.
- **ONE configuration.** No coefficient sweep, no cap sweep, no best-of-N. The
  scale was fixed pre-game by §4 and is not revisited after results.

## §3 Mandatory pre-result diagnostics (completed; NOT strength evidence)

- **Default-OFF bit-exactness.** All three shipped signatures unchanged:
  `243f9a1c1ba5b36f`, `a14ab62224f837e5`, `e45fa2ec2287eb41`. The **dev5 artifact
  itself was re-run and reproduces all three exactly**, and its SHA-256 was
  re-verified against the pinned digest.
- Release **ctest 15/15**; **ASan + UBSan Debug ctest 15/15** (127.39 s).
- **Independent oracle** (python-chess, generator not imported): **1,000
  positions, 0 mismatches**, 624 with a non-zero term
  (`benchmarks/recovery/exp0052_king_safety_oracle.json`).
- **Breakdown/evaluate invariant:** 3,997 positions, 0 mismatches, max|diff| 0.
- **Cost**, paired alternating-block A/B with a mandatory A/A control
  (A/A median 0.9971, spread 0.0619 ⇒ instrument usable): median **+0.65 %**,
  p10 0.9689, p90 1.0430 (`benchmarks/recovery/exp0052_eval_cost.json`). Inside
  the ≤10 % bar. The naive prototype that recomputed attacks cost **~20 %** and
  was rejected. **This is a local single-machine measurement, not a CI NPS gate.**
- **Liveness**, fixed depth 10, identical positions: **10/11** trees change,
  3 bestmoves differ, nodes −10.14 %
  (`benchmarks/recovery/exp0052_liveness.json`). Node counts at fixed depth are
  **tree-change proxies, never strength and never a speed measurement.**
- **Mutation matrix:** three mutants physically applied and each **KILLED** by
  ctest — computed-but-never-applied, linear-instead-of-quadratic, queen-gate
  removed. The latter two initially survived; shape and gate assertions were
  added, with pins derived from the oracle rather than hand-labelled.

### §3.1 Instrument fixes required before this run (zero games)

1. **`EvalParams` had the same silent-fallback hole that `PstFile` had.** On a
   missing/unreadable file the engine emits `info string … could not load` and
   **returns**, playing on with the previously active table. For exp-0052 that
   would silently replace the candidate with the shipped defaults and
   manufacture a plausible fake result. `scripts/dev6_tier1_job.py` now applies
   the exp-0051 assertion to **every file-valued option** (`PstFile` **and**
   `EvalParams`): each referenced path must be a declared asset (or the
   unconditionally packaged `params_abc.txt`), the probe must print
   `<Option> loaded: <path>`, and `could not load` must be absent.
   **Any exp-0052 job without `EvalParams LOAD VERIFIED` for both arms is an
   INVALID MEASUREMENT, not a result.**
2. The `king_safety` test group had **no `add_test()` entry**, so ctest reported
   **14/14 PASS while the test binary reported a failure**. The entry was added;
   ctest is now 15/15 and the group is confirmed present in ctest output.

## §4 Pre-declared scale criterion (the exp-0049 lesson)

exp-0049 lost ~160 Elo while *improving* held-out log-loss by 2.4712 %. Its eval
perturbation had **RMS 111.83 cp**; StockBear's pruning margins are calibrated in
centipawns (futility 110, reverse-futility 85, delta 200), so a term whose typical
swing rivals those margins **detunes the search** rather than adding information.

Declared **before any game**, on a fixed 3,000-position diagnostic corpus:

> **p99 |δ| ≤ 120 cp AND RMS δ < 40 cp.**

| Configuration | RMS δ | p99 \|δ\| | max \|δ\| | Verdict |
|---|---|---|---|---|
| divisor 8, coef 6, cap 64 | 187.85 | — | 1621 | **REJECTED pre-game** (worse than exp-0049) |
| divisor 16, coef 1, cap 64 | 31.31 | 138 | 271 | **FAIL** (p99 > 120) |
| **divisor 16, coef 1, cap 32 — FROZEN** | **13.87** | **56** | **64** | **PASS** |

Eval-score sd ratio 1.0072, mean δ −0.36 cp. Cap 32 units is the p99 of the
observed per-side attack-unit distribution (33), clipping only the extreme ~1 %
of sides. Evidence: `benchmarks/recovery/exp0052_eval_scale.json`.

**The criterion was NOT relaxed when the second configuration failed; the
implementation was tightened instead.** This scale is deliberately conservative
and **lowers the expected effect size**; that trade is intentional, because an
unattributable −160 Elo teaches less than a clean small result. **The frozen
coefficient and cap may not be changed after results.**

## §5 Frozen design, control and suites

- Four/five isolated `ubuntu-latest` VMs, one job each; independent raw-JSONL
  recomputation of W/D/L, score, CR1/t Elo, opening-clustered 95 % CI,
  terminations and Elo-from-score.
- **1,600 FRESH DISJOINT 8-ply openings**, `scripts/dev6_exp0052_openings.py`,
  seed **`2026110652`**. **Independently re-verified** by
  `scripts/recovery_verify_suites.py` (which does **not** import the generator):
  **0** exact final-position overlap with **51,241** earlier committed positions
  in **182** files, 0 duplicates, all **10** slice pairs mutually disjoint, slices
  exactly partition the master, all 6 digests recomputed from bytes and matched.
  Verdict **PASS**, 0 issues
  (`benchmarks/recovery/exp0052_suite_verification.json`). Slice digests in
  `benchmarks/dev6-baseline/exp0052_suites.json`.
- Jobs: `tier1-exp0052-stage0` 400 g seed `2026110660` (control/control validity
  null, fresh ctest on the packaged binary); `tier1-exp0052-batchA` 1,000 g seed
  `2026110661`; `tier1-exp0052-batchB` 1,000 g seed `2026110662`;
  `tier1-exp0052-null` 400 g seed `2026110663` (candidate options on BOTH sides);
  `tier1-exp0052-equiv` 400 g seed `2026110664` (**baseline-equivalence
  diagnostic**, §5.1, own disjoint 200-opening slice).
- **FROZEN COMBINED = batchA + batchB ONLY** (2,000 games). Nulls and the
  equivalence diagnostic are **never pooled**, and no earlier experiment's games
  are reused. Screen results are never pooled with any later confirmation.

### §5.1 Baseline-equivalence diagnostic (attribution, not validity)

Arm B is the exact dev5 artifact, while arm A is a dev6-lineage binary carrying
several **default-off** research features. All three bench signatures match
exactly, but bench identity is not proof of play identity. The `equiv` job
therefore plays **candidate with the knob OFF (`params_abc`) vs the exact dev5
artifact**, 400 games, same time control.

Pre-declared interpretation:

- If its CI **includes 0**, the candidate default is play-equivalent to dev5 and
  the batchA/B effect is cleanly attributable to `KingSafetyQuadratic`.
- If its CI **excludes 0**, batchA/B remains a valid *candidate-vs-dev5*
  measurement (which is what Gate 1 cares about) but is **NOT** attributable to
  this knob alone; the verdict must say so explicitly and no mechanism claim may
  be made. This job **cannot** by itself invalidate or rescue the screen.

## §6 Validity gate (enforced, not weakened)

Stage-0 and candidate-options null CIs must **both include 0**, and there must be
**0 TIME_FORFEIT / 0 ILLEGAL / 0 UCI / 0 ENGINE_FAILURE in ANY job, else INVALID
MEASUREMENT**: all Elo from that run is DISCARDED with no strength inference.
**Both arms must log `EvalParams LOAD VERIFIED`** in every job that plays
(§3.1); absence invalidates that job. The candidate's default bench signature
must equal `243f9a1c1ba5b36f` and the dev5 digest must verify, or the job aborts.

Exactly **ONE** bounded valid retry (own frozen prereg, fresh disjoint suites,
never pooled) is pre-authorised for a technical failure; a second failure CLOSES
exp-0052 AS TECHNICALLY UNRESOLVABLE. **No threshold may be weakened after
results.**

**No accuracy gate and no NPS gate is used.** Both instruments were shown invalid
(accuracy: exp-0049 improved log-loss and lost ~160 Elo; frozen NPS gate: 7/12
A/A false rejects on the shared sandbox). Fixed-time games charge every per-node
cost against the candidate, which is the quantity of interest.

## §7 Frozen decision rules (registered BEFORE any game)

- **ADVANCE** to a separately preregistered confirmation ONLY if frozen combined
  point ≥ **+20** Elo AND combined two-sided opening-clustered 95 % **LCB > 0**
  AND both batches ≥ **−5** AND both null CIs include 0 AND all §6 validity
  conditions hold.
- **CLOSE (mechanism rejected)** if combined 95 % **UCB < +10** Elo OR combined
  point ≤ **0**.
- **Otherwise CLOSED AS INCONCLUSIVE** by a single-run compute bound: no strength
  claim, no default change, no bundle, no rescale, no retune, no confirmation, no
  post-hoc sample increase.
- A CLOSE or INCONCLUSIVE outcome **does not license re-scaling the term and
  re-running it** — that would be a strength sweep. The next action would be a
  **conceptually distinct** direction (threats/hanging pieces), not a variant of
  this one.
- **ADVANCE does NOT satisfy Gate 1** and does not authorize any default change,
  PR strength claim, merge, tag, release or deploy.

## §8 Power, risks and integrity

2,000 confirmation games give ~**±13 Elo** half-width: powered for the +20
ADVANCE threshold and to rule out a material regression, **not** to resolve a
small effect. ~576 games would suffice for LCB > +50 **if** the true effect were
+75, so **candidate quality is the binding constraint, not sample size** —
spending thousands of decisive games on a term whose external anchors top out
near +63 (confounded) would be poor research economy.

Risks: (i) double-counting with the still-active linear `KingDanger*` terms;
(ii) `KingZoneBB` is coarse (~12 squares), measuring proximity more than mating
nets; (iii) a true effect of +10…+35 sits near this run's resolution, so
INCONCLUSIVE is a likely and honest outcome; (iv) eval/pruning scale interaction
— mitigated, not eliminated, by §4.

NO absolute / CCRL / FIDE Elo or gap-to-3000 claim. Public identity stays
**`v0.1.0-dev5`**: no version bump, no dev6/dev7 tag, no manufactured release. No
default change, no reopening of closed experiments, no burned-corpus reuse, no
pooling, no best-of-N, no PR/merge/tag/release/deploy while any gate is unmet. A
technical failure, invalid measurement, inconclusive result or closed result
**CANNOT terminate the mission**. Immutable dev5 baseline
`391cb50e13ab99168aba0255482554ab5e59d1a34af810bf8f4d2c88e5bdb918`, `origin/main`
and all historical evidence stay untouched. `DESIGN_LOG.md`, `AGENTS_LOG.md` and
`benchmarks/FAILURE_LEDGER.md` are append-only.
