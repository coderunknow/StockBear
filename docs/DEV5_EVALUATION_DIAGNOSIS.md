# dev5 evaluation diagnosis — evidence versus hypotheses

2026-11-02; preliminary investigation, not a completed causal diagnosis.

## Verified findings

1. Exact dev4 tag defaults to classical evaluation with no embedded network.
   UCI `NNUE=true` advertisement alone does not establish that a network is
   active. Baseline bench explicitly reports `network=none`.
2. The committed experimental model hashes to
   `65ed0ba19626d90fd0a2a20116d3b3d62ba3a4b5759453c58c28ab9ec7a3f1bc`.
   `git show v0.1.0-dev4:benchmarks/training/dev4-l1-128-l2-32.nnue` has the
   same hash. Historical `benchmarks/training/README.md` instead records
   `ba0bc040...`. That historical discrepancy is not repaired by silently
   changing the immutable historical report. Which artifact produced the
   original float-vs-quantized measurements remains unresolved.
3. The actual committed model agrees **exactly on 75,416 positions** with
   `scripts/verify_nnue.py`'s independent integer evaluator, using
   `benchmarks/tuning/positions.epd`. Raw output: `nnue-reference.txt` in the
   dev5 results directory. This tests serialization, feature interpretation,
   side-to-move ordering and integer forward arithmetic on these bytes. It does
   not establish float-training agreement or predictive quality.
4. Exact dev4 CTest passed all 11 entries, including neural tests, incremental
   state verification, loader rejection tests, feature differential, perft and
   UCI integration. This is evidence against a simple pervasive integer/feature
   bug, not proof that every arithmetic or make/unmake case is correct.
5. The original NNUE match raw configuration identifies the binary as dev3,
   requests `NNUE=true`, but does not specify an external NnueFile or record a
   binary/model digest. It may have used the temporary embedded-network build
   described in the history. The record alone cannot prove that the committed
   bytes were tested. New reproduction explicitly sets NnueFile; do not relabel
   historical records as measurements of the newly hashed artifact.
6. Trainer `batch_indices` previously rejected king buckets >1, despite engine
   support. A vectorized 4/16/64-bucket implementation now matches the independent
   scalar Python feature builder across all 64 king squares, both STM orders,
   four bucket configurations and randomly populated boards. These are feature
   tests, not a trained king-conditioned network or an Elo improvement.
7. The trainer's split is by game, but that does **not** prevent positions shared
   between different games from leaking across splits. The historical duplicate
   count compares board arrays only (omits STM/castling/EP), and therefore is not
   itself a measurement of identical network-input or chess-position leakage.
8. Source inspection: selfplay result orientation converts final STM result to
   White and then each record's STM. No sign inversion found in that logic.
   Unfinished ply-capped games are discarded, creating potential selection bias.
   The original corpus/checkpoint are not present here, so label distributions,
   partition overlap, learning curves and float calibration cannot be freshly
   reproduced from their original bytes.

## Competing explanations and discriminating experiments

| Question | Current evidence | Required experiment |
|---|---|---|
| Sign/perspective bug? | Integer engine/reference agree; STM ordering is present in trainer | Independent teacher/material probes, float checkpoint comparison, mirrored input/output tests |
| Quantization/overflow? | Loader and reference tests pass for actual file | Regenerate float checkpoint; quantile-wise float/integer and activation saturation measurements on held-out games |
| Wrong cp/WDL scale? | Trainer uses sigmoid(output), 300 cp/output; correctness does not calibrate chess strength | Fit scale only on training/validation, compare held-out Brier/log-loss and fixed-node matches |
| Weak/noisy labels? | Documented shallow selfplay outcome targets; original raw corpus absent | Same games/partitions, teacher-search versus outcome versus blended labels, multiple seeds |
| Insufficient representation? | Single bucket cannot directly index relative king/piece interactions | Small bucketed and HalfKP-family pilot at matched data/training budgets, then fixed-time matches |
| Overfit/leakage? | Game split permits cross-game transpositions | Canonical-input and position overlap audit, opening/source grouped partitions, near-duplicate analysis |
| Excessive inference cost? | Historical report says slowdown; new profiling not performed | Isolated inference/rebuild/update timings, single-process bench, real fixed-time comparisons |
| Search interaction? | Search pruning assumes cp-like scores | Scale sweep and isolated pruning ablations on validation openings; independent confirmation |

The historical assertion that architecture/data are *the* cause is too strong:
these are plausible hypotheses, not isolated causal results. Increasing model
size or corpus size is not yet justified. The original −708 Elo remains a
historical reported result, not a verified result for this turn's reproduction.
