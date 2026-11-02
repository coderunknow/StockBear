# StockBear dev4 — research log

This document records what dev4 tried, why each candidate was chosen or
rejected, and what was measured. It is deliberately written as a research log,
not as a success story: candidates that lost are listed with the same care as
the ones that were kept, because the cost of a false positive (shipping a
regression as an "improvement") is much higher than the cost of a documented
negative result.

Scope: make `0.1.0-dev4` measurably stronger than `0.1.0-dev3` under equal
thinking time, without copying another engine, without any paid service, and
without claiming anything that was not measured on this machine.

## 1. Method

Every candidate is treated as a controlled experiment:

1. **Hypothesis.** What should improve, and by roughly how much, with a
   mechanism — not just a hope that a flag helps.
2. **Implementation.** Written from scratch, guarded by a UCI option or a build
   flag so that the control arm stays available in the *same* binary. A
   candidate that cannot be switched off cannot be measured, and a candidate
   whose control arm is a different binary is measuring two things at once.
3. **Correctness.** Unit tests for the mechanism, `ctest` green, and an
   unchanged `bench` signature when the candidate is disabled (the signature is
   a node-level hash of a fixed search; if disabling a candidate changes it,
   the candidate is not actually off).
4. **Measurement.** Paired, colour-reversed matches over a fixed opening suite
   with pentanomial/opening-clustered confidence intervals, at a fixed node
   budget for speed and reproducibility. Promising or surprising results are
   re-checked at a time control.
5. **Decision.** Keep it only if the confidence interval says the effect is
   probably positive; otherwise record it as unproven and leave it disabled.

The acceptance gates are the ones stated in the project brief: `<0` regression,
`0..+49` unproven, `+50..+99` meaningful, `+100..+149` major, `>=+150`
breakthrough. A claim needs a 95% lower bound above zero, and the two upper
bands additionally need an independent confirmation match.

## 2. Audit of dev3 (what was actually weak)

The dev3 report leaves five concrete weaknesses on the table, and they set the
candidate list:

| Observation | Consequence |
| --- | --- |
| Three tuned evaluation candidates and five search configurations were all *not* stronger (dev3 shipped the dev2 code) | Adding more hand-tuned scalar terms has a poor expected return; the evaluation needs a different *representation*, not more parameters |
| The evaluation is a closed-form linear model over 32 aggregate features, tapered on a phase counter | It cannot express interactions (a rook on an open file *and* an unopposed king), which is where most real evaluation knowledge lives |
| No 50-move / progress awareness in the search, weak play at very low node counts | Real, but small at match time controls; noted as a limitation rather than a strength target |
| Depth-6 analysis blunders (`b1a3` scored +457 cp in a developed middlegame, a hanging queen missed) | Suggests the static evaluation is the binding constraint, not the search |
| dev3's own extra search features measured +1.3 Elo [−17.9, +20.5] | Search micro-optimisations at this strength are in the noise; a structural change is needed |

That audit is why dev4 puts most of its budget into a **learned evaluation**
and treats the search candidates as a secondary, cheap-to-test batch.

## 3. Candidate space

### 3.1 Learned evaluation (the main bet)

**Hypothesis.** A small incrementally-updated neural network over
piece-square features should beat a 32-parameter tapered linear evaluation by
+100 Elo or more, because it can represent interactions that the linear model
cannot, and because it is trained on the engine's own game results instead of
hand-set weights.

**Prior art considered (algorithms only, no code taken).** The feature ordering
"own perspective first, opponent second, score for the side to move" and the
incremental accumulator idea are public, well-documented NNUE techniques
(Stockfish's HalfKP family, and the earlier Shogi NNUE work). What was *not*
used: any network weights, any trained data, any source file. The feature set,
the quantisation scheme, the serialisation format, the SIMD kernels, the
trainer and the self-play generator in this repository are all written for this
project; `THIRD_PARTY.md` records that no third-party artifact was
incorporated.

**Chosen shape.** 768 features per perspective (12 piece kinds × 64 squares),
`768 → 128 → 32 → 1` with clipped ReLUs, quantised to int16 first layer and
int8/16 integer arithmetic afterwards. Rationale:

* *Why not king buckets yet?* A 64-bucket HalfKP-style input has 64× more
  parameters. With ~2.8M self-play positions on a single-core box, the bucket
  rows would be updated a few thousand times each — enough to fit noise,
  probably not enough to learn king-relative structure. Bucket count is a
  compile-time constant in this implementation, so it stays a cheap follow-up
  experiment rather than a design commitment.
* *Why not a transformer / larger net?* Inference cost per node matters at
  ~1-3 Mnps on this hardware, and training cost per position matters on one
  core. `128 → 32` is the largest shape that trains in under an hour here.
* *Why 768 rather than 640?* With a single king bucket there is no implicit
  king information in the feature index, so the kings have to be explicit
  features or the network cannot see them at all.

**The failure that dominated the effort** (documented in full in
`DEV4_TRAINING.md`): the first training runs "converged" to a constant 0.5
prediction with the loss pinned at the variance of the target. The cause was
not the optimiser, the learning rate or the initialisation — it was the input
ordering. With features ordered by *colour* (White's perspective first, always),
the same board maps to the same input whether White or Black is to move, while
the training target flips sign with the side to move. The best fit is therefore
the constant 0.5. Measured on 120,000 self-play positions: the correlation
between material (from White's point of view, the only thing a colour-ordered
input can express) and the side-to-move result is **−0.0003**, i.e. exactly
zero, whereas the correlation between material from the *side-to-move's* point
of view and that same target is **+0.572**. Ordering the two perspectives by
side to move fixed the learning entirely (validation loss 0.2187 → 0.1970 in
600 steps on a 106k-position subset, and it kept falling with more data).
This is recorded here rather than quietly fixed because it is the single most
important correctness property of the whole pipeline: it produces a network
that passes every structural test and plays at the strength of a constant
evaluation.

**Outcome.** With the ordering fixed the network trained normally (validation
MSE 0.207 → 0.147) and was quantised, embedded and measured — and it **lost by
708 Elo** (95 % CI [−1011, −405], 60 games at 2,500 nodes) against the classical
evaluation of the same binary. The evaluator, not the pipeline, is the weak link:
the corpus comes from a depth-4 engine, the labels are game results, and the
network has no king-relative inputs. The measurement is in
`DEV4_TRAINING.md` §6; the decision is in §4 below.

### 3.2 Search candidates

All of these are implemented as switchable options in the shipped binary; the
control arm is the dev3 search.

| Candidate | Mechanism | Prior expectation | Status |
| --- | --- | --- | --- |
| `ModernLMR` | log-log reduction table on depth × move index, one ply less on PV nodes, one more when not improving, one less for the first killer, clamped to `[0, depth-2]` | +10…+30 | implemented, measured |
| `MoveCountPruning` | skip late quiet moves beyond `3 + depth²` (halved when not improving) at depth ≤ 8 | +5…+15 | implemented, measured |
| `IIR` | depth ≥ 4 with no hash move → search one ply shallower first | +5…+15 | implemented, measured |
| `Improving` | track static eval per ply; if `staticEval > evalStack_[ply-2] - 10` use a wider reverse-futility margin and higher LMP limits | +5…+10 | implemented, measured |
| `TTEval` | store the static eval in the transposition table and reuse it for pruning decisions instead of re-evaluating | +2…+8, cheaper nodes | implemented, measured |
| Razoring | shallow qsearch probe before dropping into the search | +2…+8 | **declared but not implemented**; not advertised as a UCI option, so nothing can be turned on that does not work |
| Singular extensions | reduced verification search per move | +10…+25 | **rejected for dev4**: roughly doubles node cost per move and needs its own tuning to pay off; no budget left to validate it honestly |
| ProbCut | statistical pruning on a reduced-depth search | +5…+15 | **rejected**: high regression risk at this node budget, and the acceptance gate is "no regression" |
| History/countermove retuning | larger history tables, better maluses | dev3 already measured this at +1.3 [−17.9, +20.5] | **rejected as already-unproven**; the dev3 evidence stands and dev4 did not spend budget re-testing it |
| Time-management retune | better move-overhead and stability handling | +1…+5 | **rejected**: cannot be measured reliably at fixed nodes, and fixed-time matches on one core have wide intervals |

### 3.3 Rejected on principle, not on merit

| Idea | Why not |
| --- | --- |
| Symmetric multi-processing | The development machine has one physical core. Any thread count above one could not be validated, and shipping a `Threads` option that is untested on real parallel hardware would be exactly the kind of unverified claim the project forbids. `Threads` is therefore not advertised at all. |
| Syzygy tablebases | Adds a large binary data set with its own licensing and provenance burden, for an endgame gain that is invisible at the match lengths used here. |
| Opening book | Explicitly out of scope; a book hides search weakness instead of improving it and would contaminate every match. |
| External engines as training teachers | Licence review would be required for every artifact, and the engine's own self-play data is already sufficient to demonstrate the method. External engines appear only as *opponents* in match reports, never inside the binary. |
| Copying an existing NNUE implementation | Forbidden by the project's independence rule. Public algorithm descriptions were used; no code, weights or data. |

## 4. What the research changed in the engine, and what shipped

Three things were built, and the measurements decided which of them became
defaults:

1. **A learned evaluation** (`src/evaluation/nnue*`, `scripts/`), with a complete
   training pipeline, a verified quantised format, and a UCI option to select it.
   **Measured −708 Elo; not shipped enabled, and no network is embedded in the
   release binary.** The infrastructure and the evidence are shipped, because the
   next attempt should not have to build them again.
2. **Five switchable search refinements** that are standard in modern engines
   but absent from dev3. **All four measurable ones were neutral or negative**
   (fixed nodes and fixed time, with null controls); `TTEval` changes nothing
   measurable at all, and razoring was declared but never implemented, so it is
   not advertised. **All are off by default.**
3. **A measurement harness** that can actually resolve small effects:
   deterministic fixed-node play turned out to be *too* deterministic (every
   pair of a colour-reversed match scored identically, so the pentanomial had
   zero variance and the match carried no information), so the harness gained a
   seeded per-move node jitter and a 240-line random-opening suite. See
   `DEV4_BENCHMARKS.md`.

The net result is that **dev4's default play is identical to dev3's**, and the
release's value is the verified infrastructure, the negative results, and a
measurement method that can resolve the next candidate. That is stated plainly in
`DEV4_LIMITATIONS.md` §1 and in the report's verdict rather than being dressed up
as an improvement.

## 4a. Why "no change" is the correct outcome

The alternative — shipping a candidate whose interval includes zero, or a network
that loses 708 Elo, because the release "should" contain an improvement — would
be a false claim of the exact kind this project's process forbids. The two
candidates that were closest to usefulness (`IIR` at +6.6 [−32.2, +45.5] at a
fixed time control) are recorded with their intervals so a future run can
re-test them with more games instead of re-deriving them.

## 5. Open questions for dev5

* King-bucketed features (`NumBuckets > 1`) with the same pipeline, trained on
  several times more positions.
* Halfmove-clock and repetition-aware inputs; the search still reasons about
  them with ad-hoc constants.
* A vertical-flip-augmented data pipeline (currently only self-play generation
  is varied, not the training sample).
* Whether a second-stage eval refinement (same features, deeper supervision from
  longer searches) beats more self-play games per hour of CPU.
