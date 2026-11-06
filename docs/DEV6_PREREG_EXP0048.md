# DEV6 exp-0048 — full per-square piece-square evaluator (candidate development)

**Status:** FROZEN candidate-development preregistration. Written and committed
**before** any exp-0048 corpus game, screen game, or decisive game. This is a
*new, materially different* hypothesis, not a retry of any closed experiment.
The decisive Gate-1 measurement, if this candidate qualifies, is governed by the
already-frozen `docs/DEV6_PREREG_EXP0047.md` (2 x 6,600 games, +75 / LCB > +50 per
batch, no retry). exp-0048 covers only the *candidate development and diagnostic
screen* that must precede activation of exp-0047.

**Authoritative acceptance criteria:** `docs/DEV6_PREREG.md` §8 and the mission
strength gate (each independent 6,600-game batch: point >= +75 Elo AND two-sided
opening-clustered 95% CI lower bound strictly > +50). Nothing here weakens them.

---

## 1. Hypothesis and causal mechanism

**H:** replacing the champion's *formulaic* piece-square term (a handful of
rank/file/centre coefficients per piece) with a **full per-square table** (an
explicit middlegame and endgame value for every piece type on every square),
fitted to StockBear's own bullet-time self-play outcomes, is a *materially
stronger evaluator* at fixed time 40+4 ms.

**Mechanism:** the formulaic PST cannot express square-specific knowledge
(e.g. a knight is bad on the rim but the formula only sees centrality; a rook on
the 7th, king shelter squares, piece-specific good/bad squares). A full table
can. Crucially the per-node cost is **unchanged**: the engine already adds a
`PieceSquareMg/Eg[pt][idx]` lookup to its material accumulator; the candidate
only changes the *numbers in that lookup table*, not the work done. This is why
the candidate can pass the exp-0047 §3 cost gate (`[0.97, 1.03]` NPS) that a
neural or attack-recomputing evaluator cannot.

The candidate is delivered as the default-OFF `PstFile` UCI option (implemented
this cycle, `src/evaluation/evaluation.cpp`, `src/uci/uci.cpp`). With no file the
tables are exactly the shipped formulaic ones: bench `243f9a1c1ba5b36f`,
`bench --depth 16` `a14ab62224f837e5`, bit-identical (unit group `pst` proves a
formulaic-valued file reproduces the default evaluation exactly).

## 2. Non-repetition check (against the failure ledger)

This is **not** any closed direction:
- exp-0005 / exp-0012 (outcome/bullet *retune*): those tuned the *existing scalar*
  feature weights (including the ~15 formulaic PST coefficients). exp-0048
  introduces a *new feature family* — 6 pieces x 64 squares x 2 phases of
  independent placement values — not a re-fit of the old scalars.
- exp-0026 (six extended pawn/coordination features): those are pawn-structure /
  coordination counts (rook-on-7th, outpost, backward, chain, connected passed,
  rook-behind-passed). exp-0048 is *piece-placement value*, a different term; the
  six features stay at their champion values and are not re-tuned.
- exp-0001 (small CPU NNUE): no network, no inference cost, no training of a
  neural net; a linear table lookup at zero added per-node cost.
- exp-0013 (incremental eval): no per-move delta bookkeeping; the accumulator
  mechanism is unchanged.
- exp-0036 / exp-0038 / exp-0041…0046 (search switches): no search change at all.

## 3. Frozen corpus specification (before any corpus game)

- Generator: `scripts/dev6_exp0048_openings.py`, seed **2026110601**, **3,000**
  8-ply openings, ZERO exact final-position overlap with all 150 earlier suites
  (40,441 excluded positions); master + 8 disjoint shard slices committed.
- Games: each opening played twice with reversed colours = **6,000** self-play
  games, **40+4 ms**, Hash 16, Threads 1, max-plies 240, on isolated
  GitHub-hosted `ubuntu-latest` VMs (8 shards). Both sides are the **immutable
  dev5 champion** (`benchmarks/binaries/stockbear-dev5-release`, SHA
  `391cb50e…`, `EvalParams=research-data/params_abc.txt`, `TTEval=true`).
- Match shuffle seed: **2026110603** (identical on every shard; shards have
  disjoint opening slices). Driver: `scripts/tournament.py` unmodified.
- Positions: `scripts/build_tuning_data.py` (min-ply 12, sample-every 2,
  max 60/game, min-pieces 6, max-abs-material 1500, in-check positions excluded),
  labelled with the game outcome from the side to move.
- Corpus validity (frozen): every shard must complete its 750 games with ZERO
  `ENGINE_FAILURE` records; a shard failure invalidates the corpus export (no
  silent truncation). Time forfeits, if any, are legitimate 40+4 ms outcomes
  under the harness's existing symmetric policy and are counted and recorded in
  the export manifest; the ZERO-forfeit rule of exp-0047 §9 applies to the
  decisive run, not to this training corpus. Games capped at 240 plies are
  unadjudicated and contribute no positions (existing `build_tuning_data.py`
  behaviour, unchanged).
- Train/holdout split **by game**: unique combined game ids sorted
  ascending, shuffled with `random.Random(2026110602)`, first `ceil(0.2 * G)`
  games are the holdout. The optimiser never sees holdout positions.
- This corpus is for **evaluator fitting and accuracy measurement only**. It is
  never pooled with any strength match and never reused as a decisive batch.

## 4. Frozen accuracy metric and threshold (before corpus generation)

Let `L_champ` and `L_cand` be the mean **held-out** logistic (Texel) loss
`-mean[t*log10(p) + (1-t)*log10(1-p)]` with `p = 1/(1+10^(-s/400))`, `s` the
evaluator's centipawn score from the side to move and `t` the game result
(1/0.5/0), on the *same* held-out games the optimiser never saw. Let `B` be the
held-out Brier score `mean((p - t)^2)`.

**Activation accuracy threshold (frozen):** the candidate PST evaluator must
achieve `L_cand <= 0.97 * L_champ` (>= 3% relative held-out log-loss reduction)
**and** `B_cand <= B_champ`. The PST is fitted on the training games only; the
champion comparison uses the champion's own evaluator on the identical holdout.
If the threshold is not met, exp-0047 stays DORMANT for this candidate and the
result is recorded as a negative/inconclusive candidate-development outcome.

## 5. Frozen cost gate

Matched-toolchain NPS of the candidate configuration (same binary, PstFile
loaded + champion params + TTEval) vs the champion configuration (same binary,
champion params + TTEval), **bit-identical node counts**, >= 3 alternating
repetitions, ratio within `[0.97, 1.03]` (exp-0047 §3.2). Because only table
*values* change, the expected ratio is ~1.0; a ratio outside the band
invalidates the candidate.

Identical-node measurement (frozen): the 12 standard bench FENs
(`benchmarks/positions/search.inc`), via
`stockbear bench --nodes 300000 --hash 16 --params research-data/params_abc.txt`
plus `--pst <table>` for the candidate arm. One fresh process per arm per
repetition, 3 repetitions in the order A,B / B,A / A,B on one idle machine.
Script: `scripts/dev6_exp0048_nps.py`. NPS per arm = total included nodes /
summed engine-reported `time_us`; gate on
median(candidate NPS) / median(champion NPS).

Structural inclusion rule: a position contributes iff BOTH arms searched
exactly 300,000 nodes. Positions where either arm terminated early (forced
mate, stalemate, bare kings) are recorded with their exact node counts but
excluded from the ratio — a search that ends at a forced terminal does not
measure evaluator throughput. The included set must be identical across all
repetitions and cover at least half the suite. This rule depends only on node
counts, never on which arm was faster.

**Protocol correction, recorded before the freeze commit and before any real
exp-0048 data existed.** The first draft of this section specified a UCI
`go nodes` loop. A smoke test on a throwaway 48-game synthetic corpus showed
that the UCI `info` line reports the node count of the last *completed*
iteration, so a node-limited UCI search reports a different, eval-dependent
total per arm (1,853,814 vs 1,393,400) and the identical-count requirement is
unsatisfiable that way. `bench --nodes` reports the true searched count, which
is exactly N for every position reaching the budget. The correction was made
for that mechanical reason, on synthetic data, before the corpus was generated
and before any candidate was fitted; it is not a response to any exp-0048
result. Fixed *depth* is likewise unusable: identical node counts are
impossible once eval values differ.

## 6. Diagnostic screen (separate from the decisive gate)

After fitting, ONE Tier-1 fixed-time diagnostic screen may be run: candidate
(PstFile + champion params + TTEval) vs exact dev5 champion, 2 x 1,000 games
(batchA: 500 openings x 2; batchB: 500 openings x 2), 40+4 ms, Hash 16,
Threads 1, max-plies 240, isolated VMs, match seeds 2026110604 (A) / 2026110605
(B), 0-forfeit / 0-engine-failure validity (any violation invalidates the
screen; no retry is authorised by this prereg).

Screen suites (frozen before any game): `openings_exp0048_screen_batchA.txt`
and `openings_exp0048_screen_batchB.txt`, produced by
`scripts/dev6_exp0048_openings.py` from the SAME generator RNG stream
immediately after the 3,000 corpus openings: zero overlap with all 150 earlier
committed suites, with each other, and with the corpus openings. (Overlap with
the *corpus* is not required — the corpus is fitting data, never match evidence
— but the generator makes them disjoint anyway.)

This screen is a *diagnostic*, NOT Gate 1. Frozen interpretation rule: the
screen is POSITIVE iff both batches have point estimate > 0 and the
opening-clustered 95% CI of each batch excludes catastrophic regression
(lower bound > -20 Elo); it is NEGATIVE iff either batch point estimate <= 0.
A positive screen plus the §4 accuracy and §5 cost evidence feeds the
pre-result argument required to activate exp-0047; whether that argument
clears exp-0047 §3.3 (>= +75 compatibility) is decided in the activation
record, NOT by the screen alone. A negative screen closes this candidate
(no decisive run). No retuning after the screen, ever.

## 7. Expected-effect argument (to be completed from measured evidence)

The activation record must combine the measured §4 accuracy improvement, the §5
cost ratio, the §6 screen, and the historical NPS->Elo / accuracy->Elo evidence
in `benchmarks/FAILURE_LEDGER.md` into a pre-result argument that the true
fixed-time effect is compatible with >= +75 Elo. "Plausible direction" alone does
not satisfy exp-0047 §3.3. If the measured evidence cannot support >= +75, the
candidate is not activated and the mission continues with a different hypothesis.

## 8. Compute budget and stopping rules

- Corpus: 6,000 games (8 isolated shards), single run.
- Fitting (ALL hyperparameters frozen here, before the corpus exists):
  full-batch Adam, 300 iterations, learning rate 5.0 (centipawn units),
  beta1 0.9, beta2 0.999, eps 1e-8, no learning-rate schedule; objective =
  mean training logistic loss (natural log, link p = 1/(1+10^(-s/400))) plus
  L2 penalty `1e-5 * sum(delta^2)` on deviations from the champion's formulaic
  PST values (the initialisation). Features: signed per-square piece counts
  (White minus Black, table index = square for Black, square^56 for White),
  weighted by phase/24 (mg) and (24-phase)/24 (eg) with the engine's own
  integer phase; the champion's non-PST score (engine integer arithmetic,
  from `evaldata` counts x champion params) is a fixed offset. Final tables =
  round(initial + delta) to nearest integer, ties away from zero, clipped to
  the loader's [-2000, 2000]. One fit, one output file; no sweep, no selection.
- Screen: at most 2,000 games, single run, no retry.
- Decisive (only if activated): exp-0047's 13,200 games, single run, no retry.
- No best-of-N selection, no post-hoc retuning after a screen, no pooling.

## 9. Activation Record (filled only if §4 + §5 + §7 are satisfied)

| field | value |
|---|---|
| corpus run id / export | *(empty — not generated yet)* |
| corpus hashes (train/holdout) | *(empty)* |
| fitted PST file SHA-256 | *(empty)* |
| L_champ / L_cand / B_champ / B_cand | *(empty)* |
| NPS ratio (3 reps, node counts) | *(empty)* |
| screen run id / result | *(empty)* |
| expected-effect argument | *(empty)* |
| exp-0047 activation commit | *(empty)* |
