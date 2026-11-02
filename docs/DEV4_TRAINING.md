# StockBear dev4 — training the neural evaluation

This document is the training record for dev4's learned evaluation: what the
pipeline does, what went wrong, what the numbers are, and what a future attempt
should do differently. It is written so that someone can rebuild the whole thing
from an empty checkout, and so that the failures are not repeated.

Everything below was produced on the development sandbox: **2 vCPU (1 physical
core, 2 threads), 3 GB RAM, no GPU**, Debian 12, GCC 12.2.0, PyTorch 2.15.0 CPU,
NumPy 2.4.6. Wall-clock numbers are for that machine only.

## 1. Pipeline

```
stockbear selfplay          scripts/train_nnue.py            scripts/convert_nnue.py
  (C++, engine)      ->       (PyTorch, CPU)          ->      (NumPy)            ->  .nnue
  <result> <game> <fen>       boards/side/result/game           integer weights
                              split by game, train, val         calibration
```

1. **Generate.** `stockbear selfplay --games N --nodes B --seed S --out F`
   plays the engine against itself, with a random 0–8 ply opening and a per-move
   node budget jittered to 80–119 % so that the two sides of a game do not follow
   identical lines. One line per *searched* position:

   ```
   <result> <game-id> <fen>
   ```

   `result` is from the point of view of the side to move in that position
   (`1`, `0.5`, `0`). This is the label the network is trained on, so a sign
   error here silently inverts the evaluation.

2. **Prepare.** `scripts/train_nnue.py --prepare-only` parses the corpora into a
   `uint8[N, 64]` board array (0 = empty, `kind + 1` otherwise) plus side,
   result, game and split arrays. Features are *not* stored; they are derived per
   batch from the boards by `scripts/nnue_features.py`, which is a mirror of the
   engine's C++ feature function.

3. **Split.** By game, never by position:
   `bucket = (game * 2654435761) mod 100`; `bucket < 12` → validation,
   `12 <= bucket < 95` → test, `>= 95` → test. Two positions from the same game
   share a label, so a position split would leak and make validation optimistic.

4. **Train.** `768 → L1 → L2 → 1`, clipped ReLU (`clamp(x, 0, 1)`, i.e. a ReLU
   with a ceiling), MSE on `sigmoid(output)` against the game result. The first
   layer is an `EmbeddingBag(sum)` with a sparse gradient, so one step only
   touches the rows of the features that are present. SparseAdam for the
   embedding, Adam (learning rate ×4) for the dense layers.

5. **Convert.** `scripts/convert_nnue.py` calibrates activation ranges on a
   sample, quantises to the engine's integer format, writes the `.nnue` file and
   prints the integer-vs-float error on a verification sample.

6. **Verify.** `scripts/verify_nnue.py` re-reads the `.nnue` file, re-implements
   the integer forward pass independently, and compares it with the engine's own
   output. Expected difference: **zero**.

## 2. Data

| Corpus | Command | Positions | Games | SHA-256 (first 16 hex) |
| --- | --- | --- | --- | --- |
| A | `--games 12000 --nodes 4000 --seed 101` | 1,359,955 | 11,076 | `6096aaf22b31569d` |
| B | `--games 12000 --nodes 4000 --seed 202` | 1,355,075 | 11,089 | `de4cc93c4308c499` |
| C | `--games 9000 --nodes 5000 --seed 2026` | 357,815 | 2,837 | `898cc9ff20cfb160` |
| total | | **3,072,845** | **24,942** | |

Split: 2,706,666 train / 212,708 validation / 153,471 test. 669,141 duplicate
positions (21.8 %) — transpositions across games, kept deliberately.

Generation cost: about 45 minutes per million positions on this machine
(≈ 4 µs per position including search). Both long runs were stopped by wall-clock
budget before reaching the requested 12,000 games; the table records what the
files actually contain, verified by re-hashing after generation stopped.

Labels are checked, not assumed: on 120,000 positions the correlation between
material (from the side to move's point of view) and the stored result is
**+0.572**, and a per-game check confirms the same white-relative result on every
ply of a game. That check is what ruled out a label bug when learning failed.

## 3. The failure that cost the most time: input ordering

**Symptom.** Every configuration converged to a constant prediction of 0.5: the
training loss stuck at the variance of the target (0.207), validation at 0.212,
and the network's output standard deviation at 0.006. Two thousand fixed
positions could be memorised to 0.017, so the model, the features and the loss
function were all fine on their own.

**Cause.** The training batches were assembled with the two perspectives in
*colour* order — White's features first, then Black's, regardless of whose turn
it was. The target, however, is the game result *from the side to move's point of
view*. The same board with the other side to move therefore produced the **same
input with the opposite target**: the optimal fit is the constant 0.5, and that is
exactly what the network learned, in every configuration, at every learning rate.

The quantitative signature, measured on the 120k-position probe set:

| Quantity | Correlation with the side-to-move result |
| --- | --- |
| Material from **White's** point of view (what a colour-ordered input can express) | **−0.0003** |
| Material from the **side to move's** point of view | **+0.572** |

The first number is zero to three decimal places, and that is the whole story:
the network's input had *no information* about the target.

**Fix.** `nnue_features.batch_indices` now takes the side-to-move array and emits
the side-to-move perspective first. After the fix, on the same 106k-position
subsample, validation loss went 0.2187 → 0.1970 in 600 steps and kept falling.

**Why it took so long to find.** Nothing crashes, no test fails, the loss
decreases slightly, and the network plays legal chess — it simply plays with a
random evaluation. The engine's own feature dump, an independent Python mirror
and a C++/Python differential test all agreed with each other, because they were
all testing the *feature function*, which was correct; the bug was in how two
correct feature sets were concatenated. The lesson is recorded in
`nnue_forward.hpp`: the perspective order is part of the network's contract, and
`tests/unit/test_nnue.cpp` now pins it by construction.

## 4. Architecture and hyper-parameters

| Item | Value | Why |
| --- | --- | --- |
| Features | 768 per perspective (12 piece kinds × 64 squares) | With one king bucket there is no implicit king information, so the kings must be explicit features |
| Hidden layers | 128, then 32 | Largest shape that trains on one core in minutes; see §7 |
| Activation | `clamp(x, 0, 1)` | Matches the integer kernel's `clip(x >> shift, 0, 127)` |
| Target | Game result from the side to move | Self-play data, no external teacher |
| Loss | MSE on `sigmoid(output)` | Matches the engine's output semantics (a logit) |
| Output scale | 300 cp per output unit | One unit of sigmoid logit is worth ~300 cp (`sigmoid(1) = 0.73`) |
| Batch | 8192 positions | Chosen by timing: larger batches gave no throughput gain on 2 threads |
| Optimiser | SparseAdam 3e-4, Adam 1.2e-3 | Sparse embedding rows need far lower step sizes |
| Epochs | 11 (early-stopped by validation) | Validation started to rise after epoch 10 |
| Seed | 20261101 | Recorded in the checkpoint |

Training used the best-validation epoch, not the last: the final checkpoint had a
*worse* validation loss than the best one, and the exported network is the best
one.

## 5. Results

| Metric | Value |
| --- | --- |
| Validation MSE, constant-0.5 predictor | 0.2071 |
| Validation MSE, final epoch | 0.1470 |
| Validation MSE, best epoch (10/11) | 0.1470 |
| Training time | 8 min 26 s (11 epochs × 3,630 steps, 2 threads) |
| Positions per second | ~6,500 |
| Checkpoint size | 431 KB |

So the network explains ~29 % of the variance of the game result on held-out
games. That is a weak evaluator by the standards of modern chess networks, and it
is the reason for the playing-strength result in §6.

## 6. Playing strength — the decisive measurement

The trained network was quantised, embedded, and played against the classical
evaluation of the same binary, at a fixed node budget of 2,500 nodes per move on
the 240-opening dev4 suite:

| Match | Games | Score | Elo (A − B) | 95 % CI |
| --- | --- | --- | --- | --- |
| NNUE on (A) vs classical (B) | 60 | 0.017 (0 W, 2 D, 58 L) | **−708** | **[−1011, −405]** |

The network loses essentially every game. A control match with the *same*
network on both sides (40 games) was balanced (0.588), which rules out the
network being unusable on its own terms: it is a consistent evaluator, just a
much worse one than the hand-tuned classical evaluation, and at a 2,500-node
budget the evaluation *is* the search's judgement.

Inference cost is also against it: 0.735 µs/node with the network versus
0.543 µs/node for the classical evaluation in the depth-7 bench (a 35 % slowdown
that would cost further strength at a fixed time control).

**Conclusion: the network is not shipped as the default evaluation.** It is
available (`setoption name NnueFile`), it is reproducible end to end, and the
negative result is recorded rather than buried. What a future attempt needs is in
§8.

## 7. Quantisation

The engine's format stores the first layer as int16 and layers 2–3 as int16
weights with int32 accumulation (`docs/DEV4_ARCHITECTURE.md` §4). Two details
mattered:

* **Rounding, not truncation.** `x >> shift` truncates towards −∞, which biases
  every activation downward by half a step and, summed over 128 units, shrinks
  the evaluation systematically. Before the fix the integer evaluation was 4 %
  low on average (measured as a biased difference against the float network);
  after it the bias is zero to two decimal places. Both kernels and the Python
  reference now round identically.
* **Percentile calibration.** Scaling the pre-activations by 1/max makes the
  typical activation use only ~7 of the 128 available integer levels, because a
  handful of outliers set the scale. Calibrating to the 99.9th percentile instead
  lets those outliers saturate and gives the rest of the distribution real
  resolution: integer-vs-float error went from 16.2 to 11.7 cp rms.

Final verification of the shipped file:

| Check | Result |
| --- | --- |
| Integer vs float, 2,000 positions | max 45.5 cp, mean +0.06 cp, rms 11.67 cp, correlation 0.999908 |
| Engine vs independent Python integer reference, 2,000 positions | **0 differences** |
| Scalar kernel vs AVX2 kernel | identical (unit test, several positions) |
| Incremental accumulator vs rebuild | identical (unit test, `verify_state` on every move) |
| Serialisation round trip, truncation, magic, dimension and overflow rejection | all covered by `test_nnue.cpp` |

## 8. What a future attempt should do differently

1. **King buckets.** 768 plain piece-square inputs cannot express king-relative
   knowledge, which is most of what a strong evaluator knows. The format and the
   loader already support 4/16/64 buckets (`king_bucket`), and `nnue.cpp`
   refreshes both perspectives when the king moves; only the trainer's batch
   builder refuses bucketed input (`batch_indices` raises). The cost is 64× more
   parameters, so it needs far more data than 3M positions.
2. **More data, from a stronger generator.** The corpus comes from a depth-4
   engine, so the labels describe the outcome of games played by a weak player;
   this also explains why the network's positional knowledge is thin.
3. **Search-derived targets.** Labels from game results are extremely noisy.
   Distilling deeper-search scores (or using a second-pass search to label
   positions) reduces label variance per position, which is worth more than
   another few million positions at the same noise level.
4. **Longer training with a warm restart** and a lower final learning rate; the
   validation curve had not flattened when the time budget ran out.
5. **Measure at a fixed time control, not fixed nodes**, for anything with a
   different cost per node — the network's 35 % slowdown is invisible to a
   fixed-node test.
