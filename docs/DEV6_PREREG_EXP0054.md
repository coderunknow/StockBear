# exp-0054 preregistration — CONFIRMATION of threat / material-exposure detection
# FROZEN BEFORE ANY exp-0054 GAME (2026-11-06)

## §1 What this is, and what it is NOT

**This is the independent CONFIRMATION of the exp-0053 screen**, which met every
preregistered ADVANCE condition. It is a fresh, higher-power measurement of the
**same frozen configuration**, on **fresh disjoint openings**, with its own
frozen decision rules.

- **exp-0053's games are NEVER pooled with this confirmation.** A screen estimate
  and a confirmation estimate are different instruments; combining them would
  inflate confidence and is explicitly forbidden by the exp-0053 prereg §5.
- **No configuration change.** The candidate is byte-identical in behaviour to the
  screened one: `ThreatDetection 1 1`, weights 10/16, cap 64. Nothing is retuned,
  rescaled or re-fitted between screen and confirmation.
- **This is NOT a Gate-1 decisive run.** Gate 1 remains combined point ≥ **+75**
  AND two-sided opening-clustered 95% **LCB strictly > +50** vs the exact released
  `v0.1.0-dev5` artifact (`docs/DEV6_PREREG.md` §8, reconfirmed by the user
  2026-11-06). A confirmed ~+25 Elo term **does not** reach it.
- exp-0048/0049/0050/0051/0052/0053 verdicts stand unchanged. **exp-0047 DORMANT.**

### Why a confirmation is required rather than banking the screen

exp-0053 measured **+24.6338 Elo, 95% CI [+13.1027, +36.2193]** over 2,000 games
(996 opening clusters), with batchA **+34.72** and batchB **+14.63**. The two
batches differ by ~20 Elo, which is within sampling noise at that size but is
exactly the pattern that a single favourable screen can produce. The
baseline-equivalence diagnostic included 0 (**+1.75 [−20.65, +24.15]**), so
attribution to the knob is clean, but a screen is a *selection* instrument and
selection inflates the winner. Only an independent confirmation on untouched
openings can establish the effect.

## §2 Frozen candidate and baseline (identical to the screened configuration)

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

- **Arm A:** packaged candidate binary,
  `EvalParams=research-data/params_exp0053_threats.txt`, `TTEval=true`.
  That file is champion `params_abc` **+ `ThreatDetection 1 1`** and nothing else;
  its SHA-256 is pinned in the plan. `KingSafetyQuadratic` is absent and therefore
  **0**, so exp-0052's feature stays OFF. Declared as a packaged **asset**.
- **Arm B:** the **exact released `v0.1.0-dev5` artifact**, SHA-256
  **`391cb50e13ab99168aba0255482554ab5e59d1a34af810bf8f4d2c88e5bdb918`**,
  `EvalParams=research-data/params_abc.txt`, `TTEval=true`.
- Hash 16, Threads 1, max-plies 240, **FIXED TIME 40+4 ms, never `--nodes`**.
- The candidate source is pinned by the plan's `source_sha`; the runner rebuilds
  from it and asserts the default bench signature `243f9a1c1ba5b36f`.

## §3 Pre-result evidence (already established for this exact configuration)

Carried forward from exp-0053 because the configuration is unchanged; **none of
this is strength evidence**:

- All three shipped bench signatures bit-exact (default-OFF).
- Release ctest **16/16**; `threats` registered as test #8; binary run directly
  (exit 0, 8 tests, 0 failures). ASan+UBSan **16/16**.
- Independent python-chess oracle: **800 positions, 0 mismatches**.
- Breakdown/evaluate invariant: **3,997 positions, 0 mismatches**, term ON and OFF.
- **7 mutants applied, all 7 KILLED**, zero survivors.
- Scale criterion pre-declared, PASS first attempt: RMS **16.88 cp**, p99 **46**,
  max **64**. Cost **+1.97%** (A/A control spread 0.0598). Liveness **11/11**.

The confirmation job re-runs ctest on the packaged binary in `stage0`.

## §4 Frozen design, suites and power

- **2,400 FRESH DISJOINT 8-ply openings**, `scripts/dev6_exp0054_openings.py`,
  seed **`2026110654`**. Independently re-verified by
  `scripts/recovery_verify_suites.py` (does **not** import the generator):
  **0** overlap with **54,441** earlier committed positions in **194** files
  (including every exp-0053 suite), 0 duplicates, all **6** slice pairs mutually
  disjoint, slices exactly partition the master, all digests recomputed from
  bytes. Verdict **PASS**, 0 issues
  (`benchmarks/recovery/exp0054_suite_verification.json`).
- Jobs: `stage0` 400 g seed `2026110680` (control/control validity null + fresh
  ctest); `batchA` **2,000 g** seed `2026110681`; `batchB` **2,000 g** seed
  `2026110682`; `null` 400 g seed `2026110683` (candidate options on BOTH sides).
- **FROZEN COMBINED = batchA + batchB ONLY = 4,000 games.** Nulls never pooled.
- **Power rationale.** 2,000 games gave ~±13 Elo half-width; 4,000 gives ~**±9 Elo**.
  At the screened effect (~+25) that puts the LCB near **+16**, comfortably above
  0, and it can distinguish a real ~+25 from a null. It is deliberately **not**
  sized to resolve Gate 1, because a single term is not expected to reach +75;
  spending Gate-1-scale compute here would be poor research economy.
- Four isolated `ubuntu-latest` VMs, one job each. Independent raw-JSONL
  recomputation of W/D/L, score, CR1/t Elo, opening-clustered 95% CI,
  terminations, Elo-from-score, and full PGN replay.

## §5 Validity gate (enforced, not weakened)

Stage-0 and candidate-options null CIs must **both include 0**, and there must be
**0 TIME_FORFEIT / 0 ILLEGAL / 0 UCI / 0 ENGINE_FAILURE in ANY job, else INVALID
MEASUREMENT** — all Elo from that run is DISCARDED with no strength inference.
**Both arms must log `EvalParams LOAD VERIFIED`** in every job that plays; a
missing params file is not fatal to the engine and would fake a result. The
candidate's default bench signature must equal `243f9a1c1ba5b36f` and the dev5
digest must verify, or the job aborts. Every final PGN must replay with 0
inconsistencies, and all committed blob/per-job checksums must verify.

Exactly **ONE** bounded valid retry (own frozen prereg, fresh disjoint suites,
never pooled) is pre-authorised for a technical failure; a second failure CLOSES
exp-0054 AS TECHNICALLY UNRESOLVABLE. **No threshold may be weakened after
results.** No accuracy gate and no NPS gate is used.

## §6 Frozen decision rules (registered BEFORE any game)

- **CONFIRMED IMPROVEMENT** if frozen combined point ≥ **+10** Elo AND combined
  two-sided opening-clustered 95% **LCB > 0** AND both batches ≥ **−5** AND both
  null CIs include 0 AND all §5 validity conditions hold.
  → The threat term becomes a **banked, independently confirmed** improvement,
  eligible for inclusion in an integrated final candidate. It remains
  default-OFF until an integrated candidate passes Gate 1.
- **REJECTED** if combined 95% **UCB < +5** Elo OR combined point ≤ **0**.
  → The screen is recorded as a selection artefact; the feature stays OFF and the
  direction is closed.
- **Otherwise INCONCLUSIVE**: no strength claim, no banking, no default change,
  no pooling with the screen, no post-hoc sample increase, no rescale.
- **Under no outcome** may the screen and confirmation estimates be averaged or
  pooled, and **no outcome satisfies Gate 1**. The final integrated candidate
  must be measured **directly** against the released baseline; combined strength
  may never be inferred by adding per-component Elo estimates.

## §7 Risks and integrity

The principal risk is **regression to the mean**: exp-0053 was selected because it
advanced, so its +24.6 is an upward-biased estimate of the true effect. The +10
CONFIRMED bar is set well below the screen point estimate for exactly this reason.
Secondary risks: batch-level heterogeneity (the screen's batches differed by
~20 Elo), and the fixed 10/16 weights being a scale choice rather than a fit.

NO absolute / CCRL / FIDE Elo claim. Public identity stays **`v0.1.0-dev5`**: no
version bump, no dev6/dev7 tag, no release, no deploy, no merge. No reopening of
closed experiments, no burned-corpus reuse, no best-of-N. A technical failure,
invalid measurement, inconclusive or rejected result **CANNOT terminate the
mission**. Immutable dev5 baseline
`391cb50e13ab99168aba0255482554ab5e59d1a34af810bf8f4d2c88e5bdb918`, `origin/main`
and all historical evidence stay untouched. `DESIGN_LOG.md`, `AGENTS_LOG.md` and
`benchmarks/FAILURE_LEDGER.md` are append-only. Mission completion is governed
solely by `STOCKBEAR_COMPLETION_CHECKLIST.md`.
