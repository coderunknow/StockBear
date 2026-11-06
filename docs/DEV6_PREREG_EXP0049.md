# DEV6 exp-0049 — expressive per-square PST, correctly scaled objective

**Status:** FROZEN candidate-development preregistration. Written and committed
**before** any exp-0049 corpus game, screen game or decisive game, and before
the exp-0049 corpus exists.

This is a **NEW hypothesis**, not a retry of exp-0048. exp-0048 is CLOSED as a
NEGATIVE result (`docs/DEV6_EXP0048_REPORT.md`); its verdict, report and ledger
entry are unchanged and are not rehabilitated by anything here.

**Authoritative acceptance criteria:** `docs/DEV6_PREREG.md` §8 and the mission
strength gate (each independent 6,600-game batch: point >= +75 Elo AND
opening-clustered 95% CI lower bound strictly > +50). The decisive measurement,
if this candidate ever qualifies, is governed by the already-frozen
`docs/DEV6_PREREG_EXP0047.md`. Nothing here weakens any of them.

---

## 1. Why this is a new hypothesis and not a retune

exp-0048 froze an objective whose **optimum was its own initialisation**. Its
L2 penalty (`1e-5`, on a *mean*-normalised loss) was the same order of magnitude
as the per-entry data gradient at ~1 cp, so the fitted table moved by at most
1.22 cp (RMS 0.124 cp). It tested "formulaic PST + sub-1.3 cp noise", not an
expressive table. That is a defect in the *objective*, discovered after closure
and recorded in `benchmarks/dev6-baseline/exp0048_results/GRADIENT_DIAGNOSIS.json`.

exp-0049 differs in three substantive, pre-declared ways:

1. **Objective scale.** The regulariser is removed (`L2 = 0`), so the table is
   fitted to the data rather than pinned to the prior.
2. **Support floor.** Entries observed fewer than 200 times in the *training*
   split are frozen at the champion's formulaic value. Adam is per-coordinate
   scale-invariant, so without this a square seen a handful of times moves as
   fast as one seen 100,000 times.
3. **Magnitude cap.** Every entry is capped at +-150 cp deviation from the
   formulaic value, an a-priori chess-plausible bound for a piece-placement
   term (and far inside the loader's +-2000 limit).

**Provenance of the `L2 = 0` choice, stated plainly:** it was informed by an
EXPLORATORY grid on the CLOSED exp-0048 corpus
(`benchmarks/dev6-baseline/exp0048_exploratory/`). That is legitimate hypothesis
generation, and it is exactly why the exp-0048 corpus and holdout are declared
**BURNED** and why exp-0049 is measured on a **fresh, disjoint** corpus its
hyperparameters never saw. The support floor and the +-150 cp cap were NOT
selected on any data: they follow from the support histogram (16 entries with
zero occurrences, 32 with <200) and from chess plausibility, respectively.

## 2. Non-repetition check (against the failure ledger)

Not a closed direction: exp-0005/0012 re-fitted the *existing scalar* weights;
exp-0026 added pawn-structure/coordination *counts*; exp-0001 was a neural
network; exp-0013 was incremental-eval bookkeeping; exp-0033..0046 were search
switches. exp-0049 is explicit per-square placement value at zero added
per-node cost. It is also not exp-0048: that entry closed a *degenerate
objective*, and its ledger entry explicitly leaves a correctly scaled
successor with its own fresh corpus open.

## 3. Frozen corpus specification (before any corpus game)

- Generator `scripts/dev6_exp0049_openings.py`, seed **2026110611**: 3,000
  8-ply openings, **zero** exact final-position overlap with all **161** earlier
  committed suites (44,441 excluded positions) — explicitly **including the
  burned exp-0048 corpus and its unused screen suites**. Master + 8 disjoint
  shard slices committed; provenance in
  `benchmarks/dev6-baseline/exp0049_corpus_suites.json`.
- Games: each opening twice with reversed colours = **6,000** self-play games,
  **40+4 ms**, Hash 16, Threads 1, max-plies 240, isolated GitHub-hosted
  `ubuntu-latest` VMs (8 shards x 750). Both sides the **immutable dev5
  champion** (`benchmarks/binaries/stockbear-dev5-release`, SHA-256
  `391cb50e13ab99168aba0255482554ab5e59d1a34af810bf8f4d2c88e5bdb918`,
  `EvalParams=research-data/params_abc.txt`, `TTEval=true`).
- Match seed **2026110613**. Extractor `scripts/build_tuning_data.py`
  (min-ply 12, sample-every 2, max 60/game, min-pieces 6, max-abs-material 1500,
  in-check excluded) — unchanged.
- Validity: every shard must finish with **ZERO** `ENGINE_FAILURE` records; a
  shard failure invalidates the export (no silent truncation). Time forfeits are
  legitimate 40+4 ms outcomes, counted and recorded, never filtered. Games
  capped at 240 plies are unadjudicated and contribute no positions.
- Split **by game**: unique combined game ids sorted ascending, shuffled with
  `random.Random(2026110612)`, first `ceil(0.2 * G)` games are holdout. The
  optimiser never sees holdout rows.
- Training/accuracy data only. Never pooled with any strength match and never
  reused as a decisive batch.

## 4. Frozen fit (all hyperparameters, before the corpus exists)

Full-batch Adam, **600 iterations**, learning rate **5.0** (centipawn units),
beta1 0.9, beta2 0.999, eps 1e-8, no schedule. Objective = mean training
logistic loss, natural log, link `p = 1/(1+10^(-s/400))`. **L2 = 0.**
Initialisation = the champion's formulaic tables. Features = signed per-square
piece counts (White minus Black; table index = square for Black, square^56 for
White), weighted by phase/24 (mg) and (24-phase)/24 (eg) using the engine's own
integer phase; the champion's non-PST score is a fixed integer offset taken
from `evaldata` counts x champion params.

Post-processing, in this order: (1) entries with training support < **200** are
reset to the formulaic value; (2) deviation from the formulaic value is clipped
to **+-150 cp**; (3) round to nearest integer, ties away from zero; (4) clip to
the loader's +-2000. **One fit, one output table. No sweep, no selection, no
second fit.**

## 5. Frozen accuracy metric and threshold

Held-out Texel log-loss `L = -mean[t*log10 p + (1-t)*log10(1-p)]`,
`p = 1/(1+10^(-s/400))`, `s` the evaluator's centipawn score from the side to
move, `t` the game result (1/0.5/0). Brier `B = mean((p-t)^2)`.

**ADVANCE only if `L_cand <= 0.97 * L_champ` (>= 3 % relative reduction) AND
`B_cand <= B_champ`**, on the same held-out games, against the champion's own
evaluator. Identical to exp-0048's threshold — it is **not** relaxed to make this
candidate pass. If unmet, exp-0047 stays DORMANT and this is recorded as a
negative candidate-development outcome.

Before any metric is reported the fitter must verify three exact identities on
**every** corpus row, or abort: (a) the champion design matrix reproduces
`evaluate()`; (b) the Python rebuild of the formulaic PST equals the engine's
PST term; (c) the engine loaded with the fitted `--pst` equals the fitted model.
Without (c) the metric would describe a Python model, not the engine that plays.

## 6. Frozen cost gate

Same binary, champion params + TTEval on both arms; candidate additionally loads
the fitted `PstFile`. `stockbear bench --nodes 300000 --hash 16
--params research-data/params_abc.txt` (+ `--pst` for the candidate), one fresh
process per arm per repetition, **3** repetitions in the order A,B / B,A / A,B
on one idle machine. Script `scripts/dev6_exp0048_nps.py` (unchanged, reused).

A position contributes iff **both** arms searched exactly 300,000 nodes;
early-terminating positions (forced mate, stalemate, bare kings) are recorded
with exact node counts but excluded from the ratio. The included set must be
identical across repetitions and cover at least half the suite. Gate:
median(candidate nps) / median(champion nps) within **[0.97, 1.03]**.

## 7. Diagnostic screen (NOT Gate 1)

Only if §5 AND §6 pass. ONE Tier-1 fixed-time screen: candidate vs exact dev5
champion, 2 x 1,000 games (batchA 500 openings x2; batchB 500 openings x2),
40+4 ms, Hash 16, Threads 1, max-plies 240, isolated VMs, match seeds
**2026110614** (A) / **2026110615** (B), 0-forfeit / 0-engine-failure validity
(any violation invalidates the screen; no retry authorised).

Suites frozen before any game: `openings_exp0049_screen_batchA.txt` and
`_batchB.txt`, drawn from the same generator RNG stream immediately after the
3,000 corpus openings — zero overlap with all earlier suites, the exp-0049
corpus, and each other.

Frozen interpretation: POSITIVE iff both batch point estimates > 0 and each
opening-clustered 95 % CI lower bound > -20 Elo; NEGATIVE iff either batch point
estimate <= 0. A positive screen feeds the exp-0047 §3.3 pre-result argument;
whether that argument clears >= +75 compatibility is decided in the Activation
Record, **not** by the screen. A negative screen closes this candidate. **No
retuning after the screen, ever.**

## 8. Expected-effect argument

Must combine the measured §5 accuracy gain, the §6 cost ratio, the §7 screen and
the historical NPS->Elo / accuracy->Elo evidence in
`benchmarks/FAILURE_LEDGER.md` into a pre-result argument that the true
fixed-time effect is compatible with >= +75 Elo. "Plausible direction" does not
satisfy exp-0047 §3.3. **A 3–5 % accuracy gain is NOT by itself evidence of
+75 Elo.** If the measured evidence cannot support >= +75, the candidate is not
activated and the mission continues with a different hypothesis.

## 9. Compute budget and stopping rules

- Corpus 6,000 games (8 isolated shards), single run.
- One fit, frozen hyperparameters, no sweep.
- Screen at most 2,000 games, single run, no retry.
- Decisive (only if activated): exp-0047's 13,200 games, single run, no retry.
- No best-of-N, no post-screen retuning, no pooling, no selective exclusion.

## 10. Activation Record (filled only if §5 + §6 + §8 are satisfied)

| field | value |
|---|---|
| corpus run id / export | *(empty — corpus not generated yet)* |
| corpus hashes (train/holdout) | *(empty)* |
| fitted PST file SHA-256 | *(empty)* |
| L_champ / L_cand / B_champ / B_cand | *(empty)* |
| support-frozen entries / capped entries | *(empty)* |
| NPS ratio (3 reps, node counts) | *(empty)* |
| screen run id / result | *(empty)* |
| expected-effect argument | *(empty)* |
| exp-0047 activation commit | *(empty)* |
