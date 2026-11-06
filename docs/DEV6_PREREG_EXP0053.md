# exp-0053 preregistration — Tier-1 SCREEN of threat / material-exposure detection
# FROZEN BEFORE ANY exp-0053 GAME (2026-11-06)

## §1 What this is, and what it is NOT

**This is a SCREEN, not a Gate-1 decisive run.** One question: does rewarding
threats against undefended and pawn-attacked enemy pieces play better than the
released champion at 40+4 ms?

- It is **NOT** a retune, **NOT** a switch ablation, **NOT** a repackage of
  ProbCut / pruning / history / time management, and **NOT** a reopening of any
  closed experiment. exp-0048/0049/0050/0051/0052 verdicts stand unchanged. The
  exp-0049 corpus stays **BURNED**; exp-0052's openings and games are **not**
  reused or pooled.
- **exp-0047 remains DORMANT.**
- **A positive screen does NOT satisfy Gate 1.** The governing gate is unchanged:
  `docs/DEV6_PREREG.md` §8 — combined point ≥ **+75** AND combined two-sided
  opening-clustered 95% **LCB strictly > +50** against the exact released
  `v0.1.0-dev5` artifact. The user reconfirmed this on 2026-11-06 ("dev6 and 75+
  elo compared to baseline"); the dev4 wording in the interim directive was
  withdrawn as carry-over context.

**Why this mechanism.** StockBear has **no threat term at all**. An undefended
enemy piece, or one attacked by a pawn, is invisible to static evaluation. At
**median depth 5** (`benchmarks/recovery/champion_depth_probe.json`) static eval
dominates decisions, so material exposure that the search does not resolve is
simply not scored. This is conceptually distinct from exp-0052 (king-local
danger) and from the abandoned exp-0026 six-feature bundle (which contained no
threat term).

**Honest prior.** No clean isolated public Elo number was found for a threat term.
Stockfish's classical magnitudes (ThreatBySafePawn S(175,168), Hanging S(52,30))
establish that strong engines value these situations materially, and a
Stockfish developer describes threats as a "really important heuristic that is
always overlooked" — but that is a scale reference, **not** an effect size. Prior:
**+0 to +40 Elo**, weaker in evidence quality than exp-0052's was. **This does not
reach Gate 1 alone and is not presented as if it does.**

## §2 Frozen mechanism and arms (ONE knob, ONE configuration)

One appended `EvalParamId`, **`ThreatDetection`**, shipped **0** (default-OFF,
bit-exact). Table is 40 entries.

```
by[c]      = union of attacks by colour c's P,N,B,R,Q
byPawn[c]  = union of attacks by colour c's pawns
atkUs      = by[us]   | king attacks of us
defThem    = by[them] | king attacks of them
hanging    = enemy NON-PAWN pieces & atkUs & ~defThem
pawnThreat = ANY enemy piece & byPawn[us]
units(us)  = min(10*|hanging| + 16*|pawnThreat|, 64)
term       = ThreatDetection · (units(White) - units(Black))   [mg AND eg]
```

Fixed internal weights (10 / 16) and a fixed cap (64) with **one** scale
parameter, so the experiment has a single attributable knob.

**Cost design, and a measured dead end that shaped it.** A shared per-square
attack table was implemented first, verified bit-exact, and measured
**~19.5% SLOWER** across 90 paired blocks: storing/reloading 512 bytes cost more
than the magic-lookup recomputation it replaced. It was **reverted**. Instead the
union masks are accumulated with a few ORs **inside the loops that already
generate these attacks** (the mobility loop and the king-danger loop), and the
threat term itself is pure popcount work. Measured cost **+1.97%**.

- **Arm A (candidate):** packaged candidate binary,
  `EvalParams=research-data/params_exp0053_threats.txt`, `TTEval=true`.
  That file is champion `params_abc` **+ `ThreatDetection 1 1`** and nothing else.
  `KingSafetyQuadratic` is absent and therefore **0**, so exp-0052's feature is
  OFF and any effect is attributable to threats alone. Declared as a packaged
  **asset** in every job that references it.
- **Arm B (baseline):** the **exact released `v0.1.0-dev5` artifact**
  `benchmarks/binaries/stockbear-dev5-release`, SHA-256
  **`391cb50e13ab99168aba0255482554ab5e59d1a34af810bf8f4d2c88e5bdb918`**,
  `EvalParams=research-data/params_abc.txt`, `TTEval=true`.
- Hash 16, Threads 1, max-plies 240, **FIXED TIME 40+4 ms, never `--nodes`**.
- **ONE configuration.** No weight sweep, no cap sweep, no best-of-N.

## §3 Pre-result diagnostics (completed; NOT strength evidence)

- **Default-OFF bit-exactness:** all three shipped signatures unchanged —
  `243f9a1c1ba5b36f`, `a14ab62224f837e5`, `e45fa2ec2287eb41`.
- Release **ctest 16/16**; the `threats` group is confirmed present in CTest
  output as test #8 (the exp-0052 lesson: an unregistered group is silently
  skipped). The test binary was also run directly: **exit 0, 8 tests, 0 failures**.
- **ASan + UBSan Debug ctest 16/16** (132.96 s).
- **Independent oracle** (`scripts/check_threats.py`, python-chess, shares no code
  with the engine): **800 positions, 0 mismatches**, 566 non-zero
  (`benchmarks/recovery/exp0053_threat_oracle.json`).
- **Breakdown/evaluate invariant:** 3,997 positions, 0 mismatches, max|diff| 0,
  with threats **ON and OFF**. The hot path fuses union accumulation into
  existing loops while `eval_breakdown` uses an **independent** union builder, so
  this genuinely cross-checks the fusion.
- **Mutation matrix:** **7 mutants physically applied, all 7 KILLED**, zero
  survivors, source restored and verified
  (`benchmarks/recovery/exp0053_mutation_matrix.json`): computed-but-never-applied,
  defended-mask removed, pawn component removed, hanging component removed, cap
  removed, pawns counted as hanging targets, sign flipped. Test positions were
  **derived from the oracle** by searching for cases that discriminate one
  component each — not hand-labelled.
- **Cost**, paired alternating blocks with a mandatory A/A control (A/A spread
  0.0598 ⇒ usable): median **+1.97%**, p10 0.9759, p90 1.0784
  (`benchmarks/recovery/exp0053_eval_cost.json`). Inside the ≤10% bar. Local
  single-machine measurement, **not** a CI NPS gate.
- **Liveness**, fixed depth 10, identical positions: **11/11** trees change,
  3 bestmoves differ, nodes −10.43%
  (`benchmarks/recovery/exp0053_liveness.json`). Tree-change proxy only; **never**
  a strength or speed measurement.

### §3.1 Instrument guarantees inherited and re-applied

`scripts/dev6_tier1_job.py` asserts, per arm, that **every file-valued option**
(`EvalParams`, `PstFile`) is a declared asset (or the unconditionally packaged
`params_abc.txt`), that the probe prints `<Option> loaded: <path>`, and that
`could not load` is absent. A missing params file is **not** fatal to the engine —
it plays on with the previous table and would manufacture a fake result. **Any
exp-0053 job without `EvalParams LOAD VERIFIED` for both arms is an INVALID
MEASUREMENT, not a result.** All four guard branches were exercised on the real
runner at zero games for exp-0052 and the guard is unchanged.

## §4 Pre-declared scale criterion

Declared **before** any distribution measurement, in
`benchmarks/recovery/exp0053_scale_criterion.json`:

> **p99 |δ| ≤ 120 cp AND RMS δ < 40 cp** on a fixed 3,000-position corpus.

Rationale: pruning margins are cp-calibrated (futility 110, reverse-futility 85,
delta 200). exp-0049 perturbed eval at RMS **111.83 cp** and lost ~160 Elo despite
better log-loss.

Measured: **RMS 16.88 cp, p99 46, max 64, mean −0.13, sd ratio 0.9981** →
**PASS on the first attempt** (`benchmarks/recovery/exp0053_eval_scale.json`).
No rescaling was performed, so no criterion was adjusted after seeing data.
**The frozen weights, cap and coefficient may not be changed after results.**

## §5 Frozen design, control and suites

- Five isolated `ubuntu-latest` VMs, one job each; independent raw-JSONL
  recomputation of W/D/L, score, CR1/t Elo, opening-clustered 95% CI,
  terminations and Elo-from-score.
- **1,600 FRESH DISJOINT 8-ply openings**, `scripts/dev6_exp0053_openings.py`,
  seed **`2026110653`**. **Independently re-verified** by
  `scripts/recovery_verify_suites.py` (does **not** import the generator):
  **0** overlap with **52,841** earlier committed positions in **188** files,
  0 duplicates, all **10** slice pairs mutually disjoint, slices exactly
  partition the master, all 6 digests recomputed from bytes. Verdict **PASS**,
  0 issues (`benchmarks/recovery/exp0053_suite_verification.json`).
- Jobs: `stage0` 400 g seed `2026110670` (control/control validity null + fresh
  ctest on the packaged binary); `batchA` 1,000 g seed `2026110671`;
  `batchB` 1,000 g seed `2026110672`; `null` 400 g seed `2026110673`
  (candidate options on BOTH sides); `equiv` 400 g seed `2026110674`
  (baseline-equivalence diagnostic, §5.1).
- **FROZEN COMBINED = batchA + batchB ONLY** (2,000 games). Nulls and the
  equivalence diagnostic are **never pooled**. No earlier experiment's games are
  reused. Screen results are never pooled with any later confirmation.

### §5.1 Baseline-equivalence diagnostic (attribution, not validity)

Arm B is the exact dev5 artifact while arm A is a dev6-lineage binary carrying
several default-off features. All three bench signatures match, but bench
identity is not proof of play identity. `equiv` plays **candidate with the knob
OFF (`params_abc`) vs the exact dev5 artifact**, 400 games, same time control.

- CI **includes 0** ⇒ candidate default is play-equivalent to dev5; the batch
  effect is cleanly attributable to `ThreatDetection`.
- CI **excludes 0** ⇒ batchA/B remains a valid candidate-vs-dev5 measurement but
  is **NOT** attributable to this knob alone, and the verdict must say so.
- This job can neither invalidate nor rescue the screen.

## §6 Validity gate (enforced, not weakened)

Stage-0 and candidate-options null CIs must **both include 0**, and there must be
**0 TIME_FORFEIT / 0 ILLEGAL / 0 UCI / 0 ENGINE_FAILURE in ANY job, else INVALID
MEASUREMENT** — all Elo from that run is DISCARDED with no strength inference.
**Both arms must log `EvalParams LOAD VERIFIED`** in every job that plays. The
candidate's default bench signature must equal `243f9a1c1ba5b36f` and the dev5
digest must verify, or the job aborts.

Exactly **ONE** bounded valid retry (own frozen prereg, fresh disjoint suites,
never pooled) is pre-authorised for a technical failure; a second failure CLOSES
exp-0053 AS TECHNICALLY UNRESOLVABLE. **No threshold may be weakened after
results.**

**No accuracy gate and no NPS gate is used** — both instruments were shown invalid
(exp-0049 improved log-loss and lost ~160 Elo; the frozen NPS gate false-rejected
7/12 A/A pairs). Fixed-time games charge every per-node cost against the candidate.

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
  strength claim, merge, tag, release or deploy.

## §8 Power, risks and integrity

2,000 games give ~**±13 Elo** half-width: powered for the +20 ADVANCE bar and to
rule out a material regression, **not** to resolve a small effect. INCONCLUSIVE is
a plausible honest outcome and is pre-acknowledged.

Risks: (i) threats overlap with search — at depth 5 many are already resolved
tactically, so the term may be partly redundant; (ii) interaction with SEE-based
capture ordering and the cp-calibrated delta margin; (iii) the fixed 10/16 weights
are a scale choice, not a fit, and may be wrong in either direction; (iv) a true
effect of +0…+40 straddles this run's resolution.

**Strategic disclosure.** exp-0050, exp-0051 and exp-0052 produced no confirmed
gain. Adding small eval terms one at a time is **not** by itself a credible route
to +75, and this experiment is not claimed to be one. It is the next distinct
mechanism test, run cheaply, with a pre-declared stopping rule.

NO absolute / CCRL / FIDE Elo claim. Public identity stays **`v0.1.0-dev5`**: no
version bump, no dev6/dev7 tag, no release, no deploy. No default change, no
reopening of closed experiments, no burned-corpus reuse, no pooling, no best-of-N.
A technical failure, invalid measurement, inconclusive or closed result **CANNOT
terminate the mission**. Immutable dev5 baseline
`391cb50e13ab99168aba0255482554ab5e59d1a34af810bf8f4d2c88e5bdb918`, `origin/main`
and all historical evidence stay untouched. `DESIGN_LOG.md`, `AGENTS_LOG.md` and
`benchmarks/FAILURE_LEDGER.md` are append-only. Mission completion is governed
solely by `STOCKBEAR_COMPLETION_CHECKLIST.md`.
